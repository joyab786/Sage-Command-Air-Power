"""
SageCommand Air Power System (Aero) — Aircraft Domain Model.
Represents an authoritative airframe asset, its registration, home base,
squadron assignment, lifecycle status, and cumulative operational flight metrics.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import Field, field_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.domain.enums import AircraftStatus


class AircraftBase(AeroBaseModel):
    """Core shared fields for aircraft representations."""

    aircraft_id: str = Field(..., min_length=1, max_length=64, description="Unique aircraft identifier")
    tail_number: str = Field(..., min_length=1, max_length=32, description="Tactical tail / registration number")
    aircraft_type: str = Field(..., min_length=1, max_length=64, description="Aircraft classification or model (e.g. Su-30MKI, Rafale, Tejas)")
    variant: Optional[str] = Field(default=None, max_length=64, description="Airframe sub-variant or block designation")
    air_base: str = Field(..., min_length=1, max_length=64, description="Home operational air base")
    squadron: str = Field(..., min_length=1, max_length=64, description="Assigned squadron unit designation")
    status: AircraftStatus = Field(default=AircraftStatus.ACTIVE, description="Lifecycle status")
    total_flight_hours: float = Field(default=0.0, ge=0.0, description="Cumulative flight hours logged")
    total_flight_cycles: int = Field(default=0, ge=0, description="Cumulative flight/landing cycles logged")
    last_flight_at: Optional[datetime] = Field(default=None, description="Timestamp of most recent flight sortie")

    @field_validator("tail_number", "aircraft_id", "air_base", "squadron", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or purely whitespace")
            return stripped
        return value

    @field_validator("total_flight_hours")
    @classmethod
    def validate_hours(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("Total flight hours cannot be negative")
        return round(value, 2)

    @field_validator("total_flight_cycles")
    @classmethod
    def validate_cycles(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Total flight cycles cannot be negative")
        return value


class AircraftCreate(AircraftBase):
    """Payload contract for registering a new aircraft asset."""
    pass


class AircraftUpdate(AeroBaseModel):
    """Payload contract for updating mutable aircraft attributes."""

    variant: Optional[str] = Field(default=None, max_length=64)
    air_base: Optional[str] = Field(default=None, min_length=1, max_length=64)
    squadron: Optional[str] = Field(default=None, min_length=1, max_length=64)
    status: Optional[AircraftStatus] = None
    total_flight_hours: Optional[float] = Field(default=None, ge=0.0)
    total_flight_cycles: Optional[int] = Field(default=None, ge=0)
    last_flight_at: Optional[datetime] = None

    @field_validator("total_flight_hours")
    @classmethod
    def validate_hours(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0.0:
            raise ValueError("Total flight hours cannot be negative")
        return round(value, 2) if value is not None else None

    @field_validator("total_flight_cycles")
    @classmethod
    def validate_cycles(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Total flight cycles cannot be negative")
        return value


class AircraftResponse(AircraftBase):
    """Authoritative API response contract for aircraft entities."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    created_at: datetime = Field(..., description="Timestamp of asset registration")
    updated_at: datetime = Field(..., description="Timestamp of last metadata update")
