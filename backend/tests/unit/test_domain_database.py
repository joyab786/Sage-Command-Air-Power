"""
Unit tests for SQLAlchemy 2.0 ORM persistence, relationships, and constraints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.db.models import (
    AircraftModel,
    ComponentModel,
    MaintenanceEventModel,
    ReadinessAssessmentModel,
    MissionModel,
    utc_now,
)


def test_database_aircraft_persistence(db_session: Session):
    ac = AircraftModel(
        aircraft_id="ac_db_01",
        tail_number="SB-101",
        aircraft_type="Su-30MKI",
        air_base="Bareilly AFS",
        squadron="No. 8 Eight Pursoots",
        status="ACTIVE",
        total_flight_hours=1200.0,
        total_flight_cycles=650,
    )
    db_session.add(ac)
    db_session.commit()

    queried = db_session.execute(
        select(AircraftModel).where(AircraftModel.aircraft_id == "ac_db_01")
    ).scalar_one()

    assert queried.aircraft_id == "ac_db_01"
    assert queried.tail_number == "SB-101"
    assert queried.total_flight_hours == 1200.0


def test_database_duplicate_tail_number_fails(db_session: Session):
    ac1 = AircraftModel(
        aircraft_id="ac_dup_01",
        tail_number="SB-555",
        aircraft_type="Rafale",
        air_base="Ambala AFS",
        squadron="Golden Arrows",
    )
    ac2 = AircraftModel(
        aircraft_id="ac_dup_02",
        tail_number="SB-555",  # Duplicate tail number
        aircraft_type="Rafale",
        air_base="Ambala AFS",
        squadron="Golden Arrows",
    )
    db_session.add(ac1)
    db_session.commit()

    db_session.add(ac2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_database_component_relationship_and_cascade(db_session: Session):
    ac = AircraftModel(
        aircraft_id="ac_rel_01",
        tail_number="SB-201",
        aircraft_type="Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="Flying Daggers",
    )
    db_session.add(ac)
    db_session.commit()

    comp = ComponentModel(
        component_id="comp_rel_01",
        aircraft_id="ac_rel_01",
        component_type="TURBOFAN_ENGINE",
        serial_number="SN-F404-001",
        health_state="HEALTHY",
    )
    db_session.add(comp)
    db_session.commit()

    # Query via relationship
    reloaded_ac = db_session.execute(
        select(AircraftModel).where(AircraftModel.aircraft_id == "ac_rel_01")
    ).scalar_one()
    assert len(reloaded_ac.components) == 1
    assert reloaded_ac.components[0].component_id == "comp_rel_01"

    # Delete aircraft -> should cascade delete components
    db_session.delete(reloaded_ac)
    db_session.commit()

    orphaned = db_session.execute(
        select(ComponentModel).where(ComponentModel.component_id == "comp_rel_01")
    ).scalar_one_or_none()
    assert orphaned is None


def test_database_mission_persistence(db_session: Session):
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(hours=2)
    mission = MissionModel(
        mission_id="msn_db_01",
        mission_name="Border Patrol Alpha",
        mission_type="COMBAT_AIR_PATROL",
        scheduled_start=start,
        scheduled_end=end,
        required_aircraft=2,
        assigned_aircraft=["ac_db_01"],
        status="PLANNED",
    )
    db_session.add(mission)
    db_session.commit()

    queried = db_session.execute(
        select(MissionModel).where(MissionModel.mission_id == "msn_db_01")
    ).scalar_one()
    assert queried.mission_id == "msn_db_01"
    assert queried.required_aircraft == 2
    assert queried.assigned_aircraft == ["ac_db_01"]
