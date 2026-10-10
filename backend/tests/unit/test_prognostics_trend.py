"""
Unit tests for SageCommand Aero Prognostics — Degradation Trend Estimator.
Validates OLS regression, sample count protections, fit quality (R²),
trend direction classification, and data quality degradation penalties.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.digital_twin.models import TwinSubsystemType
from app.prognostics.models import ComponentHealthSnapshot, TrendDirection
from app.prognostics.trend import DegradationTrendEstimator


def _make_snapshot(
    aircraft_id: str,
    timestamp: datetime,
    health: float,
    wear: float = 0.05,
    dq: str = "VALID",
    subsystem: TwinSubsystemType = TwinSubsystemType.PROPULSION,
) -> ComponentHealthSnapshot:
    return ComponentHealthSnapshot(
        aircraft_id=aircraft_id,
        subsystem=subsystem,
        timestamp=timestamp,
        health_score=health,
        wear_index=wear,
        anomaly_count=0,
        critical_anomaly_count=0,
        data_quality=dq,
        confidence=1.0,
    )


def test_trend_insufficient_data_less_than_three_samples():
    """Confirms that < 3 observations yields INSUFFICIENT_DATA and does not fabricate a trend."""
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    s1 = _make_snapshot("AC-TEST-01", t0, 95.0)
    s2 = _make_snapshot("AC-TEST-01", t0 + timedelta(hours=1), 90.0)

    trend = DegradationTrendEstimator.estimate_trend([s1, s2])

    assert trend.trend_direction == TrendDirection.INSUFFICIENT_DATA
    assert trend.sample_count == 2
    assert trend.degradation_rate == 0.0
    assert trend.fit_quality is None
    assert trend.confidence <= 0.25
    assert trend.data_quality == "SPARSE"
    assert "At least 3" in trend.explanation


def test_trend_empty_snapshots():
    """Validates behavior on empty snapshot sequence."""
    trend = DegradationTrendEstimator.estimate_trend([])

    assert trend.trend_direction == TrendDirection.INSUFFICIENT_DATA
    assert trend.sample_count == 0
    assert trend.confidence == 0.20
    assert trend.current_health == 100.0


def test_trend_stable_flat_health():
    """Confirms that constant healthy observations yield STABLE with zero degradation rate."""
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    snapshots = [
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=i), 98.0)
        for i in range(5)
    ]

    trend = DegradationTrendEstimator.estimate_trend(snapshots)

    assert trend.trend_direction == TrendDirection.STABLE
    assert trend.sample_count == 5
    assert trend.slope == 0.0
    assert trend.degradation_rate == 0.0
    assert trend.fit_quality == 1.0
    assert trend.current_health == 98.0
    assert "stable" in trend.explanation.lower()


def test_trend_gradual_degradation():
    """Tests linear decline with slope calculation and fit quality."""
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    # Drops 2 health points every hour for 5 hours: 100, 98, 96, 94, 92
    snapshots = [
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=i), 100.0 - 2.0 * i)
        for i in range(5)
    ]

    trend = DegradationTrendEstimator.estimate_trend(snapshots)

    assert trend.trend_direction == TrendDirection.DEGRADING
    assert trend.sample_count == 5
    assert pytest.approx(trend.slope, 0.01) == -2.0
    assert pytest.approx(trend.degradation_rate, 0.01) == 2.0
    assert trend.fit_quality is not None and trend.fit_quality >= 0.99
    assert trend.current_health == 92.0
    assert trend.initial_health == 100.0
    assert trend.confidence > 0.80
    assert "Degradation rate is estimated at 2.00 points/hr" in trend.explanation


def test_trend_rapid_degradation():
    """Tests steep decline trajectory."""
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    # Drops 15 health points per hour: 95, 80, 65, 50
    snapshots = [
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=i), 95.0 - 15.0 * i)
        for i in range(4)
    ]

    trend = DegradationTrendEstimator.estimate_trend(snapshots)

    assert trend.trend_direction == TrendDirection.DEGRADING
    assert pytest.approx(trend.degradation_rate, 0.01) == 15.0
    assert trend.current_health == 50.0
    assert trend.initial_health == 95.0


def test_trend_improving_trajectory():
    """Confirms that recovering health yields IMPROVING trend direction."""
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    # Health increases after maintenance action: 70, 75, 80, 85
    snapshots = [
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=i), 70.0 + 5.0 * i)
        for i in range(4)
    ]

    trend = DegradationTrendEstimator.estimate_trend(snapshots)

    assert trend.trend_direction == TrendDirection.IMPROVING
    assert trend.degradation_rate == 0.0
    assert trend.slope > 0.0
    assert "recovering" in trend.explanation.lower()


def test_trend_degraded_telemetry_confidence_penalty():
    """Validates that > 30% degraded telemetry observations penalizes confidence."""
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    snapshots = [
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=0), 95.0, dq="VALID"),
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=1), 93.0, dq="DEGRADED"),
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=2), 91.0, dq="DEGRADED"),
        _make_snapshot("AC-TEST-01", t0 + timedelta(hours=3), 89.0, dq="VALID"),
    ]

    trend = DegradationTrendEstimator.estimate_trend(snapshots)

    assert trend.data_quality == "DEGRADED"
    assert "Confidence reduced due to degraded telemetry" in trend.explanation
    # Normal 4-sample with high fit would be around ~0.80, with -0.20 penalty it should be <= 0.65
    assert trend.confidence <= 0.65


def test_trend_subsecond_timestamps_discrete_steps_fallback():
    """Tests that timestamps with microsecond deltas fallback gracefully to discrete observation steps."""
    t0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Snapshots generated 10 milliseconds apart
    snapshots = [
        _make_snapshot("AC-TEST-01", t0 + timedelta(milliseconds=10 * i), 90.0 - 2.0 * i)
        for i in range(5)
    ]

    trend = DegradationTrendEstimator.estimate_trend(snapshots)

    assert trend.trend_direction == TrendDirection.DEGRADING
    assert pytest.approx(trend.slope, 0.01) == -2.0
    assert "discrete observation steps" in trend.explanation
