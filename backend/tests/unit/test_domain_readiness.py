"""
Unit tests for Aircraft Readiness domain models (FMC, PMC, NMC).
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.domain.readiness import ReadinessAssessmentCreate
from app.domain.enums import ReadinessStatus


def test_readiness_assessment_fmc():
    now = datetime.now(timezone.utc)
    ra = ReadinessAssessmentCreate(
        assessment_id="eval_001",
        aircraft_id="ac_su30_01",
        readiness_status=ReadinessStatus.FMC,
        assessed_at=now,
        reasons=["All primary subsystems nominal"],
        limiting_components=[],
        confidence=0.98,
    )
    assert ra.readiness_status == ReadinessStatus.FMC
    assert ra.confidence == 0.98
    assert len(ra.limiting_components) == 0


def test_readiness_assessment_pmc():
    now = datetime.now(timezone.utc)
    ra = ReadinessAssessmentCreate(
        assessment_id="eval_002",
        aircraft_id="ac_su30_01",
        readiness_status=ReadinessStatus.PMC,
        assessed_at=now,
        reasons=["Radar cooling pressure degraded", "Restricted to daytime training sorties"],
        limiting_components=["comp_radar_01"],
        confidence=0.92,
    )
    assert ra.readiness_status == ReadinessStatus.PMC
    assert "comp_radar_01" in ra.limiting_components


def test_readiness_confidence_out_of_bounds_fails():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        ReadinessAssessmentCreate(
            assessment_id="eval_bad_conf",
            aircraft_id="ac_01",
            readiness_status=ReadinessStatus.NMC,
            assessed_at=now,
            confidence=1.5,  # Invalid: > 1.0
        )
