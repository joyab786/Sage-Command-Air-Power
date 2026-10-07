"""
Unit tests for Phase 5 Intelligence Data Models.
Verifies enum definitions, confidence constraints (0.0 to 1.0),
schema validation, serialization, and explainability fields.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.digital_twin.models import TwinSubsystemType
from app.intelligence.models import (
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    RecommendationPriority,
    Anomaly,
    Diagnosis,
    MaintenanceRecommendation,
)


def test_intelligence_enums():
    """Verify all required enum values are present and strictly typed."""
    # Severities
    assert AnomalySeverity.INFO.value == "INFO"
    assert AnomalySeverity.LOW.value == "LOW"
    assert AnomalySeverity.MEDIUM.value == "MEDIUM"
    assert AnomalySeverity.HIGH.value == "HIGH"
    assert AnomalySeverity.CRITICAL.value == "CRITICAL"

    # Statuses
    assert AnomalyStatus.NEW.value == "NEW"
    assert AnomalyStatus.ACKNOWLEDGED.value == "ACKNOWLEDGED"
    assert AnomalyStatus.RESOLVED.value == "RESOLVED"

    # Core Anomaly Types
    assert AnomalyType.THERMAL_ANOMALY.value == "THERMAL_ANOMALY"
    assert AnomalyType.VIBRATION_ANOMALY.value == "VIBRATION_ANOMALY"
    assert AnomalyType.PRESSURE_ANOMALY.value == "PRESSURE_ANOMALY"
    assert AnomalyType.G_LOAD_ANOMALY.value == "G_LOAD_ANOMALY"
    assert AnomalyType.FUEL_FLOW_ANOMALY.value == "FUEL_FLOW_ANOMALY"
    assert AnomalyType.CONTROL_SURFACE_ANOMALY.value == "CONTROL_SURFACE_ANOMALY"
    assert AnomalyType.TELEMETRY_QUALITY_ANOMALY.value == "TELEMETRY_QUALITY_ANOMALY"
    assert AnomalyType.FLIGHT_ENVELOPE_ANOMALY.value == "FLIGHT_ENVELOPE_ANOMALY"
    assert AnomalyType.MULTI_SIGNAL_ANOMALY.value == "MULTI_SIGNAL_ANOMALY"

    # Recommendation Priorities
    assert RecommendationPriority.MONITOR.value == "MONITOR"
    assert RecommendationPriority.INSPECT.value == "INSPECT"
    assert RecommendationPriority.SCHEDULE_MAINTENANCE.value == "SCHEDULE_MAINTENANCE"
    assert RecommendationPriority.GROUND_FOR_REVIEW.value == "GROUND_FOR_REVIEW"


def test_anomaly_schema_validation():
    """Verify Anomaly model instantiation, defaults, and field structures."""
    now = datetime.now(timezone.utc)
    anomaly = Anomaly(
        aircraft_id="AERO-001",
        flight_id="SORTIE-101",
        timestamp=now,
        subsystem=TwinSubsystemType.PROPULSION,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        severity=AnomalySeverity.HIGH,
        confidence=0.92,
        detector="ThresholdDetector",
        signal="engine_temperature_c",
        observed_value=865.0,
        expected_range="≤ 780.0 °C",
        deviation=85.0,
        description="Engine temperature exceeded caution threshold.",
        evidence=["Observed 865.0 °C exceeds limit 780.0 °C"],
    )

    assert anomaly.anomaly_id.startswith("anom-")
    assert anomaly.status == AnomalyStatus.NEW
    assert anomaly.occurrence_count == 1
    assert anomaly.confidence == 0.92
    assert anomaly.aircraft_id == "AERO-001"
    assert len(anomaly.evidence) == 1


def test_confidence_bounds_validation():
    """Verify confidence must be bounded between 0.0 and 1.0."""
    now = datetime.now(timezone.utc)

    # Valid bounds
    a_min = Anomaly(
        aircraft_id="AERO-001",
        timestamp=now,
        subsystem=TwinSubsystemType.PROPULSION,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        severity=AnomalySeverity.LOW,
        confidence=0.0,
        detector="TestDetector",
        signal="test",
        observed_value=1.0,
        description="Low confidence",
    )
    assert a_min.confidence == 0.0

    a_max = Anomaly(
        aircraft_id="AERO-001",
        timestamp=now,
        subsystem=TwinSubsystemType.PROPULSION,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        severity=AnomalySeverity.CRITICAL,
        confidence=1.0,
        detector="TestDetector",
        signal="test",
        observed_value=1.0,
        description="Max confidence",
    )
    assert a_max.confidence == 1.0

    # Over 1.0 rejected
    with pytest.raises(ValidationError):
        Anomaly(
            aircraft_id="AERO-001",
            timestamp=now,
            subsystem=TwinSubsystemType.PROPULSION,
            anomaly_type=AnomalyType.THERMAL_ANOMALY,
            severity=AnomalySeverity.HIGH,
            confidence=1.05,
            detector="TestDetector",
            signal="test",
            observed_value=1.0,
            description="Invalid confidence",
        )

    # Below 0.0 rejected
    with pytest.raises(ValidationError):
        Anomaly(
            aircraft_id="AERO-001",
            timestamp=now,
            subsystem=TwinSubsystemType.PROPULSION,
            anomaly_type=AnomalyType.THERMAL_ANOMALY,
            severity=AnomalySeverity.HIGH,
            confidence=-0.1,
            detector="TestDetector",
            signal="test",
            observed_value=1.0,
            description="Invalid confidence",
        )


def test_diagnosis_schema_validation():
    """Verify Diagnosis schema requires explainability, probable causes, and bounded confidence."""
    now = datetime.now(timezone.utc)
    diag = Diagnosis(
        aircraft_id="AERO-001",
        timestamp=now,
        primary_subsystem=TwinSubsystemType.PROPULSION,
        probable_causes=["Turbine hot section thermal degradation"],
        supporting_anomalies=["anom-12345"],
        confidence=0.88,
        explanation="Engine temperature significantly elevated while vibration within normal limits.",
    )

    assert diag.diagnosis_id.startswith("diag-")
    assert diag.primary_subsystem == TwinSubsystemType.PROPULSION
    assert len(diag.probable_causes) == 1
    assert diag.confidence == 0.88


def test_maintenance_recommendation_schema():
    """Verify MaintenanceRecommendation schema and advisory priority structure."""
    now = datetime.now(timezone.utc)
    rec = MaintenanceRecommendation(
        aircraft_id="AERO-001",
        priority=RecommendationPriority.GROUND_FOR_REVIEW,
        action="Perform borescope inspection of propulsion hot section before next flight.",
        reason="Critical persistent engine overtemperature detected across multiple observations.",
        related_anomalies=["anom-12345", "anom-67890"],
        affected_subsystem=TwinSubsystemType.PROPULSION,
        confidence=0.94,
    )

    assert rec.recommendation_id.startswith("mrec-")
    assert rec.priority == RecommendationPriority.GROUND_FOR_REVIEW
    assert rec.affected_subsystem == TwinSubsystemType.PROPULSION
    assert rec.confidence == 0.94
