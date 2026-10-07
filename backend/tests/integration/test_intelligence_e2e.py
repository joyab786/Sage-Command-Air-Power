"""
End-to-End Synthetic Scenario Tests for Phase 5 Subsystem Intelligence (SIH MVP).
Demonstrates:
1. Normal Cruise -> Healthy twin, zero anomalies, routine MONITOR recommendation.
2. Thermal Spike -> Digital twin degradation, THERMAL_ANOMALY, propulsion diagnosis, inspection recommendation.
3. Vibration Spike -> VIBRATION_ANOMALY, propulsion rotating machinery diagnosis.
4. High-G Turn -> G_LOAD_ANOMALY, structural stress diagnosis.
5. Combined Scenario -> Multi-signal correlation, elevated diagnostic confidence, GROUND_FOR_REVIEW recommendation.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import AircraftModel


@pytest.fixture
def demonstration_aircraft(db_session: Session) -> str:
    """Creates authoritative aircraft for end-to-end SIH demonstration."""
    aircraft_id = "AERO-001"
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number="TS-001",
        aircraft_type="HAL Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="Flying Daggers",
        status="ACTIVE",
        total_flight_hours=140.0,
        total_flight_cycles=70,
    )
    db_session.add(ac)
    db_session.commit()
    return aircraft_id


def test_scenario_normal_cruise(test_client: TestClient, demonstration_aircraft: str):
    """
    Scenario 1: Normal Cruise
    Expected: No anomalies detected, nominal diagnosis, routine monitoring recommendation.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": demonstration_aircraft,
        "flight_id": "SORTIE-NORM-01",
        "timestamp": now,
        "source": "SYNTHETIC_GENERATOR",
        "altitude": 8500.0,
        "airspeed": 240.0,
        "mach": 0.80,
        "g_load": 1.0,
        "fuel_flow": 2100.0,
        "engine_temperature": 640.0,  # Well below 780 °C caution
        "engine_pressure": 350.0,   # Nominal range
        "vibration": 0.2,           # Nominal vibration
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
    resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert resp.status_code == 201

    # 2. Verify twin state is healthy
    twin_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/twin")
    assert twin_resp.status_code == 200
    assert twin_resp.json()["data"]["health_state"] == "HEALTHY"

    # 3. Verify zero anomalies
    anom_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/anomalies")
    assert anom_resp.status_code == 200
    assert anom_resp.json()["data"] == []

    # 4. Verify nominal diagnosis
    diag_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/diagnosis")
    assert diag_resp.status_code == 200
    assert "nominal" in diag_resp.json()["data"]["probable_causes"][0].lower()

    # 5. Verify MONITOR recommendation
    rec_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/maintenance-recommendations")
    assert rec_resp.status_code == 200
    assert rec_resp.json()["data"][0]["priority"] == "MONITOR"


def test_scenario_thermal_spike(test_client: TestClient, demonstration_aircraft: str):
    """
    Scenario 2: Thermal Spike
    Expected: THERMAL_ANOMALY on PROPULSION with HIGH/CRITICAL severity and explainable evidence.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": demonstration_aircraft,
        "flight_id": "SORTIE-THERMAL-01",
        "timestamp": now,
        "source": "SYNTHETIC_GENERATOR",
        "altitude": 8500.0,
        "airspeed": 240.0,
        "mach": 0.80,
        "g_load": 1.0,
        "fuel_flow": 2800.0,
        "engine_temperature": 925.0,  # Exceeds 850 °C critical threshold
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
    resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert resp.status_code == 201

    # 2. Check digital twin degradation
    twin_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/twin")
    assert twin_resp.status_code == 200
    twin_data = twin_resp.json()["data"]
    assert twin_data["health_state"] in ["DEGRADED", "CRITICAL"]

    # 3. Check anomaly detection
    anom_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/anomalies")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()["data"]
    thermal_anoms = [a for a in anomalies if a["anomaly_type"] == "THERMAL_ANOMALY"]
    assert len(thermal_anoms) >= 1
    anom = thermal_anoms[0]
    assert anom["subsystem"] == "PROPULSION"
    assert anom["severity"] == "CRITICAL"
    assert anom["confidence"] >= 0.85
    assert len(anom["evidence"]) > 0

    # 4. Check root-cause diagnosis
    diag_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/diagnosis")
    assert diag_resp.status_code == 200
    diag = diag_resp.json()["data"]
    assert diag["primary_subsystem"] == "PROPULSION"
    assert any("thermal" in cause.lower() for cause in diag["probable_causes"])

    # 5. Check maintenance recommendations
    rec_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/maintenance-recommendations")
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["data"]
    assert len(recs) >= 1
    assert recs[0]["priority"] in ["GROUND_FOR_REVIEW", "SCHEDULE_MAINTENANCE"]
    assert recs[0]["affected_subsystem"] == "PROPULSION"


def test_scenario_vibration_spike(test_client: TestClient, demonstration_aircraft: str):
    """
    Scenario 3: Vibration Spike
    Expected: VIBRATION_ANOMALY on PROPULSION with rotating machinery diagnosis.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": demonstration_aircraft,
        "flight_id": "SORTIE-VIB-01",
        "timestamp": now,
        "source": "SYNTHETIC_GENERATOR",
        "altitude": 7000.0,
        "airspeed": 220.0,
        "mach": 0.72,
        "g_load": 1.0,
        "fuel_flow": 2000.0,
        "engine_temperature": 660.0,
        "engine_pressure": 340.0,
        "vibration": 3.8,  # Critical vibration (> 3.0 ips)
        "control_surface_angle": 1.0,
        "units": {
            "altitude": "m",
            "airspeed": "mps",
            "temperature": "C",
            "pressure": "kpa",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    }

    resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert resp.status_code == 201

    anom_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/anomalies")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()["data"]
    vib_anoms = [a for a in anomalies if a["anomaly_type"] == "VIBRATION_ANOMALY"]
    assert len(vib_anoms) >= 1
    assert vib_anoms[0]["subsystem"] == "PROPULSION"
    assert vib_anoms[0]["severity"] == "CRITICAL"


def test_scenario_high_g_turn(test_client: TestClient, demonstration_aircraft: str):
    """
    Scenario 4: High-G Turn
    Expected: G_LOAD_ANOMALY on STRUCTURE with load factor diagnosis.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": demonstration_aircraft,
        "flight_id": "SORTIE-GLOAD-01",
        "timestamp": now,
        "source": "SYNTHETIC_GENERATOR",
        "altitude": 6000.0,
        "airspeed": 300.0,
        "mach": 0.92,
        "g_load": 8.6,  # Critical G-load (> 8.0g)
        "fuel_flow": 3200.0,
        "engine_temperature": 700.0,
        "engine_pressure": 380.0,
        "vibration": 0.2,
        "control_surface_angle": 15.0,
        "units": {
            "altitude": "m",
            "airspeed": "mps",
            "temperature": "C",
            "pressure": "kpa",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    }

    resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert resp.status_code == 201

    anom_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/anomalies")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()["data"]
    g_anoms = [a for a in anomalies if a["anomaly_type"] == "G_LOAD_ANOMALY"]
    assert len(g_anoms) >= 1
    assert g_anoms[0]["subsystem"] == "STRUCTURE"
    assert g_anoms[0]["severity"] == "CRITICAL"


def test_scenario_combined_multi_signal_correlation(test_client: TestClient, demonstration_aircraft: str):
    """
    Scenario 5: Combined Multi-Signal (Thermal + Vibration + Pressure)
    Expected: Multiple signal violations trigger multi-signal correlation,
    elevating diagnostic confidence above 0.90 and generating GROUND_FOR_REVIEW recommendation.
    """
    now = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "aircraft_id": demonstration_aircraft,
        "flight_id": "SORTIE-COMBINED-01",
        "timestamp": now,
        "source": "SYNTHETIC_GENERATOR",
        "altitude": 9000.0,
        "airspeed": 260.0,
        "mach": 0.84,
        "g_load": 1.2,
        "fuel_flow": 2700.0,
        "engine_temperature": 910.0,  # Critical thermal (> 850 °C)
        "engine_pressure": 660.0,   # Pressure exceedance (> 650 kPa)
        "vibration": 3.6,           # Critical vibration (> 3.0 ips)
        "control_surface_angle": 3.0,
        "units": {
            "altitude": "m",
            "airspeed": "mps",
            "temperature": "C",
            "pressure": "kpa",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    }

    resp = test_client.post("/api/v1/telemetry", json=telemetry_payload)
    assert resp.status_code == 201

    # Verify diagnosis
    diag_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/diagnosis")
    assert diag_resp.status_code == 200
    diag = diag_resp.json()["data"]
    assert diag["primary_subsystem"] == "PROPULSION"
    # Multi-signal agreement drives confidence above 0.90
    assert diag["confidence"] >= 0.90
    assert any("multi-signal" in cause.lower() or "thermal and mechanical" in cause.lower() for cause in diag["probable_causes"])

    # Verify recommendation
    rec_resp = test_client.get(f"/api/v1/aircraft/{demonstration_aircraft}/maintenance-recommendations")
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["data"]
    assert len(recs) >= 1
    assert recs[0]["priority"] == "GROUND_FOR_REVIEW"
    assert recs[0]["affected_subsystem"] == "PROPULSION"
    assert recs[0]["confidence"] >= 0.90
