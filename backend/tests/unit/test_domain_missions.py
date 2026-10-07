"""
Unit tests for Mission & Sortie domain models and constraints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from app.domain.mission import MissionCreate, MissionUpdate
from app.domain.enums import MissionStatus, MissionType, ReadinessStatus


def test_mission_creation_valid():
    start = datetime.now(timezone.utc) + timedelta(hours=2)
    end = start + timedelta(hours=3)
    mission = MissionCreate(
        mission_id="msn_cap_2026_01",
        mission_name="Operation Garuda Sentinel",
        mission_type=MissionType.COMBAT_AIR_PATROL,
        scheduled_start=start,
        scheduled_end=end,
        required_aircraft=4,
        assigned_aircraft=["ac_su30_01", "ac_su30_02"],
        status=MissionStatus.PLANNED,
        readiness_requirement=ReadinessStatus.FMC,
    )
    assert mission.mission_id == "msn_cap_2026_01"
    assert mission.required_aircraft == 4
    assert mission.status == MissionStatus.PLANNED
    assert len(mission.assigned_aircraft) == 2


def test_mission_end_before_start_fails():
    start = datetime.now(timezone.utc) + timedelta(hours=4)
    end = start - timedelta(hours=1)
    with pytest.raises(ValidationError):
        MissionCreate(
            mission_id="msn_bad_time",
            scheduled_start=start,
            scheduled_end=end,
            required_aircraft=2,
        )


def test_mission_zero_required_aircraft_fails():
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(hours=2)
    with pytest.raises(ValidationError):
        MissionCreate(
            mission_id="msn_zero_ac",
            scheduled_start=start,
            scheduled_end=end,
            required_aircraft=0,
        )
