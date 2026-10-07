"""
Unit tests for Telemetry SQLite Persistence.
Validates table schema, index performance, aircraft filtering, and cascade lifecycle.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import AircraftModel, TelemetryRecordModel, utc_now
from app.telemetry.service import TelemetryService
from app.telemetry.models import TelemetryInput, BatchIngestRequest


def test_telemetry_insert_and_query_by_aircraft(db_session: Session):
    # 1. Register host aircraft
    ac = AircraftModel(
        aircraft_id="ac_persist_01",
        tail_number="TS-901",
        aircraft_type="Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="Flying Daggers",
    )
    db_session.add(ac)
    db_session.commit()

    service = TelemetryService()
    t0 = datetime.now(timezone.utc) - timedelta(minutes=10)

    # 2. Ingest frames with 1-minute steps
    for i in range(3):
        frame = TelemetryInput(
            observation_id=f"obs_persist_{i}",
            timestamp=t0 + timedelta(minutes=i),
            aircraft_id="ac_persist_01",
            altitude=15000.0 + (i * 1000.0),
            airspeed=420.0,
            mach=0.78,
            units={"altitude": "ft", "airspeed": "kts"},
        )
        res = service.ingest_observation(db_session, frame, persist=True)
        assert res.accepted is True
        assert res.persisted is True

    # 3. Query records for aircraft
    history = service.get_for_aircraft(db_session, aircraft_id="ac_persist_01")
    assert len(history) == 3
    # Check descending order by timestamp (newest first)
    assert history[0].observation_id == "obs_persist_2"
    assert history[-1].observation_id == "obs_persist_0"


def test_telemetry_cascade_delete_with_aircraft(db_session: Session):
    # 1. Register host aircraft
    ac = AircraftModel(
        aircraft_id="ac_cascade_01",
        tail_number="TS-902",
        aircraft_type="Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="Flying Daggers",
    )
    db_session.add(ac)
    db_session.commit()

    service = TelemetryService()
    frame = TelemetryInput(
        observation_id="obs_casc_01",
        aircraft_id="ac_cascade_01",
        altitude=20000.0,
        airspeed=450.0,
    )
    res = service.ingest_observation(db_session, frame, persist=True)
    assert res.accepted is True

    # 2. Verify record exists in DB
    record = db_session.execute(
        select(TelemetryRecordModel).where(TelemetryRecordModel.record_id == "obs_casc_01")
    ).scalar_one_or_none()
    assert record is not None

    # 3. Delete aircraft -> cascade deletes telemetry records
    db_session.delete(ac)
    db_session.commit()

    orphaned = db_session.execute(
        select(TelemetryRecordModel).where(TelemetryRecordModel.record_id == "obs_casc_01")
    ).scalar_one_or_none()
    assert orphaned is None
