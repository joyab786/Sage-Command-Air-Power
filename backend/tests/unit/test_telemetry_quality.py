"""
Unit tests for Telemetry Quality Evaluator.
Validates quality status determination (VALID, DEGRADED, INVALID),
rejection of non-finite values, negative physical parameters, and stale timestamps.
"""

import math
import pytest
from datetime import datetime, timezone, timedelta
from app.telemetry.quality import QualityEvaluator
from app.telemetry.models import TelemetryInput, QualityStatus


def test_quality_valid_observation():
    now = datetime.now(timezone.utc)
    obs = TelemetryInput(
        aircraft_id="ac_su30_01",
        timestamp=now,
        altitude=25000.0,
        airspeed=450.0,
        mach=0.85,
        g_load=1.2,
        engine_temperature=680.0,
        engine_pressure=48.0,
        vibration=0.15,
        fuel_flow=2200.0,
    )
    result = QualityEvaluator.evaluate_input(obs)
    assert result.status == QualityStatus.VALID
    assert len(result.reasons) == 0


def test_quality_sparse_observation_degraded():
    # Only 1 or 2 channels -> DEGRADED with warning
    obs = TelemetryInput(
        aircraft_id="ac_su30_01",
        altitude=15000.0,
    )
    result = QualityEvaluator.evaluate_input(obs)
    assert result.status == QualityStatus.DEGRADED
    assert any("Sparse" in w for w in result.warnings)


def test_quality_zero_channels_invalid():
    obs = TelemetryInput(
        aircraft_id="ac_su30_01",
    )
    result = QualityEvaluator.evaluate_input(obs)
    assert result.status == QualityStatus.INVALID
    assert any("zero telemetry channel" in r for r in result.reasons)


def test_quality_future_timestamp_drift_invalid():
    # Timestamp 3 hours into future (limit is 1 hour)
    future_time = datetime.now(timezone.utc) + timedelta(hours=3)
    obs = TelemetryInput(
        aircraft_id="ac_su30_01",
        timestamp=future_time,
        altitude=20000.0,
        airspeed=400.0,
        mach=0.75,
    )
    result = QualityEvaluator.evaluate_input(obs)
    assert result.status == QualityStatus.INVALID
    assert any("future" in r for r in result.reasons)


def test_quality_nan_value_invalid():
    obs = TelemetryInput(
        aircraft_id="ac_su30_01",
        altitude=20000.0,
        airspeed=float("nan"),
        mach=0.8,
    )
    result = QualityEvaluator.evaluate_input(obs)
    assert result.status == QualityStatus.INVALID
    assert any("NaN" in r or "non-finite" in r for r in result.reasons)


def test_quality_negative_mach_and_vibration_invalid():
    obs = TelemetryInput(
        aircraft_id="ac_su30_01",
        altitude=20000.0,
        airspeed=400.0,
        mach=-0.2, # Impossible
        vibration=-0.5, # Impossible
    )
    result = QualityEvaluator.evaluate_input(obs)
    assert result.status == QualityStatus.INVALID
    assert any("negative" in r for r in result.reasons)
