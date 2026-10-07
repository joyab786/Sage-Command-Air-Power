"""
Integration tests for Aero Domain REST API Endpoints.
Validates HTTP request routing, response envelopes, serialization, and error codes.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient


def test_aircraft_crud_flow(test_client: TestClient):
    # 1. Register new aircraft
    payload = {
        "aircraft_id": "ac_api_01",
        "tail_number": "TS-401",
        "aircraft_type": "Tejas Mk1A",
        "variant": "FOC",
        "air_base": "Sulur AFS",
        "squadron": "No. 45 Flying Daggers",
        "status": "ACTIVE",
        "total_flight_hours": 320.5,
        "total_flight_cycles": 180,
    }
    create_resp = test_client.post("/api/v1/aircraft", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["success"] is True
    assert created_data["data"]["aircraft_id"] == "ac_api_01"
    assert created_data["data"]["tail_number"] == "TS-401"

    # 2. Get aircraft by ID
    get_resp = test_client.get("/api/v1/aircraft/ac_api_01")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["air_base"] == "Sulur AFS"

    # 3. List aircraft
    list_resp = test_client.get("/api/v1/aircraft")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert any(item["aircraft_id"] == "ac_api_01" for item in items)

    # 4. Filter aircraft by status
    filter_resp = test_client.get("/api/v1/aircraft?status=ACTIVE")
    assert filter_resp.status_code == 200
    assert len(filter_resp.json()["data"]) >= 1


def test_aircraft_conflict_duplicate_id(test_client: TestClient):
    payload = {
        "aircraft_id": "ac_dup_test",
        "tail_number": "KB-101",
        "aircraft_type": "Mirage 2000",
        "air_base": "Gwalior AFS",
        "squadron": "Battle Axes",
    }
    r1 = test_client.post("/api/v1/aircraft", json=payload)
    assert r1.status_code == 201

    # Second creation with same ID should yield 409
    r2 = test_client.post("/api/v1/aircraft", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "AIRCRAFT_EXISTS"


def test_aircraft_not_found(test_client: TestClient):
    resp = test_client.get("/api/v1/aircraft/ac_non_existent")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_aircraft_components_flow(test_client: TestClient):
    # Setup aircraft
    ac_payload = {
        "aircraft_id": "ac_comp_host",
        "tail_number": "SU-701",
        "aircraft_type": "Su-30MKI",
        "air_base": "Halwara AFS",
        "squadron": "Desert Tigers",
    }
    test_client.post("/api/v1/aircraft", json=ac_payload)

    # Install component
    comp_payload = {
        "component_id": "comp_radar_01",
        "aircraft_id": "ac_comp_host",
        "component_type": "RADAR",
        "serial_number": "SN-BARS-991",
        "health_state": "HEALTHY",
        "accumulated_hours": 150.0,
        "accumulated_cycles": 80,
    }
    post_comp = test_client.post("/api/v1/aircraft/ac_comp_host/components", json=comp_payload)
    assert post_comp.status_code == 201
    assert post_comp.json()["data"]["component_id"] == "comp_radar_01"

    # Query components
    get_comps = test_client.get("/api/v1/aircraft/ac_comp_host/components")
    assert get_comps.status_code == 200
    comp_list = get_comps.json()["data"]
    assert len(comp_list) == 1
    assert comp_list[0]["serial_number"] == "SN-BARS-991"


def test_aircraft_readiness_baseline_and_explicit(test_client: TestClient):
    # Setup aircraft
    ac_payload = {
        "aircraft_id": "ac_readiness_test",
        "tail_number": "RF-301",
        "aircraft_type": "Rafale",
        "air_base": "Ambala AFS",
        "squadron": "No. 17 Golden Arrows",
    }
    test_client.post("/api/v1/aircraft", json=ac_payload)

    # Baseline readiness without explicit assessment should be FMC
    baseline_resp = test_client.get("/api/v1/aircraft/ac_readiness_test/readiness")
    assert baseline_resp.status_code == 200
    assert baseline_resp.json()["data"]["readiness_status"] == "FMC"

    # Post explicit readiness evaluation (PMC due to subsystem degradation)
    now = datetime.now(timezone.utc).isoformat()
    eval_payload = {
        "assessment_id": "eval_rf_001",
        "aircraft_id": "ac_readiness_test",
        "readiness_status": "PMC",
        "assessed_at": now,
        "reasons": ["Auxiliary hydraulic pressure minor oscillation"],
        "limiting_components": ["comp_hyd_02"],
        "confidence": 0.95,
    }
    post_eval = test_client.post("/api/v1/aircraft/ac_readiness_test/readiness", json=eval_payload)
    assert post_eval.status_code == 201

    # Next readiness check should return explicit PMC
    updated_resp = test_client.get("/api/v1/aircraft/ac_readiness_test/readiness")
    assert updated_resp.status_code == 200
    assert updated_resp.json()["data"]["readiness_status"] == "PMC"
    assert "comp_hyd_02" in updated_resp.json()["data"]["limiting_components"]


def test_mission_api_flow(test_client: TestClient):
    start = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()

    msn_payload = {
        "mission_id": "msn_api_01",
        "mission_name": "Exercise Desert Strike",
        "mission_type": "TRAINING",
        "scheduled_start": start,
        "scheduled_end": end,
        "required_aircraft": 4,
        "assigned_aircraft": ["ac_api_01"],
        "status": "PLANNED",
        "readiness_requirement": "FMC",
    }

    create_resp = test_client.post("/api/v1/missions", json=msn_payload)
    assert create_resp.status_code == 201
    assert create_resp.json()["data"]["mission_id"] == "msn_api_01"

    get_resp = test_client.get("/api/v1/missions/msn_api_01")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["mission_name"] == "Exercise Desert Strike"

    list_resp = test_client.get("/api/v1/missions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) >= 1
