"""
SageCommand Air Power System (Aero) — Unit Tests: Digital Twin Models.
Verifies AircraftTwinState schemas, subsystem models, enum bounds, and health reasons.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.digital_twin.models import (
    TwinSubsystemType,
    TwinHealthState,
    HealthReason,
    SubsystemState,
    AircraftTwinState,
    FlightSession,
    utc_now,
)


def test_twin_enums():
    """Verifies conceptual subsystem and health state enums."""
    assert TwinSubsystemType.PROPULSION.value == "PROPULSION"
    assert TwinSubsystemType.HYDRAULIC.value == "HYDRAULIC"
    assert TwinSubsystemType.STRUCTURE.value == "STRUCTURE"
    assert TwinSubsystemType.AVIONICS.value == "AVIONICS"
    assert TwinSubsystemType.FUEL.value == "FUEL"
    assert TwinSubsystemType.FLIGHT_CONTROLS.value == "FLIGHT_CONTROLS"

    assert TwinHealthState.HEALTHY.value == "HEALTHY"
    assert TwinHealthState.DEGRADED.value == "DEGRADED"
    assert TwinHealthState.WARNING.value == "WARNING"
    assert TwinHealthState.CRITICAL.value == "CRITICAL"
    assert TwinHealthState.FAILED.value == "FAILED"
    assert TwinHealthState.UNKNOWN.value == "UNKNOWN"


def test_health_reason_structure():
    """Verifies structured explainability reason schema."""
    reason = HealthReason(
        signal="vibration",
        observed=1.42,
        contribution=-35.0,
        reason="Severe mechanical vibration exceedance",
    )
    assert reason.signal == "vibration"
    assert reason.observed == 1.42
    assert reason.contribution == -35.0
    assert "vibration exceedance" in reason.reason


def test_subsystem_state_bounds():
    """Verifies subsystem state constraints and defaults."""
    sub = SubsystemState(
        subsystem=TwinSubsystemType.PROPULSION,
        health_state=TwinHealthState.HEALTHY,
        health_score=95.5,
        wear_index=0.12,
        last_updated_at=utc_now(),
        contributing_signals=["engine_temperature", "vibration"],
    )
    assert sub.health_score == 95.5
    assert sub.wear_index == 0.12

    # Health score out of bounds
    with pytest.raises(ValidationError):
        SubsystemState(
            subsystem=TwinSubsystemType.PROPULSION,
            health_score=105.0,
            last_updated_at=utc_now(),
        )

    # Wear index out of bounds
    with pytest.raises(ValidationError):
        SubsystemState(
            subsystem=TwinSubsystemType.PROPULSION,
            wear_index=1.5,
            last_updated_at=utc_now(),
        )


def test_aircraft_twin_state_creation():
    """Verifies creation and defaults of AircraftTwinState."""
    now = datetime.now(timezone.utc)
    state = AircraftTwinState(
        aircraft_id="SU-30-SB001",
        timestamp=now,
        operational_status="IN_FLIGHT",
        altitude=10500.0,
        airspeed=245.0,
        mach=0.82,
        g_load=1.05,
        fuel_flow=2400.0,
        engine_temperature=840.0,
        engine_pressure=1420.0,
        vibration=0.35,
        flight_hours=125.4,
        flight_cycles=42,
        current_flight_id="FLT-2026-001",
        health_state=TwinHealthState.HEALTHY,
        health_score=98.0,
        wear_index=0.08,
    )
    assert state.aircraft_id == "SU-30-SB001"
    assert state.altitude == 10500.0
    assert state.health_state == TwinHealthState.HEALTHY
    assert state.health_score == 98.0
    assert state.wear_index == 0.08
    assert state.data_quality == "VALID"


def test_flight_session_model():
    """Verifies flight session model creation."""
    now = datetime.now(timezone.utc)
    sess = FlightSession(
        session_id="sess_001",
        aircraft_id="RAFALE-RB001",
        flight_id="FLT-900",
        started_at=now,
        last_seen_at=now,
        duration_seconds=120.0,
        cycle_counted=False,
    )
    assert sess.session_id == "sess_001"
    assert sess.duration_seconds == 120.0
    assert not sess.cycle_counted
