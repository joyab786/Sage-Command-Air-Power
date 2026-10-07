"""
Unit tests for Anomaly Detectors (Threshold, Statistical, and Composite).
Verifies deterministic rules, boundary values, zero variance safety,
and data quality anomaly generation.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import (
    AircraftTwinState,
    TwinSubsystemType,
    TwinHealthState,
    SubsystemState,
)
from app.intelligence.models import (
    AnomalySeverity,
    AnomalyType,
)
from app.intelligence.anomaly.threshold import ThresholdAnomalyDetector
from app.intelligence.anomaly.statistical import StatisticalAnomalyDetector
from app.intelligence.anomaly.detectors import CompositeAnomalyDetector


def create_sample_telemetry(
    aircraft_id: str = "AERO-001",
    timestamp: datetime = None,
    engine_temp: float = 650.0,
    engine_pressure: float = 350.0,
    vibration: float = 0.2,
    g_load: float = 1.0,
    mach: float = 0.8,
    airspeed: float = 240.0,
    control_surface: float = 5.0,
    quality: QualityStatus = QualityStatus.VALID,
) -> NormalizedTelemetry:
    """Helper to produce standard normalized telemetry frames."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    return NormalizedTelemetry(
        observation_id="obs-test-01",
        aircraft_id=aircraft_id,
        flight_id="SORTIE-01",
        timestamp=timestamp,
        altitude_m=8000.0,
        airspeed_mps=airspeed,
        mach=mach,
        g_load=g_load,
        fuel_flow_kg_h=2200.0,
        engine_temperature_c=engine_temp,
        engine_pressure_kpa=engine_pressure,
        vibration_ips=vibration,
        control_surface_angle_deg=control_surface,
        quality_status=quality,
        envelope_status=EnvelopeStatus.WITHIN_ENVELOPE,
        source="TEST_SUITE",
    )


def test_threshold_detector_normal_flight():
    """Verify threshold detector returns no anomalies for nominal flight data."""
    detector = ThresholdAnomalyDetector()
    telemetry = create_sample_telemetry()
    anomalies = detector.detect(telemetry)
    assert len(anomalies) == 0


def test_threshold_detector_thermal_anomalies():
    """Verify caution vs critical severity scaling on engine temperature."""
    detector = ThresholdAnomalyDetector()

    # 1. Below caution (770 °C < 780 °C caution threshold) -> No anomaly
    t_normal = create_sample_telemetry(engine_temp=770.0)
    assert len(detector.detect(t_normal)) == 0

    # 2. Caution level (800 °C > 780 °C caution threshold, < 850 °C critical threshold)
    t_caution = create_sample_telemetry(engine_temp=800.0)
    anoms_c = detector.detect(t_caution)
    assert len(anoms_c) == 1
    assert anoms_c[0].anomaly_type == AnomalyType.THERMAL_ANOMALY
    assert anoms_c[0].subsystem == TwinSubsystemType.PROPULSION
    assert anoms_c[0].severity in [AnomalySeverity.MEDIUM, AnomalySeverity.HIGH]
    assert anoms_c[0].observed_value == 800.0
    assert "caution" in anoms_c[0].description.lower()

    # 3. Critical level (920 °C > 850 °C critical limit)
    t_crit = create_sample_telemetry(engine_temp=920.0)
    anoms_crit = detector.detect(t_crit)
    assert len(anoms_crit) == 1
    assert anoms_crit[0].severity == AnomalySeverity.CRITICAL
    assert anoms_crit[0].observed_value == 920.0
    assert anoms_crit[0].confidence >= 0.90


def test_threshold_detector_vibration_spike():
    """Verify vibration spike detection and propulsion subsystem attribution."""
    detector = ThresholdAnomalyDetector()

    # Vibration = 4.2 ips (> 3.5 ips critical limit)
    t_vib = create_sample_telemetry(vibration=4.2)
    anoms = detector.detect(t_vib)
    assert len(anoms) == 1
    assert anoms[0].anomaly_type == AnomalyType.VIBRATION_ANOMALY
    assert anoms[0].subsystem == TwinSubsystemType.PROPULSION
    assert anoms[0].severity == AnomalySeverity.CRITICAL
    assert anoms[0].signal == "vibration_ips"


def test_threshold_detector_g_load_exceedance():
    """Verify structural G-load anomaly triggered on high load factor."""
    detector = ThresholdAnomalyDetector()

    # G-load = 8.5g (> 7.5g caution, > 8.0g critical)
    t_gload = create_sample_telemetry(g_load=8.5)
    anoms = detector.detect(t_gload)
    assert len(anoms) == 1
    assert anoms[0].anomaly_type == AnomalyType.G_LOAD_ANOMALY
    assert anoms[0].subsystem == TwinSubsystemType.STRUCTURE
    assert anoms[0].severity == AnomalySeverity.CRITICAL


def test_threshold_detector_flight_control_anomaly():
    """Verify flight control deflection angle threshold violation."""
    detector = ThresholdAnomalyDetector()

    # Control surface angle = 35.0 deg (> 30.0 deg critical limit)
    t_ctrl = create_sample_telemetry(control_surface=35.0)
    anoms = detector.detect(t_ctrl)
    assert len(anoms) == 1
    assert anoms[0].anomaly_type == AnomalyType.CONTROL_SURFACE_ANOMALY
    assert anoms[0].subsystem == TwinSubsystemType.FLIGHT_CONTROLS
    assert anoms[0].severity == AnomalySeverity.CRITICAL


def test_threshold_detector_degraded_telemetry_quality():
    """Verify degraded telemetry generates a data quality anomaly with moderate severity."""
    detector = ThresholdAnomalyDetector()

    t_deg = create_sample_telemetry(quality=QualityStatus.DEGRADED)
    anoms = detector.detect(t_deg)
    assert len(anoms) == 1
    assert anoms[0].anomaly_type == AnomalyType.TELEMETRY_QUALITY_ANOMALY
    assert anoms[0].subsystem == TwinSubsystemType.AVIONICS
    assert anoms[0].severity in [AnomalySeverity.LOW, AnomalySeverity.MEDIUM]


def test_statistical_detector_insufficient_samples():
    """Verify statistical detector does not trigger when observations are below minimum_samples."""
    detector = StatisticalAnomalyDetector(window_size=10, min_samples=5, z_threshold=2.5)

    # Feed 4 nominal observations (< 5 min_samples)
    for i in range(4):
        t = create_sample_telemetry(engine_temp=650.0 + i)
        anoms = detector.detect(t)
        assert len(anoms) == 0


def test_statistical_detector_zero_variance_safety():
    """Verify zero variance does not cause division by zero or spurious alerts."""
    detector = StatisticalAnomalyDetector(window_size=10, min_samples=5, z_threshold=2.5)

    # Feed identical values (std_dev = 0.0)
    for _ in range(6):
        t = create_sample_telemetry(engine_temp=700.0)
        anoms = detector.detect(t)
        assert len(anoms) == 0


def test_statistical_detector_outlier_detection():
    """Verify statistical detector identifies statistical outliers once baseline is established."""
    detector = StatisticalAnomalyDetector(window_size=10, min_samples=5, z_threshold=2.5)

    # Feed 6 stable baseline observations around 650 °C with slight noise
    temps = [648.0, 652.0, 650.0, 649.0, 651.0, 650.0]
    for temp in temps:
        t = create_sample_telemetry(engine_temp=temp)
        anoms = detector.detect(t)
        assert len(anoms) == 0

    # Inject a statistical outlier that is still within standard hard limit (e.g., 730 °C vs ~650 °C)
    t_outlier = create_sample_telemetry(engine_temp=730.0)
    anoms = detector.detect(t_outlier)

    # Should detect statistical anomaly
    assert len(anoms) >= 1
    stat_anom = next(a for a in anoms if "statistical" in a.detector.lower())
    assert stat_anom.signal == "engine_temperature_c"
    assert "z=" in stat_anom.description.lower() or "z-score" in stat_anom.description.lower()
    assert stat_anom.confidence >= 0.75


def test_composite_anomaly_detector():
    """Verify composite detector aggregates all active detectors safely."""
    detector = CompositeAnomalyDetector()

    # Normal frame -> 0 anomalies
    t_norm = create_sample_telemetry()
    assert len(detector.detect_all(t_norm)) == 0

    # Frame with both thermal spike and vibration spike
    t_multi = create_sample_telemetry(engine_temp=890.0, vibration=4.0)
    anoms = detector.detect_all(t_multi)
    assert len(anoms) >= 2
    types = {a.anomaly_type for a in anoms}
    assert AnomalyType.THERMAL_ANOMALY in types
    assert AnomalyType.VIBRATION_ANOMALY in types
