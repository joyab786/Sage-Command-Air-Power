"""
Unit tests for SyntheticFlightGenerator.
Validates deterministic reproducibility, profile behavior, and data formatting.
"""

import pytest
from app.telemetry.generator import SyntheticFlightGenerator


def test_generator_deterministic_seed():
    gen1 = SyntheticFlightGenerator(seed=123)
    seq1 = gen1.generate_flight_sequence(aircraft_id="ac_test_01", profile="NORMAL_CRUISE", count=5)

    gen2 = SyntheticFlightGenerator(seed=123)
    seq2 = gen2.generate_flight_sequence(aircraft_id="ac_test_01", profile="NORMAL_CRUISE", count=5)

    # Identical seed must produce identical observations
    for f1, f2 in zip(seq1, seq2):
        assert f1.altitude == f2.altitude
        assert f1.airspeed == f2.airspeed
        assert f1.mach == f2.mach
        assert f1.g_load == f2.g_load
        assert f1.engine_temperature == f2.engine_temperature


def test_generator_all_supported_profiles():
    gen = SyntheticFlightGenerator(seed=999)
    for profile in SyntheticFlightGenerator.SUPPORTED_PROFILES:
        seq = gen.generate_flight_sequence(
            aircraft_id="ac_prof_01",
            profile=profile,
            count=4,
        )
        assert len(seq) == 4
        assert all(f.aircraft_id == "ac_prof_01" for f in seq)
        assert all(f.source == "synthetic_demo" for f in seq)
        assert all(f.altitude is not None for f in seq)
        assert all(f.mach is not None for f in seq)


def test_generator_thermal_and_vibration_spike_dynamics():
    gen = SyntheticFlightGenerator(seed=42)
    thermal_seq = gen.generate_flight_sequence(
        aircraft_id="ac_spike_01", profile="THERMAL_SPIKE", count=5
    )
    # Verify progressive temperature ascent in thermal spike
    temps = [f.engine_temperature for f in thermal_seq]
    assert temps[-1] > temps[0]

    vib_seq = gen.generate_flight_sequence(
        aircraft_id="ac_spike_02", profile="VIBRATION_SPIKE", count=5
    )
    vibs = [f.vibration for f in vib_seq]
    assert vibs[-1] > vibs[0]


def test_generator_unknown_profile_fails():
    gen = SyntheticFlightGenerator(seed=42)
    with pytest.raises(ValueError, match="Unknown flight profile"):
        gen.generate_flight_sequence(aircraft_id="ac_01", profile="WARP_DRIVE")
