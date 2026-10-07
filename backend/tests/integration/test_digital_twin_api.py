"""
SageCommand Air Power System (Aero) — Integration Tests: Digital Twin API & Ingestion Flow.
Verifies GET /aircraft/{id}/twin, GET /aircraft/{id}/twin/history,
and end-to-end telemetry ingestion state estimation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models import AircraftModel


@pytest.fixture
def registered_aircraft(db_session: Session) -> str:
    """Creates a sample aircraft in the test database."""
    aircraft_id = "TWIN-TEST-SU30"
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number="SB-TWIN-001",
        aircraft_type="SU-30MKI",
        air_base="Pune AFS",
        squadron="No. 20 Squadron",
        status="ACTIVE",
        total_flight_hours=120.0,
        total_flight_cycles=60,
    )
    db_session.add(ac)
    db_session.commit()
    return aircraft_id


def test_get_initial_baseline_twin_state(test_client: TestClient, registered_aircraft: str):
    """Verifies that an aircraft with no prior telemetry returns a baseline nominal twin state."""
    resp = test_client.get(f"/api/v1/aircraft/{registered_aircraft}/twin")
    assert resp.status_code == 200
    body = resp.json()

    assert body["success"] is True
    data = body["data"]
    assert data["aircraft_id"] == registered_aircraft
    assert data["health_state"] == "HEALTHY"
    assert data["health_score"] == 100.0
    assert data["data_quality"] == "BASELINE"
    assert data["flight_hours"] == 120.0
    assert data["flight_cycles"] == 60
    assert "PROPULSION" in data["subsystem_states"]
    assert "HYDRAULIC" in data["subsystem_states"]
    assert data["subsystem_states"]["HYDRAULIC"]["health_state"] == "UNKNOWN"


def test_end_to_end_telemetry_updates_twin(test_client: TestClient, registered_aircraft: str):
    """
    COMPLETE END-TO-END VERIFICATION:
    1. Ingest valid telemetry frame via POST /api/v1/telemetry
    2. Confirm telemetry is accepted and persisted
    3. Query GET /api/v1/aircraft/{id}/twin and verify updated state reflects telemetry
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": registered_aircraft,
        "flight_id": "SORTIE-LIVE-01",
        "timestamp": now,
        "altitude": 32000.0,  # feet
        "airspeed": 480.0,    # knots
        "mach": 0.82,
        "g_load": 1.05,
        "engine_temperature": 1350.0,  # Fahrenheit (~732.2°C, nominal)
        "engine_pressure": 65.0,       # psi (~448.2 kPa, nominal)
        "vibration": 0.35,             # ips
        "fuel_flow": 5200.0,           # lbs/h
        "units": {
            "altitude": "ft",
            "airspeed": "kts",
            "temperature": "F",
            "pressure": "psi",
            "vibration": "ips",
            "fuel_flow": "lbs/h",
        },
    }

    # Step 1: POST Telemetry
    post_resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert post_resp.status_code == 201
    assert post_resp.json()["data"]["accepted"] is True

    # Step 2: GET Twin State
    twin_resp = test_client.get(f"/api/v1/aircraft/{registered_aircraft}/twin")
    assert twin_resp.status_code == 200
    twin_data = twin_resp.json()["data"]

    # Verify unit conversions carried into twin state
    assert round(twin_data["altitude"], 1) == 9753.6    # 32000 ft -> 9753.6 m
    assert round(twin_data["airspeed"], 1) == 246.9    # 480 kts -> 246.9 m/s
    assert round(twin_data["engine_temperature"], 1) == 732.2  # 1350 F -> 732.2 C
    assert twin_data["operational_status"] == "IN_FLIGHT"
    assert twin_data["health_state"] == "HEALTHY"
    assert twin_data["health_score"] >= 90.0
    assert twin_data["current_flight_id"] == "SORTIE-LIVE-01"


def test_thermal_anomaly_degrades_twin_health(test_client: TestClient, registered_aircraft: str):
    """
    Verifies that ingesting telemetry with thermal exceedance visibly degrades
    the digital twin health state and generates structured explainability reasons.
    """
    now = datetime.now(timezone.utc).isoformat()
    anomaly_payload = {
        "aircraft_id": registered_aircraft,
        "flight_id": "SORTIE-HEAT-01",
        "timestamp": now,
        "altitude": 10000.0,
        "airspeed": 250.0,
        "mach": 0.85,
        "g_load": 1.2,
        "engine_temperature": 1070.0,  # Exceeds 1050°C critical limit!
        "engine_pressure": 450.0,
        "vibration": 0.40,
        "units": {
            "altitude": "m",
            "airspeed": "m/s",
            "temperature": "C",
            "pressure": "kPa",
            "vibration": "ips",
        },
    }

    post_resp = test_client.post("/api/v1/telemetry", json=anomaly_payload)
    assert post_resp.status_code == 201

    twin_resp = test_client.get(f"/api/v1/aircraft/{registered_aircraft}/twin")
    assert twin_resp.status_code == 200
    twin_data = twin_resp.json()["data"]

    assert twin_data["health_score"] < 75.0
    assert twin_data["health_state"] in ("WARNING", "CRITICAL")
    assert len(twin_data["health_reasons"]) > 0
    assert any(r["signal"] == "engine_temperature" for r in twin_data["health_reasons"])
    assert twin_data["subsystem_states"]["PROPULSION"]["health_state"] in ("WARNING", "CRITICAL")


def test_invalid_telemetry_does_not_mutate_twin(test_client: TestClient, registered_aircraft: str):
    """
    SAFETY REQUIREMENT: Invalid telemetry (unphysical values, NaN)
    must be rejected and must NOT update the digital twin state.
    """
    # 1. Ingest initial valid frame so a persisted twin state exists
    now = datetime.now(timezone.utc)
    valid_payload = {
        "aircraft_id": registered_aircraft,
        "timestamp": now.isoformat(),
        "altitude": 5000.0,
        "airspeed": 200.0,
        "engine_temperature": 700.0,
        "engine_pressure": 400.0,
        "vibration": 0.30,
        "units": {"altitude": "m", "airspeed": "m/s", "temperature": "C", "pressure": "kPa"},
    }
    test_client.post("/api/v1/telemetry", json=valid_payload)

    initial_twin = test_client.get(f"/api/v1/aircraft/{registered_aircraft}/twin").json()["data"]
    initial_timestamp = initial_twin["timestamp"]

    # 2. Ingest invalid telemetry (negative pressure)
    invalid_payload = {
        "aircraft_id": registered_aircraft,
        "timestamp": (now + timedelta(seconds=30)).isoformat(),
        "altitude": 5000.0,
        "airspeed": 200.0,
        "engine_pressure": -50.0,  # Unphysical negative pressure
        "units": {"pressure": "kPa"},
    }

    post_resp = test_client.post("/api/v1/telemetry", json=invalid_payload)
    assert post_resp.status_code == 201
    assert post_resp.json()["data"]["accepted"] is False

    # 3. Check twin state has NOT changed
    subsequent_twin = test_client.get(f"/api/v1/aircraft/{registered_aircraft}/twin").json()["data"]
    assert subsequent_twin["timestamp"] == initial_timestamp


def test_twin_history_endpoint(test_client: TestClient, registered_aircraft: str):
    """Verifies GET /aircraft/{id}/twin/history returns chronological history with pagination."""
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    # Ingest 2 observations
    for i in range(2):
        test_client.post(
            "/api/v1/telemetry",
            json={
                "aircraft_id": registered_aircraft,
                "flight_id": "SORTIE-HIST",
                "timestamp": (base_time + timedelta(seconds=i * 20)).isoformat(),
                "altitude": 5000.0 + (i * 1000),
                "airspeed": 200.0,
                "units": {"altitude": "m", "airspeed": "m/s"},
            },
        )

    resp = test_client.get(f"/api/v1/aircraft/{registered_aircraft}/twin/history?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    history = body["data"]
    assert len(history) >= 2


def test_twin_unknown_aircraft_404(test_client: TestClient):
    """Verifies that querying a non-existent aircraft returns 404."""
    resp = test_client.get("/api/v1/aircraft/NON-EXISTENT-AIRCRAFT/twin")
    assert resp.status_code == 404

    resp_hist = test_client.get("/api/v1/aircraft/NON-EXISTENT-AIRCRAFT/twin/history")
    assert resp_hist.status_code == 404
