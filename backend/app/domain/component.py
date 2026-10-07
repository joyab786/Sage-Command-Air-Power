"""
SageCommand Air Power System (Aero) — Component Domain Model.
Represents an aircraft subsystem or Line Replaceable Unit (LRU),
tracking its serial identity, parent airframe link, operational hours/cycles,
and dynamic health condition assessment.
"""

from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.domain.enums import ComponentHealth, ComponentType


class ComponentBase(AeroBaseModel):
    """Core shared fields for subsystem and component representations."""

    component_id: str = Field(..., min_length=1, max_length=64, description="Unique component identifier")
    aircraft_id: str = Field(..., min_length=1, max_length=64, description="Foreign identifier of host aircraft")
    component_type: ComponentType = Field(..., description="Standardized subsystem classification")
    serial_number: str = Field(..., min_length=1, max_length=64, description="Manufacturer serial number")
    health_state: ComponentHealth = Field(default=ComponentHealth.HEALTHY, description="Current health condition")
    installation_date: Optional[datetime] = Field(default=None, description="Date of airframe integration")
    accumulated_hours: float = Field(default=0.0, ge=0.0, description="Cumulative operational hours")
    accumulated_cycles: int = Field(default=0, ge=0, description="Cumulative operational or thermal cycles")
    last_maintenance_at: Optional[datetime] = Field(default=None, description="Timestamp of most recent service")

    @field_validator("component_id", "aircraft_id", "serial_number", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Identifier cannot be empty or purely whitespace")
            return stripped
        return value

    @field_validator("accumulated_hours")
    @classmethod
    def validate_hours(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("Accumulated hours cannot be negative")
        return round(value, 2)

    @field_validator("accumulated_cycles")
    @classmethod
    def validate_cycles(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Accumulated cycles cannot be negative")
        return value


class ComponentCreate(ComponentBase):
    """Payload contract for registering an installed subsystem component."""
    pass


class ComponentUpdate(AeroBaseModel):
    """Payload contract for updating component health or operational wear."""

    health_state: Optional[ComponentHealth] = None
    accumulated_hours: Optional[float] = Field(default=None, ge=0.0)
    accumulated_cycles: Optional[int] = Field(default=None, ge=0)
    last_maintenance_at: Optional[datetime] = None

    @field_validator("accumulated_hours")
    @classmethod
    def validate_hours(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0.0:
            raise ValueError("Accumulated hours cannot be negative")
        return round(value, 2) if value is not None else None

    @field_validator("accumulated_cycles")
    @classmethod
    def validate_cycles(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Accumulated cycles cannot be negative")
        return value


class ComponentResponse(ComponentBase):
    """Authoritative API response contract for component entities."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    created_at: datetime = Field(..., description="Timestamp of component registration")
    updated_at: datetime = Field(..., description="Timestamp of last record update")
