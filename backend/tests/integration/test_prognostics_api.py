"""
Integration tests for SageCommand Aero Prognostics API Endpoints.
Verifies GET /prognostics, GET /prognostics/history, GET /health-trend,
and GET /maintenance-forecast endpoints, including 404s, filtering, and persistence.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import AircraftModel, AircraftTwinStateModel, PrognosticRecordModel


@pytest.fixture
def prog_aircraft(db_session: Session) -> str:
    """Registers an aircraft and twin state for prognostics API testing."""
    aircraft_id = "PROG-TEST-01"
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number="PT-001",
        aircraft_type="HAL Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="Flying Daggers",
        status="ACTIVE",
        total_flight_hours=120.0,
        total_flight_cycles=65,
    )
    db_session.add(ac)

    # Add initial twin state
    twin = AircraftTwinStateModel(
        state_id="twin-prog-01",
        aircraft_id=aircraft_id,
        timestamp=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        operational_status="ACTIVE",
        health_score=95.0,
        wear_index=0.08,
        flight_hours=120.0,
        flight_cycles=65,
        subsystem_states={
            "PROPULSION": {"health": 95.0, "wear": 0.08},
            "AVIONICS": {"health": 99.0, "wear": 0.02},
        },
    )
    db_session.add(twin)
    db_session.commit()
    return aircraft_id


def test_get_prognostics_nominal(test_client: TestClient, prog_aircraft: str):
    """Verifies GET /prognostics computes assessment, validates bounds, and persists record."""
    resp = test_client.get(f"/api/v1/aircraft/{prog_aircraft}/prognostics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    data = body["data"]
    assert data["aircraft_id"] == prog_aircraft
    assert data["primary_subsystem"] == "PROPULSION"

    rul = data["rul"]
    assert rul["estimated_rul_hours"] >= 0.0
    assert rul["lower_bound_hours"] <= rul["estimated_rul_hours"] <= rul["upper_bound_hours"]
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["readiness_impact"] in ["FMC_SUPPORTED", "PMC_RESTRICTED", "NMC_GROUNDED"]

    # Verify that assessment was persisted in prognostic history
    hist_resp = test_client.get(f"/api/v1/aircraft/{prog_aircraft}/prognostics/history")
    assert hist_resp.status_code == 200
    hist_body = hist_resp.json()
    assert hist_body["success"] is True
    assert len(hist_body["data"]) >= 1
    assert hist_body["data"][0]["aircraft_id"] == prog_aircraft


def test_get_health_trend_api(test_client: TestClient, prog_aircraft: str):
    """Verifies GET /health-trend returns OLS degradation trend."""
    resp = test_client.get(f"/api/v1/aircraft/{prog_aircraft}/health-trend?subsystem=PROPULSION")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    trend = body["data"]
    assert trend["aircraft_id"] == prog_aircraft
    assert trend["subsystem"] == "PROPULSION"
    assert trend["trend_direction"] in ["STABLE", "DEGRADING", "IMPROVING", "INSUFFICIENT_DATA"]
    assert 0.0 <= trend["confidence"] <= 1.0


def test_get_maintenance_forecast_api(test_client: TestClient, prog_aircraft: str):
    """Verifies GET /maintenance-forecast returns prioritized forecast."""
    resp = test_client.get(f"/api/v1/aircraft/{prog_aircraft}/maintenance-forecast")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    forecast = body["data"]
    assert forecast["aircraft_id"] == prog_aircraft
    assert forecast["priority"] in [
        "MONITOR",
        "PLAN_MAINTENANCE",
        "INSPECT_SOON",
        "PRIORITY_INSPECTION",
        "GROUND_FOR_REVIEW",
    ]
    assert len(forecast["action"]) > 0
    assert len(forecast["explanation"]) > 0


def test_prognostics_404_for_unknown_aircraft(test_client: TestClient):
    """Verifies that queries for a non-existent aircraft return 404."""
    unknown = "NON-EXISTENT-AIRCRAFT-999"

    resp1 = test_client.get(f"/api/v1/aircraft/{unknown}/prognostics")
    assert resp1.status_code == 404

    resp2 = test_client.get(f"/api/v1/aircraft/{unknown}/health-trend")
    assert resp2.status_code == 404

    resp3 = test_client.get(f"/api/v1/aircraft/{unknown}/maintenance-forecast")
    assert resp3.status_code == 404

    resp4 = test_client.get(f"/api/v1/aircraft/{unknown}/prognostics/history")
    assert resp4.status_code == 404


def test_prognostics_history_pagination(test_client: TestClient, prog_aircraft: str, db_session: Session):
    """Tests pagination limits on historical prognostic records."""
    # Seed multiple prognostic records
    for i in range(5):
        record = PrognosticRecordModel(
            record_id=f"rec-page-{i}",
            aircraft_id=prog_aircraft,
            timestamp=datetime(2026, 10, 1, 12, i, tzinfo=timezone.utc),
            subsystem="PROPULSION",
            health_score=90.0 - i,
            wear_index=0.10,
            trend_direction="DEGRADING",
            degradation_rate=1.0,
            slope=-1.0,
            estimated_rul_hours=65.0 - i,
            estimated_rul_cycles=32,
            lower_bound_hours=50.0,
            upper_bound_hours=80.0,
            confidence=0.88,
            forecast_priority="INSPECT_SOON",
            prediction_method="TREND_LINEAR_EXTRAPOLATION",
            limiting_factors=["Test factor"],
            explanation="Pagination test record",
            recommended_action="Inspect",
        )
        db_session.add(record)
    db_session.commit()

    resp = test_client.get(f"/api/v1/aircraft/{prog_aircraft}/prognostics/history?limit=2")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
