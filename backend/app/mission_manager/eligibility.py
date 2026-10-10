"""
SageCommand Air Power System (Aero) — Aircraft Eligibility Evaluation Engine.
Provides deterministic, explainable multi-signal airframe qualification against proposed sorties.
Evaluates lifecycle status, type requirements, authoritative readiness, active anomalies,
scheduled maintenance conflicts, and prognostic Remaining Useful Life (RUL) with semantic safeguards.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    AnomalyModel,
    MaintenanceEventModel,
    PrognosticRecordModel,
    ReadinessAssessmentModel,
)
from app.mission_manager.models import (
    AircraftEligibilityReport,
    EligibilityEvidence,
    EligibilityStatus,
    ProposedSortie,
)


class AircraftEligibilityEvaluator:
    """
    Deterministic rule engine evaluating aircraft readiness and lifing constraints for sortie commitments.
    """

    MIN_TWIN_HEALTH_THRESHOLD: float = 50.0
    MAX_TWIN_WEAR_THRESHOLD: float = 0.90
    RUL_SAFETY_BUFFER_HOURS: float = 5.0

    @classmethod
    def evaluate_aircraft(
        cls,
        db: Session,
        aircraft_id: str,
        sortie: Optional[ProposedSortie] = None,
    ) -> AircraftEligibilityReport:
        """
        Evaluates an aircraft against general airworthiness and specific sortie operational parameters.
        Returns a structured, explainable AircraftEligibilityReport.
        """
        # 1. Authoritative aircraft existence check
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found for mission eligibility evaluation",
                details={"aircraft_id": aircraft_id},
            )

        reasons: List[str] = []
        is_ineligible = False
        is_insufficient_evidence = False
        requires_review = False

        # ---------------------------------------------------------------------
        # 2. Lifecycle Status Rule
        # ---------------------------------------------------------------------
        lifecycle_status = str(aircraft.status)
        if lifecycle_status != "ACTIVE":
            is_ineligible = True
            reasons.append(
                f"Airframe operational lifecycle status is '{lifecycle_status}', which precludes mission assignment."
            )

        # ---------------------------------------------------------------------
        # 3. Aircraft Type Matching Rule
        # ---------------------------------------------------------------------
        if sortie and sortie.required_aircraft_type:
            if aircraft.aircraft_type.strip().lower() != sortie.required_aircraft_type.strip().lower():
                is_ineligible = True
                reasons.append(
                    f"Aircraft type '{aircraft.aircraft_type}' does not match sortie requirement '{sortie.required_aircraft_type}'."
                )

        # ---------------------------------------------------------------------
        # 4. Authoritative Readiness Assessment Rule
        # ---------------------------------------------------------------------
        latest_readiness = db.execute(
            select(ReadinessAssessmentModel)
            .where(ReadinessAssessmentModel.aircraft_id == aircraft_id)
            .order_by(desc(ReadinessAssessmentModel.assessed_at))
            .limit(1)
        ).scalar_one_or_none()

        readiness_status: Optional[str] = None
        readiness_confidence: Optional[float] = None

        if not latest_readiness:
            # Missing readiness evidence must not silently mean ready!
            is_insufficient_evidence = True
            reasons.append(
                "Missing authoritative readiness assessment record; cannot verify mission capability without evaluation."
            )
        else:
            readiness_status = str(latest_readiness.readiness_status)
            readiness_confidence = latest_readiness.confidence

            if readiness_status == "NMC":
                is_ineligible = True
                r_notes = f": {', '.join(latest_readiness.reasons)}" if latest_readiness.reasons else ""
                reasons.append(f"Authoritative readiness status is NMC (Non-Mission Capable){r_notes}.")
            elif readiness_status == "PMC":
                requires_review = True
                reasons.append(
                    "Aircraft readiness is PMC (Partially Mission Capable); requires flight lead/commander clearance."
                )

            if readiness_confidence is not None and readiness_confidence < 0.60:
                requires_review = True
                reasons.append(
                    f"Readiness assessment confidence is low ({readiness_confidence:.2f}); telemetry backing is uncertain."
                )

        # ---------------------------------------------------------------------
        # 5. Maintenance Conflict Check
        # ---------------------------------------------------------------------
        open_maintenance = db.execute(
            select(MaintenanceEventModel).where(
                and_(
                    MaintenanceEventModel.aircraft_id == aircraft_id,
                    MaintenanceEventModel.status.in_(["OPEN", "IN_PROGRESS", "SCHEDULED"]),
                )
            )
        ).scalars().all()

        maint_conflict_ids: List[str] = []
        for me in open_maintenance:
            if me.status == "IN_PROGRESS":
                is_ineligible = True
                maint_conflict_ids.append(me.maintenance_event_id)
                reasons.append(
                    f"Maintenance event '{me.maintenance_event_id}' ({me.description}) is currently IN_PROGRESS."
                )
            elif sortie and me.scheduled_at:
                sched_dt = me.scheduled_at if me.scheduled_at.tzinfo else me.scheduled_at.replace(tzinfo=timezone.utc)
                s_start = sortie.start_time if sortie.start_time.tzinfo else sortie.start_time.replace(tzinfo=timezone.utc)
                s_end = sortie.end_time if sortie.end_time.tzinfo else sortie.end_time.replace(tzinfo=timezone.utc)
                # Check scheduled window overlap with sortie window
                if s_start <= sched_dt <= s_end:
                    is_ineligible = True
                    maint_conflict_ids.append(me.maintenance_event_id)
                    reasons.append(
                        f"Scheduled maintenance event '{me.maintenance_event_id}' overlaps planned sortie window."
                    )

        # ---------------------------------------------------------------------
        # 6. Active Anomalies Check (Phase 5 Intelligence)
        # ---------------------------------------------------------------------
        active_anomalies = db.execute(
            select(AnomalyModel).where(
                and_(
                    AnomalyModel.aircraft_id == aircraft_id,
                    AnomalyModel.status.in_(["NEW", "ACKNOWLEDGED"]),
                )
            )
        ).scalars().all()

        crit_count = sum(1 for a in active_anomalies if a.severity == "CRITICAL")
        high_count = sum(1 for a in active_anomalies if a.severity == "HIGH")

        if crit_count > 0:
            is_ineligible = True
            crit_ids = [a.anomaly_id for a in active_anomalies if a.severity == "CRITICAL"]
            reasons.append(
                f"Airframe has {crit_count} active CRITICAL anomal{'y' if crit_count == 1 else 'ies'} ({', '.join(crit_ids)})."
            )
        elif high_count > 0:
            requires_review = True
            high_ids = [a.anomaly_id for a in active_anomalies if a.severity == "HIGH"]
            reasons.append(
                f"Airframe has {high_count} active HIGH severity anomal{'y' if high_count == 1 else 'ies'} ({', '.join(high_ids)})."
            )

        # ---------------------------------------------------------------------
        # 7. Digital Twin State & Telemetry Quality
        # ---------------------------------------------------------------------
        twin_state = db.execute(
            select(AircraftTwinStateModel)
            .where(AircraftTwinStateModel.aircraft_id == aircraft_id)
            .order_by(desc(AircraftTwinStateModel.timestamp))
            .limit(1)
        ).scalar_one_or_none()

        health_score: Optional[float] = None
        wear_index: Optional[float] = None
        data_quality: str = "VALID"

        if twin_state:
            health_score = twin_state.health_score
            wear_index = twin_state.wear_index
            data_quality = twin_state.data_quality or "VALID"

            if health_score < cls.MIN_TWIN_HEALTH_THRESHOLD:
                is_ineligible = True
                reasons.append(
                    f"Digital twin overall health score ({health_score:.1f}) is below minimum flight threshold ({cls.MIN_TWIN_HEALTH_THRESHOLD:.0f})."
                )
            if wear_index > cls.MAX_TWIN_WEAR_THRESHOLD:
                requires_review = True
                reasons.append(
                    f"Digital twin wear index ({wear_index:.2f}) exceeds advisory threshold ({cls.MAX_TWIN_WEAR_THRESHOLD:.2f})."
                )
            if data_quality != "VALID":
                requires_review = True
                reasons.append(
                    f"Recent telemetry data quality is '{data_quality}', indicating degraded sensor reliability."
                )
        else:
            requires_review = True
            reasons.append("Digital twin state record is absent; real-time health estimation unavailable.")

        # ---------------------------------------------------------------------
        # 8. Prognostics & RUL Safeguard
        # ---------------------------------------------------------------------
        latest_prog = db.execute(
            select(PrognosticRecordModel)
            .where(PrognosticRecordModel.aircraft_id == aircraft_id)
            .order_by(desc(PrognosticRecordModel.timestamp))
            .limit(1)
        ).scalar_one_or_none()

        rul_hours: Optional[float] = None
        rul_is_supported: bool = True
        rul_status: Optional[str] = None
        rul_confidence: Optional[float] = None
        forecast_priority: Optional[str] = None

        if latest_prog:
            rul_hours = latest_prog.estimated_rul_hours
            rul_is_supported = bool(latest_prog.is_supported)
            rul_status = str(latest_prog.rul_status) if latest_prog.rul_status else "ESTIMATED"
            rul_confidence = latest_prog.confidence
            forecast_priority = str(latest_prog.forecast_priority)

            # A. Ground for review forecast
            if forecast_priority == "GROUND_FOR_REVIEW":
                is_ineligible = True
                reasons.append(
                    "Prognostic maintenance forecast demands GROUND_FOR_REVIEW prior to flight clearance."
                )
            elif forecast_priority == "PRIORITY_INSPECTION":
                requires_review = True
                reasons.append(
                    "Prognostic maintenance forecast advises PRIORITY_INSPECTION turnaround review."
                )

            # B. Semantic Safeguard: Unsupported RUL
            if not rul_is_supported or rul_status == "INSUFFICIENT_DATA":
                requires_review = True
                reasons.append(
                    "Prognostic RUL is unsupported due to insufficient historical observations. Demonstration ceiling cannot guarantee flight lifing."
                )
            else:
                # Supported RUL: check against sortie duration commitment
                req_hours = (sortie.estimated_duration_hours or 2.0) if sortie else 2.0
                if rul_hours < (req_hours + cls.RUL_SAFETY_BUFFER_HOURS):
                    is_ineligible = True
                    reasons.append(
                        f"Supported Remaining Useful Life ({rul_hours:.1f} hrs) is insufficient for sortie duration ({req_hours:.1f} hrs + {cls.RUL_SAFETY_BUFFER_HOURS:.0f} hr safety buffer)."
                    )

            if rul_confidence is not None and rul_confidence < 0.60:
                requires_review = True
                reasons.append(
                    f"Prognostic prediction confidence is low ({rul_confidence:.2f}); expanded lifing uncertainty bounds."
                )

        # ---------------------------------------------------------------------
        # 9. Synthesize Final Categorical Decision
        # ---------------------------------------------------------------------
        if is_ineligible:
            final_status = EligibilityStatus.INELIGIBLE
            is_eligible = False
            human_review = False
        elif is_insufficient_evidence:
            final_status = EligibilityStatus.INSUFFICIENT_EVIDENCE
            is_eligible = False
            human_review = True
        elif requires_review:
            final_status = EligibilityStatus.ELIGIBLE_WITH_REVIEW
            is_eligible = True
            human_review = True
        else:
            final_status = EligibilityStatus.ELIGIBLE
            is_eligible = True
            human_review = False
            if not reasons:
                reasons.append(
                    "Aircraft meets all airworthiness, readiness (FMC), and prognostic health criteria."
                )

        evidence = EligibilityEvidence(
            aircraft_lifecycle_status=lifecycle_status,
            aircraft_type=aircraft.aircraft_type,
            readiness_status=readiness_status,
            readiness_confidence=readiness_confidence,
            health_score=health_score,
            wear_index=wear_index,
            active_anomalies_count=len(active_anomalies),
            critical_anomalies_count=crit_count,
            high_anomalies_count=high_count,
            maintenance_conflicts=maint_conflict_ids,
            rul_hours=rul_hours,
            rul_is_supported=rul_is_supported,
            rul_status=rul_status,
            rul_confidence=rul_confidence,
            forecast_priority=forecast_priority,
            data_quality=data_quality,
        )

        return AircraftEligibilityReport(
            aircraft_id=aircraft_id,
            sortie_id=sortie.sortie_id if sortie else None,
            status=final_status,
            reasons=reasons,
            evidence=evidence,
            is_eligible=is_eligible,
            requires_human_review=human_review,
            assessed_at=datetime.now(timezone.utc),
        )
