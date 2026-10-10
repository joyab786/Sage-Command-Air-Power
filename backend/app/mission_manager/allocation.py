"""
SageCommand Air Power System (Aero) — Deterministic Mission Allocation Engine.
Assigns synthetic aircraft to proposed sorties based on eligibility, maintenance clearance,
prognostic lifing, and schedule availability. Prevents overlapping assignments and guarantees explainability.
"""

from datetime import datetime, timezone
import uuid
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AircraftModel
from app.mission_manager.models import (
    ProposedSortie,
    SortiePriority,
    SortieAllocationProposal,
    ATOAllocationResult,
    AllocationApprovalStatus,
    EligibilityStatus,
    AircraftEligibilityReport,
)
from app.mission_manager.eligibility import AircraftEligibilityEvaluator


class AllocationScorer:
    """
    Computes a transparent, deterministic matching score for candidate aircraft.
    """

    @classmethod
    def compute_score(cls, report: AircraftEligibilityReport) -> Tuple[float, Dict[str, float]]:
        """
        Calculates composite score based on readiness, health, wear, prognostics, and anomalies.
        Higher score indicates stronger operational alignment.
        """
        ev = report.evidence
        breakdown: Dict[str, float] = {}

        # 1. Readiness component (max 30.0)
        if ev.readiness_status == "FMC":
            s_readiness = 30.0
        elif ev.readiness_status == "PMC":
            s_readiness = 15.0
        else:
            s_readiness = 0.0
        breakdown["readiness_score"] = s_readiness

        # 2. Health score component (max 30.0)
        h = ev.health_score if ev.health_score is not None else 100.0
        s_health = round((h / 100.0) * 30.0, 2)
        breakdown["health_score"] = s_health

        # 3. Wear index component (max 15.0)
        w = ev.wear_index if ev.wear_index is not None else 0.0
        s_wear = round(max(0.0, 1.0 - w) * 15.0, 2)
        breakdown["wear_score"] = s_wear

        # 4. Prognostic RUL component (max 15.0)
        if ev.rul_hours is not None and ev.rul_is_supported:
            s_rul = round(min(1.0, ev.rul_hours / 100.0) * 15.0, 2)
        else:
            # Unsupported or absent RUL: conservative baseline margin
            s_rul = 5.0
        breakdown["prognostic_rul_score"] = s_rul

        # 5. Eligibility tier bonus (max 10.0)
        if report.status == EligibilityStatus.ELIGIBLE:
            s_tier = 10.0
        else:
            s_tier = 0.0
        breakdown["tier_bonus"] = s_tier

        # 6. Anomaly penalties
        p_high = ev.high_anomalies_count * 15.0
        breakdown["anomaly_penalty"] = p_high

        total_score = round(max(0.0, s_readiness + s_health + s_wear + s_rul + s_tier - p_high), 2)
        return total_score, breakdown


class AllocationEngine:
    """
    Greedy bounded matching engine evaluating synthetic sorties against eligible airframes.
    Guarantees zero overlapping sortie commitments for any single airframe asset.
    """

    PRIORITY_WEIGHTS = {
        SortiePriority.URGENT: 4,
        SortiePriority.HIGH: 3,
        SortiePriority.ROUTINE: 2,
        SortiePriority.LOW: 1,
    }

    @classmethod
    def allocate_sorties(
        cls,
        db: Session,
        ato_id: str,
        sorties: List[ProposedSortie],
    ) -> ATOAllocationResult:
        """
        Executes deterministic allocation for all sorties in an ATO document.
        """
        # 1. Fetch candidate airframes from database
        all_aircraft = db.execute(select(AircraftModel).order_by(AircraftModel.aircraft_id.asc())).scalars().all()
        aircraft_ids = [a.aircraft_id for a in all_aircraft]

        # 2. Sort sorties deterministically: priority desc -> start_time asc -> sortie_id asc
        sorted_sorties = sorted(
            sorties,
            key=lambda s: (
                -cls.PRIORITY_WEIGHTS.get(s.priority, 1),
                s.start_time,
                s.sortie_id,
            ),
        )

        # 3. Schedule tracking map: aircraft_id -> list of (start_time, end_time, sortie_id)
        assigned_schedules: Dict[str, List[Tuple[datetime, datetime, str]]] = {aid: [] for aid in aircraft_ids}

        proposals: List[SortieAllocationProposal] = []
        unfilled_ids: List[str] = []

        for sortie in sorted_sorties:
            eligible_candidates: List[Tuple[AircraftEligibilityReport, float, Dict[str, float]]] = []
            conflicts: List[str] = []

            for aid in aircraft_ids:
                report = AircraftEligibilityEvaluator.evaluate_aircraft(db, aircraft_id=aid, sortie=sortie)

                if report.status in (EligibilityStatus.INELIGIBLE, EligibilityStatus.INSUFFICIENT_EVIDENCE):
                    conflicts.append(f"{aid} ineligible: {'; '.join(report.reasons)}")
                    continue

                # Aircraft is ELIGIBLE or ELIGIBLE_WITH_REVIEW — check temporal schedule conflict
                has_schedule_overlap = False
                for c_start, c_end, c_sid in assigned_schedules[aid]:
                    # Overlap condition: not (c_end <= sortie.start_time or c_start >= sortie.end_time)
                    if not (c_end <= sortie.start_time or c_start >= sortie.end_time):
                        has_schedule_overlap = True
                        conflicts.append(
                            f"{aid} is already allocated to overlapping sortie '{c_sid}' ({c_start.strftime('%H:%M')}-{c_end.strftime('%H:%M')})"
                        )
                        break

                if not has_schedule_overlap:
                    score, breakdown = AllocationScorer.compute_score(report)
                    eligible_candidates.append((report, score, breakdown))

            # 4. Rank candidates deterministically
            if eligible_candidates:
                # Sort: score desc -> health desc -> aircraft_id asc (stable tie-breaking)
                eligible_candidates.sort(
                    key=lambda item: (
                        -item[1],
                        -(item[0].evidence.health_score or 0.0),
                        item[0].aircraft_id,
                    )
                )

                best_report, best_score, best_breakdown = eligible_candidates[0]
                best_aid = best_report.aircraft_id
                alternatives = [c[0].aircraft_id for c in eligible_candidates[1:]]

                # Lock temporal window for best_aid
                assigned_schedules[best_aid].append((sortie.start_time, sortie.end_time, sortie.sortie_id))

                # Determine proposal approval status (NEVER automatically APPROVED!)
                if best_report.status == EligibilityStatus.ELIGIBLE_WITH_REVIEW:
                    prop_status = AllocationApprovalStatus.REQUIRES_REVIEW
                    rev_flag = "REQUIRES_REVIEW (operator clearance mandatory)"
                else:
                    prop_status = AllocationApprovalStatus.PROPOSED
                    rev_flag = "PROPOSED (pending flight lead approval)"

                explanation = (
                    f"Aircraft '{best_aid}' selected for sortie '{sortie.sortie_id}' "
                    f"with composite score {best_score:.1f} (Readiness: {best_report.evidence.readiness_status}, "
                    f"Health: {best_report.evidence.health_score or 100:.1f}, "
                    f"RUL: {best_report.evidence.rul_hours or 0:.1f} hrs). "
                    f"Status: {rev_flag}. "
                    f"Available alternatives: {', '.join(alternatives) if alternatives else 'None'}."
                )

                proposal = SortieAllocationProposal(
                    proposal_id=f"prop-{uuid.uuid4().hex[:12]}",
                    ato_id=ato_id,
                    sortie_id=sortie.sortie_id,
                    proposed_aircraft_id=best_aid,
                    eligibility_status=best_report.status,
                    score=best_score,
                    scoring_breakdown=best_breakdown,
                    evidence=best_report.evidence,
                    conflicts=conflicts,
                    alternatives=alternatives,
                    explanation=explanation,
                    status=prop_status,
                    proposed_at=datetime.now(timezone.utc),
                )
                proposals.append(proposal)

            else:
                # Unfilled allocation
                unfilled_ids.append(sortie.sortie_id)
                expl = (
                    f"No eligible aircraft available for sortie '{sortie.sortie_id}' "
                    f"({sortie.required_aircraft_type}, {sortie.start_time.strftime('%H:%M')}-{sortie.end_time.strftime('%H:%M')}). "
                    f"All candidate airframes are ineligible or committed to overlapping sorties."
                )

                proposal = SortieAllocationProposal(
                    proposal_id=f"prop-{uuid.uuid4().hex[:12]}",
                    ato_id=ato_id,
                    sortie_id=sortie.sortie_id,
                    proposed_aircraft_id=None,
                    eligibility_status=None,
                    score=0.0,
                    scoring_breakdown={},
                    evidence=None,
                    conflicts=conflicts,
                    alternatives=[],
                    explanation=expl,
                    status=AllocationApprovalStatus.REQUIRES_REVIEW,
                    proposed_at=datetime.now(timezone.utc),
                )
                proposals.append(proposal)

        allocated_count = sum(1 for p in proposals if p.proposed_aircraft_id is not None)
        review_count = sum(1 for p in proposals if p.status == AllocationApprovalStatus.REQUIRES_REVIEW)

        summary_expl = (
            f"Generated {len(proposals)} allocation proposals for ATO '{ato_id}'. "
            f"{allocated_count}/{len(sorties)} sorties successfully matched. "
            f"{review_count} proposals require human review. "
            f"{len(unfilled_ids)} sorties unfilled due to resource/conflict constraints."
        )

        return ATOAllocationResult(
            ato_id=ato_id,
            proposals=proposals,
            unfilled_sorties=unfilled_ids,
            total_sorties=len(sorties),
            allocated_count=allocated_count,
            requires_review_count=review_count,
            unfilled_count=len(unfilled_ids),
            generated_at=datetime.now(timezone.utc),
            explanation=summary_expl,
        )
