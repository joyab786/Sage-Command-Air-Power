"""
SageCommand Air Power System (Aero) — Unit Tests: Flight Sessions and Operational Counters.
Verifies flight session lifecycle, elapsed duration tracking,
and cycle increment idempotency across multiple telemetry frames.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.db.models import AircraftModel, FlightSessionModel
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.service import DigitalTwinService


def _setup_test_aircraft(db: Session, aircraft_id: str = "SU30-SESS-01") -> AircraftModel:
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number=f"T-{aircraft_id}",
        aircraft_type="SU-30MKI",
        air_base="Pune AFS",
        squadron="No. 20 Squadron",
        status="ACTIVE",
        total_flight_hours=0.0,
        total_flight_cycles=0,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def test_flight_session_creation_and_no_double_counting(db_session: Session):
    """
    CRITICAL TEST: Ingesting multiple telemetry frames for the SAME flight_id
    must update elapsed hours but MUST NOT increment flight cycles repeatedly.
    """
    service = DigitalTwinService()
    aircraft = _setup_test_aircraft(db_session, "SU30-TEST-01")

    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Frame 1: Flight starts
    f1 = NormalizedTelemetry(
        observation_id="obs_f1",
        aircraft_id=aircraft.aircraft_id,
        flight_id="SORTIE-01",
        timestamp=base_time,
        altitude_m=500.0,
        airspeed_mps=120.0,
        mach=0.35,
        g_load=1.1,
        engine_temperature_c=750.0,
        engine_pressure_kpa=1200.0,
        vibration_ips=0.30,
        quality_status=QualityStatus.VALID,
    )
    state1 = service.process_telemetry(db_session, f1)

    assert state1.flight_cycles == 0
    assert state1.flight_hours == 0.0

    # Frame 2: 120 seconds later in the same flight
    f2 = NormalizedTelemetry(
        observation_id="obs_f2",
        aircraft_id=aircraft.aircraft_id,
        flight_id="SORTIE-01",
        timestamp=base_time + timedelta(seconds=120),
        altitude_m=3000.0,
        airspeed_mps=200.0,
        mach=0.60,
        g_load=1.0,
        engine_temperature_c=800.0,
        engine_pressure_kpa=1300.0,
        vibration_ips=0.32,
        quality_status=QualityStatus.VALID,
    )
    state2 = service.process_telemetry(db_session, f2)

    # Cycles MUST still be 0 (flight is still in progress)
    assert state2.flight_cycles == 0
    # Flight hours should reflect 120 seconds = 120/3600 = ~0.033 hours
    assert state2.flight_hours > 0.0
    assert round(state2.flight_hours, 2) == 0.03

    # Frame 3: Another 180 seconds later (total 300s)
    f3 = NormalizedTelemetry(
        observation_id="obs_f3",
        aircraft_id=aircraft.aircraft_id,
        flight_id="SORTIE-01",
        timestamp=base_time + timedelta(seconds=300),
        altitude_m=6000.0,
        airspeed_mps=240.0,
        mach=0.75,
        g_load=1.0,
        engine_temperature_c=810.0,
        engine_pressure_kpa=1350.0,
        vibration_ips=0.31,
        quality_status=QualityStatus.VALID,
    )
    state3 = service.process_telemetry(db_session, f3)

    assert state3.flight_cycles == 0
    assert round(state3.flight_hours, 2) == 0.08


def test_session_close_increments_cycle_once(db_session: Session):
    """Verifies that concluding a flight increments cycle count exactly once."""
    service = DigitalTwinService()
    aircraft = _setup_test_aircraft(db_session, "SU30-TEST-02")
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    telem = NormalizedTelemetry(
        observation_id="obs_c1",
        aircraft_id=aircraft.aircraft_id,
        flight_id="SORTIE-02",
        timestamp=base_time,
        altitude_m=2000.0,
        airspeed_mps=150.0,
        mach=0.45,
        g_load=1.0,
        engine_temperature_c=780.0,
        engine_pressure_kpa=1250.0,
        vibration_ips=0.30,
        quality_status=QualityStatus.VALID,
    )
    service.process_telemetry(db_session, telem)

    # Conclude the flight explicitly
    session = service.close_flight(db_session, aircraft_id=aircraft.aircraft_id, flight_id="SORTIE-02")
    assert session is not None
    assert session.cycle_counted is True

    # Aircraft cycles now incremented by 1
    db_session.refresh(aircraft)
    assert aircraft.total_flight_cycles == 1

    # Closing again should be a no-op (idempotent)
    session2 = service.close_flight(db_session, aircraft_id=aircraft.aircraft_id, flight_id="SORTIE-02")
    assert session2 is None
    db_session.refresh(aircraft)
    assert aircraft.total_flight_cycles == 1


def test_new_flight_id_closes_previous_session(db_session: Session):
    """Verifies that starting a new flight_id automatically transitions previous flight session."""
    service = DigitalTwinService()
    aircraft = _setup_test_aircraft(db_session, "SU30-TEST-03")
    t0 = datetime.now(timezone.utc) - timedelta(minutes=20)
    t1 = datetime.now(timezone.utc) - timedelta(minutes=5)

    # Sortie A
    f_a = NormalizedTelemetry(
        observation_id="obs_a",
        aircraft_id=aircraft.aircraft_id,
        flight_id="SORTIE-ALPHA",
        timestamp=t0,
        altitude_m=4000.0,
        airspeed_mps=200.0,
        mach=0.60,
        g_load=1.0,
        engine_temperature_c=790.0,
        engine_pressure_kpa=1300.0,
        vibration_ips=0.30,
        quality_status=QualityStatus.VALID,
    )
    service.process_telemetry(db_session, f_a)

    # Sortie B arrives
    f_b = NormalizedTelemetry(
        observation_id="obs_b",
        aircraft_id=aircraft.aircraft_id,
        flight_id="SORTIE-BRAVO",
        timestamp=t1,
        altitude_m=1000.0,
        airspeed_mps=150.0,
        mach=0.45,
        g_load=1.0,
        engine_temperature_c=760.0,
        engine_pressure_kpa=1220.0,
        vibration_ips=0.28,
        quality_status=QualityStatus.VALID,
    )
    state_b = service.process_telemetry(db_session, f_b)

    # SORTIE-ALPHA was closed, incrementing cycle count to 1
    assert state_b.flight_cycles == 1
    assert state_b.current_flight_id == "SORTIE-BRAVO"
