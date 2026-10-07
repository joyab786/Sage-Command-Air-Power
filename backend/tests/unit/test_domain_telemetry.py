"""
Unit tests for Telemetry domain contract and validation rules.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.domain.telemetry import TelemetryObservation
from app.domain.enums import TelemetryQuality


def test_telemetry_observation_full():
    now = datetime.now(timezone.utc)
    obs = TelemetryObservation(
        observation_id="obs_001",
        timestamp=now,
        aircraft_id="ac_su30_01",
        flight_id="flight_sort_101",
        altitude_ft=28500.0,
        airspeed_kts=540.0,
        mach=1.45,
        g_load=4.2,
        fuel_flow_kg_h=3200.0,
        engine_temperature_c=745.0,
        engine_pressure_psi=48.5,
        vibration_ips=0.22,
        control_surface_angle_deg=12.5,
        quality=TelemetryQuality.GOOD,
        source="SIMULATION",
        unit_metadata={"altitude": "ft", "mach": "ratio", "egt": "C"},
    )
    assert obs.observation_id == "obs_001"
    assert obs.mach == 1.45
    assert obs.g_load == 4.2
    assert obs.quality == TelemetryQuality.GOOD


def test_telemetry_partial_observation():
    now = datetime.now(timezone.utc)
    obs = TelemetryObservation(
        observation_id="obs_partial_001",
        timestamp=now,
        aircraft_id="ac_su30_01",
        altitude_ft=12000.0,
    )
    assert obs.altitude_ft == 12000.0
    assert obs.mach is None
    assert obs.vibration_ips is None
    assert obs.quality == TelemetryQuality.GOOD


def test_telemetry_negative_mach_fails():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        TelemetryObservation(
            observation_id="obs_bad_mach",
            timestamp=now,
            aircraft_id="ac_01",
            mach=-0.5,
        )


def test_telemetry_negative_fuel_fails():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        TelemetryObservation(
            observation_id="obs_bad_fuel",
            timestamp=now,
            aircraft_id="ac_01",
            fuel_flow_kg_h=-100.0,
        )
