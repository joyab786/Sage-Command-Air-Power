"""
SageCommand Air Power System (Aero) — Unit Tests: Prognostics Models.
Verifies strongly typed contracts, enum values, confidence bounds, and uncertainty constraints.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.digital_twin.models import TwinSubsystemType
from app.prognostics.models import (
    ComponentHealthSnapshot,
    DegradationTrend,
    MaintenanceForecast,
    MaintenanceForecastPriority,
    PredictionMethod,
    PrognosticAssessment,
    PrognosticRecordResponse,
    RULPrediction,
    TrendDirection,
)


def test_trend_direction_enum_values():
    assert TrendDirection.IMPROVING == "IMPROVING"
    assert TrendDirection.STABLE == "STABLE"
    assert TrendDirection.DEGRADING == "DEGRADING"
    assert TrendDirection.INSUFFICIENT_DATA == "INSUFFICIENT_DATA"


def test_forecast_priority_enum_values():
    assert MaintenanceForecastPriority.MONITOR == "MONITOR"
    assert MaintenanceForecastPriority.PLAN_MAINTENANCE == "PLAN_MAINTENANCE"
    assert MaintenanceForecastPriority.INSPECT_SOON == "INSPECT_SOON"
    assert MaintenanceForecastPriority.PRIORITY_INSPECTION == "PRIORITY_INSPECTION"
    assert MaintenanceForecastPriority.GROUND_FOR_REVIEW == "GROUND_FOR_REVIEW"


def test_prediction_method_enum_values():
    assert PredictionMethod.TREND_LINEAR_EXTRAPOLATION == "TREND_LINEAR_EXTRAPOLATION"
    assert PredictionMethod.WEAR_ACCELERATION_MODEL == "WEAR_ACCELERATION_MODEL"
    assert PredictionMethod.COMPOSITE_CONSERVATIVE_BOUND == "COMPOSITE_CONSERVATIVE_BOUND"
    assert PredictionMethod.BASELINE_NOMINAL == "BASELINE_NOMINAL"
    assert PredictionMethod.INSUFFICIENT_HISTORY_FALLBACK == "INSUFFICIENT_HISTORY_FALLBACK"


def test_component_health_snapshot_valid():
    now = datetime.now(timezone.utc)
    snap = ComponentHealthSnapshot(
        aircraft_id="AERO-001",
        subsystem=TwinSubsystemType.PROPULSION,
        timestamp=now,
        health_score=88.5,
        wear_index=0.12,
        anomaly_count=1,
        critical_anomaly_count=0,
        active_anomaly_severity="MEDIUM",
        data_quality="VALID",
        confidence=0.92,
    )
    assert snap.aircraft_id == "AERO-001"
    assert snap.health_score == 88.5
    assert snap.wear_index == 0.12
    assert snap.confidence == 0.92
    assert snap.snapshot_id.startswith("snap-")


def test_component_health_snapshot_invalid_confidence():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        ComponentHealthSnapshot(
            aircraft_id="AERO-001",
            subsystem=TwinSubsystemType.PROPULSION,
            timestamp=now,
            health_score=88.5,
            confidence=1.5,
        )

    with pytest.raises(ValidationError):
        ComponentHealthSnapshot(
            aircraft_id="AERO-001",
            subsystem=TwinSubsystemType.PROPULSION,
            timestamp=now,
            health_score=88.5,
            confidence=-0.1,
        )


def test_component_health_snapshot_invalid_health():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        ComponentHealthSnapshot(
            aircraft_id="AERO-001",
            subsystem=TwinSubsystemType.PROPULSION,
            timestamp=now,
            health_score=105.0,
        )


def test_degradation_trend_model_valid():
    trend = DegradationTrend(
        aircraft_id="AERO-001",
        subsystem=TwinSubsystemType.PROPULSION,
        sample_count=10,
        current_health=85.0,
        initial_health=95.0,
        degradation_rate=1.0,
        slope=-1.0,
        trend_direction=TrendDirection.DEGRADING,
        fit_quality=0.98,
        confidence=0.88,
        explanation="Consistent health degradation observed across 10 observations.",
    )
    assert trend.trend_direction == TrendDirection.DEGRADING
    assert trend.fit_quality == 0.98
    assert trend.degradation_rate == 1.0


def test_rul_prediction_bounds_and_confidence():
    rul = RULPrediction(
        aircraft_id="AERO-001",
        subsystem=TwinSubsystemType.PROPULSION,
        estimated_rul_hours=60.0,
        estimated_rul_cycles=30,
        lower_bound_hours=48.0,
        upper_bound_hours=72.0,
        health_score=85.0,
        wear_index=0.20,
        degradation_rate=1.0,
        confidence=0.85,
        prediction_method=PredictionMethod.TREND_LINEAR_EXTRAPOLATION,
        explanation="RUL extrapolated to caution boundary.",
        recommended_action="Schedule inspection within 50 flight hours.",
    )
    assert rul.estimated_rul_hours == 60.0
    assert rul.lower_bound_hours <= rul.estimated_rul_hours <= rul.upper_bound_hours
    assert rul.confidence == 0.85


def test_rul_prediction_rejects_negative_bounds():
    with pytest.raises(ValidationError):
        RULPrediction(
            aircraft_id="AERO-001",
            subsystem=TwinSubsystemType.PROPULSION,
            estimated_rul_hours=50.0,
            lower_bound_hours=-5.0,  # Negative bound prohibited
            upper_bound_hours=60.0,
            health_score=80.0,
            confidence=0.8,
            explanation="Test",
            recommended_action="Test",
        )


def test_rul_prediction_rejects_inverted_bounds():
    # lower_bound > estimated_rul
    with pytest.raises(ValidationError):
        RULPrediction(
            aircraft_id="AERO-001",
            subsystem=TwinSubsystemType.PROPULSION,
            estimated_rul_hours=50.0,
            lower_bound_hours=55.0,
            upper_bound_hours=60.0,
            health_score=80.0,
            confidence=0.8,
            explanation="Test",
            recommended_action="Test",
        )

    # estimated_rul > upper_bound
    with pytest.raises(ValidationError):
        RULPrediction(
            aircraft_id="AERO-001",
            subsystem=TwinSubsystemType.PROPULSION,
            estimated_rul_hours=50.0,
            lower_bound_hours=40.0,
            upper_bound_hours=45.0,
            health_score=80.0,
            confidence=0.8,
            explanation="Test",
            recommended_action="Test",
        )


def test_maintenance_forecast_model_valid():
    fcst = MaintenanceForecast(
        aircraft_id="AERO-001",
        priority=MaintenanceForecastPriority.PLAN_MAINTENANCE,
        urgency_horizon_hours=200.0,
        affected_subsystems=[TwinSubsystemType.PROPULSION],
        primary_driver="Gradual turbine thermal degradation",
        recommended_window="Within next 150 flight hours",
        action="Perform scheduled preventative servicing",
        confidence=0.85,
        explanation="Gradual degradation allows scheduled turnaround.",
    )
    assert fcst.priority == MaintenanceForecastPriority.PLAN_MAINTENANCE
    assert fcst.affected_subsystems == [TwinSubsystemType.PROPULSION]


def test_prognostic_assessment_composite_model():
    trend = DegradationTrend(
        aircraft_id="AERO-001",
        subsystem=TwinSubsystemType.PROPULSION,
        sample_count=5,
        current_health=90.0,
        initial_health=95.0,
        degradation_rate=1.0,
        slope=-1.0,
        trend_direction=TrendDirection.DEGRADING,
        fit_quality=0.95,
        confidence=0.85,
        explanation="Test trend",
    )
    rul = RULPrediction(
        aircraft_id="AERO-001",
        subsystem=TwinSubsystemType.PROPULSION,
        estimated_rul_hours=65.0,
        lower_bound_hours=50.0,
        upper_bound_hours=80.0,
        health_score=90.0,
        confidence=0.85,
        explanation="Test RUL",
        recommended_action="Test action",
    )
    fcst = MaintenanceForecast(
        aircraft_id="AERO-001",
        priority=MaintenanceForecastPriority.INSPECT_SOON,
        primary_driver="Test driver",
        recommended_window="Next 50 hours",
        action="Test action",
        explanation="Test forecast",
    )

    assessment = PrognosticAssessment(
        aircraft_id="AERO-001",
        primary_subsystem=TwinSubsystemType.PROPULSION,
        current_health_score=90.0,
        current_wear_index=0.15,
        trend=trend,
        rul=rul,
        forecast=fcst,
        confidence=0.85,
        explanation="Composite assessment valid",
    )
    assert assessment.aircraft_id == "AERO-001"
    assert assessment.readiness_impact == "FMC_SUPPORTED"
    assert assessment.assessment_id.startswith("prog-")
