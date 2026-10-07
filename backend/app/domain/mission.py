"""
SageCommand Air Power System (Aero) — Mission & Sortie Domain Model.
Represents tactical mission commitments, airframe demand, schedule boundaries,
assigned assets, and required airframe readiness thresholds.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import Field, field_validator, model_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.domain.enums import MissionStatus, MissionType, ReadinessStatus


class MissionBase(AeroBaseModel):
    """Core shared fields for mission / sortie planning."""

    mission_id: str = Field(..., min_length=1, max_length=64, description="Unique mission identifier")
    mission_name: Optional[str] = Field(default=None, max_length=128, description="Tactical operation or exercise codename")
    mission_type: MissionType = Field(default=MissionType.TRAINING, description="Operational profile")
    scheduled_start: datetime = Field(..., description="Target sortie launch time")
    scheduled_end: datetime = Field(..., description="Target sortie recovery / mission completion time")
    required_aircraft: int = Field(default=1, gt=0, description="Minimum number of mission-capable airframes required")
    assigned_aircraft: List[str] = Field(default_factory=list, description="List of assigned aircraft IDs / tail numbers")
    status: MissionStatus = Field(default=MissionStatus.PLANNED, description="Operational mission execution state")
    readiness_requirement: ReadinessStatus = Field(default=ReadinessStatus.FMC, description="Minimum airframe readiness threshold required")

    @field_validator("mission_id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Mission ID cannot be empty")
            return stripped
        return value

    @field_validator("required_aircraft")
    @classmethod
    def validate_required_aircraft(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Required aircraft must be strictly positive (> 0)")
        return value

    @model_validator(mode="after")
    def validate_schedule(self) -> "MissionBase":
        if self.scheduled_end < self.scheduled_start:
            raise ValueError("Scheduled mission end cannot precede scheduled start")
        return self


class MissionCreate(MissionBase):
    """Payload contract for registering a new mission plan."""
    pass


class MissionUpdate(AeroBaseModel):
    """Payload contract for updating mission assignment and execution status."""

    mission_name: Optional[str] = Field(default=None, max_length=128)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    required_aircraft: Optional[int] = Field(default=None, gt=0)
    assigned_aircraft: Optional[List[str]] = None
    status: Optional[MissionStatus] = None
    readiness_requirement: Optional[ReadinessStatus] = None

    @field_validator("required_aircraft")
    @classmethod
    def validate_required_aircraft(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("Required aircraft must be strictly positive (> 0)")
        return value

    @model_validator(mode="after")
    def validate_schedule_bounds(self) -> "MissionUpdate":
        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_end < self.scheduled_start:
                raise ValueError("Scheduled mission end cannot precede scheduled start")
        return self


class MissionResponse(MissionBase):
    """Authoritative API response contract for mission entities."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    created_at: datetime = Field(..., description="Timestamp of mission creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")
