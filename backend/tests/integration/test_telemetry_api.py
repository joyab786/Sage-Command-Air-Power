"""
Integration tests for Aero Telemetry API Endpoints.
Validates HTTP request routing, single/batch ingestion, recent and historical queries,
synthetic demo generation, and edge-case handling.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_aircraft(test_client: TestClient):
    """Ensures test host aircraft is registered before telemetry tests."""
    ac_payload = {
        "aircraft_id": "ac_telem_test",
        "tail_number": "TL-101",
        "aircraft_type": "Su-30MKI",
        "air_base": "Pune AFS",
        "squadron": "No. 20 Lightnings",
    }
    test_client.post("/api/v1/aircraft", json=ac_payload)


def test_telemetry_single_ingest_success(test_client: TestClient):
    payload = {
        "observation_id": "obs_api_01",
        "aircraft_id": "ac_telem_test",
        "flight_id": "flt_test_01",
        "altitude": 32000.0,
        "airspeed": 480.0,
        "mach": 0.82,
        "g_load": 1.1,
        "fuel_flow": 2400.0,
        "engine_temperature": 640.0,
        "engine_pressure": 45.0,
        "vibration": 0.18,
        "units": {
            "altitude": "ft",
            "airspeed": "kts",
            "temperature": "C",
            "pressure": "psi",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    }
    resp = test_client.post("/api/v1/telemetry", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["accepted"] is True
    assert data["observation_id"] == "obs_api_01"
    assert data["normalized"]["altitude_m"] == 9753.6
    assert data["envelope"]["status"] == "WITHIN_ENVELOPE"


def test_telemetry_ingest_unknown_aircraft_fails(test_client: TestClient):
    payload = {
        "aircraft_id": "ac_non_existent",
        "altitude": 10000.0,
        "airspeed": 300.0,
    }
    resp = test_client.post("/api/v1/telemetry", json=payload)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_telemetry_ingest_envelope_violation_reported(test_client: TestClient):
    payload = {
        "aircraft_id": "ac_telem_test",
        "altitude": 10000.0,
        "airspeed": 400.0,
        "mach": 0.8,
        "g_load": 9.8, # Exceeds 9.0G hard limit!
        "units": {"altitude": "m", "airspeed": "mps"},
    }
    resp = test_client.post("/api/v1/telemetry", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["accepted"] is True
    assert data["envelope"]["status"] == "EXCEEDED"
    assert len(data["envelope"]["violations"]) == 1
    assert data["envelope"]["violations"][0]["parameter"] == "g_load"


def test_telemetry_batch_ingest(test_client: TestClient):
    batch_payload = {
        "observations": [
            {
                "observation_id": f"obs_b_{i}",
                "aircraft_id": "ac_telem_test",
                "altitude": 10000.0 + (i * 500),
                "airspeed": 300.0,
            }
            for i in range(4)
        ]
    }
    resp = test_client.post("/api/v1/telemetry/batch", json=batch_payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["total_received"] == 4
    assert data["total_accepted"] == 4
    assert data["total_rejected"] == 0


def test_telemetry_recent_endpoint(test_client: TestClient):
    resp = test_client.get("/api/v1/telemetry/recent?limit=10")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


def test_aircraft_telemetry_history_endpoint(test_client: TestClient):
    resp = test_client.get("/api/v1/aircraft/ac_telem_test/telemetry?limit=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


def test_aircraft_telemetry_unknown_aircraft_404(test_client: TestClient):
    resp = test_client.get("/api/v1/aircraft/ac_phantom_99/telemetry")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_telemetry_demo_generate_endpoint(test_client: TestClient):
    payload = {
        "aircraft_id": "ac_telem_test",
        "profile": "SUPERSONIC_CRUISE",
        "count": 5,
        "seed": 42,
    }
    resp = test_client.post("/api/v1/telemetry/demo/generate", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["total_received"] == 5
    assert data["total_accepted"] == 5
    assert data["total_rejected"] == 0


def test_telemetry_empty_batch_validation_error(test_client: TestClient):
    resp = test_client.post("/api/v1/telemetry/batch", json={"observations": []})
    assert resp.status_code == 422
