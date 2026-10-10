"""
SageCommand Air Power System (Aero) — Mission Manager Service.
Orchestrates synthetic ATO document ingestion, validation, aircraft eligibility evaluation,
deterministic allocation proposals, and human review governance with cryptographic audit logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import Session

from app.contracts.common import ActorIdentity, ActorType
from app.core.exceptions import NotFoundError, ConflictError, ValidationError as AeroValidationError
from app.core.logging import get_logger
from app.db.models import (
    ATODocumentModel,
    ProposedSortieModel,
    SortieAllocationProposalModel,
    utc_now,
)
from app.mission_manager.models import (
    ATODocument,
    ProposedSortie,
    SortiePriority,
    SortieStatus,
    ATOValidationStatus,
    ATOValidationResponse,
    AircraftEligibilityReport,
    SortieAllocationProposal,
    ATOAllocationResult,
    AllocationApprovalStatus,
    AllocationReviewResponse,
)
from app.mission_manager.ato_parser import ATOParser
from app.mission_manager.eligibility import AircraftEligibilityEvaluator
from app.mission_manager.allocation import AllocationEngine
from app.services.audit_ledger import default_audit_ledger

logger = get_logger(__name__)


def create_demo_ato_dict(ato_id: str = "ATO-DEMO-20261010-01") -> Dict[str, Any]:
    """Generates a standard synthetic ATO dictionary for demonstration and testing."""
    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    return {
        "ato_id": ato_id,
        "schema_version": "1.0.0",
        "issue_timestamp": t0.isoformat(),
        "planning_window_start": t0.isoformat(),
        "planning_window_end": (t0 + timedelta(hours=24)).isoformat(),
        "source": "SYNTHETIC_SIH_DEMO",
        "sorties": [
            {
                "sortie_id": f"{ato_id}-SRT-01",
                "mission_category": "COMBAT_AIR_PATROL",
                "start_time": (t0 + timedelta(hours=2)).isoformat(),
                "end_time": (t0 + timedelta(hours=5)).isoformat(),
                "required_aircraft_type": "HAL Tejas Mk1A",
                "required_capabilities": ["BVR_RADAR", "AIR_TO_AIR"],
                "min_aircraft_count": 1,
                "priority": "URGENT",
                "estimated_duration_hours": 3.0,
                "status": "UNASSIGNED",
                "explanation": "High-priority air defense patrol requirement.",
            },
            {
                "sortie_id": f"{ato_id}-SRT-02",
                "mission_category": "RECONNAISSANCE",
                "start_time": (t0 + timedelta(hours=4)).isoformat(),
                "end_time": (t0 + timedelta(hours=7)).isoformat(),
                "required_aircraft_type": "HAL Tejas Mk1A",
                "required_capabilities": ["RECON_SENSOR"],
                "min_aircraft_count": 1,
                "priority": "HIGH",
                "estimated_duration_hours": 3.0,
                "status": "UNASSIGNED",
                "explanation": "High-altitude intelligence surveillance sortie.",
            },
            {
                "sortie_id": f"{ato_id}-SRT-03",
                "mission_category": "TRAINING",
                "start_time": (t0 + timedelta(hours=8)).isoformat(),
                "end_time": (t0 + timedelta(hours=10)).isoformat(),
                "required_aircraft_type": "HAL Tejas Mk1A",
                "required_capabilities": ["TRAINING_POD"],
                "min_aircraft_count": 1,
                "priority": "ROUTINE",
                "estimated_duration_hours": 2.0,
                "status": "UNASSIGNED",
                "explanation": "Routine instrument training flight.",
            },
            {
                "sortie_id": f"{ato_id}-SRT-04",
                "mission_category": "FERRY",
                "start_time": (t0 + timedelta(hours=12)).isoformat(),
                "end_time": (t0 + timedelta(hours=15)).isoformat(),
                "required_aircraft_type": "HAL Tejas Mk1A",
                "required_capabilities": ["EXTERNAL_TANKS"],
                "min_aircraft_count": 1,
                "priority": "LOW",
                "estimated_duration_hours": 3.0,
                "status": "UNASSIGNED",
                "explanation": "Inter-base relocation and ferry sortie.",
            },
        ],
    }


class MissionManagerService:
    """
    Authoritative Mission Manager & ATO Decision-Support Service.
    """

    def validate_ato(self, payload: Dict[str, Any]) -> ATOValidationResponse:
        """Validates untrusted ATO payload against schema and security rules."""
        _, val_resp = ATOParser.parse_dict(payload)
        return val_resp

    def import_ato(
        self,
        db: Session,
        payload: Optional[Dict[str, Any]] = None,
        actor: Optional[ActorIdentity] = None,
    ) -> ATODocument:
        """
        Parses, validates, and persists a synthetic ATO document and its proposed sorties.
        """
        data = payload or create_demo_ato_dict()
        document, val_resp = ATOParser.parse_dict(data)

        if not val_resp.is_valid or document is None:
            finding_msgs = [f"[{f.severity}] {f.code}: {f.message}" for f in val_resp.findings]
            raise AeroValidationError(
                f"ATO Document '{val_resp.ato_id}' failed validation: {'; '.join(finding_msgs[:3])}",
                details={"findings": [f.model_dump() for f in val_resp.findings]},
            )

        # 1. Upsert ATO document record
        existing = db.execute(
            select(ATODocumentModel).where(ATODocumentModel.ato_id == document.ato_id)
        ).scalar_one_or_none()

        if existing:
            # Cleanly replace child sorties and proposals
            db.execute(delete(SortieAllocationProposalModel).where(SortieAllocationProposalModel.ato_id == document.ato_id))
            db.execute(delete(ProposedSortieModel).where(ProposedSortieModel.ato_id == document.ato_id))
            db.delete(existing)
            db.flush()

        doc_model = ATODocumentModel(
            ato_id=document.ato_id,
            schema_version=document.schema_version,
            issue_timestamp=document.issue_timestamp,
            planning_window_start=document.planning_window_start,
            planning_window_end=document.planning_window_end,
            source=document.source,
            validation_status=document.validation_status.value,
            validation_findings=[f.model_dump() for f in document.validation_findings],
            raw_document=data,
            created_at=utc_now(),
        )
        db.add(doc_model)

        # 2. Add child proposed sorties
        for s in document.sorties:
            sortie_model = ProposedSortieModel(
                sortie_id=s.sortie_id,
                ato_id=document.ato_id,
                mission_category=s.mission_category,
                start_time=s.start_time,
                end_time=s.end_time,
                required_aircraft_type=s.required_aircraft_type,
                required_capabilities=s.required_capabilities,
                min_aircraft_count=s.min_aircraft_count,
                priority=s.priority.value,
                estimated_duration_hours=s.estimated_duration_hours,
                status=s.status.value,
                explanation=s.explanation,
                created_at=utc_now(),
            )
            db.add(sortie_model)

        db.commit()

        # 3. Cryptographic audit logging
        acting_actor = actor or ActorIdentity(
            actor_id="SYS_MISSION_MANAGER",
            actor_type=ActorType.SYSTEM,
            roles=["operator"],
        )
        default_audit_ledger.append_event(
            event_type="ATO_IMPORTED",
            actor=acting_actor,
            action="IMPORT_ATO_DOCUMENT",
            result="SUCCESS",
            resource_type="ATO_DOCUMENT",
            resource_id=document.ato_id,
            payload={"ato_id": document.ato_id, "sortie_count": len(document.sorties)},
        )

        return document

    def get_ato(self, db: Session, ato_id: str) -> ATODocument:
        """Retrieves persisted ATO document and its child sorties."""
        doc_model = db.execute(
            select(ATODocumentModel).where(ATODocumentModel.ato_id == ato_id)
        ).scalar_one_or_none()

        if not doc_model:
            raise NotFoundError(
                f"ATO document '{ato_id}' not found",
                details={"ato_id": ato_id},
            )

        sorties: List[ProposedSortie] = []
        for sm in doc_model.sorties:
            sorties.append(
                ProposedSortie(
                    sortie_id=sm.sortie_id,
                    mission_category=sm.mission_category,
                    start_time=sm.start_time,
                    end_time=sm.end_time,
                    required_aircraft_type=sm.required_aircraft_type,
                    required_capabilities=sm.required_capabilities or [],
                    min_aircraft_count=sm.min_aircraft_count,
                    priority=SortiePriority(sm.priority),
                    estimated_duration_hours=sm.estimated_duration_hours,
                    status=SortieStatus(sm.status),
                    explanation=sm.explanation,
                )
            )

        return ATODocument(
            ato_id=doc_model.ato_id,
            schema_version=doc_model.schema_version,
            issue_timestamp=doc_model.issue_timestamp,
            planning_window_start=doc_model.planning_window_start,
            planning_window_end=doc_model.planning_window_end,
            source=doc_model.source,
            sorties=sorties,
            validation_status=ATOValidationStatus(doc_model.validation_status),
            validation_findings=doc_model.validation_findings or [],
            created_at=doc_model.created_at,
        )

    def evaluate_aircraft_eligibility(
        self,
        db: Session,
        aircraft_id: str,
        sortie_id: Optional[str] = None,
    ) -> AircraftEligibilityReport:
        """Evaluates aircraft airframe eligibility standalone or against a specific sortie requirement."""
        target_sortie: Optional[ProposedSortie] = None
        if sortie_id:
            sm = db.execute(
                select(ProposedSortieModel).where(ProposedSortieModel.sortie_id == sortie_id)
            ).scalar_one_or_none()
            if not sm:
                raise NotFoundError(
                    f"Sortie '{sortie_id}' not found for eligibility evaluation",
                    details={"sortie_id": sortie_id},
                )
            target_sortie = ProposedSortie(
                sortie_id=sm.sortie_id,
                mission_category=sm.mission_category,
                start_time=sm.start_time,
                end_time=sm.end_time,
                required_aircraft_type=sm.required_aircraft_type,
                required_capabilities=sm.required_capabilities or [],
                min_aircraft_count=sm.min_aircraft_count,
                priority=SortiePriority(sm.priority),
                estimated_duration_hours=sm.estimated_duration_hours,
                status=SortieStatus(sm.status),
                explanation=sm.explanation,
            )

        return AircraftEligibilityEvaluator.evaluate_aircraft(db, aircraft_id=aircraft_id, sortie=target_sortie)

    def generate_allocation_proposals(
        self,
        db: Session,
        ato_id: str,
        persist: bool = True,
        actor: Optional[ActorIdentity] = None,
    ) -> ATOAllocationResult:
        """
        Executes deterministic allocation for all sorties in an ATO and persists proposals.
        """
        ato_doc = self.get_ato(db, ato_id)
        result = AllocationEngine.allocate_sorties(db, ato_id=ato_id, sorties=ato_doc.sorties)

        if persist:
            # Clear previous proposals for this ATO
            db.execute(delete(SortieAllocationProposalModel).where(SortieAllocationProposalModel.ato_id == ato_id))
            db.flush()

            for prop in result.proposals:
                prop_model = SortieAllocationProposalModel(
                    proposal_id=prop.proposal_id,
                    ato_id=ato_id,
                    sortie_id=prop.sortie_id,
                    proposed_aircraft_id=prop.proposed_aircraft_id,
                    eligibility_status=prop.eligibility_status.value if prop.eligibility_status else None,
                    score=prop.score,
                    scoring_breakdown=prop.scoring_breakdown,
                    evidence=prop.evidence.model_dump() if prop.evidence else None,
                    conflicts=prop.conflicts,
                    alternatives=prop.alternatives,
                    explanation=prop.explanation,
                    status=prop.status.value,
                    proposed_at=prop.proposed_at,
                    created_at=utc_now(),
                )
                db.add(prop_model)
            db.commit()

            acting_actor = actor or ActorIdentity(
                actor_id="SYS_ALLOCATION_ENGINE",
                actor_type=ActorType.SYSTEM,
                roles=["planner"],
            )
            default_audit_ledger.append_event(
                event_type="ATO_ALLOCATIONS_GENERATED",
                actor=acting_actor,
                action="GENERATE_ALLOCATION_PROPOSALS",
                result="SUCCESS",
                resource_type="ATO_DOCUMENT",
                resource_id=ato_id,
                payload={
                    "ato_id": ato_id,
                    "proposals_count": len(result.proposals),
                    "allocated_count": result.allocated_count,
                    "unfilled_count": result.unfilled_count,
                },
            )

        return result

    def get_allocation_proposals(
        self,
        db: Session,
        ato_id: str,
    ) -> List[SortieAllocationProposal]:
        """Retrieves stored allocation proposals for an ATO document."""
        # Ensure ATO exists
        self.get_ato(db, ato_id)

        models = db.execute(
            select(SortieAllocationProposalModel)
            .where(SortieAllocationProposalModel.ato_id == ato_id)
            .order_by(SortieAllocationProposalModel.proposed_at.asc())
        ).scalars().all()

        if not models:
            # If not yet generated, compute and return
            res = self.generate_allocation_proposals(db, ato_id=ato_id, persist=True)
            return res.proposals

        results: List[SortieAllocationProposal] = []
        for m in models:
            results.append(
                SortieAllocationProposal(
                    proposal_id=m.proposal_id,
                    ato_id=m.ato_id,
                    sortie_id=m.sortie_id,
                    proposed_aircraft_id=m.proposed_aircraft_id,
                    eligibility_status=m.eligibility_status,
                    score=m.score,
                    scoring_breakdown=m.scoring_breakdown or {},
                    evidence=m.evidence,
                    conflicts=m.conflicts or [],
                    alternatives=m.alternatives or [],
                    explanation=m.explanation,
                    status=AllocationApprovalStatus(m.status),
                    proposed_at=m.proposed_at,
                    reviewed_by=m.reviewed_by,
                    reviewed_at=m.reviewed_at,
                    review_decision_reason=m.review_decision_reason,
                    audit_event_id=m.audit_event_id,
                )
            )
        return results

    def approve_proposal(
        self,
        db: Session,
        proposal_id: str,
        approver: ActorIdentity,
        decision_reason: str,
    ) -> AllocationReviewResponse:
        """
        Authorizes an aircraft allocation proposal through human-in-the-loop governance.
        Transitions state to APPROVED with cryptographic audit ledger recording. Idempotent.
        """
        prop_model = db.execute(
            select(SortieAllocationProposalModel).where(SortieAllocationProposalModel.proposal_id == proposal_id)
        ).scalar_one_or_none()

        if not prop_model:
            raise NotFoundError(
                f"Allocation proposal '{proposal_id}' not found",
                details={"proposal_id": proposal_id},
            )

        # Idempotency check: already approved by this actor
        if prop_model.status == AllocationApprovalStatus.APPROVED.value:
            return AllocationReviewResponse(
                proposal_id=proposal_id,
                status=AllocationApprovalStatus.APPROVED,
                reviewed_by=prop_model.reviewed_by or approver.actor_id,
                reviewed_at=prop_model.reviewed_at or datetime.now(timezone.utc),
                audit_event_id=prop_model.audit_event_id,
                message=f"Allocation proposal '{proposal_id}' is already APPROVED.",
            )

        if prop_model.status == AllocationApprovalStatus.REJECTED.value:
            raise ConflictError(
                f"Cannot approve proposal '{proposal_id}' which was previously REJECTED.",
                details={"proposal_id": proposal_id, "current_status": prop_model.status},
            )

        if not prop_model.proposed_aircraft_id:
            raise ConflictError(
                f"Cannot approve proposal '{proposal_id}' because no candidate aircraft was allocated (unfilled).",
                details={"proposal_id": proposal_id},
            )

        now = datetime.now(timezone.utc)
        prop_model.status = AllocationApprovalStatus.APPROVED.value
        prop_model.reviewed_by = approver.actor_id
        prop_model.reviewed_at = now
        prop_model.review_decision_reason = decision_reason

        # Append to cryptographic audit ledger
        audit_event = default_audit_ledger.append_event(
            event_type="MISSION_ALLOCATION_APPROVED",
            actor=approver,
            action="APPROVE_AIRCRAFT_ALLOCATION",
            result="APPROVED",
            resource_type="ALLOCATION_PROPOSAL",
            resource_id=proposal_id,
            payload={
                "proposal_id": proposal_id,
                "ato_id": prop_model.ato_id,
                "sortie_id": prop_model.sortie_id,
                "aircraft_id": prop_model.proposed_aircraft_id,
                "reason": decision_reason,
            },
        )
        prop_model.audit_event_id = audit_event.event_id
        db.commit()

        return AllocationReviewResponse(
            proposal_id=proposal_id,
            status=AllocationApprovalStatus.APPROVED,
            reviewed_by=approver.actor_id,
            reviewed_at=now,
            audit_event_id=audit_event.event_id,
            message=f"Allocation proposal '{proposal_id}' approved for airframe '{prop_model.proposed_aircraft_id}'.",
        )

    def reject_proposal(
        self,
        db: Session,
        proposal_id: str,
        reviewer: ActorIdentity,
        decision_reason: str,
    ) -> AllocationReviewResponse:
        """
        Rejects an allocation proposal through human-in-the-loop governance.
        Transitions state to REJECTED with cryptographic audit recording. Idempotent.
        """
        prop_model = db.execute(
            select(SortieAllocationProposalModel).where(SortieAllocationProposalModel.proposal_id == proposal_id)
        ).scalar_one_or_none()

        if not prop_model:
            raise NotFoundError(
                f"Allocation proposal '{proposal_id}' not found",
                details={"proposal_id": proposal_id},
            )

        # Idempotency check
        if prop_model.status == AllocationApprovalStatus.REJECTED.value:
            return AllocationReviewResponse(
                proposal_id=proposal_id,
                status=AllocationApprovalStatus.REJECTED,
                reviewed_by=prop_model.reviewed_by or reviewer.actor_id,
                reviewed_at=prop_model.reviewed_at or datetime.now(timezone.utc),
                audit_event_id=prop_model.audit_event_id,
                message=f"Allocation proposal '{proposal_id}' is already REJECTED.",
            )

        if prop_model.status == AllocationApprovalStatus.APPROVED.value:
            raise ConflictError(
                f"Cannot directly reject an already APPROVED allocation proposal '{proposal_id}' without prior revocation.",
                details={"proposal_id": proposal_id},
            )

        now = datetime.now(timezone.utc)
        prop_model.status = AllocationApprovalStatus.REJECTED.value
        prop_model.reviewed_by = reviewer.actor_id
        prop_model.reviewed_at = now
        prop_model.review_decision_reason = decision_reason

        audit_event = default_audit_ledger.append_event(
            event_type="MISSION_ALLOCATION_REJECTED",
            actor=reviewer,
            action="REJECT_AIRCRAFT_ALLOCATION",
            result="REJECTED",
            resource_type="ALLOCATION_PROPOSAL",
            resource_id=proposal_id,
            payload={
                "proposal_id": proposal_id,
                "ato_id": prop_model.ato_id,
                "sortie_id": prop_model.sortie_id,
                "aircraft_id": prop_model.proposed_aircraft_id,
                "reason": decision_reason,
            },
        )
        prop_model.audit_event_id = audit_event.event_id
        db.commit()

        return AllocationReviewResponse(
            proposal_id=proposal_id,
            status=AllocationApprovalStatus.REJECTED,
            reviewed_by=reviewer.actor_id,
            reviewed_at=now,
            audit_event_id=audit_event.event_id,
            message=f"Allocation proposal '{proposal_id}' rejected by {reviewer.actor_id}.",
        )


default_mission_manager_service = MissionManagerService()
