"""
SageCommand Air Power System (Aero) — Aircraft Readiness Domain Model.
Represents standardized military readiness assessments (FMC, PMC, NMC),
capturing contributing reasons, limiting subsystems, and evaluation confidence.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import Field, field_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.domain.enums import ReadinessStatus


class ReadinessAssessmentBase(AeroBaseModel):
    """Core shared fields for aircraft readiness assessments."""

    assessment_id: str = Field(..., min_length=1, max_length=64, description="Unique readiness assessment identifier")
    aircraft_id: str = Field(..., min_length=1, max_length=64, description="Target aircraft identifier")
    readiness_status: ReadinessStatus = Field(default=ReadinessStatus.FMC, description="Readiness capability classification")
    assessed_at: datetime = Field(..., description="Timestamp when readiness evaluation occurred")
    reasons: List[str] = Field(default_factory=list, description="Causal justification or degradation notes")
    limiting_components: List[str] = Field(default_factory=list, description="IDs of degraded or limiting subsystems")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Analytical assessment confidence score (0.0 to 1.0)")

    @field_validator("aircraft_id", "assessment_id", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Identifier cannot be empty")
            return stripped
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError("Confidence score must be bounded between 0.0 and 1.0")
        return round(value, 4)


class ReadinessAssessmentCreate(ReadinessAssessmentBase):
    """Payload contract for registering an evaluated readiness assessment."""
    pass


class ReadinessAssessmentResponse(ReadinessAssessmentBase):
    """Authoritative API response contract for readiness assessments."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    created_at: datetime = Field(..., description="Timestamp of assessment generation")
