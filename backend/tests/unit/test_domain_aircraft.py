"""
Unit tests for Aircraft domain model and contract validations.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.domain.aircraft import AircraftCreate, AircraftUpdate, AircraftResponse
from app.domain.enums import AircraftStatus


def test_aircraft_creation_valid():
    ac = AircraftCreate(
        aircraft_id="ac_su30_01",
        tail_number="SB-021",
        aircraft_type="Su-30MKI",
        variant="Super Sukhoi",
        air_base="Pune AFS",
        squadron="No. 20 Lightnings",
        status=AircraftStatus.ACTIVE,
        total_flight_hours=1450.5,
        total_flight_cycles=820,
    )
    assert ac.aircraft_id == "ac_su30_01"
    assert ac.tail_number == "SB-021"
    assert ac.total_flight_hours == 1450.5
    assert ac.total_flight_cycles == 820
    assert ac.status == AircraftStatus.ACTIVE


def test_aircraft_negative_flight_hours_fails():
    with pytest.raises(ValidationError):
        AircraftCreate(
            aircraft_id="ac_neg_01",
            tail_number="SB-999",
            aircraft_type="Su-30MKI",
            air_base="Pune AFS",
            squadron="No. 20",
            total_flight_hours=-10.0,
        )


def test_aircraft_negative_flight_cycles_fails():
    with pytest.raises(ValidationError):
        AircraftCreate(
            aircraft_id="ac_neg_02",
            tail_number="SB-998",
            aircraft_type="Su-30MKI",
            air_base="Pune AFS",
            squadron="No. 20",
            total_flight_cycles=-5,
        )


def test_aircraft_whitespace_stripping():
    ac = AircraftCreate(
        aircraft_id="  ac_strip_01  ",
        tail_number="  SB-055  ",
        aircraft_type="Tejas Mk1A",
        air_base=" Sulur AFS ",
        squadron=" Flying Daggers ",
    )
    assert ac.aircraft_id == "ac_strip_01"
    assert ac.tail_number == "SB-055"
    assert ac.air_base == "Sulur AFS"
    assert ac.squadron == "Flying Daggers"


def test_aircraft_empty_identifier_fails():
    with pytest.raises(ValidationError):
        AircraftCreate(
            aircraft_id="   ",
            tail_number="SB-001",
            aircraft_type="Tejas",
            air_base="Sulur",
            squadron="Daggers",
        )


def test_aircraft_update_partial_fields():
    update = AircraftUpdate(
        status=AircraftStatus.MAINTENANCE,
        total_flight_hours=1500.0,
    )
    assert update.status == AircraftStatus.MAINTENANCE
    assert update.total_flight_hours == 1500.0
    assert update.air_base is None
