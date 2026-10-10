"""
SageCommand Air Power System (Aero) — Unit Tests: Aircraft Eligibility Engine.
Tests deterministic qualification of airframes against readiness, maintenance,
anomalies, and prognostic RUL semantic safeguards.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    AnomalyModel,
    MaintenanceEventModel,
    PrognosticRecordModel,
    ReadinessAssessmentModel,
    utc_now,
)
from app.mission_manager.models import (
    EligibilityStatus,
    ProposedSortie,
    SortiePriority,
)
from app.mission_manager.eligibility import AircraftEligibilityEvaluator


def _create_aircraft(db: Session, aircraft_id: str, aircraft_type: str = "HAL Tejas Mk1A", status: str = "ACTIVE") -> AircraftModel:
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number=f"T-{aircraft_id}",
        aircraft_type=aircraft_type,
        status=status,
        air_base="BAREILLY_AFS",
        squadron="1st Tigers",
        total_flight_hours=250.0,
        total_flight_cycles=120,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(ac)
    db.commit()
    return ac


def _create_sortie(
    sortie_id: str = "SRT-TEST-01",
    aircraft_type: str = "HAL Tejas Mk1A",
    duration_hours: float = 2.0,
) -> ProposedSortie:
    t0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    return ProposedSortie(
        sortie_id=sortie_id,
        mission_category="TRAINING",
        start_time=t0,
        end_time=t0 + timedelta(hours=duration_hours),
        required_aircraft_type=aircraft_type,
        required_capabilities=["RADAR"],
        min_aircraft_count=1,
        priority=SortiePriority.ROUTINE,
        estimated_duration_hours=duration_hours,
    )


def test_evaluator_aircraft_not_found_raises_not_found_error(db_session: Session):
    with pytest.raises(NotFoundError) as exc_info:
        AircraftEligibilityEvaluator.evaluate_aircraft(db_session, aircraft_id="NON-EXISTENT")
    assert "not found" in str(exc_info.value.message).lower()


def test_evaluator_inactive_lifecycle_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-RETIRED-01", status="RETIRED")
    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-RETIRED-01")

    assert report.status == EligibilityStatus.INELIGIBLE
    assert not report.is_eligible
    assert any("lifecycle status is 'RETIRED'" in r for r in report.reasons)


def test_evaluator_aircraft_type_mismatch_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-SU30-01", aircraft_type="Su-30MKI")
    sortie = _create_sortie(aircraft_type="HAL Tejas Mk1A")
    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-SU30-01", sortie=sortie)

    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("does not match sortie requirement" in r for r in report.reasons)


def test_evaluator_missing_readiness_insufficient_evidence(db_session: Session):
    """Missing readiness evidence must not silently assume ready!"""
    _create_aircraft(db_session, "AC-NO-READINESS-01")
    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-NO-READINESS-01")

    assert report.status == EligibilityStatus.INSUFFICIENT_EVIDENCE
    assert not report.is_eligible
    assert report.requires_human_review
    assert any("Missing authoritative readiness assessment record" in r for r in report.reasons)


def test_evaluator_readiness_nmc_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-NMC-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-NMC-01",
        aircraft_id="AC-NMC-01",
        readiness_status="NMC",
        assessed_at=utc_now(),
        confidence=0.95,
        reasons=["Avionics cooling failure"],
    )
    db_session.add(readiness)
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-NMC-01")
    assert report.status == EligibilityStatus.INELIGIBLE
    assert not report.is_eligible
    assert any("NMC (Non-Mission Capable)" in r for r in report.reasons)


def test_evaluator_readiness_pmc_requires_review(db_session: Session):
    _create_aircraft(db_session, "AC-PMC-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-PMC-01",
        aircraft_id="AC-PMC-01",
        readiness_status="PMC",
        assessed_at=utc_now(),
        confidence=0.90,
        reasons=["Auxiliary power unit degraded"],
    )
    db_session.add(readiness)
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-PMC-01")
    assert report.status == EligibilityStatus.ELIGIBLE_WITH_REVIEW
    assert report.is_eligible
    assert report.requires_human_review
    assert any("PMC" in r for r in report.reasons)


def test_evaluator_low_readiness_confidence_requires_review(db_session: Session):
    _create_aircraft(db_session, "AC-LOW-CONF-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-LOW-CONF-01",
        aircraft_id="AC-LOW-CONF-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.45,
        reasons=[],
    )
    db_session.add(readiness)
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-LOW-CONF-01")
    assert report.status == EligibilityStatus.ELIGIBLE_WITH_REVIEW
    assert any("confidence is low (0.45)" in r for r in report.reasons)


def test_evaluator_maintenance_in_progress_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-MAINT-INPROG-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-MAINT-01",
        aircraft_id="AC-MAINT-INPROG-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    maint = MaintenanceEventModel(
        maintenance_event_id="MNT-1001",
        aircraft_id="AC-MAINT-INPROG-01",
        component_id=None,
        description="Hydraulic pump overhaul",
        status="IN_PROGRESS",
        priority="HIGH",
        created_at=utc_now(),
    )
    db_session.add_all([readiness, maint])
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-MAINT-INPROG-01")
    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("is currently IN_PROGRESS" in r for r in report.reasons)


def test_evaluator_maintenance_scheduled_overlap_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-MAINT-SCHED-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-SCHED-01",
        aircraft_id="AC-MAINT-SCHED-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    sortie = _create_sortie(sortie_id="SRT-SCHED-01")
    maint = MaintenanceEventModel(
        maintenance_event_id="MNT-1002",
        aircraft_id="AC-MAINT-SCHED-01",
        component_id=None,
        description="Scheduled 100-hour engine inspection",
        status="SCHEDULED",
        priority="MEDIUM",
        scheduled_at=sortie.start_time + timedelta(hours=1),
        created_at=utc_now(),
    )
    db_session.add_all([readiness, maint])
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-MAINT-SCHED-01", sortie=sortie)
    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("overlaps planned sortie window" in r for r in report.reasons)


def test_evaluator_critical_anomaly_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-CRIT-ANOM-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-CRIT-01",
        aircraft_id="AC-CRIT-ANOM-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    anom = AnomalyModel(
        anomaly_id="ANOM-CRIT-01",
        aircraft_id="AC-CRIT-ANOM-01",
        subsystem="ENGINE",
        severity="CRITICAL",
        status="NEW",
        anomaly_type="TURBINE_OVERTEMP",
        confidence=0.98,
        description="Critical turbine temperature spike",
        detector="THRESHOLD",
        signal="engine_temperature_c",
        timestamp=utc_now(),
    )
    db_session.add_all([readiness, anom])
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-CRIT-ANOM-01")
    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("active CRITICAL anomaly" in r for r in report.reasons)


def test_evaluator_high_anomaly_requires_review(db_session: Session):
    _create_aircraft(db_session, "AC-HIGH-ANOM-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-HIGH-01",
        aircraft_id="AC-HIGH-ANOM-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    anom = AnomalyModel(
        anomaly_id="ANOM-HIGH-01",
        aircraft_id="AC-HIGH-ANOM-01",
        subsystem="HYDRAULICS",
        severity="HIGH",
        status="NEW",
        anomaly_type="PRESSURE_DRIFT",
        confidence=0.85,
        description="Hydraulic pressure drift",
        detector="STATISTICAL",
        signal="hydraulic_pressure_kpa",
        timestamp=utc_now(),
    )
    db_session.add_all([readiness, anom])
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-HIGH-ANOM-01")
    assert report.status == EligibilityStatus.ELIGIBLE_WITH_REVIEW
    assert any("active HIGH severity anomaly" in r for r in report.reasons)


def test_evaluator_digital_twin_low_health_ineligible(db_session: Session):
    _create_aircraft(db_session, "AC-LOW-HEALTH-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-HEALTH-01",
        aircraft_id="AC-LOW-HEALTH-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    twin = AircraftTwinStateModel(
        state_id="TWIN-HEALTH-01",
        aircraft_id="AC-LOW-HEALTH-01",
        health_score=42.0,  # Below threshold 50.0
        wear_index=0.60,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    db_session.add_all([readiness, twin])
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-LOW-HEALTH-01")
    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("below minimum flight threshold" in r for r in report.reasons)


def test_evaluator_rul_safeguard_unsupported_requires_review(db_session: Session):
    """
    RUL Semantic Safeguard:
    Unsupported RUL or insufficient historical observations must NOT be treated as infinite remaining life.
    Must evaluate to ELIGIBLE_WITH_REVIEW and require explicit human review.
    """
    _create_aircraft(db_session, "AC-UNSUPPORTED-RUL-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-RUL-UNSUPP-01",
        aircraft_id="AC-UNSUPPORTED-RUL-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    twin = AircraftTwinStateModel(
        state_id="TWIN-RUL-01",
        aircraft_id="AC-UNSUPPORTED-RUL-01",
        health_score=95.0,
        wear_index=0.10,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    prog = PrognosticRecordModel(
        record_id="PROG-UNSUPP-01",
        aircraft_id="AC-UNSUPPORTED-RUL-01",
        subsystem="PROPULSION",
        health_score=95.0,
        wear_index=0.10,
        trend_direction="STABLE",
        degradation_rate=0.0,
        slope=0.0,
        estimated_rul_hours=100.0,
        lower_bound_hours=80.0,
        upper_bound_hours=120.0,
        prediction_method="EXPONENTIAL_DEGRADATION",
        is_supported=False,
        rul_status="INSUFFICIENT_DATA",
        confidence=0.50,
        forecast_priority="ROUTINE",
        explanation="Fallback nominal ceiling due to insufficient historical telemetry.",
        recommended_action="Gather telemetry baseline observations.",
        timestamp=utc_now(),
    )
    db_session.add_all([readiness, twin, prog])
    db_session.commit()

    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-UNSUPPORTED-RUL-01")
    assert report.status == EligibilityStatus.ELIGIBLE_WITH_REVIEW
    assert report.requires_human_review
    assert any("insufficient historical observations" in r for r in report.reasons)


def test_evaluator_rul_insufficient_for_sortie_ineligible(db_session: Session):
    """Supported RUL lower than (sortie_duration + buffer) triggers INELIGIBLE."""
    _create_aircraft(db_session, "AC-LOW-RUL-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-RUL-LOW-01",
        aircraft_id="AC-LOW-RUL-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    twin = AircraftTwinStateModel(
        state_id="TWIN-LOW-RUL-01",
        aircraft_id="AC-LOW-RUL-01",
        health_score=80.0,
        wear_index=0.40,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    prog = PrognosticRecordModel(
        record_id="PROG-LOW-01",
        aircraft_id="AC-LOW-RUL-01",
        subsystem="PROPULSION",
        health_score=80.0,
        wear_index=0.40,
        trend_direction="DEGRADING",
        degradation_rate=0.05,
        slope=-0.05,
        estimated_rul_hours=6.0,  # Sortie is 3.0 hrs + 5.0 buffer = 8.0 hrs needed
        lower_bound_hours=4.0,
        upper_bound_hours=8.0,
        prediction_method="EXPONENTIAL_DEGRADATION",
        is_supported=True,
        rul_status="ESTIMATED",
        confidence=0.88,
        forecast_priority="ROUTINE",
        explanation="Accelerated thermal degradation.",
        recommended_action="Inspect turbine within 10 flight hours.",
        timestamp=utc_now(),
    )
    db_session.add_all([readiness, twin, prog])
    db_session.commit()

    sortie = _create_sortie(sortie_id="SRT-3HR", duration_hours=3.0)
    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-LOW-RUL-01", sortie=sortie)

    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("Remaining Useful Life (6.0 hrs) is insufficient" in r for r in report.reasons)


def test_evaluator_fully_qualified_fmc_eligible(db_session: Session):
    _create_aircraft(db_session, "AC-CLEAN-01")
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-CLEAN-01",
        aircraft_id="AC-CLEAN-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
    )
    twin = AircraftTwinStateModel(
        state_id="TWIN-CLEAN-01",
        aircraft_id="AC-CLEAN-01",
        health_score=98.0,
        wear_index=0.08,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    prog = PrognosticRecordModel(
        record_id="PROG-CLEAN-01",
        aircraft_id="AC-CLEAN-01",
        subsystem="PROPULSION",
        health_score=98.0,
        wear_index=0.08,
        trend_direction="STABLE",
        degradation_rate=0.0,
        slope=0.0,
        estimated_rul_hours=75.0,
        lower_bound_hours=60.0,
        upper_bound_hours=90.0,
        prediction_method="EXPONENTIAL_DEGRADATION",
        is_supported=True,
        rul_status="ESTIMATED",
        confidence=0.92,
        forecast_priority="ROUTINE",
        explanation="Stable degradation pattern.",
        recommended_action="Continue nominal monitoring.",
        timestamp=utc_now(),
    )
    db_session.add_all([readiness, twin, prog])
    db_session.commit()

    sortie = _create_sortie(sortie_id="SRT-CLEAN-01", duration_hours=2.0)
    report = AircraftEligibilityEvaluator.evaluate_aircraft(db_session, "AC-CLEAN-01", sortie=sortie)

    assert report.status == EligibilityStatus.ELIGIBLE
    assert report.is_eligible
    assert not report.requires_human_review
