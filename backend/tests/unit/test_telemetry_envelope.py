"""
Unit tests for FlightEnvelopeChecker.
Validates detection of WITHIN_ENVELOPE, CAUTION, and EXCEEDED statuses,
as well as boundary parameters across altitude, airspeed, G-load, and temperatures.
"""

import pytest
from datetime import datetime, timezone
from app.telemetry.envelope import (
    FlightEnvelopeChecker,
    FlightEnvelopeProfile,
    DEFAULT_DEMO_ENVELOPE,
)
from app.telemetry.models import NormalizedTelemetry, EnvelopeStatus


def test_envelope_within_nominal_limits():
    checker = FlightEnvelopeChecker()
    norm = NormalizedTelemetry(
        observation_id="obs_nom_01",
        timestamp=datetime.now(timezone.utc),
        aircraft_id="ac_su30_01",
        altitude_m=10000.0,      # limit is 18500, caution 16000
        airspeed_mps=250.0,      # limit is 700, caution 650
        mach=0.85,               # limit is 2.25, caution 2.0
        g_load=1.2,              # limit is 9.0, caution 7.5
        engine_temperature_c=650.0, # limit is 850, caution 780
        engine_pressure_kpa=350.0,  # limit is 650, caution 600
        vibration_ips=0.20,      # limit is 0.8, caution 0.5
    )
    result = checker.evaluate(norm)
    assert result.status == EnvelopeStatus.WITHIN_ENVELOPE
    assert len(result.violations) == 0
    assert result.parameters_checked == 7


def test_envelope_caution_triggered():
    checker = FlightEnvelopeChecker()
    norm = NormalizedTelemetry(
        observation_id="obs_caut_01",
        timestamp=datetime.now(timezone.utc),
        aircraft_id="ac_su30_01",
        altitude_m=10000.0,
        g_load=8.2,              # Caution threshold is 7.5, hard limit is 9.0
        engine_temperature_c=650.0,
    )
    result = checker.evaluate(norm)
    assert result.status == EnvelopeStatus.CAUTION
    assert len(result.violations) == 1
    assert result.violations[0].parameter == "g_load"
    assert result.violations[0].severity == "CAUTION"


def test_envelope_exceeded_hard_limit():
    checker = FlightEnvelopeChecker()
    norm = NormalizedTelemetry(
        observation_id="obs_exc_01",
        timestamp=datetime.now(timezone.utc),
        aircraft_id="ac_su30_01",
        altitude_m=10000.0,
        g_load=9.6,              # Hard limit is 9.0 -> EXCEEDED
    )
    result = checker.evaluate(norm)
    assert result.status == EnvelopeStatus.EXCEEDED
    assert len(result.violations) == 1
    assert result.violations[0].parameter == "g_load"
    assert result.violations[0].severity == "CRITICAL"


def test_envelope_multiple_simultaneous_violations():
    checker = FlightEnvelopeChecker()
    norm = NormalizedTelemetry(
        observation_id="obs_multi_01",
        timestamp=datetime.now(timezone.utc),
        aircraft_id="ac_su30_01",
        altitude_m=19500.0,         # Limit high is 18500 -> CRITICAL
        engine_temperature_c=800.0, # Caution high is 780 -> CAUTION
        vibration_ips=0.92,         # Limit high is 0.8 -> CRITICAL
    )
    result = checker.evaluate(norm)
    assert result.status == EnvelopeStatus.EXCEEDED
    assert len(result.violations) == 3
    params = [v.parameter for v in result.violations]
    assert "altitude" in params
    assert "engine_temperature" in params
    assert "vibration" in params
