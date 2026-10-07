"""
Unit tests for Root-Cause Diagnostic Synthesis Engine.
Verifies multi-signal correlation, subsystem attribution,
explainable evidence generation, and degraded confidence penalties.
"""

from datetime import datetime, timezone
import pytest

from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import (
    AircraftTwinState,
    TwinSubsystemType,
    TwinHealthState,
    SubsystemState,
)
from app.intelligence.models import (
    Anomaly,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
)
from app.intelligence.diagnosis.root_cause import RootCauseDiagnosisEngine


def create_mock_anomaly(
    aircraft_id: str = "AERO-001",
    subsystem: TwinSubsystemType = TwinSubsystemType.PROPULSION,
    anomaly_type: AnomalyType = AnomalyType.THERMAL_ANOMALY,
    signal: str = "engine_temperature_c",
    severity: AnomalySeverity = AnomalySeverity.HIGH,
    confidence: float = 0.85,
    observed_value: float = 850.0,
) -> Anomaly:
    """Helper to generate mock anomaly instances."""
    return Anomaly(
        aircraft_id=aircraft_id,
        flight_id="SORTIE-01",
        timestamp=datetime.now(timezone.utc),
        subsystem=subsystem,
        anomaly_type=anomaly_type,
        severity=severity,
        confidence=confidence,
        detector="TestDetector",
        signal=signal,
        observed_value=observed_value,
        description=f"Detected {anomaly_type.value} on {signal}",
        evidence=[f"{signal} reached {observed_value}"],
    )


def test_diagnosis_empty_anomalies():
    """Verify diagnosis returns nominal assessment when no anomalies exist."""
    engine = RootCauseDiagnosisEngine()
    diag = engine.diagnose(active_anomalies=[])
    assert diag.aircraft_id == "UNKNOWN"
    assert "no active anomalies" in diag.explanation.lower()
    assert len(diag.probable_causes) == 1
    assert "nominal" in diag.probable_causes[0].lower()
    assert diag.confidence == 1.0


def test_diagnosis_single_thermal_anomaly():
    """Verify diagnosis attributes thermal anomaly to propulsion subsystem with cautious language."""
    engine = RootCauseDiagnosisEngine()
    anom = create_mock_anomaly(
        subsystem=TwinSubsystemType.PROPULSION,
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        signal="engine_temperature_c",
        observed_value=840.0,
    )

    diag = engine.diagnose(active_anomalies=[anom])
    assert diag.aircraft_id == "AERO-001"
    assert diag.primary_subsystem == TwinSubsystemType.PROPULSION
    assert len(diag.probable_causes) > 0
    # Must use cautious language
    assert any("probable" in c.lower() or "possible" in c.lower() for c in diag.probable_causes)
    assert diag.confidence >= 0.70


def test_diagnosis_multi_signal_propulsion_correlation():
    """Verify multi-signal correlation (Thermal + Vibration + Pressure) increases diagnostic confidence."""
    engine = RootCauseDiagnosisEngine()

    a_temp = create_mock_anomaly(
        signal="engine_temperature_c",
        anomaly_type=AnomalyType.THERMAL_ANOMALY,
        confidence=0.85,
        observed_value=880.0,
    )
    a_vib = create_mock_anomaly(
        signal="vibration_ips",
        anomaly_type=AnomalyType.VIBRATION_ANOMALY,
        confidence=0.88,
        observed_value=3.8,
    )
    a_press = create_mock_anomaly(
        signal="engine_pressure_kpa",
        anomaly_type=AnomalyType.PRESSURE_ANOMALY,
        confidence=0.80,
        observed_value=620.0,
    )

    diag = engine.diagnose(active_anomalies=[a_temp, a_vib, a_press])

    assert diag.primary_subsystem == TwinSubsystemType.PROPULSION
    # Multi-signal correlation should push confidence to high level (>= 0.90)
    assert diag.confidence >= 0.90
    assert any("multi-signal" in c.lower() or "thermal and mechanical" in c.lower() for c in diag.probable_causes)
    assert "multi-signal correlation" in diag.explanation.lower()


def test_diagnosis_structural_stress():
    """Verify G-load anomaly diagnoses airframe structural stress."""
    engine = RootCauseDiagnosisEngine()
    a_gload = create_mock_anomaly(
        subsystem=TwinSubsystemType.STRUCTURE,
        anomaly_type=AnomalyType.G_LOAD_ANOMALY,
        signal="g_load",
        observed_value=8.2,
    )

    diag = engine.diagnose(active_anomalies=[a_gload])
    assert diag.primary_subsystem == TwinSubsystemType.STRUCTURE
    assert any("structural" in c.lower() or "load factor" in c.lower() for c in diag.probable_causes)


def test_diagnosis_telemetry_degraded_penalty():
    """Verify degraded telemetry reduces diagnostic confidence."""
    engine = RootCauseDiagnosisEngine()
    anom = create_mock_anomaly(confidence=0.85)

    telemetry_valid = NormalizedTelemetry(
        observation_id="obs-01",
        aircraft_id="AERO-001",
        timestamp=datetime.now(timezone.utc),
        altitude_m=5000.0,
        airspeed_mps=200.0,
        mach=0.6,
        g_load=1.0,
        fuel_flow_kg_h=2000.0,
        engine_temperature_c=800.0,
        quality_status=QualityStatus.VALID,
    )

    telemetry_degraded = NormalizedTelemetry(
        observation_id="obs-02",
        aircraft_id="AERO-001",
        timestamp=datetime.now(timezone.utc),
        altitude_m=5000.0,
        airspeed_mps=200.0,
        mach=0.6,
        g_load=1.0,
        fuel_flow_kg_h=2000.0,
        engine_temperature_c=800.0,
        quality_status=QualityStatus.DEGRADED,
    )

    diag_valid = engine.diagnose(active_anomalies=[anom], telemetry=telemetry_valid)
    diag_deg = engine.diagnose(active_anomalies=[anom], telemetry=telemetry_degraded)

    assert diag_deg.confidence < diag_valid.confidence
    assert "telemetry quality was degraded" in diag_deg.explanation.lower()
