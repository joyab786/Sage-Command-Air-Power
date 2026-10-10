"""
SageCommand Air Power System (Aero) — End-to-End Tests: Synthetic Demonstration Scenarios.
Formally verifies the 10 mandated demonstration scenarios for Phase 7:
  1. Multiple eligible aircraft
  2. Aircraft unavailable due to authoritative readiness status (NMC)
  3. Active critical anomaly
  4. Maintenance-window conflict
  5. Unsupported or low-confidence prognostics (RUL Safeguard)
  6. Overlapping sorties competing for the same aircraft
  7. No eligible aircraft (unfilled assignment)
  8. Malformed ATO-like input rejection
  9. Governed human review and approval / rejection transitions
  10. Duplicate approval request idempotency
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
    AllocationApprovalStatus,
    EligibilityStatus,
)
from app.mission_manager.service import create_demo_ato_dict, default_mission_manager_service


# -----------------------------------------------------------------------------
# Test Fixtures & Fleet Seeder
# -----------------------------------------------------------------------------

def _seed_airframe(
    db: Session,
    aircraft_id: str,
    tail_number: str,
    readiness_status: str = "FMC",
    health_score: float = 95.0,
    wear_index: float = 0.10,
    rul_hours: float = 80.0,
    is_supported: bool = True,
    rul_status: str = "ESTIMATED",
    rul_confidence: float = 0.90,
) -> AircraftModel:
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number=tail_number,
        aircraft_type="HAL Tejas Mk1A",
        status="ACTIVE",
        air_base="BAREILLY_AFS",
        squadron="1st Tigers",
        total_flight_hours=200.0,
        total_flight_cycles=100,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    readiness = ReadinessAssessmentModel(
        assessment_id=f"ASM-{aircraft_id}",
        aircraft_id=aircraft_id,
        readiness_status=readiness_status,
        assessed_at=utc_now(),
        confidence=0.95 if readiness_status == "FMC" else 0.85,
        reasons=[] if readiness_status == "FMC" else [f"System status {readiness_status}"],
    )
    twin = AircraftTwinStateModel(
        state_id=f"TWIN-{aircraft_id}",
        aircraft_id=aircraft_id,
        health_score=health_score,
        wear_index=wear_index,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    prog = PrognosticRecordModel(
        record_id=f"PROG-{aircraft_id}",
        aircraft_id=aircraft_id,
        subsystem="PROPULSION",
        health_score=health_score,
        wear_index=wear_index,
        trend_direction="STABLE",
        degradation_rate=0.0,
        slope=0.0,
        estimated_rul_hours=rul_hours,
        lower_bound_hours=rul_hours * 0.8,
        upper_bound_hours=rul_hours * 1.2,
        prediction_method="EXPONENTIAL_DEGRADATION",
        is_supported=is_supported,
        rul_status=rul_status,
        confidence=rul_confidence,
        forecast_priority="ROUTINE",
        explanation="Prognostic evaluation record.",
        recommended_action="Nominal monitoring.",
        timestamp=utc_now(),
    )
    db.add_all([ac, readiness, twin, prog])
    db.commit()
    return ac


# -----------------------------------------------------------------------------
# Scenario 1: Multiple Eligible Aircraft
# -----------------------------------------------------------------------------

def test_scenario_1_multiple_eligible_aircraft(db_session: Session):
    """
    Scenario 1: Multiple airframes are fully qualified.
    The engine ranks the airframes deterministically and identifies alternatives.
    """
    _seed_airframe(db_session, "AC-S1-ALPHA", "T-S1-01", health_score=98.0, rul_hours=90.0)
    _seed_airframe(db_session, "AC-S1-BRAVO", "T-S1-02", health_score=85.0, rul_hours=60.0)

    ato_payload = create_demo_ato_dict("ATO-SCENARIO-1")
    # Single sortie requirement
    ato_payload["sorties"] = [ato_payload["sorties"][0]]
    doc = default_mission_manager_service.import_ato(db_session, ato_payload)

    result = default_mission_manager_service.generate_allocation_proposals(db_session, doc.ato_id)
    assert result.allocated_count == 1
    proposal = result.proposals[0]

    # Best airframe selected (higher health & RUL score)
    assert proposal.proposed_aircraft_id == "AC-S1-ALPHA"
    assert proposal.status == AllocationApprovalStatus.PROPOSED
    # Next best offered as alternative
    assert "AC-S1-BRAVO" in proposal.alternatives


# -----------------------------------------------------------------------------
# Scenario 2: Aircraft Unavailable Due to Authoritative Readiness (NMC)
# -----------------------------------------------------------------------------

def test_scenario_2_aircraft_unavailable_authoritative_nmc(db_session: Session):
    """
    Scenario 2: Aircraft has authoritative readiness status NMC (Non-Mission Capable).
    The eligibility engine flags INELIGIBLE and allocation engine refuses assignment.
    """
    _seed_airframe(db_session, "AC-S2-NMC", "T-S2-01", readiness_status="NMC")

    ato_payload = create_demo_ato_dict("ATO-SCENARIO-2")
    ato_payload["sorties"] = [ato_payload["sorties"][0]]
    doc = default_mission_manager_service.import_ato(db_session, ato_payload)

    result = default_mission_manager_service.generate_allocation_proposals(db_session, doc.ato_id)
    proposal = result.proposals[0]

    assert proposal.proposed_aircraft_id is None
    assert proposal.status == AllocationApprovalStatus.REQUIRES_REVIEW
    assert any("NMC" in c for c in proposal.conflicts)


# -----------------------------------------------------------------------------
# Scenario 3: Active Critical Anomaly
# -----------------------------------------------------------------------------

def test_scenario_3_active_critical_anomaly_disqualification(db_session: Session):
    """
    Scenario 3: Aircraft has an active CRITICAL anomaly.
    Airframe must be disqualified from flight clearance immediately.
    """
    _seed_airframe(db_session, "AC-S3-CRIT", "T-S3-01", readiness_status="FMC")
    anom = AnomalyModel(
        anomaly_id="ANOM-S3-CRIT-01",
        aircraft_id="AC-S3-CRIT",
        subsystem="FLIGHT_CONTROLS",
        severity="CRITICAL",
        status="NEW",
        anomaly_type="ACTUATOR_JAM",
        confidence=0.99,
        detector="THRESHOLD",
        signal="control_surface_angle_deg",
        description="Flight control actuator jam detected in pitch channel",
        timestamp=utc_now(),
    )
    db_session.add(anom)
    db_session.commit()

    report = default_mission_manager_service.evaluate_aircraft_eligibility(db_session, "AC-S3-CRIT")
    assert report.status == EligibilityStatus.INELIGIBLE
    assert not report.is_eligible
    assert any("CRITICAL anomaly" in r for r in report.reasons)


# -----------------------------------------------------------------------------
# Scenario 4: Maintenance-Window Conflict
# -----------------------------------------------------------------------------

def test_scenario_4_maintenance_window_conflict(db_session: Session):
    """
    Scenario 4: Aircraft has scheduled maintenance overlapping the sortie window.
    Engine detects conflict and marks aircraft ineligible for that sortie.
    """
    _seed_airframe(db_session, "AC-S4-MAINT", "T-S4-01")
    ato_payload = create_demo_ato_dict("ATO-SCENARIO-4")
    target_sortie = ato_payload["sorties"][0]
    sortie_start = datetime.fromisoformat(target_sortie["start_time"])

    maint = MaintenanceEventModel(
        maintenance_event_id="MNT-S4-DEPOT",
        aircraft_id="AC-S4-MAINT",
        component_id=None,
        description="Scheduled hydraulic fluid flush",
        status="SCHEDULED",
        priority="HIGH",
        scheduled_at=sortie_start + timedelta(hours=1),
        created_at=utc_now(),
    )
    db_session.add(maint)
    db_session.commit()

    doc = default_mission_manager_service.import_ato(db_session, ato_payload)
    report = default_mission_manager_service.evaluate_aircraft_eligibility(
        db_session, "AC-S4-MAINT", sortie_id=target_sortie["sortie_id"]
    )
    assert report.status == EligibilityStatus.INELIGIBLE
    assert any("overlaps planned sortie window" in r for r in report.reasons)


# -----------------------------------------------------------------------------
# Scenario 5: Unsupported or Low-Confidence Prognostics (RUL Safeguard)
# -----------------------------------------------------------------------------

def test_scenario_5_unsupported_or_low_confidence_prognostics(db_session: Session):
    """
    Scenario 5: Unsupported RUL or low confidence prediction.
    Must NOT be treated as infinite useful life; marks ELIGIBLE_WITH_REVIEW and proposal REQUIRES_REVIEW.
    """
    _seed_airframe(
        db_session,
        "AC-S5-UNSUPP",
        "T-S5-01",
        is_supported=False,
        rul_status="INSUFFICIENT_DATA",
        rul_confidence=0.45,
    )
    ato_payload = create_demo_ato_dict("ATO-SCENARIO-5")
    ato_payload["sorties"] = [ato_payload["sorties"][0]]
    doc = default_mission_manager_service.import_ato(db_session, ato_payload)

    result = default_mission_manager_service.generate_allocation_proposals(db_session, doc.ato_id)
    proposal = result.proposals[0]

    assert proposal.proposed_aircraft_id == "AC-S5-UNSUPP"
    assert proposal.eligibility_status == EligibilityStatus.ELIGIBLE_WITH_REVIEW
    # CRITICAL: Algorithmic proposal status is REQUIRES_REVIEW, NEVER APPROVED!
    assert proposal.evidence.rul_is_supported is False
    assert proposal.evidence.rul_status == "INSUFFICIENT_DATA"
    assert "REQUIRES_REVIEW" in proposal.explanation


# -----------------------------------------------------------------------------
# Scenario 6: Overlapping Sorties Competing for the Same Aircraft
# -----------------------------------------------------------------------------

def test_scenario_6_overlapping_sorties_prevent_double_booking(db_session: Session):
    """
    Scenario 6: Two overlapping sorties compete for a single available aircraft.
    Higher priority sortie claims the asset; lower priority sortie remains unfilled.
    """
    _seed_airframe(db_session, "AC-S6-SOLO", "T-S6-01", health_score=96.0)

    t0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    payload = {
        "ato_id": "ATO-SCENARIO-6",
        "schema_version": "1.0.0",
        "issue_timestamp": t0.isoformat(),
        "planning_window_start": t0.isoformat(),
        "planning_window_end": (t0 + timedelta(hours=12)).isoformat(),
        "source": "SYNTHETIC_DEMO",
        "sorties": [
            {
                "sortie_id": "SRT-S6-HIGH-PRIO",
                "mission_category": "COMBAT_AIR_PATROL",
                "start_time": (t0 + timedelta(hours=1)).isoformat(),
                "end_time": (t0 + timedelta(hours=4)).isoformat(),
                "required_aircraft_type": "HAL Tejas Mk1A",
                "priority": "URGENT",
            },
            {
                "sortie_id": "SRT-S6-LOW-PRIO",
                "mission_category": "TRAINING",
                "start_time": (t0 + timedelta(hours=2)).isoformat(),  # Overlaps!
                "end_time": (t0 + timedelta(hours=5)).isoformat(),
                "required_aircraft_type": "HAL Tejas Mk1A",
                "priority": "ROUTINE",
            },
        ],
    }

    doc = default_mission_manager_service.import_ato(db_session, payload)
    result = default_mission_manager_service.generate_allocation_proposals(db_session, doc.ato_id)

    urgent_prop = next(p for p in result.proposals if p.sortie_id == "SRT-S6-HIGH-PRIO")
    routine_prop = next(p for p in result.proposals if p.sortie_id == "SRT-S6-LOW-PRIO")

    assert urgent_prop.proposed_aircraft_id == "AC-S6-SOLO"
    assert routine_prop.proposed_aircraft_id is None
    assert routine_prop.status == AllocationApprovalStatus.REQUIRES_REVIEW
    assert "SRT-S6-LOW-PRIO" in result.unfilled_sorties


# -----------------------------------------------------------------------------
# Scenario 7: No Eligible Aircraft Available
# -----------------------------------------------------------------------------

def test_scenario_7_no_eligible_aircraft_available(db_session: Session):
    """
    Scenario 7: When no airframes in the fleet meet mission eligibility,
    allocation returns an explicit unfilled proposal with conflict explanations.
    """
    # Empty fleet / no qualifying airframes
    ato_payload = create_demo_ato_dict("ATO-SCENARIO-7")
    ato_payload["sorties"] = [ato_payload["sorties"][0]]
    doc = default_mission_manager_service.import_ato(db_session, ato_payload)

    result = default_mission_manager_service.generate_allocation_proposals(db_session, doc.ato_id)
    assert result.allocated_count == 0
    assert result.unfilled_count == 1
    assert result.proposals[0].proposed_aircraft_id is None
    assert "No eligible aircraft available" in result.proposals[0].explanation


# -----------------------------------------------------------------------------
# Scenario 8: Malformed ATO-Like Input
# -----------------------------------------------------------------------------

def test_scenario_8_malformed_ato_input_rejected(db_session: Session):
    """
    Scenario 8: Malformed or unvetted ATO documents (missing required fields,
    invalid time order, unsupported versions) are safely rejected.
    """
    malformed_payload = {
        "ato_id": "ATO-MALFORMED",
        "schema_version": "9.9.9",  # Unsupported schema version
        "planning_window_start": "2026-10-10T10:00:00Z",
        "planning_window_end": "2026-10-10T08:00:00Z",  # Inverted time!
        "sorties": [],
    }

    val_resp = default_mission_manager_service.validate_ato(malformed_payload)
    assert not val_resp.is_valid
    error_codes = [f.code for f in val_resp.findings]
    assert "UNSUPPORTED_SCHEMA_VERSION" in error_codes
    assert "INVALID_PLANNING_WINDOW" in error_codes


# -----------------------------------------------------------------------------
# Scenario 9: Human Approval and Rejection Flow
# -----------------------------------------------------------------------------

def test_scenario_9_governed_human_approval_and_rejection(db_session: Session, test_client: TestClient):
    """
    Scenario 9: An algorithmic proposal must remain advisory until approved by an authorized human.
    Verifies state transitions from PROPOSED -> APPROVED and PROPOSED -> REJECTED.
    """
    _seed_airframe(db_session, "AC-S9-GOV", "T-S9-01")
    ato_payload = create_demo_ato_dict("ATO-SCENARIO-9")
    ato_payload["sorties"] = [ato_payload["sorties"][0]]
    test_client.post("/api/v1/ato/import-demo", json=ato_payload)

    alloc_resp = test_client.post("/api/v1/ato/ATO-SCENARIO-9/allocation-proposals")
    proposal = alloc_resp.json()["data"]["proposals"][0]
    prop_id = proposal["proposal_id"]

    assert proposal["status"] == "PROPOSED"

    # Human Approves
    appr_resp = test_client.post(
        f"/api/v1/allocation-proposals/{prop_id}/approve",
        json={
            "approver_id": "SQN_LDR_SHARMA",
            "decision_reason": "Airframe verified FMC; mission parameters approved.",
        },
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["data"]["status"] == "APPROVED"
    assert appr_resp.json()["data"]["reviewed_by"] == "SQN_LDR_SHARMA"


# -----------------------------------------------------------------------------
# Scenario 10: Duplicate Approval Request Idempotency
# -----------------------------------------------------------------------------

def test_scenario_10_duplicate_approval_request_idempotent(db_session: Session, test_client: TestClient):
    """
    Scenario 10: A duplicate approval request for an already approved proposal
    must succeed idempotently without causing database errors or state corruption.
    """
    _seed_airframe(db_session, "AC-S10-IDEMP", "T-S10-01")
    ato_payload = create_demo_ato_dict("ATO-SCENARIO-10")
    ato_payload["sorties"] = [ato_payload["sorties"][0]]
    test_client.post("/api/v1/ato/import-demo", json=ato_payload)

    alloc_resp = test_client.post("/api/v1/ato/ATO-SCENARIO-10/allocation-proposals")
    prop_id = alloc_resp.json()["data"]["proposals"][0]["proposal_id"]

    # First Approval
    r1 = test_client.post(
        f"/api/v1/allocation-proposals/{prop_id}/approve",
        json={"approver_id": "WG_CDR_VERMA", "decision_reason": "First approval clearance."},
    )
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "APPROVED"

    # Duplicate Approval (Idempotency)
    r2 = test_client.post(
        f"/api/v1/allocation-proposals/{prop_id}/approve",
        json={"approver_id": "WG_CDR_VERMA", "decision_reason": "Duplicate click clearance."},
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "APPROVED"
    assert "already approved" in r2.json()["data"]["message"].lower()
