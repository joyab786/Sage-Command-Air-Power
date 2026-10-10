"""
SageCommand Air Power System (Aero) — Prognostics & Remaining Useful Life (RUL) Models.
Defines typed Pydantic v2 schemas for health history snapshots, degradation trends,
Remaining Useful Life (RUL) predictions, uncertainty bounds, and maintenance forecasts.
"""

from datetime import datetime, timezone
import uuid
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator, model_validator, ConfigDict
from app.contracts.base import AeroBaseModel
from app.digital_twin.models import TwinSubsystemType


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class TrendDirection(str, Enum):
    """Directional trajectory of subsystem operational health over time."""

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DEGRADING = "DEGRADING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MaintenanceForecastPriority(str, Enum):
    """Decision-support operational urgency for prognostic maintenance actions."""

    MONITOR = "MONITOR"
    PLAN_MAINTENANCE = "PLAN_MAINTENANCE"
    INSPECT_SOON = "INSPECT_SOON"
    PRIORITY_INSPECTION = "PRIORITY_INSPECTION"
    GROUND_FOR_REVIEW = "GROUND_FOR_REVIEW"


class PredictionMethod(str, Enum):
    """Prognostic algorithm utilized to compute Remaining Useful Life."""

    TREND_LINEAR_EXTRAPOLATION = "TREND_LINEAR_EXTRAPOLATION"
    WEAR_ACCELERATION_MODEL = "WEAR_ACCELERATION_MODEL"
    COMPOSITE_CONSERVATIVE_BOUND = "COMPOSITE_CONSERVATIVE_BOUND"
    BASELINE_NOMINAL = "BASELINE_NOMINAL"
    INSUFFICIENT_HISTORY_FALLBACK = "INSUFFICIENT_HISTORY_FALLBACK"


class ComponentHealthSnapshot(AeroBaseModel):
    """
    Point-in-time health observation for an aircraft subsystem or component.
    Derived from digital twin state snapshots and telemetry evaluations.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    snapshot_id: str = Field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:12]}", description="Unique snapshot identifier")
    aircraft_id: str = Field(..., description="Target aircraft airframe identifier")
    subsystem: TwinSubsystemType = Field(..., description="Observed aircraft subsystem")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of observation")
    health_score: float = Field(..., ge=0.0, le=100.0, description="Health rating at observation time (0-100)")
    wear_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized cumulative wear index (0.0-1.0)")
    anomaly_count: int = Field(default=0, ge=0, description="Count of active anomalies at snapshot time")
    critical_anomaly_count: int = Field(default=0, ge=0, description="Count of critical anomalies")
    active_anomaly_severity: Optional[str] = Field(default=None, description="Maximum active anomaly severity")
    data_quality: str = Field(default="VALID", description="Data quality rating (VALID, DEGRADED, INVALID)")
    flight_hours: float = Field(default=0.0, ge=0.0, description="Cumulative flight hours at observation")
    flight_cycles: int = Field(default=0, ge=0, description="Cumulative flight cycles at observation")
    source: str = Field(default="DIGITAL_TWIN", description="Originating diagnostic source")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Observation data quality confidence")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class DegradationTrend(AeroBaseModel):
    """
    Estimated health degradation trajectory over chronological observations.
    Quantifies degradation rate, direction, regression slope, and statistical fit quality.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    trend_id: str = Field(default_factory=lambda: f"trd-{uuid.uuid4().hex[:12]}", description="Unique trend assessment ID")
    aircraft_id: str = Field(..., description="Target aircraft identifier")
    subsystem: TwinSubsystemType = Field(..., description="Evaluated aircraft subsystem")
    observation_start: Optional[datetime] = Field(default=None, description="Timestamp of earliest observation")
    observation_end: Optional[datetime] = Field(default=None, description="Timestamp of latest observation")
    sample_count: int = Field(default=0, ge=0, description="Number of chronological observations analyzed")
    current_health: float = Field(default=100.0, ge=0.0, le=100.0, description="Latest observed health score")
    initial_health: float = Field(default=100.0, ge=0.0, le=100.0, description="Initial observed health score in window")
    degradation_rate: float = Field(default=0.0, ge=0.0, description="Health points consumed per operating hour")
    slope: float = Field(default=0.0, description="OLS regression slope (delta health per hour)")
    trend_direction: TrendDirection = Field(default=TrendDirection.STABLE, description="Categorical trend direction")
    fit_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="R-squared coefficient of determination")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Assessment confidence score")
    data_quality: str = Field(default="VALID", description="Aggregate data quality of supporting observations")
    explanation: str = Field(..., description="Transparent explanation of the estimated degradation trend")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class RULPrediction(AeroBaseModel):
    """
    Explainable Remaining Useful Life (RUL) prediction with explicit uncertainty bounds.
    Estimates safe remaining flight hours and cycles before reaching critical demonstration threshold.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    prediction_id: str = Field(default_factory=lambda: f"rul-{uuid.uuid4().hex[:12]}", description="Unique prediction identifier")
    aircraft_id: str = Field(..., description="Target aircraft identifier")
    subsystem: TwinSubsystemType = Field(..., description="Evaluated aircraft subsystem")
    prediction_timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of prediction generation")
    estimated_rul_hours: float = Field(..., ge=0.0, description="Central estimate of remaining useful flight hours")
    estimated_rul_cycles: Optional[int] = Field(default=None, ge=0, description="Estimated remaining flight cycles")
    lower_bound_hours: float = Field(..., ge=0.0, description="Conservative lower bound with uncertainty margin")
    upper_bound_hours: float = Field(..., ge=0.0, description="Optimistic upper bound with uncertainty margin")
    health_score: float = Field(..., ge=0.0, le=100.0, description="Current health score informing prediction")
    wear_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Current wear index informing prediction")
    degradation_rate: float = Field(default=0.0, ge=0.0, description="Degradation rate in health points per hour")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence in RUL prediction accuracy")
    prediction_method: PredictionMethod = Field(default=PredictionMethod.TREND_LINEAR_EXTRAPOLATION)
    data_quality: str = Field(default="VALID", description="Data quality classification of telemetry inputs")
    limiting_factors: List[str] = Field(default_factory=list, description="Primary physical or statistical constraints")
    explanation: str = Field(..., description="Structured, transparent natural-language justification")
    recommended_action: str = Field(..., description="Advisory decision-support recommendation")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)

    @field_validator("lower_bound_hours")
    @classmethod
    def validate_bounds(cls, v: float, info: Any) -> float:
        if v < 0.0:
            raise ValueError(f"Lower bound hours cannot be negative, got {v}")
        return v

    @model_validator(mode="after")
    def validate_bounds_ordering(self) -> "RULPrediction":
        if self.lower_bound_hours > self.estimated_rul_hours or self.estimated_rul_hours > self.upper_bound_hours:
            raise ValueError(
                f"Bounds invariant violation: lower_bound ({self.lower_bound_hours}) <= "
                f"estimated_rul ({self.estimated_rul_hours}) <= upper_bound ({self.upper_bound_hours})"
            )
        return self


class MaintenanceForecast(AeroBaseModel):
    """
    Decision-support maintenance forecast derived from RUL horizon and anomaly severity.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    forecast_id: str = Field(default_factory=lambda: f"fcst-{uuid.uuid4().hex[:12]}", description="Unique forecast identifier")
    aircraft_id: str = Field(..., description="Target aircraft identifier")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of forecast generation")
    priority: MaintenanceForecastPriority = Field(..., description="Actionable priority category")
    urgency_horizon_hours: Optional[float] = Field(default=None, ge=0.0, description="Hours remaining before required action")
    affected_subsystems: List[TwinSubsystemType] = Field(default_factory=list, description="Subsystems driving the forecast")
    primary_driver: str = Field(..., description="Primary reason or limiting subsystem driving priority")
    recommended_window: str = Field(..., description="Recommended timeframe for servicing")
    action: str = Field(..., description="Recommended engineering or maintenance inspection action")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Analytical forecast confidence")
    explanation: str = Field(..., description="Explainable diagnostic rationale")
    related_anomalies: List[str] = Field(default_factory=list, description="IDs of contributing active anomalies")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class PrognosticAssessment(AeroBaseModel):
    """
    Composite prognostic intelligence assessment for an aircraft airframe.
    Unifies subsystem degradation trends, RUL predictions, and maintenance forecasts.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    assessment_id: str = Field(default_factory=lambda: f"prog-{uuid.uuid4().hex[:12]}", description="Unique prognostic assessment ID")
    aircraft_id: str = Field(..., description="Target aircraft airframe identifier")
    timestamp: datetime = Field(default_factory=utc_now, description="Assessment computation timestamp")
    primary_subsystem: TwinSubsystemType = Field(..., description="Subsystem with most critical prognostic condition")
    current_health_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Overall aircraft health score")
    current_wear_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall aircraft wear index")
    trend: DegradationTrend = Field(..., description="Degradation trend for primary subsystem")
    rul: RULPrediction = Field(..., description="RUL prediction for primary subsystem")
    forecast: MaintenanceForecast = Field(..., description="Consolidated maintenance forecast")
    subsystem_predictions: Dict[str, RULPrediction] = Field(default_factory=dict, description="Predictions across all subsystems")
    readiness_impact: str = Field(default="FMC_SUPPORTED", description="Estimated readiness consequence (FMC/PMC/NMC)")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Composite prognostic assessment confidence")
    explanation: str = Field(..., description="Comprehensive explainable synthesis")


class PrognosticRecordResponse(AeroBaseModel):
    """API response contract for historical persisted prognostic records."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    record_id: str
    aircraft_id: str
    timestamp: datetime
    subsystem: str
    health_score: float
    wear_index: float
    trend_direction: str
    degradation_rate: float
    slope: float
    estimated_rul_hours: float
    estimated_rul_cycles: Optional[int] = None
    lower_bound_hours: float
    upper_bound_hours: float
    confidence: float
    forecast_priority: str
    prediction_method: str
    limiting_factors: List[str] = Field(default_factory=list)
    explanation: str
    recommended_action: str
    created_at: datetime

