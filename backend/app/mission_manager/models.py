"""
SageCommand Air Power System (Aero) — Mission Manager & ATO Models.
Defines strongly typed Pydantic v2 domain schemas for Air Tasking Orders (ATO),
proposed sorties, eligibility evidence, deterministic allocation proposals, and human review governance.
"""

from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator, model_validator, ConfigDict
from app.contracts.base import AeroBaseModel


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ATOValidationStatus(str, Enum):
    """Validation compliance status for parsed ATO documents."""

    VALID = "VALID"
    INVALID = "INVALID"
    WARNINGS = "WARNINGS"


class SortiePriority(str, Enum):
    """Operational urgency level of a planned sortie."""

    URGENT = "URGENT"
    HIGH = "HIGH"
    ROUTINE = "ROUTINE"
    LOW = "LOW"


class SortieStatus(str, Enum):
    """Assignment and planning state of a proposed sortie."""

    UNASSIGNED = "UNASSIGNED"
    ALLOCATED = "ALLOCATED"
    CONFLICTED = "CONFLICTED"
    CANCELLED = "CANCELLED"


class EligibilityStatus(str, Enum):
    """Defensible classification of aircraft eligibility for a sortie commitment."""

    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_REVIEW = "ELIGIBLE_WITH_REVIEW"
    INELIGIBLE = "INELIGIBLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AllocationApprovalStatus(str, Enum):
    """Governance review status of an algorithmic allocation proposal."""

    PROPOSED = "PROPOSED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ValidationFinding(AeroBaseModel):
    """Structured linting or validation issue within an ATO document."""

    severity: str = Field(..., description="ERROR | WARNING | INFO")
    code: str = Field(..., description="Machine-readable error rule code")
    message: str = Field(..., description="Human-readable explanation")
    field: Optional[str] = Field(default=None, description="Affected field path")
    sortie_id: Optional[str] = Field(default=None, description="Affected sortie identifier")


class ProposedSortie(AeroBaseModel):
    """
    Non-operational synthetic sortie requirement extracted from an ATO document.
    Specifies timing, required aircraft type, capabilities, and priority without combat or weapon parameters.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    sortie_id: str = Field(..., min_length=1, max_length=64, description="Unique sortie identifier within ATO")
    mission_category: str = Field(default="TRAINING", description="Synthetic mission category label")
    start_time: datetime = Field(..., description="Target sortie launch timestamp")
    end_time: datetime = Field(..., description="Target sortie recovery timestamp")
    required_aircraft_type: str = Field(..., min_length=1, description="Required airframe type (e.g., HAL Tejas Mk1A)")
    required_capabilities: List[str] = Field(default_factory=list, description="Required subsystem capability tags")
    min_aircraft_count: int = Field(default=1, ge=1, description="Minimum airframes required")
    priority: SortiePriority = Field(default=SortiePriority.ROUTINE, description="Sortie operational priority")
    estimated_duration_hours: Optional[float] = Field(default=None, ge=0.0, description="Estimated flight hours")
    status: SortieStatus = Field(default=SortieStatus.UNASSIGNED, description="Current allocation status")
    explanation: Optional[str] = Field(default=None, description="Operational planning justification")

    @model_validator(mode="after")
    def validate_duration_and_times(self) -> "ProposedSortie":
        if self.end_time <= self.start_time:
            raise ValueError(
                f"Sortie end_time ({self.end_time}) must be strictly after start_time ({self.start_time})"
            )
        duration = (self.end_time - self.start_time).total_seconds() / 3600.0
        if self.estimated_duration_hours is None:
            self.estimated_duration_hours = round(duration, 2)
        return self


class ATODocument(AeroBaseModel):
    """
    Structured synthetic Air Tasking Order (ATO) document model.
    Encapsulates planning cycle metadata, temporal window, and candidate proposed sorties.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    ato_id: str = Field(..., min_length=1, max_length=64, description="Unique synthetic ATO document ID")
    schema_version: str = Field(default="1.0.0", description="ATO document schema format version")
    issue_timestamp: datetime = Field(default_factory=utc_now, description="Document release timestamp")
    planning_window_start: datetime = Field(..., description="Earliest valid launch window boundary")
    planning_window_end: datetime = Field(..., description="Latest valid recovery window boundary")
    source: str = Field(default="SYNTHETIC_SIH_DEMO", description="Originating authority or simulation source")
    sorties: List[ProposedSortie] = Field(default_factory=list, description="Proposed flight sorties")
    validation_status: ATOValidationStatus = Field(default=ATOValidationStatus.VALID)
    validation_findings: List[ValidationFinding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_planning_window(self) -> "ATODocument":
        if self.planning_window_end <= self.planning_window_start:
            raise ValueError("Planning window end must be strictly after planning window start")
        return self


class ATOValidationResponse(AeroBaseModel):
    """API response contract returning validation results for an uploaded or inspected ATO."""

    ato_id: str
    is_valid: bool
    validation_status: ATOValidationStatus
    findings: List[ValidationFinding] = Field(default_factory=list)
    sortie_count: int = 0
    validated_at: datetime = Field(default_factory=utc_now)


class EligibilityEvidence(AeroBaseModel):
    """Structured diagnostic evidence supporting an aircraft eligibility determination."""

    aircraft_lifecycle_status: str
    aircraft_type: str
    readiness_status: Optional[str] = None
    readiness_confidence: Optional[float] = None
    health_score: Optional[float] = None
    wear_index: Optional[float] = None
    active_anomalies_count: int = 0
    critical_anomalies_count: int = 0
    high_anomalies_count: int = 0
    maintenance_conflicts: List[str] = Field(default_factory=list)
    rul_hours: Optional[float] = None
    rul_is_supported: bool = True
    rul_status: Optional[str] = None
    rul_confidence: Optional[float] = None
    forecast_priority: Optional[str] = None
    data_quality: str = "VALID"


class AircraftEligibilityReport(AeroBaseModel):
    """Explainable eligibility assessment for a specific aircraft airframe."""

    aircraft_id: str
    sortie_id: Optional[str] = None
    status: EligibilityStatus
    reasons: List[str] = Field(default_factory=list)
    evidence: EligibilityEvidence
    is_eligible: bool
    requires_human_review: bool
    assessed_at: datetime = Field(default_factory=utc_now)


class SortieAllocationProposal(AeroBaseModel):
    """
    Explainable algorithmic recommendation matching an airframe to a proposed sortie.
    Remains strictly advisory (PROPOSED or REQUIRES_REVIEW) until authorized by a human.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    proposal_id: str = Field(default_factory=lambda: f"prop-{uuid.uuid4().hex[:12]}")
    ato_id: str
    sortie_id: str
    proposed_aircraft_id: Optional[str] = None
    eligibility_status: Optional[EligibilityStatus] = None
    score: float = 0.0
    scoring_breakdown: Dict[str, float] = Field(default_factory=dict)
    evidence: Optional[EligibilityEvidence] = None
    conflicts: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    explanation: str
    status: AllocationApprovalStatus = Field(default=AllocationApprovalStatus.PROPOSED)
    proposed_at: datetime = Field(default_factory=utc_now)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_decision_reason: Optional[str] = None
    audit_event_id: Optional[str] = None


class ATOAllocationResult(AeroBaseModel):
    """Aggregated allocation response synthesizing all sortie recommendations for an ATO."""

    ato_id: str
    proposals: List[SortieAllocationProposal] = Field(default_factory=list)
    unfilled_sorties: List[str] = Field(default_factory=list)
    total_sorties: int = 0
    allocated_count: int = 0
    requires_review_count: int = 0
    unfilled_count: int = 0
    generated_at: datetime = Field(default_factory=utc_now)
    explanation: str


class AllocationReviewRequest(AeroBaseModel):
    """Human review decision request payload (approve or reject an allocation proposal)."""

    decision_reason: str = Field(..., min_length=3, description="Justification for human approval or rejection")
    approver_id: Optional[str] = Field(default=None, description="Operator or commander identifier")


class AllocationReviewResponse(AeroBaseModel):
    """Authoritative API response confirming approval or rejection state transition."""

    proposal_id: str
    status: AllocationApprovalStatus
    reviewed_by: str
    reviewed_at: datetime
    audit_event_id: Optional[str] = None
    message: str
