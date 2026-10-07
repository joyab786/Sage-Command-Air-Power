"""
SageCommand Air Power System (Aero) — Unit Tests: Digital Twin Persistence.
Verifies relational storage of twin states, history snapshot retrieval,
and default baseline initialization under SQLite.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.db.models import AircraftModel
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import TwinHealthState
from app.digital_twin.service import DigitalTwinService


def _create_aircraft(db: Session, aircraft_id: str = "RAFALE-TWIN-01") -> AircraftModel:
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number=f"T-{aircraft_id}",
        aircraft_type="Dassault Rafale",
        air_base="Ambala AFS",
        squadron="No. 17 Squadron",
        status="ACTIVE",
        total_flight_hours=50.0,
        total_flight_cycles=25,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def test_twin_persistence_and_latest_state(db_session: Session):
    """Verifies that processing telemetry persists twin state and latest state is queryable."""
    service = DigitalTwinService()
    aircraft = _create_aircraft(db_session, "RAFALE-P1")

    # Initial state query before any telemetry arrives returns baseline
    baseline = service.get_current_state(db_session, aircraft.aircraft_id)
    assert baseline.aircraft_id == aircraft.aircraft_id
    assert baseline.data_quality == "BASELINE"
    assert baseline.health_state == TwinHealthState.HEALTHY
    assert baseline.flight_hours == 50.0

    # Ingest telemetry
    now = datetime.now(timezone.utc)
    telem = NormalizedTelemetry(
        observation_id="obs_p1",
        aircraft_id=aircraft.aircraft_id,
        flight_id="MISSION-10",
        timestamp=now,
        altitude_m=11000.0,
        airspeed_mps=260.0,
        mach=0.88,
        g_load=1.05,
        engine_temperature_c=830.0,
        engine_pressure_kpa=1380.0,
        vibration_ips=0.34,
        quality_status=QualityStatus.VALID,
    )
    saved = service.process_telemetry(db_session, telem)
    assert saved.altitude == 11000.0

    # Now get_current_state returns the persisted estimated state
    current = service.get_current_state(db_session, aircraft.aircraft_id)
    assert current.altitude == 11000.0
    assert current.airspeed == 260.0
    assert current.health_score >= 90.0
    assert current.data_quality == "VALID"


def test_twin_state_history(db_session: Session):
    """Verifies that historical snapshots are retained chronologically."""
    service = DigitalTwinService()
    aircraft = _create_aircraft(db_session, "RAFALE-P2")
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    # Ingest 3 successive observations
    for i in range(3):
        t = base_time + timedelta(seconds=i * 30)
        telem = NormalizedTelemetry(
            observation_id=f"obs_hist_{i}",
            aircraft_id=aircraft.aircraft_id,
            flight_id="MISSION-20",
            timestamp=t,
            altitude_m=8000.0 + (i * 500),
            airspeed_mps=200.0 + (i * 10),
            engine_temperature_c=800.0,
            engine_pressure_kpa=1300.0,
            vibration_ips=0.30,
            quality_status=QualityStatus.VALID,
        )
        service.process_telemetry(db_session, telem)

    history = service.get_state_history(db_session, aircraft.aircraft_id, limit=10)
    assert len(history) == 3
    # Ordered descending by timestamp (latest first)
    assert history[0].altitude == 9000.0
    assert history[1].altitude == 8500.0
    assert history[2].altitude == 8000.0


def test_twin_reset_state(db_session: Session):
    """Verifies state reset purges history."""
    service = DigitalTwinService()
    aircraft = _create_aircraft(db_session, "RAFALE-P3")
    telem = NormalizedTelemetry(
        observation_id="obs_rst",
        aircraft_id=aircraft.aircraft_id,
        flight_id="MISSION-30",
        timestamp=datetime.now(timezone.utc),
        altitude_m=5000.0,
        airspeed_mps=180.0,
        engine_temperature_c=800.0,
        engine_pressure_kpa=1200.0,
        vibration_ips=0.30,
        quality_status=QualityStatus.VALID,
    )
    service.process_telemetry(db_session, telem)
    assert len(service.get_state_history(db_session, aircraft.aircraft_id)) == 1

    service.reset_state(db_session, aircraft.aircraft_id)
    assert len(service.get_state_history(db_session, aircraft.aircraft_id)) == 0
