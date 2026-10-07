"""
SageCommand Air Power System (Aero) — Maintenance Domain Model.
Represents maintenance events, servicing actions, and predictive work orders
linked to airframe assets or specific subsystem components.
"""

from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator, model_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.domain.enums import MaintenanceStatus, MaintenancePriority, MaintenanceType


class MaintenanceEventBase(AeroBaseModel):
    """Core shared fields for maintenance event tracking."""

    maintenance_event_id: str = Field(..., min_length=1, max_length=64, description="Unique maintenance event identifier")
    aircraft_id: str = Field(..., min_length=1, max_length=64, description="Target aircraft identifier")
    component_id: Optional[str] = Field(default=None, max_length=64, description="Affected subsystem or LRU ID")
    maintenance_type: MaintenanceType = Field(default=MaintenanceType.SCHEDULED, description="Maintenance category")
    status: MaintenanceStatus = Field(default=MaintenanceStatus.OPEN, description="Workflow lifecycle state")
    priority: MaintenancePriority = Field(default=MaintenancePriority.MEDIUM, description="Operational urgency")
    detected_at: datetime = Field(..., description="Timestamp when maintenance need was recognized")
    scheduled_at: Optional[datetime] = Field(default=None, description="Planned service execution time")
    completed_at: Optional[datetime] = Field(default=None, description="Actual completion timestamp")
    description: str = Field(..., min_length=1, max_length=1000, description="Description of issue and required remediation")
    source: str = Field(default="MANUAL", max_length=64, description="Origin: MANUAL, PREDICTIVE_RUL, ANOMALY_DETECTOR")

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Description cannot be empty")
            return stripped
        return value

    @model_validator(mode="after")
    def validate_timestamps(self) -> "MaintenanceEventBase":
        if self.completed_at and self.detected_at:
            if self.completed_at < self.detected_at:
                raise ValueError("Completion timestamp cannot precede detection timestamp")
        return self


class MaintenanceEventCreate(MaintenanceEventBase):
    """Payload contract for registering a new maintenance event."""
    pass


class MaintenanceEventUpdate(AeroBaseModel):
    """Payload contract for progressing maintenance lifecycle state."""

    status: Optional[MaintenanceStatus] = None
    priority: Optional[MaintenancePriority] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=1000)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Description cannot be empty")
            return stripped
        return value


class MaintenanceEventResponse(MaintenanceEventBase):
    """Authoritative API response contract for maintenance events."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    created_at: datetime = Field(..., description="Timestamp of event creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")
