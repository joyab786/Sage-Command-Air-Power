"""
SageCommand Air Power System (Aero) — Air Tasking Order (ATO) & Allocation API Routes.
Exposes endpoints for ATO schema validation, synthetic ingestion, deterministic allocation proposals,
and human review governance (approve/reject) with cryptographic audit logging.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status, Header
from sqlalchemy.orm import Session

from app.contracts.base import ApiResponse
from app.contracts.common import ActorIdentity, ActorType
from app.db.database import get_db
from app.mission_manager.models import (
    ATODocument,
    ATOValidationResponse,
    SortieAllocationProposal,
    ATOAllocationResult,
    AllocationReviewRequest,
    AllocationReviewResponse,
)
from app.mission_manager.service import default_mission_manager_service

ato_router = APIRouter(prefix="/ato", tags=["Air Tasking Orders & Sorties"])
proposals_router = APIRouter(prefix="/allocation-proposals", tags=["Allocation Governance"])


def get_current_actor(
    x_actor_id: Optional[str] = Header(default=None, alias="X-Actor-ID"),
    x_actor_role: Optional[str] = Header(default=None, alias="X-Actor-Role"),
) -> ActorIdentity:
    """Extracts or defaults caller identity from request headers for governance audit."""
    actor_id = x_actor_id or "FLIGHT_LEAD_01"
    role = x_actor_role or "flight_lead"
    return ActorIdentity(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        roles=[role],
    )


# -----------------------------------------------------------------------------
# ATO Validation & Ingestion Endpoints
# -----------------------------------------------------------------------------

@ato_router.post(
    "/validate",
    response_model=ApiResponse[ATOValidationResponse],
    summary="Validate ATO Document Schema",
    description="Validates a synthetic ATO JSON payload against structural schema, temporal bounds, and safety constraints.",
)
def validate_ato_document(
    payload: Dict[str, Any],
) -> ApiResponse[ATOValidationResponse]:
    val_resp = default_mission_manager_service.validate_ato(payload)
    msg = "ATO document schema is valid" if val_resp.is_valid else "ATO document failed validation rules"
    return ApiResponse[ATOValidationResponse](
        data=val_resp,
        message=msg,
        success=val_resp.is_valid,
    )


@ato_router.post(
    "/import-demo",
    response_model=ApiResponse[ATODocument],
    status_code=status.HTTP_201_CREATED,
    summary="Import Synthetic Demonstration ATO",
    description="Imports a standard or custom synthetic ATO document into persistent storage for allocation planning.",
)
def import_demo_ato(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: ActorIdentity = Depends(get_current_actor),
) -> ApiResponse[ATODocument]:
    doc = default_mission_manager_service.import_ato(db, payload=payload, actor=actor)
    return ApiResponse[ATODocument](
        data=doc,
        message=f"ATO document '{doc.ato_id}' with {len(doc.sorties)} proposed sorties imported successfully",
    )


@ato_router.get(
    "/{ato_id}",
    response_model=ApiResponse[ATODocument],
    summary="Get ATO Document",
    description="Retrieves a persisted synthetic ATO document and its proposed sorties by identifier.",
)
def get_ato_document(
    ato_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[ATODocument]:
    doc = default_mission_manager_service.get_ato(db, ato_id)
    return ApiResponse[ATODocument](
        data=doc,
        message=f"ATO document '{ato_id}' found",
    )


# -----------------------------------------------------------------------------
# Allocation Proposals Endpoints
# -----------------------------------------------------------------------------

@ato_router.post(
    "/{ato_id}/allocation-proposals",
    response_model=ApiResponse[ATOAllocationResult],
    summary="Generate Sortie Allocation Proposals",
    description="Computes deterministic aircraft allocation recommendations for all proposed sorties in the ATO.",
)
def generate_allocation_proposals(
    ato_id: str,
    db: Session = Depends(get_db),
    actor: ActorIdentity = Depends(get_current_actor),
) -> ApiResponse[ATOAllocationResult]:
    result = default_mission_manager_service.generate_allocation_proposals(
        db, ato_id=ato_id, persist=True, actor=actor
    )
    return ApiResponse[ATOAllocationResult](
        data=result,
        message=result.explanation,
    )


@ato_router.get(
    "/{ato_id}/allocation-proposals",
    response_model=ApiResponse[List[SortieAllocationProposal]],
    summary="List Allocation Proposals for ATO",
    description="Retrieves all stored aircraft allocation proposals and approval statuses for an ATO.",
)
def list_allocation_proposals(
    ato_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[List[SortieAllocationProposal]]:
    proposals = default_mission_manager_service.get_allocation_proposals(db, ato_id=ato_id)
    return ApiResponse[List[SortieAllocationProposal]](
        data=proposals,
        message=f"Retrieved {len(proposals)} allocation proposals for ATO '{ato_id}'",
    )


# -----------------------------------------------------------------------------
# Human Governance: Approve / Reject Allocation Proposals
# -----------------------------------------------------------------------------

@proposals_router.post(
    "/{proposal_id}/approve",
    response_model=ApiResponse[AllocationReviewResponse],
    summary="Approve Allocation Proposal (Human-in-the-Loop)",
    description="Authorizes an aircraft allocation proposal through operational command review. Cryptographically audited.",
)
def approve_allocation_proposal(
    proposal_id: str,
    request: AllocationReviewRequest,
    db: Session = Depends(get_db),
    actor: ActorIdentity = Depends(get_current_actor),
) -> ApiResponse[AllocationReviewResponse]:
    effective_approver = ActorIdentity(
        actor_id=request.approver_id or actor.actor_id,
        actor_type=ActorType.USER,
        roles=actor.roles,
    )
    review_resp = default_mission_manager_service.approve_proposal(
        db,
        proposal_id=proposal_id,
        approver=effective_approver,
        decision_reason=request.decision_reason,
    )
    return ApiResponse[AllocationReviewResponse](
        data=review_resp,
        message=review_resp.message,
    )


@proposals_router.post(
    "/{proposal_id}/reject",
    response_model=ApiResponse[AllocationReviewResponse],
    summary="Reject Allocation Proposal (Human-in-the-Loop)",
    description="Rejects an aircraft allocation proposal with explanation. Cryptographically audited.",
)
def reject_allocation_proposal(
    proposal_id: str,
    request: AllocationReviewRequest,
    db: Session = Depends(get_db),
    actor: ActorIdentity = Depends(get_current_actor),
) -> ApiResponse[AllocationReviewResponse]:
    effective_reviewer = ActorIdentity(
        actor_id=request.approver_id or actor.actor_id,
        actor_type=ActorType.USER,
        roles=actor.roles,
    )
    review_resp = default_mission_manager_service.reject_proposal(
        db,
        proposal_id=proposal_id,
        reviewer=effective_reviewer,
        decision_reason=request.decision_reason,
    )
    return ApiResponse[AllocationReviewResponse](
        data=review_resp,
        message=review_resp.message,
    )
