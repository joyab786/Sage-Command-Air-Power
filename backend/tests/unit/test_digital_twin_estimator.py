"""
SageCommand Air Power System (Aero) — Unit Tests: Digital Twin State Estimator.
Verifies telemetry-to-twin mapping, previous state retention across sparse frames,
and operational status transitions.
"""

from datetime import datetime, timezone, timedelta
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import AircraftTwinState, TwinHealthState
from app.digital_twin.estimator import DigitalTwinEstimator


def test_estimator_full_frame():
    """Verifies complete mapping of all telemetry channels to twin state."""
    now = datetime.now(timezone.utc)
    telemetry = NormalizedTelemetry(
        observation_id="obs_001",
        aircraft_id="TEJAS-LA001",
        flight_id="FLT-100",
        timestamp=now,
        altitude_m=9000.0,
        airspeed_mps=280.0,
        mach=0.92,
        g_load=1.2,
        fuel_flow_kg_h=2100.0,
        engine_temperature_c=820.0,
        engine_pressure_kpa=1350.0,
        vibration_ips=0.42,
        quality_status=QualityStatus.VALID,
        envelope_status=EnvelopeStatus.WITHIN_ENVELOPE,
    )

    state = DigitalTwinEstimator.estimate_state(
        telemetry=telemetry,
        previous_state=None,
        flight_hours=10.5,
        flight_cycles=4,
    )

    assert state.aircraft_id == "TEJAS-LA001"
    assert state.timestamp == now
    assert state.current_flight_id == "FLT-100"
    assert state.altitude == 9000.0
    assert state.airspeed == 280.0
    assert state.mach == 0.92
    assert state.g_load == 1.2
    assert state.fuel_flow == 2100.0
    assert state.engine_temperature == 820.0
    assert state.engine_pressure == 1350.0
    assert state.vibration == 0.42
    assert state.flight_hours == 10.5
    assert state.flight_cycles == 4
    assert state.operational_status == "IN_FLIGHT"
    assert state.health_state == TwinHealthState.HEALTHY


def test_estimator_sparse_frame_preserves_previous_state():
    """
    CRITICAL TEST: Verifies that missing fields in a new telemetry frame
    do NOT overwrite valid prior state with None or zeroes.
    """
    t0 = datetime.now(timezone.utc) - timedelta(seconds=10)
    t1 = datetime.now(timezone.utc)

    # Initial frame with full altitude, airspeed, temperature, and pressure
    initial_telemetry = NormalizedTelemetry(
        observation_id="obs_init",
        aircraft_id="MKI-SB002",
        flight_id="FLT-200",
        timestamp=t0,
        altitude_m=8500.0,
        airspeed_mps=240.0,
        mach=0.80,
        g_load=1.0,
        fuel_flow_kg_h=2300.0,
        engine_temperature_c=810.0,
        engine_pressure_kpa=1400.0,
        vibration_ips=0.30,
    )

    state_prev = DigitalTwinEstimator.estimate_state(
        telemetry=initial_telemetry,
        previous_state=None,
    )
    assert state_prev.altitude == 8500.0
    assert state_prev.engine_temperature == 810.0

    # New frame omitting altitude, engine_pressure, and fuel_flow
    sparse_telemetry = NormalizedTelemetry(
        observation_id="obs_sparse",
        aircraft_id="MKI-SB002",
        flight_id="FLT-200",
        timestamp=t1,
        altitude_m=None,       # Omitted
        airspeed_mps=250.0,    # Updated
        mach=0.83,             # Updated
        g_load=1.1,
        fuel_flow_kg_h=None,   # Omitted
        engine_temperature_c=815.0, # Updated
        engine_pressure_kpa=None,   # Omitted
        vibration_ips=0.32,
    )

    state_new = DigitalTwinEstimator.estimate_state(
        telemetry=sparse_telemetry,
        previous_state=state_prev,
    )

    # Retained previous values
    assert state_new.altitude == 8500.0
    assert state_new.fuel_flow == 2300.0
    assert state_new.engine_pressure == 1400.0

    # Updated values
    assert state_new.airspeed == 250.0
    assert state_new.mach == 0.83
    assert state_new.engine_temperature == 815.0
    assert state_new.timestamp == t1
