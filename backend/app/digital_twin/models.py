"""
SageCommand Air Power System (Aero) — Aircraft Digital Twin Models.
Defines typed schemas for estimated operational state, conceptual subsystems,
health scoring, structured explainability reasons, wear indices, and flight sessions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field, ConfigDict
from app.contracts.base import AeroBaseModel


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class TwinSubsystemType(str, Enum):
    """Conceptual aerospace subsystems monitored by the digital twin."""

    PROPULSION = "PROPULSION"
    FUEL = "FUEL"
    HYDRAULIC = "HYDRAULIC"
    FLIGHT_CONTROLS = "FLIGHT_CONTROLS"
    AVIONICS = "AVIONICS"
    STRUCTURE = "STRUCTURE"


class TwinHealthState(str, Enum):
    """Categorical operational health classification for airframe and subsystems."""

    HEALTHY = "HEALTHY"      # 90 - 100: Nominal operations
    DEGRADED = "DEGRADED"    # 75 - 89: Usable with minor non-critical warnings
    WARNING = "WARNING"      # 50 - 74: Caution/advisory threshold exceeded
    CRITICAL = "CRITICAL"    # 25 - 49: Severe condition requiring immediate attention
    FAILED = "FAILED"        # 0 - 24: Unsafe / subsystem inoperative
    UNKNOWN = "UNKNOWN"      # Unobserved / no dedicated telemetry sensor


class HealthReason(AeroBaseModel):
    """Structured explainability reason for health score degradation."""

    signal: str = Field(..., description="Sensor channel or evaluation condition")
    observed: Optional[float] = Field(default=None, description="Observed parameter value in normalized units")
    contribution: float = Field(..., description="Penalty deducted from base score (negative or positive)")
    reason: str = Field(..., description="Human-readable explanation of why this condition caused degradation")


class SubsystemState(AeroBaseModel):
    """Estimated operational state for a specific aircraft subsystem."""

    subsystem: TwinSubsystemType = Field(..., description="Subsystem classification")
    health_state: TwinHealthState = Field(default=TwinHealthState.HEALTHY)
    health_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Calculated health score (0-100)")
    wear_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized cumulative wear index (0.0-1.0)")
    last_updated_at: datetime = Field(default_factory=utc_now)
    contributing_signals: List[str] = Field(default_factory=list, description="Sensor channels informing this state")
    warnings: List[str] = Field(default_factory=list, description="Diagnostic warnings or operational cautions")


class AircraftTwinState(AeroBaseModel):
    """
    Authoritative estimated operational state of an aircraft airframe.
    Continuously updated by incoming normalized telemetry observations.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    aircraft_id: str = Field(..., description="Authoritative host aircraft ID")
    timestamp: datetime = Field(..., description="Timestamp of the estimated state snapshot")
    operational_status: str = Field(default="ACTIVE", description="Aircraft operational readiness / mission status")

    # Current flight dynamics & telemetry snapshot
    altitude: Optional[float] = Field(default=None, description="Estimated altitude in meters (m)")
    airspeed: Optional[float] = Field(default=None, description="Estimated airspeed in meters/second (m/s)")
    mach: Optional[float] = Field(default=None, description="Estimated Mach number")
    g_load: Optional[float] = Field(default=None, description="Estimated normal acceleration in G units")
    fuel_flow: Optional[float] = Field(default=None, description="Estimated fuel consumption rate in kg/h")
    engine_temperature: Optional[float] = Field(default=None, description="Estimated core engine temperature in °C")
    engine_pressure: Optional[float] = Field(default=None, description="Estimated core engine pressure in kPa")
    vibration: Optional[float] = Field(default=None, description="Estimated mechanical vibration in ips")

    # Operational cumulative counters
    flight_hours: float = Field(default=0.0, ge=0.0, description="Cumulative flight hours recorded")
    flight_cycles: int = Field(default=0, ge=0, description="Cumulative flight cycles completed")
    current_flight_id: Optional[str] = Field(default=None, description="Active flight / sortie identifier")

    # Aggregated health & wear condition
    health_state: TwinHealthState = Field(default=TwinHealthState.HEALTHY, description="Overall airframe health state")
    health_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Composite health rating (0-100)")
    wear_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Composite structural/engine wear index (0.0-1.0)")
    subsystem_states: Dict[str, SubsystemState] = Field(default_factory=dict, description="State map by subsystem type")
    health_reasons: List[HealthReason] = Field(default_factory=list, description="Transparent explainability reasons")
    active_warnings: List[str] = Field(default_factory=list, description="Active flight envelope / sensor warnings")

    # Metadata
    data_quality: str = Field(default="VALID", description="Data quality rating of driving telemetry (VALID, DEGRADED)")
    last_updated_at: datetime = Field(default_factory=utc_now, description="Timestamp when twin state was computed")


class FlightSession(AeroBaseModel):
    """Lightweight tracking model for an active or completed flight session."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    session_id: str = Field(..., description="Unique flight session identifier")
    aircraft_id: str = Field(..., description="Associated aircraft identifier")
    flight_id: str = Field(..., description="Sortie or flight identifier")
    started_at: datetime = Field(..., description="Timestamp when session was initiated")
    last_seen_at: datetime = Field(..., description="Timestamp of latest observation in session")
    ended_at: Optional[datetime] = Field(default=None, description="Timestamp when session concluded")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Total elapsed flight duration in seconds")
    cycle_counted: bool = Field(default=False, description="True if this flight session cycle has been incremented")
