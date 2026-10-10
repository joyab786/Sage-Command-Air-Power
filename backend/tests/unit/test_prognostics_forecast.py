"""
Unit tests for SageCommand Aero Prognostics — Maintenance Forecaster.
Validates all 5 operational priority tiers (GROUND_FOR_REVIEW, PRIORITY_INSPECTION,
INSPECT_SOON, PLAN_MAINTENANCE, MONITOR), action explanations, and Phase 5 integration.
"""

from datetime import datetime, timezone
import pytest

from app.digital_twin.models import TwinSubsystemType
from app.intelligence.models import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
    MaintenanceRecommendation,
    RecommendationPriority,
)
from app.prognostics.forecast import MaintenanceForecaster, default_maintenance_forecaster
from app.prognostics.models import (
    MaintenanceForecastPriority,
    PredictionMethod,
    RULPrediction,
)


def _build_rul(
    rul_hours: float = 1000.0,
    rate: float = 0.0,
    subsystem: TwinSubsystemType = TwinSubsystemType.PROPULSION,
    confidence: float = 0.90,
) -> RULPrediction:
    return RULPrediction(
        aircraft_id="AC-TEST-01",
        subsystem=subsystem,
        prediction_timestamp=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        estimated_rul_hours=rul_hours,
        estimated_rul_cycles=int(rul_hours * 0.5),
        lower_bound_hours=max(0.0, rul_hours * 0.8),
        upper_bound_hours=rul_hours * 1.2,
        health_score=85.0,
        wear_index=0.10,
        degradation_rate=rate,
        confidence=confidence,
        prediction_method=PredictionMethod.TREND_LINEAR_EXTRAPOLATION if rate > 0 else PredictionMethod.BASELINE_NOMINAL,
        data_quality="VALID",
        limiting_factors=[],
        explanation="Synthetic test RUL",
        recommended_action="Inspect",
    )


def test_forecast_ground_for_review_on_critical_anomaly():
    """Confirms CRITICAL anomaly escalates forecast directly to GROUND_FOR_REVIEW."""
    rul = _build_rul(rul_hours=120.0, rate=0.5)
    crit_anomaly = Anomaly(
        anomaly_id="ANOM-C-01",
        aircraft_id="AC-TEST-01",
        subsystem=TwinSubsystemType.PROPULSION,
        signal="engine_temperature_c",
        severity=AnomalySeverity.CRITICAL,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        description="Severe turbine overheating",
    )

    forecast = default_maintenance_forecaster.generate_forecast(
        rul=rul, active_anomalies=[crit_anomaly]
    )

    assert forecast.priority == MaintenanceForecastPriority.GROUND_FOR_REVIEW
    assert "Immediate prior to next flight" in forecast.recommended_window
    assert "Ground airframe 'AC-TEST-01'" in forecast.action
    assert "ANOM-C-01" in forecast.related_anomalies


def test_forecast_ground_for_review_on_imminent_rul_depletion():
    """Confirms RUL < 15.0 hrs triggers GROUND_FOR_REVIEW even without active anomalies."""
    rul = _build_rul(rul_hours=10.0, rate=3.0)
    forecast = default_maintenance_forecaster.generate_forecast(rul=rul)

    assert forecast.priority == MaintenanceForecastPriority.GROUND_FOR_REVIEW
    assert forecast.urgency_horizon_hours == 10.0


def test_forecast_ground_for_review_on_existing_ground_recommendation():
    """Confirms Phase 5 recommendation GROUND_FOR_REVIEW is respected."""
    rul = _build_rul(rul_hours=100.0, rate=0.5)
    rec = MaintenanceRecommendation(
        recommendation_id="REC-01",
        aircraft_id="AC-TEST-01",
        affected_subsystem=TwinSubsystemType.PROPULSION,
        priority=RecommendationPriority.GROUND_FOR_REVIEW,
        action="Pre-flight turbine teardown",
        reason="Detected cracked blade signature",
    )

    forecast = default_maintenance_forecaster.generate_forecast(
        rul=rul, recommendations=[rec]
    )

    assert forecast.priority == MaintenanceForecastPriority.GROUND_FOR_REVIEW


def test_forecast_priority_inspection_on_high_anomaly():
    """Confirms HIGH anomaly triggers PRIORITY_INSPECTION."""
    rul = _build_rul(rul_hours=200.0, rate=0.2)
    high_anom = Anomaly(
        anomaly_id="ANOM-H-01",
        aircraft_id="AC-TEST-01",
        subsystem=TwinSubsystemType.PROPULSION,
        signal="vibration_ips",
        severity=AnomalySeverity.HIGH,
        anomaly_type=AnomalyType.VIBRATION_ANOMALY,
        description="Elevated vibration",
    )

    forecast = default_maintenance_forecaster.generate_forecast(
        rul=rul, active_anomalies=[high_anom]
    )

    assert forecast.priority == MaintenanceForecastPriority.PRIORITY_INSPECTION
    assert "turnaround inspection" in forecast.action.lower()


def test_forecast_priority_inspection_on_short_rul():
    """Confirms RUL < 60.0 hrs triggers PRIORITY_INSPECTION."""
    rul = _build_rul(rul_hours=45.0, rate=1.0)
    forecast = default_maintenance_forecaster.generate_forecast(rul=rul)

    assert forecast.priority == MaintenanceForecastPriority.PRIORITY_INSPECTION


def test_forecast_inspect_soon_on_medium_window():
    """Confirms RUL < 150.0 hrs triggers INSPECT_SOON."""
    rul = _build_rul(rul_hours=110.0, rate=0.2)
    forecast = default_maintenance_forecaster.generate_forecast(rul=rul)

    assert forecast.priority == MaintenanceForecastPriority.INSPECT_SOON
    assert "Within next 50 flight hours" in forecast.recommended_window


def test_forecast_plan_maintenance_on_gradual_trend():
    """Confirms gradual degradation with moderate horizon triggers PLAN_MAINTENANCE."""
    rul = _build_rul(rul_hours=250.0, rate=0.3)
    forecast = default_maintenance_forecaster.generate_forecast(rul=rul)

    assert forecast.priority == MaintenanceForecastPriority.PLAN_MAINTENANCE
    assert "upcoming maintenance cycle" in forecast.action.lower()


def test_forecast_monitor_nominal_health():
    """Confirms healthy airframe subsystem triggers MONITOR."""
    rul = _build_rul(rul_hours=1000.0, rate=0.0)
    forecast = default_maintenance_forecaster.generate_forecast(rul=rul)

    assert forecast.priority == MaintenanceForecastPriority.MONITOR
    assert "Standard periodic depot inspection" in forecast.recommended_window
    assert "operating nominally" in forecast.action
