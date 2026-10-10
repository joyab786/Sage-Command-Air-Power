"""
Unit tests for SageCommand Aero Prognostics — Remaining Useful Life (RUL) Predictor.
Validates BaseRULPredictor protocol, linear extrapolation formulas, conservative wear bounding,
Phase 5 anomaly modifiers, uncertainty interval guarantees, and non-negative bounds.
"""

from datetime import datetime, timezone
import pytest

from app.digital_twin.models import AircraftTwinState, TwinSubsystemType
from app.intelligence.models import Anomaly, AnomalySeverity, AnomalyType
from app.prognostics.models import (
    DegradationTrend,
    PredictionMethod,
    RULPrediction,
    TrendDirection,
)
from app.prognostics.rul import BaseRULPredictor, DeterministicRULPredictor, default_rul_predictor


def _build_trend(
    direction: TrendDirection,
    cur_health: float = 85.0,
    rate: float = 1.5,
    confidence: float = 0.90,
    dq: str = "VALID",
    samples: int = 5,
) -> DegradationTrend:
    return DegradationTrend(
        aircraft_id="AC-TEST-01",
        subsystem=TwinSubsystemType.PROPULSION,
        observation_start=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        observation_end=datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc),
        sample_count=samples,
        current_health=cur_health,
        initial_health=95.0,
        degradation_rate=rate,
        slope=-rate if direction == TrendDirection.DEGRADING else 0.0,
        trend_direction=direction,
        fit_quality=0.98,
        confidence=confidence,
        data_quality=dq,
        explanation="Synthetic test trend",
    )


def test_rul_protocol_conformance():
    """Confirms DeterministicRULPredictor adheres to BaseRULPredictor protocol."""
    predictor = DeterministicRULPredictor()
    assert isinstance(predictor, BaseRULPredictor)


def test_rul_insufficient_history_fallback():
    """Validates fallback to nominal ceiling with low confidence on insufficient data."""
    trend = _build_trend(TrendDirection.INSUFFICIENT_DATA, cur_health=90.0, samples=2)
    rul = default_rul_predictor.predict(trend)

    assert rul.prediction_method == PredictionMethod.INSUFFICIENT_HISTORY_FALLBACK
    assert rul.estimated_rul_hours == 1000.0
    assert rul.is_supported is False
    assert rul.is_nominal_ceiling is True
    assert rul.rul_status == "INSUFFICIENT_DATA"
    assert rul.confidence <= 0.25
    assert any("Insufficient historical observations" in factor for factor in rul.limiting_factors)
    assert rul.lower_bound_hours <= rul.estimated_rul_hours <= rul.upper_bound_hours


def test_rul_stable_trend_nominal_baseline():
    """Validates healthy stable subsystem returns nominal baseline."""
    trend = _build_trend(TrendDirection.STABLE, cur_health=95.0, rate=0.0)
    rul = default_rul_predictor.predict(trend)

    assert rul.prediction_method == PredictionMethod.BASELINE_NOMINAL
    assert rul.estimated_rul_hours == 1000.0
    assert rul.is_supported is True
    assert rul.is_nominal_ceiling is True
    assert rul.rul_status == "NOMINAL_BASELINE"
    assert rul.confidence == 0.90
    assert "stable" in rul.explanation.lower()


def test_rul_semantic_safeguard_unsupported_not_treated_as_guaranteed_life():
    """Confirms unsupported RUL is explicitly tagged is_supported=False to prevent unvalidated lifing."""
    trend_insufficient = _build_trend(TrendDirection.INSUFFICIENT_DATA, cur_health=88.0, samples=1)
    rul_insufficient = default_rul_predictor.predict(trend_insufficient)

    assert rul_insufficient.is_supported is False
    assert rul_insufficient.rul_status == "INSUFFICIENT_DATA"
    assert rul_insufficient.is_nominal_ceiling is True

    trend_degrading = _build_trend(TrendDirection.DEGRADING, cur_health=85.0, rate=2.0, samples=5)
    rul_degrading = default_rul_predictor.predict(trend_degrading)

    assert rul_degrading.is_supported is True
    assert rul_degrading.is_nominal_ceiling is False
    assert rul_degrading.rul_status == "ESTIMATED"


def test_rul_degrading_trend_linear_formula():
    """
    Validates linear extrapolation:
    health_margin = cur_health (85.0) - threshold (25.0) = 60.0
    degradation_rate = 2.0 pts/hr
    expected trend RUL = 60.0 / 2.0 = 30.0 hours.
    """
    trend = _build_trend(TrendDirection.DEGRADING, cur_health=85.0, rate=2.0)
    rul = default_rul_predictor.predict(trend)

    assert rul.prediction_method == PredictionMethod.TREND_LINEAR_EXTRAPOLATION
    assert pytest.approx(rul.estimated_rul_hours, 0.1) == 30.0
    assert rul.lower_bound_hours <= rul.estimated_rul_hours <= rul.upper_bound_hours
    assert rul.lower_bound_hours >= 0.0
    assert "30.0 hours" in rul.explanation


def test_rul_conservative_wear_bounding():
    """
    Validates that when wear index is more restrictive than health trend,
    the composite conservative bound limits the RUL estimate.
    """
    # Health trend suggests 60.0 / 1.0 = 60 hours
    trend = _build_trend(TrendDirection.DEGRADING, cur_health=85.0, rate=1.0)

    # Twin wear index is 0.98 -> wear margin = (1.0 - 0.98) = 0.02
    # wear_rul = 0.02 * 1000.0 = 20.0 hours < 60.0 hours
    twin_state = AircraftTwinState(
        aircraft_id="AC-TEST-01",
        timestamp=datetime.now(timezone.utc),
        operational_status="ACTIVE",
        wear_index=0.98,
        health_score=85.0,
    )

    rul = default_rul_predictor.predict(trend, current_state=twin_state)

    assert rul.prediction_method == PredictionMethod.COMPOSITE_CONSERVATIVE_BOUND
    assert pytest.approx(rul.estimated_rul_hours, 0.1) == 20.0
    assert any("wear" in f.lower() for f in rul.limiting_factors)


def test_rul_active_critical_anomaly_modifier():
    """Validates that a CRITICAL anomaly clamps RUL <= 15 hrs, decreases confidence, and advises grounding."""
    trend = _build_trend(TrendDirection.DEGRADING, cur_health=90.0, rate=0.5)
    # Without anomaly: (90 - 25)/0.5 = 130 hours

    crit_anomaly = Anomaly(
        anomaly_id="ANOM-CRIT-01",
        aircraft_id="AC-TEST-01",
        subsystem=TwinSubsystemType.PROPULSION,
        signal="vibration_ips",
        observed_value=2.8,
        expected_range="[0.0, 0.8]",
        severity=AnomalySeverity.CRITICAL,
        anomaly_type=AnomalyType.VIBRATION_ANOMALY,
        description="Severe turbine shaft vibration spike",
    )

    rul = default_rul_predictor.predict(trend, active_anomalies=[crit_anomaly])

    assert rul.estimated_rul_hours <= 15.0
    assert any("CRITICAL" in f for f in rul.limiting_factors)
    assert "Ground aircraft for immediate engineering inspection" in rul.recommended_action
    assert rul.lower_bound_hours <= rul.estimated_rul_hours <= rul.upper_bound_hours


def test_rul_active_high_anomaly_modifier():
    """Validates that a HIGH anomaly restricts RUL <= 80 hrs."""
    trend = _build_trend(TrendDirection.DEGRADING, cur_health=90.0, rate=0.2)
    # Without anomaly: (90 - 25)/0.2 = 325 hours

    high_anomaly = Anomaly(
        anomaly_id="ANOM-HIGH-01",
        aircraft_id="AC-TEST-01",
        subsystem=TwinSubsystemType.PROPULSION,
        signal="engine_temperature_c",
        observed_value=980.0,
        expected_range="[400.0, 850.0]",
        severity=AnomalySeverity.HIGH,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        description="Turbine over-temperature condition",
    )

    rul = default_rul_predictor.predict(trend, active_anomalies=[high_anomaly])

    assert rul.estimated_rul_hours <= 80.0
    assert any("HIGH" in f for f in rul.limiting_factors)


def test_rul_never_negative_even_below_failure_threshold():
    """Confirms RUL is safely bounded at 0.0 when health score is already depleted."""
    # Health at 20.0, threshold is 25.0
    trend = _build_trend(TrendDirection.DEGRADING, cur_health=20.0, rate=5.0)
    rul = default_rul_predictor.predict(trend)

    assert rul.estimated_rul_hours == 0.0
    assert rul.lower_bound_hours == 0.0
    assert rul.upper_bound_hours >= 0.0


def test_rul_uncertainty_interval_expansion_on_degraded_data():
    """Tests that degraded telemetry data expands the uncertainty margin."""
    trend_valid = _build_trend(TrendDirection.DEGRADING, cur_health=85.0, rate=2.0, dq="VALID")
    trend_degraded = _build_trend(TrendDirection.DEGRADING, cur_health=85.0, rate=2.0, dq="DEGRADED")

    rul_valid = default_rul_predictor.predict(trend_valid)
    rul_degraded = default_rul_predictor.predict(trend_degraded)

    margin_valid = rul_valid.upper_bound_hours - rul_valid.lower_bound_hours
    margin_degraded = rul_degraded.upper_bound_hours - rul_degraded.lower_bound_hours

    assert margin_degraded > margin_valid
    assert any("Degraded telemetry" in f for f in rul_degraded.limiting_factors)
