"""
SageCommand Air Power System (Aero) — Intelligence & Anomaly Detection Models.
Defines typed schemas for anomalies, severity ratings, lifecycle states,
subsystem diagnoses, root-cause evidence, and maintenance recommendations.
"""

from datetime import datetime, timezone
import uuid
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import Field, field_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.digital_twin.models import TwinSubsystemType


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AnomalySeverity(str, Enum):
    """Urgency and operational severity level of an anomaly."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyStatus(str, Enum):
    """Lifecycle progression state of an active anomaly."""

    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AnomalyType(str, Enum):
    """Controlled categorization of operational aerospace anomalies."""

    THERMAL_ANOMALY = "THERMAL_ANOMALY"
    VIBRATION_ANOMALY = "VIBRATION_ANOMALY"
    PRESSURE_ANOMALY = "PRESSURE_ANOMALY"
    G_LOAD_ANOMALY = "G_LOAD_ANOMALY"
    FUEL_FLOW_ANOMALY = "FUEL_FLOW_ANOMALY"
    CONTROL_SURFACE_ANOMALY = "CONTROL_SURFACE_ANOMALY"
    TELEMETRY_QUALITY_ANOMALY = "TELEMETRY_QUALITY_ANOMALY"
    FLIGHT_ENVELOPE_ANOMALY = "FLIGHT_ENVELOPE_ANOMALY"
    MULTI_SIGNAL_ANOMALY = "MULTI_SIGNAL_ANOMALY"


class RecommendationPriority(str, Enum):
    """Decision-support operational urgency for maintenance actions."""

    MONITOR = "MONITOR"
    INSPECT = "INSPECT"
    SCHEDULE_MAINTENANCE = "SCHEDULE_MAINTENANCE"
    GROUND_FOR_REVIEW = "GROUND_FOR_REVIEW"


class Anomaly(AeroBaseModel):
    """
    Structured record of an observed physical or data anomaly.
    Encapsulates detection evidence, affected subsystem, and confidence.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    anomaly_id: str = Field(default_factory=lambda: f"anom-{uuid.uuid4().hex[:12]}", description="Unique anomaly instance identifier")
    aircraft_id: str = Field(..., description="Host aircraft airframe identifier")
    flight_id: Optional[str] = Field(default=None, description="Active flight / sortie ID")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of telemetry observation")
    subsystem: TwinSubsystemType = Field(..., description="Affected conceptual subsystem")
    anomaly_type: AnomalyType = Field(..., description="Classification category")
    severity: AnomalySeverity = Field(..., description="Operational severity rating")
    status: AnomalyStatus = Field(default=AnomalyStatus.NEW, description="Lifecycle status")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Statistical / heuristic confidence (0.0 to 1.0)")
    detector: str = Field(default="THRESHOLD_RULE_DETECTOR", description="Name of the detecting algorithm")
    signal: str = Field(..., description="Primary telemetry signal or channel evaluated")
    observed_value: Optional[float] = Field(default=None, description="Observed parameter value")
    expected_range: Optional[str] = Field(default=None, description="Nominal demonstration baseline range")
    deviation: Optional[float] = Field(default=0.0, description="Numerical delta or z-score deviation")
    description: str = Field(..., description="Clear human-readable diagnostic description")
    evidence: Union[Dict[str, Any], List[Any]] = Field(default_factory=list, description="Structured supporting metrics and diagnostic context")
    occurrence_count: int = Field(default=1, ge=1, description="Number of consecutive observations confirming anomaly")
    first_detected_at: datetime = Field(default_factory=utc_now)
    last_detected_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = Field(default=None)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class Diagnosis(AeroBaseModel):
    """
    Subsystem-level diagnostic synthesis combining anomalies, digital twin state,
    and multi-signal evidence to explain probable cause.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    diagnosis_id: str = Field(default_factory=lambda: f"diag-{uuid.uuid4().hex[:12]}", description="Unique diagnosis evaluation ID")
    aircraft_id: str = Field(..., description="Target aircraft identifier")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of diagnostic generation")
    primary_subsystem: TwinSubsystemType = Field(..., description="Subsystem primarily affected")
    probable_causes: List[str] = Field(default_factory=list, description="Cautious, probable engineering causes identified")
    supporting_anomalies: List[str] = Field(default_factory=list, description="IDs of anomalies supporting this diagnosis")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Diagnostic synthesis confidence")
    explanation: str = Field(default="", description="Detailed, explainable reasoning narrative")
    signals_involved: List[str] = Field(default_factory=list, description="All contributing telemetry signals")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class MaintenanceRecommendation(AeroBaseModel):
    """
    Actionable, decision-support maintenance recommendation derived from
    diagnostic evidence and current aircraft health.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    recommendation_id: str = Field(default_factory=lambda: f"mrec-{uuid.uuid4().hex[:12]}", description="Unique recommendation identifier")
    aircraft_id: str = Field(..., description="Target aircraft identifier")
    priority: RecommendationPriority = Field(..., description="Advisory urgency level")
    action: str = Field(..., description="Recommended engineering inspection or servicing action")
    reason: str = Field(..., description="Explainable justification for recommendation")
    related_anomalies: List[str] = Field(default_factory=list, description="Associated anomaly IDs")
    affected_subsystem: TwinSubsystemType = Field(..., description="Primary subsystem requiring attention")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Recommendation confidence")
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)
