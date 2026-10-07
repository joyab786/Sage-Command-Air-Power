"""
SageCommand Air Power System (Aero) — Telemetry Domain Contract.
Represents a normalized telemetry observation across avionics, propulsion,
aerodynamic, and structural sensor channels.
"""

from datetime import datetime
from typing import Optional, Dict
from pydantic import Field, field_validator
from app.contracts.base import AeroBaseModel
from app.domain.enums import TelemetryQuality


class TelemetryObservation(AeroBaseModel):
    """
    Normalized sensor observation contract for flight telemetry.
    Designed for flexible, partially populated sensor frames.
    """

    observation_id: str = Field(..., min_length=1, max_length=64, description="Unique observation event ID")
    timestamp: datetime = Field(..., description="Timestamp of sensor recording")
    aircraft_id: str = Field(..., min_length=1, max_length=64, description="Target aircraft identifier")
    flight_id: Optional[str] = Field(default=None, max_length=64, description="Active flight / sortie identifier")

    # Aerodynamic / Flight Envelope Channels
    altitude_ft: Optional[float] = Field(default=None, description="Barometric or GPS altitude in feet")
    airspeed_kts: Optional[float] = Field(default=None, ge=0.0, description="Calibrated or indicated airspeed in knots")
    mach: Optional[float] = Field(default=None, ge=0.0, description="Mach flight speed ratio")
    g_load: Optional[float] = Field(default=None, description="Normal acceleration in G units")

    # Propulsion & Mechanical Channels
    fuel_flow_kg_h: Optional[float] = Field(default=None, ge=0.0, description="Total engine fuel burn rate in kg/h")
    engine_temperature_c: Optional[float] = Field(default=None, description="Exhaust Gas Temperature (EGT) or turbine temp in Celsius")
    engine_pressure_psi: Optional[float] = Field(default=None, description="Engine core oil/hydraulic pressure in PSI")
    vibration_ips: Optional[float] = Field(default=None, ge=0.0, description="Engine/airframe vibration in inches per second")

    # Flight Controls
    control_surface_angle_deg: Optional[float] = Field(default=None, description="Primary control surface deflection in degrees")

    # Data Quality & Provenance
    quality: TelemetryQuality = Field(default=TelemetryQuality.GOOD, description="Signal integrity flag")
    source: str = Field(default="SIMULATION", max_length=64, description="Telemetry origin (e.g. SIMULATION, TELEMETRY_STREAM, FDR)")
    unit_metadata: Optional[Dict[str, str]] = Field(default=None, description="Explicit engineering unit definitions")

    @field_validator("aircraft_id", "observation_id", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Identifier cannot be empty")
            return stripped
        return value

    @field_validator("mach")
    @classmethod
    def validate_mach(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0.0:
            raise ValueError("Mach cannot be negative")
        return value

    @field_validator("fuel_flow_kg_h")
    @classmethod
    def validate_fuel(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0.0:
            raise ValueError("Fuel flow cannot be negative")
        return value

    @field_validator("vibration_ips")
    @classmethod
    def validate_vibration(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0.0:
            raise ValueError("Vibration amplitude cannot be negative")
        return value
