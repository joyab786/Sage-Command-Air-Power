"""
SageCommand Air Power System (Aero) — Unit Tests: Deterministic Allocation Engine.
Tests scoring formulas, priority sorting, stable tie-breaking, conflict tracking,
and strict non-overlapping aircraft commitment enforcement.
"""

from datetime import datetime, timedelta, timezone
from typing import List
import pytest
from sqlalchemy.orm import Session

from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    PrognosticRecordModel,
    ReadinessAssessmentModel,
    utc_now,
)
from app.mission_manager.models import (
    AllocationApprovalStatus,
    EligibilityEvidence,
    EligibilityStatus,
    AircraftEligibilityReport,
    ProposedSortie,
    SortiePriority,
    SortieStatus,
)
from app.mission_manager.allocation import AllocationScorer, AllocationEngine


def _setup_fleet(db: Session) -> List[AircraftModel]:
    fleet = []
    for aid in ["AC-ALPHA-01", "AC-BRAVO-02", "AC-CHARLIE-03"]:
        ac = AircraftModel(
            aircraft_id=aid,
            tail_number=f"T-{aid}",
            aircraft_type="HAL Tejas Mk1A",
            status="ACTIVE",
            air_base="BAREILLY_AFS",
            squadron="1st Tigers",
            total_flight_hours=200.0,
            total_flight_cycles=100,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        fleet.append(ac)
        db.add(ac)
    db.commit()
    return fleet


def _attach_fmc_state(db: Session, aircraft_id: str, health: float = 95.0, rul: float = 80.0):
    readiness = ReadinessAssessmentModel(
        assessment_id=f"ASM-{aircraft_id}",
        aircraft_id=aircraft_id,
        readiness_status="FMC",
        assessed_at=utc_now(),
        confidence=0.95,
        reasons=[],
    )
    twin = AircraftTwinStateModel(
        state_id=f"TWIN-{aircraft_id}",
        aircraft_id=aircraft_id,
        health_score=health,
        wear_index=0.10,
        data_quality="VALID",
        timestamp=utc_now(),
    )
    prog = PrognosticRecordModel(
        record_id=f"PROG-{aircraft_id}",
        aircraft_id=aircraft_id,
        subsystem="PROPULSION",
        health_score=health,
        wear_index=0.10,
        trend_direction="STABLE",
        degradation_rate=0.0,
        slope=0.0,
        estimated_rul_hours=rul,
        lower_bound_hours=rul * 0.8,
        upper_bound_hours=rul * 1.2,
        prediction_method="EXPONENTIAL_DEGRADATION",
        is_supported=True,
        rul_status="ESTIMATED",
        confidence=0.90,
        forecast_priority="ROUTINE",
        explanation="Nominal operation.",
        recommended_action="Routine monitor.",
        timestamp=utc_now(),
    )
    db.add_all([readiness, twin, prog])
    db.commit()


def test_allocation_scorer_deterministic_formula():
    """Verifies documented scoring formula calculation."""
    report = AircraftEligibilityReport(
        aircraft_id="AC-TEST-01",
        status=EligibilityStatus.ELIGIBLE,
        reasons=["Clean"],
        evidence=EligibilityEvidence(
            aircraft_lifecycle_status="ACTIVE",
            aircraft_type="HAL Tejas Mk1A",
            readiness_status="FMC",
            readiness_confidence=0.95,
            health_score=90.0,
            wear_index=0.20,
            active_anomalies_count=0,
            critical_anomalies_count=0,
            high_anomalies_count=0,
            maintenance_conflicts=[],
            rul_hours=50.0,
            rul_is_supported=True,
            rul_status="ESTIMATED",
            rul_confidence=0.90,
            forecast_priority="ROUTINE",
            data_quality="VALID",
        ),
        is_eligible=True,
        requires_human_review=False,
        assessed_at=datetime.now(timezone.utc),
    )

    score, breakdown = AllocationScorer.compute_score(report)

    # Readiness: 30.0 (FMC)
    # Health: (90 / 100) * 30 = 27.0
    # Wear: (1.0 - 0.20) * 15 = 12.0
    # RUL: (50 / 100) * 15 = 7.5
    # Tier bonus: 10.0 (ELIGIBLE)
    # High anomaly penalty: 0.0
    # Total expected: 30.0 + 27.0 + 12.0 + 7.5 + 10.0 = 86.5
    assert breakdown["readiness_score"] == 30.0
    assert breakdown["health_score"] == 27.0
    assert breakdown["wear_score"] == 12.0
    assert breakdown["prognostic_rul_score"] == 7.5
    assert breakdown["tier_bonus"] == 10.0
    assert breakdown["anomaly_penalty"] == 0.0
    assert score == 86.5


def test_allocation_scorer_unsupported_rul_baseline():
    """Unsupported RUL receives conservative baseline score of 5.0."""
    report = AircraftEligibilityReport(
        aircraft_id="AC-TEST-02",
        status=EligibilityStatus.ELIGIBLE_WITH_REVIEW,
        reasons=["Unsupported RUL"],
        evidence=EligibilityEvidence(
            aircraft_lifecycle_status="ACTIVE",
            aircraft_type="HAL Tejas Mk1A",
            readiness_status="PMC",
            readiness_confidence=0.90,
            health_score=80.0,
            wear_index=0.10,
            active_anomalies_count=1,
            critical_anomalies_count=0,
            high_anomalies_count=1,
            maintenance_conflicts=[],
            rul_hours=100.0,
            rul_is_supported=False,
            rul_status="INSUFFICIENT_DATA",
            rul_confidence=0.50,
            forecast_priority="ROUTINE",
            data_quality="VALID",
        ),
        is_eligible=True,
        requires_human_review=True,
        assessed_at=datetime.now(timezone.utc),
    )

    score, breakdown = AllocationScorer.compute_score(report)
    assert breakdown["readiness_score"] == 15.0  # PMC
    assert breakdown["prognostic_rul_score"] == 5.0  # Conservative baseline
    assert breakdown["tier_bonus"] == 0.0  # ELIGIBLE_WITH_REVIEW gets no bonus
    assert breakdown["anomaly_penalty"] == 15.0  # 1 HIGH anomaly


def test_allocation_engine_prevents_overlapping_commitments(db_session: Session):
    """
    CRITICAL REQUIREMENT:
    Ensure an aircraft cannot be allocated to two overlapping sorties.
    When two sorties compete for the same time window, the higher priority sortie gets the airframe,
    and the second sortie gets the next best airframe or becomes unfilled.
    """
    _setup_fleet(db_session)
    # Only make ONE aircraft eligible: AC-ALPHA-01
    _attach_fmc_state(db_session, "AC-ALPHA-01", health=98.0, rul=90.0)

    t0 = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    sorties = [
        ProposedSortie(
            sortie_id="SRT-OVERLAP-01",
            mission_category="COMBAT_AIR_PATROL",
            start_time=t0,
            end_time=t0 + timedelta(hours=3),
            required_aircraft_type="HAL Tejas Mk1A",
            priority=SortiePriority.URGENT,
        ),
        ProposedSortie(
            sortie_id="SRT-OVERLAP-02",
            mission_category="TRAINING",
            start_time=t0 + timedelta(hours=1),  # Overlaps by 2 hours!
            end_time=t0 + timedelta(hours=4),
            required_aircraft_type="HAL Tejas Mk1A",
            priority=SortiePriority.ROUTINE,
        ),
    ]

    result = AllocationEngine.allocate_sorties(db_session, ato_id="ATO-TEST-OVERLAP", sorties=sorties)

    prop1 = next(p for p in result.proposals if p.sortie_id == "SRT-OVERLAP-01")
    prop2 = next(p for p in result.proposals if p.sortie_id == "SRT-OVERLAP-02")

    # URGENT sortie gets AC-ALPHA-01
    assert prop1.proposed_aircraft_id == "AC-ALPHA-01"
    assert prop1.status == AllocationApprovalStatus.PROPOSED

    # ROUTINE sortie cannot get AC-ALPHA-01 because of overlap, and other airframes lack readiness
    assert prop2.proposed_aircraft_id is None
    assert prop2.status == AllocationApprovalStatus.REQUIRES_REVIEW
    assert "SRT-OVERLAP-02" in result.unfilled_sorties
    assert any("already allocated to overlapping sortie 'SRT-OVERLAP-01'" in c for c in prop2.conflicts)


def test_allocation_engine_multi_aircraft_distribution(db_session: Session):
    """When multiple aircraft are available, overlapping sorties are distributed across distinct airframes."""
    _setup_fleet(db_session)
    _attach_fmc_state(db_session, "AC-ALPHA-01", health=99.0, rul=90.0)
    _attach_fmc_state(db_session, "AC-BRAVO-02", health=95.0, rul=80.0)

    t0 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    sorties = [
        ProposedSortie(
            sortie_id="SRT-CONCURRENT-01",
            mission_category="RECONNAISSANCE",
            start_time=t0,
            end_time=t0 + timedelta(hours=2),
            required_aircraft_type="HAL Tejas Mk1A",
            priority=SortiePriority.HIGH,
        ),
        ProposedSortie(
            sortie_id="SRT-CONCURRENT-02",
            mission_category="TRAINING",
            start_time=t0,
            end_time=t0 + timedelta(hours=2),
            required_aircraft_type="HAL Tejas Mk1A",
            priority=SortiePriority.ROUTINE,
        ),
    ]

    result = AllocationEngine.allocate_sorties(db_session, ato_id="ATO-TEST-MULTI", sorties=sorties)

    assigned_airframes = [p.proposed_aircraft_id for p in result.proposals]
    assert len(assigned_airframes) == 2
    # Distinct airframes assigned
    assert len(set(assigned_airframes)) == 2
    assert "AC-ALPHA-01" in assigned_airframes
    assert "AC-BRAVO-02" in assigned_airframes
    assert result.unfilled_count == 0


def test_allocation_engine_stable_tie_breaking(db_session: Session):
    """Stable tie breaking: identical score and health breaks ties deterministically by aircraft_id ascending."""
    _setup_fleet(db_session)
    # Both identical health and rul
    _attach_fmc_state(db_session, "AC-BRAVO-02", health=95.0, rul=80.0)
    _attach_fmc_state(db_session, "AC-ALPHA-01", health=95.0, rul=80.0)

    t0 = datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc)
    sortie = ProposedSortie(
        sortie_id="SRT-TIE-01",
        mission_category="TRAINING",
        start_time=t0,
        end_time=t0 + timedelta(hours=2),
        required_aircraft_type="HAL Tejas Mk1A",
        priority=SortiePriority.ROUTINE,
    )

    result = AllocationEngine.allocate_sorties(db_session, ato_id="ATO-TEST-TIE", sorties=[sortie])
    # Tie broken lexicographically: AC-ALPHA-01 before AC-BRAVO-02
    assert result.proposals[0].proposed_aircraft_id == "AC-ALPHA-01"
    assert "AC-BRAVO-02" in result.proposals[0].alternatives
