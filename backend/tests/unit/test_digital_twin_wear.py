"""
SageCommand Air Power System (Aero) — Unit Tests: Wear Estimator.
Verifies operational wear index derivation, exposure stress increments,
subsystem wear allocation, and strict bounding in [0.0, 1.0].
"""

from datetime import datetime, timezone
from app.telemetry.models import NormalizedTelemetry
from app.digital_twin.models import (
    TwinSubsystemType,
    TwinHealthState,
    SubsystemState,
    utc_now,
)
from app.digital_twin.wear import WearEstimator


def _create_base_telemetry() -> NormalizedTelemetry:
    return NormalizedTelemetry(
        observation_id="obs_wear",
        aircraft_id="MKI-001",
        timestamp=datetime.now(timezone.utc),
        altitude_m=9000.0,
        airspeed_mps=240.0,
        mach=0.80,
        g_load=1.0,
        fuel_flow_kg_h=2000.0,
        engine_temperature_c=800.0,
        engine_pressure_kpa=1200.0,
        vibration_ips=0.35,
    )


def test_wear_zero_exposure():
    """Verifies that an airframe with 0 hours, 0 cycles, and benign sensors has 0.0 wear."""
    telem = _create_base_telemetry()
    wear = WearEstimator.calculate_wear(telem, flight_hours=0.0, flight_cycles=0)
    assert wear == 0.0


def test_wear_hours_and_cycles_scaling():
    """Verifies that accumulated flight hours and cycles increase wear predictably."""
    telem = _create_base_telemetry()
    # 2000 hours (half of 4000 TBO -> 0.20) + 1000 cycles (half of 2000 cycles -> 0.15) = 0.35
    wear = WearEstimator.calculate_wear(telem, flight_hours=2000.0, flight_cycles=1000)
    assert 0.34 <= wear <= 0.36


def test_wear_dynamic_stress_exposures():
    """Verifies thermal, vibration, and high-G dynamic stress increments."""
    telem = _create_base_telemetry()
    telem.engine_temperature_c = 1050.0  # + thermal increment
    telem.vibration_ips = 1.30          # + vibration increment
    telem.g_load = 8.5                  # + high-G increment

    wear = WearEstimator.calculate_wear(telem, flight_hours=500.0, flight_cycles=200)
    base_wear = WearEstimator.calculate_wear(_create_base_telemetry(), flight_hours=500.0, flight_cycles=200)

    assert wear > base_wear
    assert wear <= 1.0


def test_wear_strict_bounds_and_monotonicity():
    """Verifies wear is strictly clamped between 0.0 and 1.0 and retains baseline."""
    telem = _create_base_telemetry()
    telem.engine_temperature_c = 1500.0
    telem.vibration_ips = 3.0
    telem.g_load = 15.0

    wear = WearEstimator.calculate_wear(telem, flight_hours=10000.0, flight_cycles=10000)
    assert wear == 1.0  # Clamped at 1.0

    # Retains previous wear index even if stress ceases
    benign_telem = _create_base_telemetry()
    subsequent_wear = WearEstimator.calculate_wear(
        benign_telem,
        flight_hours=100.0,
        flight_cycles=50,
        previous_wear_index=0.45,
    )
    assert subsequent_wear >= 0.45


def test_subsystem_wear_application():
    """Verifies that individual subsystems receive appropriate wear indices."""
    now = utc_now()
    subsystems = {
        s.value: SubsystemState(
            subsystem=s,
            health_state=TwinHealthState.HEALTHY,
            health_score=100.0,
            wear_index=0.0,
            last_updated_at=now,
        )
        for s in TwinSubsystemType
    }

    telem = _create_base_telemetry()
    telem.engine_temperature_c = 1020.0
    telem.g_load = 8.2

    WearEstimator.apply_subsystem_wear(
        subsystems=subsystems,
        telemetry=telem,
        flight_hours=1000.0,
        flight_cycles=500,
    )

    prop_wear = subsystems[TwinSubsystemType.PROPULSION.value].wear_index
    struct_wear = subsystems[TwinSubsystemType.STRUCTURE.value].wear_index
    hyd_wear = subsystems[TwinSubsystemType.HYDRAULIC.value].wear_index

    assert prop_wear > 0.0
    assert struct_wear > 0.0
    assert hyd_wear == 0.0  # Unobserved
