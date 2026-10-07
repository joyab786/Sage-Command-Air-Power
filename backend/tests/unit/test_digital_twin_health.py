"""
SageCommand Air Power System (Aero) — Unit Tests: Aircraft Health Estimator.
Verifies deterministic rule-based health scoring, explainability reasons,
subsystem health breakdowns, and unobserved channel handling.
"""

from datetime import datetime, timezone
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import TwinHealthState, TwinSubsystemType
from app.digital_twin.health import AircraftHealthEstimator


def _create_nominal_telemetry() -> NormalizedTelemetry:
    return NormalizedTelemetry(
        observation_id="obs_nom",
        aircraft_id="MKI-001",
        timestamp=datetime.now(timezone.utc),
        altitude_m=10000.0,
        airspeed_mps=240.0,
        mach=0.80,
        g_load=1.0,
        fuel_flow_kg_h=2000.0,
        engine_temperature_c=800.0,
        engine_pressure_kpa=1200.0,
        vibration_ips=0.35,
        quality_status=QualityStatus.VALID,
        envelope_status=EnvelopeStatus.WITHIN_ENVELOPE,
    )


def test_health_estimator_nominal():
    """Verifies that nominal cruise conditions produce HEALTHY ratings."""
    telem = _create_nominal_telemetry()
    score, state, reasons, subsystems, warnings = AircraftHealthEstimator.evaluate_health(telem)

    assert score >= 90.0
    assert state == TwinHealthState.HEALTHY
    assert len(reasons) == 0
    assert len(warnings) == 0

    # Verify hydraulic reports UNKNOWN and does not manufacture sensor data
    assert subsystems[TwinSubsystemType.HYDRAULIC.value].health_state == TwinHealthState.UNKNOWN
    assert "No dedicated hydraulic sensor" in subsystems[TwinSubsystemType.HYDRAULIC.value].warnings[0]


def test_health_estimator_thermal_anomaly():
    """Verifies that thermal exceedance triggers explainable degradation."""
    telem = _create_nominal_telemetry()
    telem.engine_temperature_c = 1060.0  # Above 1050°C critical threshold

    score, state, reasons, subsystems, warnings = AircraftHealthEstimator.evaluate_health(telem)

    assert score < 75.0
    assert state in (TwinHealthState.WARNING, TwinHealthState.CRITICAL)
    assert any(r.signal == "engine_temperature" for r in reasons)
    thermal_reason = next(r for r in reasons if r.signal == "engine_temperature")
    assert thermal_reason.observed == 1060.0
    assert thermal_reason.contribution == -35.0
    assert "Critical turbine thermal exceedance" in thermal_reason.reason
    assert subsystems[TwinSubsystemType.PROPULSION.value].health_state in (
        TwinHealthState.WARNING,
        TwinHealthState.CRITICAL,
    )


def test_health_estimator_vibration_anomaly():
    """Verifies that vibration spikes trigger explainable mechanical degradation."""
    telem = _create_nominal_telemetry()
    telem.vibration_ips = 1.35  # Above 1.25 ips critical limit

    score, state, reasons, subsystems, warnings = AircraftHealthEstimator.evaluate_health(telem)

    assert score < 75.0
    assert any(r.signal == "vibration" for r in reasons)
    vib_reason = next(r for r in reasons if r.signal == "vibration")
    assert vib_reason.observed == 1.35
    assert vib_reason.contribution == -35.0
    assert "Severe mechanical vibration exceedance" in vib_reason.reason


def test_health_estimator_compounded_anomalies():
    """Verifies multiple simultaneous anomalies compound degradation predictably."""
    telem = _create_nominal_telemetry()
    telem.engine_temperature_c = 1060.0  # -35
    telem.vibration_ips = 1.35          # -35
    telem.g_load = 9.2                  # -35

    score, state, reasons, subsystems, warnings = AircraftHealthEstimator.evaluate_health(telem)

    # 100 - (35 + 35 + 35) = -5 -> clamped to 0.0
    assert score == 0.0
    assert state == TwinHealthState.FAILED
    assert len(reasons) >= 3


def test_health_estimator_deterministic():
    """Verifies that identical inputs yield identical health outputs."""
    telem = _create_nominal_telemetry()
    telem.engine_temperature_c = 980.0
    telem.vibration_ips = 0.90

    res1 = AircraftHealthEstimator.evaluate_health(telem)
    res2 = AircraftHealthEstimator.evaluate_health(telem)

    assert res1[0] == res2[0]  # Score
    assert res1[1] == res2[1]  # State
    assert len(res1[2]) == len(res2[2])  # Reasons count
    for r1, r2 in zip(res1[2], res2[2]):
        assert r1.contribution == r2.contribution
        assert r1.reason == r2.reason
