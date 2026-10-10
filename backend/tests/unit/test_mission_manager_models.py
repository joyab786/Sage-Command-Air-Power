"""
Unit tests for SageCommand Aero Mission Manager — Domain Models.
Validates Pydantic v2 schemas, temporal ordering, priority weights, and enum values.
"""

from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.mission_manager.models import (
    ATODocument,
    ProposedSortie,
    SortiePriority,
    SortieStatus,
    ATOValidationStatus,
    EligibilityStatus,
    AllocationApprovalStatus,
    SortieAllocationProposal,
    ValidationFinding,
)


def test_mission_manager_enums():
    assert ATOValidationStatus.VALID == "VALID"
    assert ATOValidationStatus.INVALID == "INVALID"
    assert ATOValidationStatus.WARNINGS == "WARNINGS"

    assert SortiePriority.URGENT == "URGENT"
    assert SortiePriority.HIGH == "HIGH"
    assert SortiePriority.ROUTINE == "ROUTINE"
    assert SortiePriority.LOW == "LOW"

    assert SortieStatus.UNASSIGNED == "UNASSIGNED"
    assert SortieStatus.ALLOCATED == "ALLOCATED"
    assert SortieStatus.CONFLICTED == "CONFLICTED"

    assert EligibilityStatus.ELIGIBLE == "ELIGIBLE"
    assert EligibilityStatus.ELIGIBLE_WITH_REVIEW == "ELIGIBLE_WITH_REVIEW"
    assert EligibilityStatus.INELIGIBLE == "INELIGIBLE"
    assert EligibilityStatus.INSUFFICIENT_EVIDENCE == "INSUFFICIENT_EVIDENCE"

    assert AllocationApprovalStatus.PROPOSED == "PROPOSED"
    assert AllocationApprovalStatus.REQUIRES_REVIEW == "REQUIRES_REVIEW"
    assert AllocationApprovalStatus.APPROVED == "APPROVED"
    assert AllocationApprovalStatus.REJECTED == "REJECTED"


def test_proposed_sortie_valid():
    t0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=2, minutes=30)
    sortie = ProposedSortie(
        sortie_id="SRT-001",
        mission_category="TRAINING",
        start_time=t0,
        end_time=t1,
        required_aircraft_type="HAL Tejas Mk1A",
        required_capabilities=["RADAR", "NAV"],
        priority=SortiePriority.HIGH,
    )
    assert sortie.sortie_id == "SRT-001"
    assert sortie.estimated_duration_hours == 2.5
    assert sortie.min_aircraft_count == 1
    assert sortie.status == SortieStatus.UNASSIGNED


def test_proposed_sortie_invalid_times():
    t0 = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_early = t0 - timedelta(hours=1)
    with pytest.raises(ValidationError):
        ProposedSortie(
            sortie_id="SRT-INVALID",
            start_time=t0,
            end_time=t_early,
            required_aircraft_type="HAL Tejas Mk1A",
        )


def test_ato_document_valid():
    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t_end = t0 + timedelta(hours=24)
    sortie = ProposedSortie(
        sortie_id="SRT-01",
        start_time=t0 + timedelta(hours=2),
        end_time=t0 + timedelta(hours=4),
        required_aircraft_type="HAL Tejas Mk1A",
    )
    ato = ATODocument(
        ato_id="ATO-TEST-01",
        planning_window_start=t0,
        planning_window_end=t_end,
        sorties=[sortie],
    )
    assert ato.ato_id == "ATO-TEST-01"
    assert ato.schema_version == "1.0.0"
    assert len(ato.sorties) == 1
    assert ato.validation_status == ATOValidationStatus.VALID


def test_ato_document_invalid_planning_window():
    t0 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ATODocument(
            ato_id="ATO-BAD-WIN",
            planning_window_start=t0,
            planning_window_end=t0 - timedelta(hours=2),
        )


def test_sortie_allocation_proposal_model():
    prop = SortieAllocationProposal(
        proposal_id="prop-001",
        ato_id="ATO-01",
        sortie_id="SRT-01",
        proposed_aircraft_id="AERO-01",
        eligibility_status=EligibilityStatus.ELIGIBLE,
        score=85.5,
        conflicts=[],
        alternatives=["AERO-02"],
        explanation="Best candidate with high health and FMC readiness.",
        status=AllocationApprovalStatus.PROPOSED,
    )
    assert prop.proposal_id == "prop-001"
    assert prop.proposed_aircraft_id == "AERO-01"
    assert prop.status == AllocationApprovalStatus.PROPOSED
    assert prop.reviewed_by is None
