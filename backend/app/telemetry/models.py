"""
SageCommand Air Power System (Aero) — Telemetry Data Fabric Models.
Defines schemas for normalized telemetry frames, quality evaluations,
flight envelope assessments, ingestion payloads, and batch results.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator, ConfigDict
from app.contracts.base import AeroBaseModel


class QualityStatus(str, Enum):
    """Integrity classification for ingested telemetry observation."""

    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"


class EnvelopeStatus(str, Enum):
    """Flight envelope compliance classification."""

    WITHIN_ENVELOPE = "WITHIN_ENVELOPE"
    CAUTION = "CAUTION"
    EXCEEDED = "EXCEEDED"


class EnvelopeViolation(AeroBaseModel):
    """Detailed parameter boundary violation record."""

    parameter: str = Field(..., description="Observed parameter name (e.g., g_load, altitude)")
    observed_value: float = Field(..., description="Value recorded in normalized units")
    limit: float = Field(..., description="Threshold boundary value")
    direction: str = Field(..., description="ABOVE or BELOW boundary")
    severity: str = Field(..., description="CAUTION, HIGH, or CRITICAL")
    message: str = Field(..., description="Descriptive diagnostic advisory")


class QualityAssessmentResult(AeroBaseModel):
    """Diagnostic result from data quality assessment."""

    status: QualityStatus = Field(default=QualityStatus.VALID)
    reasons: List[str] = Field(default_factory=list, description="Reasons for INVALID or DEGRADED rating")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal data fidelity warnings")
    metrics_evaluated: int = Field(default=0, description="Total channels verified")


class EnvelopeAssessmentResult(AeroBaseModel):
    """Result of evaluating an observation against flight envelope boundaries."""

    status: EnvelopeStatus = Field(default=EnvelopeStatus.WITHIN_ENVELOPE)
    violations: List[EnvelopeViolation] = Field(default_factory=list)
    parameters_checked: int = Field(default=0)


class NormalizedTelemetry(AeroBaseModel):
    """
    Canonical internal representation of a flight telemetry frame.
    All channels are converted to authoritative standard units:
      - altitude: meters (m)
      - airspeed: meters per second (m/s)
      - engine_temperature: degrees Celsius (°C)
      - engine_pressure: kilopascals (kPa)
      - vibration: inches per second (ips)
      - fuel_flow: kg per hour (kg/h)
      - control surfaces: degrees (deg)
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    observation_id: str = Field(..., description="Unique observation event identifier")
    timestamp: datetime = Field(..., description="Observation timestamp in UTC")
    aircraft_id: str = Field(..., description="Authoritative host aircraft ID")
    flight_id: Optional[str] = Field(default=None, description="Active sortie / flight identifier")

    # Normalized physical channels
    altitude_m: Optional[float] = Field(default=None, description="Altitude in meters")
    airspeed_mps: Optional[float] = Field(default=None, description="Airspeed in meters/second")
    mach: Optional[float] = Field(default=None, description="Mach number")
    g_load: Optional[float] = Field(default=None, description="Normal acceleration in G units")
    fuel_flow_kg_h: Optional[float] = Field(default=None, description="Fuel consumption rate in kg/h")
    engine_temperature_c: Optional[float] = Field(default=None, description="Turbine/exhaust temperature in Celsius")
    engine_pressure_kpa: Optional[float] = Field(default=None, description="Core engine pressure in kilopascals")
    vibration_ips: Optional[float] = Field(default=None, description="Vibration amplitude in inches/second")
    control_surface_angle_deg: Optional[float] = Field(default=None, description="Control surface deflection in degrees")

    # Assessment metadata
    quality_status: QualityStatus = Field(default=QualityStatus.VALID)
    envelope_status: EnvelopeStatus = Field(default=EnvelopeStatus.WITHIN_ENVELOPE)
    source: str = Field(default="TELEMETRY_STREAM")
    raw_units: Dict[str, str] = Field(default_factory=dict, description="Original ingested units map")


class TelemetryInput(AeroBaseModel):
    """
    Flexible input frame for ingesting raw or external telemetry observations.
    Supports heterogeneous units via unit metadata dictionary.
    """

    observation_id: Optional[str] = Field(default=None, description="Optional caller observation ID (generated if omitted)")
    timestamp: Optional[datetime] = Field(default=None, description="Observation timestamp (defaults to current UTC)")
    aircraft_id: str = Field(..., min_length=1, max_length=64, description="Target aircraft identifier")
    flight_id: Optional[str] = Field(default=None, max_length=64, description="Sortie/flight identifier")

    # Channel inputs
    altitude: Optional[float] = None
    airspeed: Optional[float] = None
    mach: Optional[float] = None
    g_load: Optional[float] = None
    fuel_flow: Optional[float] = None
    engine_temperature: Optional[float] = None
    engine_pressure: Optional[float] = None
    vibration: Optional[float] = None
    control_surface_angle: Optional[float] = None

    # Unit declarations: e.g. {"altitude": "ft", "airspeed": "kts", "temperature": "C", "pressure": "psi"}
    units: Optional[Dict[str, str]] = Field(default=None, description="Engineering units map for supplied channels")
    source: Optional[str] = Field(default="INGESTION", description="Telemetry signal source")

    @field_validator("aircraft_id", mode="before")
    @classmethod
    def strip_aircraft_id(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("aircraft_id cannot be empty")
            return stripped
        return v


class TelemetryIngestResult(AeroBaseModel):
    """Comprehensive response for a single telemetry frame ingestion."""

    accepted: bool = Field(..., description="True if observation entered buffer/database")
    observation_id: str = Field(...)
    aircraft_id: str = Field(...)
    quality: QualityAssessmentResult = Field(...)
    envelope: EnvelopeAssessmentResult = Field(...)
    normalized: Optional[NormalizedTelemetry] = Field(default=None)
    persisted: bool = Field(default=False)
    buffered: bool = Field(default=False)
    warnings: List[str] = Field(default_factory=list)


class BatchIngestRequest(AeroBaseModel):
    """Batch ingestion payload containing multiple telemetry observations."""

    observations: List[TelemetryInput] = Field(..., min_length=1, max_length=1000)


class BatchIngestResult(AeroBaseModel):
    """Summary of batch ingestion processing."""

    total_received: int = Field(...)
    total_accepted: int = Field(...)
    total_rejected: int = Field(...)
    results: List[TelemetryIngestResult] = Field(default_factory=list)


class DemoGenerateRequest(AeroBaseModel):
    """Request schema for generating synthetic demonstration flight profiles."""

    aircraft_id: str = Field(..., min_length=1, max_length=64)
    flight_id: Optional[str] = Field(default=None, max_length=64)
    profile: str = Field(default="NORMAL_CRUISE", description="NORMAL_CRUISE, TAKEOFF_CLIMB, HIGH_G_TURN, SUPERSONIC_CRUISE, THERMAL_SPIKE, VIBRATION_SPIKE")
    count: int = Field(default=10, ge=1, le=200, description="Number of synthetic frames to generate")
    seed: Optional[int] = Field(default=42, description="Random seed for deterministic output")
