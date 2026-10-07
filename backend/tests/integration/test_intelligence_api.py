"""
Integration tests for Subsystem Intelligence API Routes.
Verifies GET /anomalies, GET /anomalies/{id}, POST /acknowledge, POST /resolve,
GET /diagnosis, and GET /maintenance-recommendations endpoints.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import AircraftModel


@pytest.fixture
def intel_aircraft(db_session: Session) -> str:
    """Registers an aircraft for intelligence API testing."""
    aircraft_id = "INTEL-TEST-01"
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number="IT-001",
        aircraft_type="Dassault Rafale",
        air_base="Ambala AFS",
        squadron="Golden Arrows",
        status="ACTIVE",
        total_flight_hours=85.0,
        total_flight_cycles=42,
    )
    db_session.add(ac)
    db_session.commit()
    return aircraft_id


def test_empty_anomalies_and_diagnosis(test_client: TestClient, intel_aircraft: str):
    """Verifies that an aircraft with no anomalies returns empty list and nominal diagnosis."""
    # 1. Query anomalies
    resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/anomalies")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []

    # 2. Query diagnosis
    diag_resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/diagnosis")
    assert diag_resp.status_code == 200
    diag_body = diag_resp.json()
    assert diag_body["success"] is True
    assert diag_body["data"]["aircraft_id"] == intel_aircraft
    assert "nominal" in diag_body["data"]["probable_causes"][0].lower()

    # 3. Query maintenance recommendations
    rec_resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/maintenance-recommendations")
    assert rec_resp.status_code == 200
    rec_body = rec_resp.json()
    assert rec_body["success"] is True
    assert len(rec_body["data"]) == 1
    assert rec_body["data"][0]["priority"] == "MONITOR"


def test_telemetry_triggers_anomalies_and_api_queries(test_client: TestClient, intel_aircraft: str):
    """
    Ingests telemetry with thermal overtemperature.
    Verifies anomaly generation, querying by ID, acknowledging, and resolving via API.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": intel_aircraft,
        "flight_id": "SORTIE-INTEL-01",
        "timestamp": now,
        "source": "SIMULATOR",
        "altitude": 10000.0,
        "airspeed": 250.0,
        "mach": 0.85,
        "g_load": 1.0,
        "fuel_flow": 2200.0,
        "engine_temperature": 920.0,  # Critical thermal overtemp (> 850 °C)
        "engine_pressure": 380.0,
        "vibration": 0.2,
        "control_surface_angle": 2.0,
        "units": {
            "altitude": "m",
            "airspeed": "mps",
            "temperature": "C",
            "pressure": "kpa",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    }

    # 1. Ingest telemetry
    ingest_resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert ingest_resp.status_code == 201

    # 2. Verify anomaly appears in GET /anomalies
    anom_resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/anomalies")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()["data"]
    assert len(anomalies) >= 1

    thermal_anom = next(a for a in anomalies if a["anomaly_type"] == "THERMAL_ANOMALY")
    assert thermal_anom["severity"] == "CRITICAL"
    assert thermal_anom["status"] == "NEW"
    assert thermal_anom["observed_value"] == 920.0
    anom_id = thermal_anom["anomaly_id"]

    # 3. Query specific anomaly by ID
    detail_resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/anomalies/{anom_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["anomaly_id"] == anom_id
    assert detail["subsystem"] == "PROPULSION"

    # 4. Acknowledge the anomaly
    ack_resp = test_client.post(f"/api/v1/aircraft/{intel_aircraft}/anomalies/{anom_id}/acknowledge")
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()["data"]
    assert ack_data["status"] == "ACKNOWLEDGED"

    # 5. Resolve the anomaly
    res_resp = test_client.post(f"/api/v1/aircraft/{intel_aircraft}/anomalies/{anom_id}/resolve")
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]
    assert res_data["status"] == "RESOLVED"

    # 6. Verify cannot acknowledge an already resolved anomaly
    invalid_ack = test_client.post(f"/api/v1/aircraft/{intel_aircraft}/anomalies/{anom_id}/acknowledge")
    assert invalid_ack.status_code in [400, 422]


def test_diagnosis_and_maintenance_recommendations_after_anomaly(test_client: TestClient, intel_aircraft: str):
    """
    Ingests critical telemetry and verifies that diagnosis and maintenance recommendations
    reflect the elevated severity and recommend inspection or ground for review.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": intel_aircraft,
        "flight_id": "SORTIE-INTEL-02",
        "timestamp": now,
        "source": "SIMULATOR",
        "altitude": 8000.0,
        "airspeed": 230.0,
        "mach": 0.78,
        "g_load": 1.0,
        "fuel_flow": 2100.0,
        "engine_temperature": 910.0,
        "engine_pressure": 360.0,
        "vibration": 0.2,
        "units": {
            "altitude": "m",
            "airspeed": "mps",
            "temperature": "C",
            "pressure": "kpa",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    }

    ingest_resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert ingest_resp.status_code == 201

    # Check diagnosis
    diag_resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/diagnosis")
    assert diag_resp.status_code == 200
    diag = diag_resp.json()["data"]
    assert diag["primary_subsystem"] == "PROPULSION"
    assert diag["confidence"] >= 0.75

    # Check maintenance recommendations
    rec_resp = test_client.get(f"/api/v1/aircraft/{intel_aircraft}/maintenance-recommendations")
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["data"]
    assert len(recs) >= 1
    assert recs[0]["priority"] in ["GROUND_FOR_REVIEW", "SCHEDULE_MAINTENANCE"]
    assert recs[0]["affected_subsystem"] == "PROPULSION"


def test_api_404_for_unknown_aircraft(test_client: TestClient):
    """Verifies 404 responses for non-existent aircraft."""
    unknown = "NONEXISTENT-AC"
    assert test_client.get(f"/api/v1/aircraft/{unknown}/anomalies").status_code == 404
    assert test_client.get(f"/api/v1/aircraft/{unknown}/diagnosis").status_code == 404
    assert test_client.get(f"/api/v1/aircraft/{unknown}/maintenance-recommendations").status_code == 404
