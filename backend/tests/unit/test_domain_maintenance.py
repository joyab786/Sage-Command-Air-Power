"""
Unit tests for Maintenance domain models, priority levels, and timestamp rules.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from app.domain.maintenance import MaintenanceEventCreate
from app.domain.enums import MaintenanceStatus, MaintenancePriority, MaintenanceType


def test_maintenance_creation_valid():
    now = datetime.now(timezone.utc)
    evt = MaintenanceEventCreate(
        maintenance_event_id="maint_001",
        aircraft_id="ac_su30_01",
        component_id="comp_al31fp_01",
        maintenance_type=MaintenanceType.PREDICTIVE,
        status=MaintenanceStatus.OPEN,
        priority=MaintenancePriority.HIGH,
        detected_at=now,
        description="Abnormal EGT thermal drift detected during cruise.",
        source="PREDICTIVE_RUL",
    )
    assert evt.maintenance_event_id == "maint_001"
    assert evt.status == MaintenanceStatus.OPEN
    assert evt.priority == MaintenancePriority.HIGH
    assert evt.source == "PREDICTIVE_RUL"


def test_maintenance_completed_before_detected_fails():
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=2)
    with pytest.raises(ValidationError):
        MaintenanceEventCreate(
            maintenance_event_id="maint_bad_time",
            aircraft_id="ac_01",
            maintenance_type=MaintenanceType.CORRECTIVE,
            status=MaintenanceStatus.COMPLETED,
            priority=MaintenancePriority.MEDIUM,
            detected_at=now,
            completed_at=past,  # Invalid: completed before detected
            description="Completed before detection",
        )


def test_maintenance_empty_description_fails():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        MaintenanceEventCreate(
            maintenance_event_id="maint_empty_desc",
            aircraft_id="ac_01",
            detected_at=now,
            description="   ",
        )
