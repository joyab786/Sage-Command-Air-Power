"""
Unit tests for Component domain model and health states.
"""

import pytest
from pydantic import ValidationError
from app.domain.component import ComponentCreate, ComponentUpdate
from app.domain.enums import ComponentHealth, ComponentType


def test_component_creation_valid():
    comp = ComponentCreate(
        component_id="comp_al31fp_01",
        aircraft_id="ac_su30_01",
        component_type=ComponentType.TURBOFAN_ENGINE,
        serial_number="SN-ENG-88210",
        health_state=ComponentHealth.HEALTHY,
        accumulated_hours=420.5,
        accumulated_cycles=210,
    )
    assert comp.component_id == "comp_al31fp_01"
    assert comp.aircraft_id == "ac_su30_01"
    assert comp.component_type == ComponentType.TURBOFAN_ENGINE
    assert comp.health_state == ComponentHealth.HEALTHY
    assert comp.accumulated_hours == 420.5
    assert comp.accumulated_cycles == 210


def test_component_negative_accumulated_hours_fails():
    with pytest.raises(ValidationError):
        ComponentCreate(
            component_id="comp_fail_01",
            aircraft_id="ac_01",
            component_type=ComponentType.HYDRAULICS,
            serial_number="SN-HYD-001",
            accumulated_hours=-1.0,
        )


def test_component_negative_accumulated_cycles_fails():
    with pytest.raises(ValidationError):
        ComponentCreate(
            component_id="comp_fail_02",
            aircraft_id="ac_01",
            component_type=ComponentType.AVIONICS,
            serial_number="SN-AVI-001",
            accumulated_cycles=-10,
        )


def test_component_health_transitions():
    update = ComponentUpdate(health_state=ComponentHealth.WARNING)
    assert update.health_state == ComponentHealth.WARNING

    update_critical = ComponentUpdate(health_state=ComponentHealth.CRITICAL)
    assert update_critical.health_state == ComponentHealth.CRITICAL
