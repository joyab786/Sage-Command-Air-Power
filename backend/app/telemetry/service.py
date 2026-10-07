"""
SageCommand Air Power System (Aero) — Telemetry Service.
Coordinates the end-to-end ingestion pipeline:
Validation → Normalization → Quality Evaluation → Envelope Evaluation → In-Memory Buffer → SQLite Persistence.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.exceptions import NotFoundError, ValidationError, AeroException
from app.core.logging import get_logger
from app.db.models import TelemetryRecordModel, AircraftModel, utc_now
from app.services.aircraft_service import AircraftService
from app.telemetry.models import (
    TelemetryInput,
    NormalizedTelemetry,
    QualityStatus,
    EnvelopeStatus,
    QualityAssessmentResult,
    EnvelopeAssessmentResult,
    TelemetryIngestResult,
    BatchIngestRequest,
    BatchIngestResult,
    DemoGenerateRequest,
)
from app.telemetry.normalizer import TelemetryNormalizer
from app.telemetry.quality import QualityEvaluator
from app.telemetry.envelope import FlightEnvelopeChecker
from app.telemetry.buffer import default_telemetry_buffer, TelemetryBuffer
from app.telemetry.generator import SyntheticFlightGenerator

logger = get_logger(__name__)


class TelemetryService:
    """Orchestration service for the Aero Telemetry Data Fabric."""

    def __init__(
        self,
        buffer: Optional[TelemetryBuffer] = None,
        envelope_checker: Optional[FlightEnvelopeChecker] = None,
    ):
        self.buffer = buffer or default_telemetry_buffer
        self.envelope_checker = envelope_checker or FlightEnvelopeChecker()

    def ingest_observation(
        self, db: Session, raw_input: TelemetryInput, persist: bool = True
    ) -> TelemetryIngestResult:
        """
        Processes a single incoming telemetry frame through the data fabric pipeline:
        1. Validate target aircraft exists.
        2. Input pre-validation (sanity, timestamps, identity).
        3. Normalization to standard SI units.
        4. Post-normalization quality evaluation.
        5. Flight envelope checking (caution & exceedance).
        6. Append to in-memory ring buffer.
        7. Persist to relational storage.
        """
        obs_id = raw_input.observation_id or f"obs_{utc_now().strftime('%Y%m%d%H%M%S%f')[:18]}"

        # 1. Verify target aircraft exists in authoritative fleet registry
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == raw_input.aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Cannot ingest telemetry: aircraft '{raw_input.aircraft_id}' not found in registry",
                details={"aircraft_id": raw_input.aircraft_id},
            )

        # 2. Input pre-inspection
        input_quality = QualityEvaluator.evaluate_input(raw_input)
        if input_quality.status == QualityStatus.INVALID:
            logger.warning(
                f"Rejected invalid telemetry input for {raw_input.aircraft_id}: {input_quality.reasons}"
            )
            return TelemetryIngestResult(
                accepted=False,
                observation_id=obs_id,
                aircraft_id=raw_input.aircraft_id,
                quality=input_quality,
                envelope=EnvelopeAssessmentResult(status=EnvelopeStatus.WITHIN_ENVELOPE),
                normalized=None,
                persisted=False,
                buffered=False,
                warnings=input_quality.warnings,
            )

        # 3. Normalization
        try:
            normalized = TelemetryNormalizer.normalize(raw_input)
            normalized.observation_id = obs_id
        except ValueError as exc:
            logger.warning(f"Normalization failed for {raw_input.aircraft_id}: {exc}")
            failed_quality = QualityAssessmentResult(
                status=QualityStatus.INVALID,
                reasons=[str(exc)],
                warnings=[],
                metrics_evaluated=1,
            )
            return TelemetryIngestResult(
                accepted=False,
                observation_id=obs_id,
                aircraft_id=raw_input.aircraft_id,
                quality=failed_quality,
                envelope=EnvelopeAssessmentResult(status=EnvelopeStatus.WITHIN_ENVELOPE),
                normalized=None,
                persisted=False,
                buffered=False,
            )

        # 4. Post-normalization quality evaluation
        post_quality = QualityEvaluator.evaluate_normalized(normalized)
        if post_quality.status == QualityStatus.INVALID:
            logger.warning(
                f"Rejected unphysical normalized telemetry for {raw_input.aircraft_id}: {post_quality.reasons}"
            )
            return TelemetryIngestResult(
                accepted=False,
                observation_id=obs_id,
                aircraft_id=raw_input.aircraft_id,
                quality=post_quality,
                envelope=EnvelopeAssessmentResult(status=EnvelopeStatus.WITHIN_ENVELOPE),
                normalized=None,
                persisted=False,
                buffered=False,
            )

        # 5. Envelope checking
        envelope_res = self.envelope_checker.evaluate(normalized)

        # Update metadata flags on normalized model
        normalized.quality_status = (
            QualityStatus.DEGRADED
            if (input_quality.status == QualityStatus.DEGRADED or post_quality.status == QualityStatus.DEGRADED)
            else QualityStatus.VALID
        )
        normalized.envelope_status = envelope_res.status

        # 6. Buffer ingestion
        self.buffer.append(normalized)
        buffered = True

        # 7. Persistent relational commit
        persisted = False
        if persist:
            record = TelemetryRecordModel(
                record_id=normalized.observation_id,
                aircraft_id=normalized.aircraft_id,
                flight_id=normalized.flight_id,
                timestamp=normalized.timestamp,
                altitude_m=normalized.altitude_m,
                airspeed_mps=normalized.airspeed_mps,
                mach=normalized.mach,
                g_load=normalized.g_load,
                fuel_flow_kg_h=normalized.fuel_flow_kg_h,
                engine_temperature_c=normalized.engine_temperature_c,
                engine_pressure_kpa=normalized.engine_pressure_kpa,
                vibration_ips=normalized.vibration_ips,
                control_surface_angle_deg=normalized.control_surface_angle_deg,
                quality=normalized.quality_status.value,
                envelope_status=normalized.envelope_status.value,
                source=normalized.source,
                raw_units=normalized.raw_units,
                created_at=utc_now(),
            )
            db.add(record)
            db.commit()
            persisted = True

            # 8. Digital Twin State Estimation Update
            try:
                from app.digital_twin.service import default_digital_twin_service
                default_digital_twin_service.process_telemetry(db, normalized)
            except Exception as dt_exc:
                logger.warning(
                    f"Digital twin state update advisory for aircraft '{normalized.aircraft_id}': {dt_exc}"
                )

            # 9. Subsystem Intelligence & Anomaly Detection Processing
            try:
                from app.intelligence.service import default_intelligence_service
                default_intelligence_service.process_telemetry(db, normalized)
            except Exception as intel_exc:
                logger.warning(
                    f"Subsystem intelligence processing advisory for aircraft '{normalized.aircraft_id}': {intel_exc}"
                )

        combined_warnings = list(set(input_quality.warnings + post_quality.warnings))
        return TelemetryIngestResult(
            accepted=True,
            observation_id=normalized.observation_id,
            aircraft_id=normalized.aircraft_id,
            quality=QualityAssessmentResult(
                status=normalized.quality_status,
                reasons=[],
                warnings=combined_warnings,
                metrics_evaluated=input_quality.metrics_evaluated + post_quality.metrics_evaluated,
            ),
            envelope=envelope_res,
            normalized=normalized,
            persisted=persisted,
            buffered=buffered,
            warnings=combined_warnings,
        )

    def ingest_batch(
        self, db: Session, request: BatchIngestRequest, persist: bool = True
    ) -> BatchIngestResult:
        """Processes a batch of incoming telemetry frames."""
        results: List[TelemetryIngestResult] = []
        accepted = 0
        rejected = 0

        for frame in request.observations:
            try:
                res = self.ingest_observation(db, frame, persist=persist)
                results.append(res)
                if res.accepted:
                    accepted += 1
                else:
                    rejected += 1
            except NotFoundError as err:
                rejected += 1
                results.append(
                    TelemetryIngestResult(
                        accepted=False,
                        observation_id=frame.observation_id or "unknown",
                        aircraft_id=frame.aircraft_id,
                        quality=QualityAssessmentResult(
                            status=QualityStatus.INVALID,
                            reasons=[str(err.message)],
                        ),
                        envelope=EnvelopeAssessmentResult(status=EnvelopeStatus.WITHIN_ENVELOPE),
                        persisted=False,
                        buffered=False,
                    )
                )

        return BatchIngestResult(
            total_received=len(request.observations),
            total_accepted=accepted,
            total_rejected=rejected,
            results=results,
        )

    def get_recent(
        self, db: Session, limit: int = 50, aircraft_id: Optional[str] = None
    ) -> List[NormalizedTelemetry]:
        """
        Queries recent telemetry records. Falls back to database if buffer is depleted.
        """
        # First check in-memory buffer
        buffered = self.buffer.get_recent(limit=limit, aircraft_id=aircraft_id)
        if len(buffered) >= limit:
            return buffered[:limit]

        # Query database for authoritative historical records
        query = select(TelemetryRecordModel).order_by(desc(TelemetryRecordModel.timestamp))
        if aircraft_id:
            query = query.where(TelemetryRecordModel.aircraft_id == aircraft_id)
        query = query.limit(limit)

        records = db.execute(query).scalars().all()
        return [
            NormalizedTelemetry(
                observation_id=rec.record_id,
                timestamp=rec.timestamp,
                aircraft_id=rec.aircraft_id,
                flight_id=rec.flight_id,
                altitude_m=rec.altitude_m,
                airspeed_mps=rec.airspeed_mps,
                mach=rec.mach,
                g_load=rec.g_load,
                fuel_flow_kg_h=rec.fuel_flow_kg_h,
                engine_temperature_c=rec.engine_temperature_c,
                engine_pressure_kpa=rec.engine_pressure_kpa,
                vibration_ips=rec.vibration_ips,
                control_surface_angle_deg=rec.control_surface_angle_deg,
                quality_status=QualityStatus(rec.quality),
                envelope_status=EnvelopeStatus(rec.envelope_status),
                source=rec.source,
                raw_units=rec.raw_units or {},
            )
            for rec in records
        ]

    def get_for_aircraft(
        self, db: Session, aircraft_id: str, limit: int = 50, offset: int = 0
    ) -> List[NormalizedTelemetry]:
        """
        Retrieves chronologically sorted historical telemetry frames for a specific aircraft.
        """
        # Verify aircraft exists
        AircraftService.get_aircraft(db, aircraft_id)

        query = (
            select(TelemetryRecordModel)
            .where(TelemetryRecordModel.aircraft_id == aircraft_id)
            .order_by(desc(TelemetryRecordModel.timestamp))
            .offset(offset)
            .limit(limit)
        )
        records = db.execute(query).scalars().all()
        return [
            NormalizedTelemetry(
                observation_id=rec.record_id,
                timestamp=rec.timestamp,
                aircraft_id=rec.aircraft_id,
                flight_id=rec.flight_id,
                altitude_m=rec.altitude_m,
                airspeed_mps=rec.airspeed_mps,
                mach=rec.mach,
                g_load=rec.g_load,
                fuel_flow_kg_h=rec.fuel_flow_kg_h,
                engine_temperature_c=rec.engine_temperature_c,
                engine_pressure_kpa=rec.engine_pressure_kpa,
                vibration_ips=rec.vibration_ips,
                control_surface_angle_deg=rec.control_surface_angle_deg,
                quality_status=QualityStatus(rec.quality),
                envelope_status=EnvelopeStatus(rec.envelope_status),
                source=rec.source,
                raw_units=rec.raw_units or {},
            )
            for rec in records
        ]

    def generate_and_ingest_demo(
        self, db: Session, request: DemoGenerateRequest
    ) -> BatchIngestResult:
        """
        Generates and ingests synthetic flight telemetry for a given demonstration profile.
        """
        # Verify aircraft exists
        AircraftService.get_aircraft(db, request.aircraft_id)

        generator = SyntheticFlightGenerator(seed=request.seed)
        frames = generator.generate_flight_sequence(
            aircraft_id=request.aircraft_id,
            profile=request.profile,
            count=request.count,
            flight_id=request.flight_id,
        )
        batch_req = BatchIngestRequest(observations=frames)
        return self.ingest_batch(db, batch_req, persist=True)


default_telemetry_service = TelemetryService()
