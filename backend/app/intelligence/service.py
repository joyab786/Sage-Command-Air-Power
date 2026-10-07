"""
SageCommand Air Power System (Aero) — Subsystem Intelligence Service.
Coordinates anomaly detection, statistical baselines, active anomaly correlation/deduplication,
root-cause diagnostic synthesis, and actionable maintenance recommendations.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, desc, func, and_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.models import (
    AircraftModel,
    AnomalyModel,
    utc_now,
)
from app.telemetry.models import NormalizedTelemetry, QualityStatus
from app.digital_twin.models import AircraftTwinState, TwinSubsystemType
from app.digital_twin.service import default_digital_twin_service
from app.intelligence.models import (
    Anomaly,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    Diagnosis,
    MaintenanceRecommendation,
    RecommendationPriority,
)
from app.intelligence.anomaly.detectors import CompositeAnomalyDetector, default_composite_detector
from app.intelligence.diagnosis.root_cause import RootCauseDiagnosisEngine, default_diagnosis_engine
from app.intelligence.maintenance import (
    MaintenanceRecommendationEngine,
    default_maintenance_engine,
)

logger = get_logger(__name__)

SEVERITY_RANKS = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime instance is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class IntelligenceService:
    """
    Subsystem Intelligence Service (SIH MVP).
    Orchestrates deterministic detection, correlation/deduplication,
    root-cause diagnosis, and maintenance advisory intelligence.
    """

    def __init__(
        self,
        detector: Optional[CompositeAnomalyDetector] = None,
        diagnosis_engine: Optional[RootCauseDiagnosisEngine] = None,
        maintenance_engine: Optional[MaintenanceRecommendationEngine] = None,
        correlation_window_seconds: float = 300.0,
    ) -> None:
        self.detector = detector or default_composite_detector
        self.diagnosis_engine = diagnosis_engine or default_diagnosis_engine
        self.maintenance_engine = maintenance_engine or default_maintenance_engine
        self.correlation_window_seconds = correlation_window_seconds
        self._latest_diagnoses: Dict[str, Diagnosis] = {}
        self._latest_recommendations: Dict[str, List[MaintenanceRecommendation]] = {}

    def _record_to_schema(self, record: AnomalyModel) -> Anomaly:
        """Converts an AnomalyModel DB record into a Pydantic Anomaly schema."""
        # Convert subsystem enum safely
        try:
            subsystem = TwinSubsystemType(record.subsystem)
        except (ValueError, KeyError):
            subsystem = TwinSubsystemType.PROPULSION

        # Convert anomaly type safely
        try:
            anomaly_type = AnomalyType(record.anomaly_type)
        except (ValueError, KeyError):
            anomaly_type = AnomalyType.THERMAL_ANOMALY

        # Convert severity safely
        try:
            severity = AnomalySeverity(record.severity)
        except (ValueError, KeyError):
            severity = AnomalySeverity.MEDIUM

        # Convert status safely
        try:
            status = AnomalyStatus(record.status)
        except (ValueError, KeyError):
            status = AnomalyStatus.NEW

        return Anomaly(
            anomaly_id=record.anomaly_id,
            aircraft_id=record.aircraft_id,
            flight_id=record.flight_id,
            timestamp=ensure_utc(record.timestamp),
            subsystem=subsystem,
            anomaly_type=anomaly_type,
            severity=severity,
            status=status,
            confidence=record.confidence,
            detector=record.detector,
            signal=record.signal,
            observed_value=record.observed_value,
            expected_range=record.expected_range,
            deviation=record.deviation,
            description=record.description,
            evidence=record.evidence if record.evidence is not None else [],
            occurrence_count=record.occurrence_count,
            first_detected_at=ensure_utc(record.first_detected_at),
            last_detected_at=ensure_utc(record.last_detected_at),
            resolved_at=ensure_utc(record.resolved_at),
        )

    def process_telemetry(
        self,
        db: Session,
        telemetry: NormalizedTelemetry,
    ) -> Dict:
        """
        Processes normalized telemetry through the intelligence pipeline.
        1. Skips INVALID telemetry (safety boundary).
        2. Retrieves the current digital twin state.
        3. Executes composite anomaly detection.
        4. Correlates and deduplicates detections with active anomalies.
        5. Performs root-cause diagnostic synthesis.
        6. Generates decision-support maintenance recommendations.
        """
        if telemetry.quality_status == QualityStatus.INVALID:
            logger.info(
                f"Skipping intelligence processing for INVALID telemetry '{telemetry.observation_id}'"
            )
            return {
                "aircraft_id": telemetry.aircraft_id,
                "anomalies_detected": 0,
                "active_anomalies": 0,
                "diagnosis": None,
                "recommendations": [],
            }

        # Verify aircraft exists
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == telemetry.aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            logger.warning(
                f"Aircraft '{telemetry.aircraft_id}' not found for intelligence processing"
            )
            return {
                "aircraft_id": telemetry.aircraft_id,
                "anomalies_detected": 0,
                "active_anomalies": 0,
                "diagnosis": None,
                "recommendations": [],
            }

        # 1. Fetch current digital twin state
        twin_state: Optional[AircraftTwinState] = None
        try:
            twin_state = default_digital_twin_service.get_current_state(db, telemetry.aircraft_id)
        except Exception as exc:
            logger.debug(f"Could not retrieve twin state for {telemetry.aircraft_id}: {exc}")

        # 2. Execute anomaly detectors
        detected = self.detector.detect_all(telemetry, twin_state)

        # 3. Correlate / Deduplicate with active database records
        t_obs = ensure_utc(telemetry.timestamp)
        active_records = list(
            db.execute(
                select(AnomalyModel).where(
                    AnomalyModel.aircraft_id == telemetry.aircraft_id,
                    AnomalyModel.status.in_(["NEW", "ACKNOWLEDGED"]),
                )
            ).scalars().all()
        )

        for anomaly in detected:
            # Find an existing active record with matching subsystem, type, and signal
            match = next(
                (
                    rec
                    for rec in active_records
                    if rec.subsystem == anomaly.subsystem.value
                    and rec.anomaly_type == anomaly.anomaly_type.value
                    and rec.signal == anomaly.signal
                ),
                None,
            )

            if match is not None:
                match_last_seen = ensure_utc(match.last_detected_at)
                elapsed = (t_obs - match_last_seen).total_seconds() if match_last_seen else 0.0

                if elapsed <= self.correlation_window_seconds:
                    # Update active anomaly
                    match.occurrence_count += 1
                    match.last_detected_at = t_obs
                    match.observed_value = anomaly.observed_value
                    match.deviation = anomaly.deviation
                    # Persistent observations gradually increase confidence up to 0.98
                    match.confidence = min(0.98, round(match.confidence + 0.02, 3))

                    # If incoming severity is higher, upgrade severity
                    new_rank = SEVERITY_RANKS.get(anomaly.severity.value, 0)
                    cur_rank = SEVERITY_RANKS.get(match.severity, 0)
                    if new_rank > cur_rank:
                        match.severity = anomaly.severity.value
                        match.description = anomaly.description

                    # Append novel evidence
                    if isinstance(anomaly.evidence, list):
                        existing_evidence = list(match.evidence) if isinstance(match.evidence, list) else []
                        for ev in anomaly.evidence:
                            if ev not in existing_evidence:
                                existing_evidence.append(ev)
                        match.evidence = existing_evidence[-10:]
                    elif isinstance(anomaly.evidence, dict):
                        match.evidence = anomaly.evidence

                    match.updated_at = utc_now()
                    continue

            # If no active correlation match or outside window, create new record
            new_record = AnomalyModel(
                anomaly_id=anomaly.anomaly_id,
                aircraft_id=anomaly.aircraft_id,
                flight_id=anomaly.flight_id,
                timestamp=anomaly.timestamp,
                subsystem=anomaly.subsystem.value,
                anomaly_type=anomaly.anomaly_type.value,
                severity=anomaly.severity.value,
                status=anomaly.status.value,
                confidence=anomaly.confidence,
                detector=anomaly.detector,
                signal=anomaly.signal,
                observed_value=anomaly.observed_value,
                expected_range=anomaly.expected_range,
                deviation=anomaly.deviation,
                description=anomaly.description,
                evidence=anomaly.evidence,
                occurrence_count=1,
                first_detected_at=t_obs,
                last_detected_at=t_obs,
                resolved_at=None,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(new_record)
            active_records.append(new_record)

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning(f"Could not persist anomaly record: {exc}")

        # 4. Form complete active anomalies list for diagnosis
        active_anomalies: List[Anomaly] = [
            self._record_to_schema(rec)
            for rec in active_records
            if rec.status in ["NEW", "ACKNOWLEDGED"]
        ]

        # 5. Diagnostic synthesis
        diagnosis = self.diagnosis_engine.diagnose(
            active_anomalies=active_anomalies,
            twin_state=twin_state,
            telemetry=telemetry,
            aircraft_id=telemetry.aircraft_id,
        )
        self._latest_diagnoses[telemetry.aircraft_id] = diagnosis

        # 6. Maintenance recommendation
        recommendations = self.maintenance_engine.recommend(
            anomalies=active_anomalies,
            diagnosis=diagnosis,
            twin_state=twin_state,
            aircraft_id=telemetry.aircraft_id,
        )
        self._latest_recommendations[telemetry.aircraft_id] = recommendations

        return {
            "aircraft_id": telemetry.aircraft_id,
            "anomalies_detected": len(detected),
            "active_anomalies": len(active_anomalies),
            "diagnosis": diagnosis,
            "recommendations": recommendations,
        }

    def get_anomalies(
        self,
        db: Session,
        aircraft_id: str,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        subsystem: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Anomaly], int]:
        """Queries historical or active anomalies for a given aircraft with filtering."""
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id},
            )

        stmt = select(AnomalyModel).where(AnomalyModel.aircraft_id == aircraft_id)

        if severity:
            stmt = stmt.where(AnomalyModel.severity == severity.upper())
        if status:
            stmt = stmt.where(AnomalyModel.status == status.upper())
        if subsystem:
            stmt = stmt.where(AnomalyModel.subsystem == subsystem.upper())
        if from_time:
            stmt = stmt.where(AnomalyModel.timestamp >= ensure_utc(from_time))
        if to_time:
            stmt = stmt.where(AnomalyModel.timestamp <= ensure_utc(to_time))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        paged_stmt = stmt.order_by(desc(AnomalyModel.timestamp)).limit(limit).offset(offset)
        records = db.execute(paged_stmt).scalars().all()

        return [self._record_to_schema(r) for r in records], total

    def get_anomaly(
        self,
        db: Session,
        aircraft_id: str,
        anomaly_id: str,
    ) -> Anomaly:
        """Retrieves a single anomaly record by aircraft and anomaly ID."""
        record = db.execute(
            select(AnomalyModel).where(
                AnomalyModel.aircraft_id == aircraft_id,
                AnomalyModel.anomaly_id == anomaly_id,
            )
        ).scalar_one_or_none()

        if not record:
            raise NotFoundError(
                f"Anomaly '{anomaly_id}' for aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id, "anomaly_id": anomaly_id},
            )

        return self._record_to_schema(record)

    def acknowledge_anomaly(
        self,
        db: Session,
        aircraft_id: str,
        anomaly_id: str,
    ) -> Anomaly:
        """
        Acknowledges an active anomaly.
        Lifecycle rule: NEW -> ACKNOWLEDGED.
        Reject: RESOLVED -> ACKNOWLEDGED.
        """
        record = db.execute(
            select(AnomalyModel).where(
                AnomalyModel.aircraft_id == aircraft_id,
                AnomalyModel.anomaly_id == anomaly_id,
            )
        ).scalar_one_or_none()

        if not record:
            raise NotFoundError(
                f"Anomaly '{anomaly_id}' for aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id, "anomaly_id": anomaly_id},
            )

        if record.status == AnomalyStatus.RESOLVED.value:
            raise ValidationError(
                f"Cannot acknowledge anomaly '{anomaly_id}' because it is already RESOLVED",
                details={"status": record.status},
            )

        if record.status != AnomalyStatus.ACKNOWLEDGED.value:
            record.status = AnomalyStatus.ACKNOWLEDGED.value
            record.updated_at = utc_now()
            db.commit()

        return self._record_to_schema(record)

    def resolve_anomaly(
        self,
        db: Session,
        aircraft_id: str,
        anomaly_id: str,
    ) -> Anomaly:
        """
        Resolves an active anomaly through explicit operator action.
        Lifecycle rule: NEW -> RESOLVED or ACKNOWLEDGED -> RESOLVED.
        """
        record = db.execute(
            select(AnomalyModel).where(
                AnomalyModel.aircraft_id == aircraft_id,
                AnomalyModel.anomaly_id == anomaly_id,
            )
        ).scalar_one_or_none()

        if not record:
            raise NotFoundError(
                f"Anomaly '{anomaly_id}' for aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id, "anomaly_id": anomaly_id},
            )

        if record.status != AnomalyStatus.RESOLVED.value:
            record.status = AnomalyStatus.RESOLVED.value
            record.resolved_at = utc_now()
            record.updated_at = utc_now()
            db.commit()

        return self._record_to_schema(record)

    def get_latest_diagnosis(
        self,
        db: Session,
        aircraft_id: str,
    ) -> Diagnosis:
        """
        Retrieves the latest synthesized diagnostic assessment for an aircraft.
        If not cached in memory, re-synthesizes from active persisted anomalies.
        """
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id},
            )

        if aircraft_id in self._latest_diagnoses:
            return self._latest_diagnoses[aircraft_id]

        # Re-synthesize from active anomalies
        active_records = db.execute(
            select(AnomalyModel).where(
                AnomalyModel.aircraft_id == aircraft_id,
                AnomalyModel.status.in_(["NEW", "ACKNOWLEDGED"]),
            )
        ).scalars().all()
        active_anomalies = [self._record_to_schema(r) for r in active_records]

        twin_state: Optional[AircraftTwinState] = None
        try:
            twin_state = default_digital_twin_service.get_current_state(db, aircraft_id)
        except Exception:
            pass

        diagnosis = self.diagnosis_engine.diagnose(
            active_anomalies=active_anomalies,
            twin_state=twin_state,
            telemetry=None,
            aircraft_id=aircraft_id,
        )
        self._latest_diagnoses[aircraft_id] = diagnosis
        return diagnosis

    def get_maintenance_recommendations(
        self,
        db: Session,
        aircraft_id: str,
    ) -> List[MaintenanceRecommendation]:
        """
        Retrieves current actionable maintenance recommendations for an aircraft.
        If not cached in memory, re-evaluates against current diagnosis and twin health.
        """
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id},
            )

        if aircraft_id in self._latest_recommendations:
            return self._latest_recommendations[aircraft_id]

        diagnosis = self.get_latest_diagnosis(db, aircraft_id)

        twin_state: Optional[AircraftTwinState] = None
        try:
            twin_state = default_digital_twin_service.get_current_state(db, aircraft_id)
        except Exception:
            pass

        active_records = db.execute(
            select(AnomalyModel).where(
                AnomalyModel.aircraft_id == aircraft_id,
                AnomalyModel.status.in_(["NEW", "ACKNOWLEDGED"]),
            )
        ).scalars().all()
        active_anomalies = [self._record_to_schema(r) for r in active_records]

        recommendations = self.maintenance_engine.recommend(
            anomalies=active_anomalies,
            diagnosis=diagnosis,
            twin_state=twin_state,
            aircraft_id=aircraft_id,
        )
        self._latest_recommendations[aircraft_id] = recommendations
        return recommendations


# Default singleton instance
default_intelligence_service = IntelligenceService()
