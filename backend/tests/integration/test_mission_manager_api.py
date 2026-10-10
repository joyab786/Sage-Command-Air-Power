"""
SageCommand Air Power System (Aero) — Integration Tests: Mission Manager API Endpoints.
Tests REST API endpoints, response envelopes, error contracts, and governance approval workflows.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    PrognosticRecordModel,
    ReadinessAssessmentModel,
    utc_now,
)
from app.mission_manager.service import create_demo_ato_dict


@pytest.fixture
def seed_test_airframe(db_session: Session):
    ac = AircraftModel(
        aircraft_id="AC-API-TEST-01",
        tail_number="T-API-01",
        aircraft_type="HAL Tejas Mk1A",
        status="ACTIVE",
        air_base="BAREILLY_AFS",
        squadron="1st Tigers",
        total_flight_hours=150.0,
        total_flight_cycles=80,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    readiness = ReadinessAssessmentModel(
        assessment_id="ASM-API-01",
        aircraft_id="AC-API-TEST-01",
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
        reasons=[],
    )
    twin = AircraftTwinStateModel(
        state_id="TWIN-API-01",
        aircraft_id="AC-API-TEST-01",
        health_score=94.0,
        wear_index=0.12,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    prog = PrognosticRecordModel(
        record_id="PROG-API-01",
        aircraft_id="AC-API-TEST-01",
        subsystem="PROPULSION",
        health_score=94.0,
        wear_index=0.12,
        trend_direction="STABLE",
        degradation_rate=0.0,
        slope=0.0,
        estimated_rul_hours=65.0,
        lower_bound_hours=55.0,
        upper_bound_hours=75.0,
        prediction_method="EXPONENTIAL_DEGRADATION",
        is_supported=True,
        rul_status="ESTIMATED",
        confidence=0.90,
        forecast_priority="ROUTINE",
        explanation="Nominal operation.",
        recommended_action="Monitor telemetry.",
        timestamp=utc_now(),
    )
    db_session.add_all([ac, readiness, twin, prog])
    db_session.commit()
    return ac


def test_api_ato_validate_valid_payload(test_client: TestClient):
    payload = create_demo_ato_dict("ATO-API-VAL-01")
    resp = test_client.post("/api/v1/ato/validate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["is_valid"] is True
    assert body["data"]["findings"] == []


def test_api_ato_validate_malformed_payload(test_client: TestClient):
    payload = {"schema_version": "1.0.0"}  # Missing required fields
    resp = test_client.post("/api/v1/ato/validate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["data"]["is_valid"] is False
    assert len(body["data"]["findings"]) > 0


def test_api_ato_import_demo_and_get(test_client: TestClient):
    payload = create_demo_ato_dict("ATO-API-IMPORT-01")
    resp = test_client.post("/api/v1/ato/import-demo", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["ato_id"] == "ATO-API-IMPORT-01"
    assert len(body["data"]["sorties"]) == 4

    # GET imported ATO
    get_resp = test_client.get("/api/v1/ato/ATO-API-IMPORT-01")
    assert get_resp.status_code == 200
    get_body = get_resp.json()
    assert get_body["data"]["ato_id"] == "ATO-API-IMPORT-01"


def test_api_ato_get_nonexistent_returns_404(test_client: TestClient):
    resp = test_client.get("/api/v1/ato/ATO-DOES-NOT-EXIST")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "not found" in body["error"]["message"].lower()


def test_api_aircraft_mission_eligibility(test_client: TestClient, seed_test_airframe):
    resp = test_client.get("/api/v1/aircraft/AC-API-TEST-01/mission-eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["aircraft_id"] == "AC-API-TEST-01"
    assert body["data"]["status"] == "ELIGIBLE"
    assert body["data"]["is_eligible"] is True


def test_api_aircraft_mission_eligibility_not_found(test_client: TestClient):
    resp = test_client.get("/api/v1/aircraft/AC-UNKNOWN/mission-eligibility")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False


def test_api_generate_and_list_allocation_proposals(test_client: TestClient, seed_test_airframe):
    # Import demo ATO first
    payload = create_demo_ato_dict("ATO-API-ALLOC-01")
    test_client.post("/api/v1/ato/import-demo", json=payload)

    # Generate proposals
    resp = test_client.post("/api/v1/ato/ATO-API-ALLOC-01/allocation-proposals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["total_sorties"] == 4
    proposals = body["data"]["proposals"]
    assert len(proposals) == 4

    # Verify non-overlapping sorties (SRT-01, SRT-03, SRT-04) received AC-API-TEST-01
    matched = [p for p in proposals if p["proposed_aircraft_id"] == "AC-API-TEST-01"]
    assert len(matched) == 3

    # Verify overlapping sortie (SRT-02: 4-7 hrs overlaps SRT-01: 2-5 hrs) remains unfilled
    unfilled = [p for p in proposals if p["proposed_aircraft_id"] is None]
    assert len(unfilled) == 1
    assert "SRT-02" in unfilled[0]["sortie_id"]

    # List proposals via GET
    list_resp = test_client.get("/api/v1/ato/ATO-API-ALLOC-01/allocation-proposals")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 4


def test_api_human_governance_approve_reject_flow(test_client: TestClient, seed_test_airframe):
    # Setup and generate proposals
    payload = create_demo_ato_dict("ATO-API-GOV-01")
    test_client.post("/api/v1/ato/import-demo", json=payload)
    alloc_resp = test_client.post("/api/v1/ato/ATO-API-GOV-01/allocation-proposals")
    proposals = alloc_resp.json()["data"]["proposals"]

    matched = next(p for p in proposals if p["proposed_aircraft_id"] == "AC-API-TEST-01")
    prop_id = matched["proposal_id"]

    # 1. Approve proposal
    appr_resp = test_client.post(
        f"/api/v1/allocation-proposals/{prop_id}/approve",
        json={
            "approver_id": "COMM_RAO_44",
            "decision_reason": "Cleared by Squadron Operations Officer for primary combat air patrol.",
        },
    )
    assert appr_resp.status_code == 200
    appr_body = appr_resp.json()
    assert appr_body["success"] is True
    assert appr_body["data"]["status"] == "APPROVED"
    assert appr_body["data"]["reviewed_by"] == "COMM_RAO_44"
    assert appr_body["data"]["audit_event_id"] is not None

    # 2. Idempotent approval request: returns 200 with already approved message
    idemp_resp = test_client.post(
        f"/api/v1/allocation-proposals/{prop_id}/approve",
        json={
            "approver_id": "COMM_RAO_44",
            "decision_reason": "Cleared again.",
        },
    )
    assert idemp_resp.status_code == 200
    assert idemp_resp.json()["data"]["status"] == "APPROVED"
    assert "already approved" in idemp_resp.json()["data"]["message"].lower()

    # 3. Rejecting an already APPROVED proposal returns 409 Conflict
    conf_resp = test_client.post(
        f"/api/v1/allocation-proposals/{prop_id}/reject",
        json={
            "approver_id": "COMM_RAO_44",
            "decision_reason": "Attempting to reject approved without revocation.",
        },
    )
    assert conf_resp.status_code == 409
    assert conf_resp.json()["success"] is False
