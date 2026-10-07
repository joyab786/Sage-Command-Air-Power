"""
Unit tests for Maintenance Recommendation Engine.
Verifies decision-support advisory rules, priority assignments,
cautious wording, and integration with twin health state.
"""

from datetime import datetime, timezone
import pytest

from app.digital_twin.models import (
    AircraftTwinState,
    TwinSubsystemType,
    TwinHealthState,
    SubsystemState,
)
from app.intelligence.models import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
    Diagnosis,
    RecommendationPriority,
)
from app.intelligence.maintenance import MaintenanceRecommendationEngine


def test_maintenance_recommendation_nominal():
    """Verify monitor recommendation generated when no anomalies are present."""
    engine = MaintenanceRecommendationEngine()
    diag = Diagnosis(
        aircraft_id="AERO-001",
        timestamp=datetime.now(timezone.utc),
        primary_subsystem=TwinSubsystemType.PROPULSION,
        probable_causes=["Subsystems operating within nominal envelope"],
        confidence=1.0,
        explanation="No active anomalies detected.",
    )

    recs = engine.recommend(anomalies=[], diagnosis=diag)
    assert len(recs) == 1
    assert recs[0].priority == RecommendationPriority.MONITOR
    assert recs[0].aircraft_id == "AERO-001"
    assert "routine" in recs[0].action.lower()


def test_maintenance_recommendation_ground_for_review_on_critical():
    """Verify GROUND_FOR_REVIEW recommendation on CRITICAL severity anomalies."""
    engine = MaintenanceRecommendationEngine()
    now = datetime.now(timezone.utc)

    crit_anom = Anomaly(
        anomaly_id="anom-crit-01",
        aircraft_id="AERO-001",
        timestamp=now,
        subsystem=TwinSubsystemType.PROPULSION,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        severity=AnomalySeverity.CRITICAL,
        confidence=0.95,
        detector="ThresholdDetector",
        signal="engine_temperature_c",
        observed_value=930.0,
        description="Critical propulsion overtemperature observed.",
        evidence=["Observed 930.0 °C exceeds 850.0 °C limit"],
    )

    diag = Diagnosis(
        aircraft_id="AERO-001",
        timestamp=now,
        primary_subsystem=TwinSubsystemType.PROPULSION,
        probable_causes=["Severe turbine thermal stress"],
        supporting_anomalies=[crit_anom.anomaly_id],
        confidence=0.95,
        explanation="Critical propulsion thermal condition requiring immediate review.",
    )

    recs = engine.recommend(anomalies=[crit_anom], diagnosis=diag)
    assert len(recs) >= 1
    top_rec = recs[0]
    assert top_rec.priority == RecommendationPriority.GROUND_FOR_REVIEW
    assert top_rec.affected_subsystem == TwinSubsystemType.PROPULSION
    assert "advisory" in top_rec.action.lower() or "inspection" in top_rec.action.lower()
    # Ensure cautious advisory wording (not autonomous command)
    assert "recommend" in top_rec.action.lower() or "advisory" in top_rec.action.lower() or "perform" in top_rec.action.lower()


def test_maintenance_recommendation_schedule_maintenance_on_high():
    """Verify SCHEDULE_MAINTENANCE recommended for HIGH severity issues."""
    engine = MaintenanceRecommendationEngine()
    now = datetime.now(timezone.utc)

    high_anom = Anomaly(
        anomaly_id="anom-high-01",
        aircraft_id="AERO-001",
        timestamp=now,
        subsystem=TwinSubsystemType.PROPULSION,
        anomaly_type=AnomalyType.VIBRATION_ANOMALY,
        severity=AnomalySeverity.HIGH,
        confidence=0.88,
        detector="ThresholdDetector",
        signal="vibration_ips",
        observed_value=3.2,
        description="Elevated vibration detected.",
    )

    diag = Diagnosis(
        aircraft_id="AERO-001",
        timestamp=now,
        primary_subsystem=TwinSubsystemType.PROPULSION,
        probable_causes=["Rotor unbalance or bearing wear"],
        supporting_anomalies=[high_anom.anomaly_id],
        confidence=0.88,
        explanation="Elevated propulsion vibration detected.",
    )

    recs = engine.recommend(anomalies=[high_anom], diagnosis=diag)
    assert len(recs) >= 1
    assert recs[0].priority == RecommendationPriority.SCHEDULE_MAINTENANCE
    assert recs[0].affected_subsystem == TwinSubsystemType.PROPULSION


def test_maintenance_recommendation_inspect_on_medium():
    """Verify INSPECT recommended for MEDIUM severity anomalies."""
    engine = MaintenanceRecommendationEngine()
    now = datetime.now(timezone.utc)

    med_anom = Anomaly(
        anomaly_id="anom-med-01",
        aircraft_id="AERO-001",
        timestamp=now,
        subsystem=TwinSubsystemType.STRUCTURE,
        anomaly_type=AnomalyType.G_LOAD_ANOMALY,
        severity=AnomalySeverity.MEDIUM,
        confidence=0.75,
        detector="ThresholdDetector",
        signal="g_load",
        observed_value=7.6,
        description="Caution-level G-load factor sustained.",
    )

    diag = Diagnosis(
        aircraft_id="AERO-001",
        timestamp=now,
        primary_subsystem=TwinSubsystemType.STRUCTURE,
        probable_causes=["Moderate structural loading during maneuver"],
        supporting_anomalies=[med_anom.anomaly_id],
        confidence=0.75,
        explanation="Caution G-load encountered.",
    )

    recs = engine.recommend(anomalies=[med_anom], diagnosis=diag)
    assert len(recs) >= 1
    assert recs[0].priority == RecommendationPriority.INSPECT
    assert recs[0].affected_subsystem == TwinSubsystemType.STRUCTURE
