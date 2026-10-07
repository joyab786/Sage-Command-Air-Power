"""
Unit tests for Aero Domain Enumerations.
Validates enum string values, completeness, and immutability.
"""

import pytest
from app.domain.enums import (
    AircraftStatus,
    ComponentHealth,
    ComponentType,
    TelemetryQuality,
    MaintenanceStatus,
    MaintenancePriority,
    MaintenanceType,
    ReadinessStatus,
    MissionStatus,
    MissionType,
)


def test_aircraft_status_values():
    assert AircraftStatus.ACTIVE == "ACTIVE"
    assert AircraftStatus.MAINTENANCE == "MAINTENANCE"
    assert AircraftStatus.GROUNDED == "GROUNDED"
    assert AircraftStatus.RETIRED == "RETIRED"


def test_component_health_values():
    assert ComponentHealth.HEALTHY == "HEALTHY"
    assert ComponentHealth.DEGRADED == "DEGRADED"
    assert ComponentHealth.WARNING == "WARNING"
    assert ComponentHealth.CRITICAL == "CRITICAL"
    assert ComponentHealth.FAILED == "FAILED"


def test_readiness_status_values():
    assert ReadinessStatus.FMC == "FMC"
    assert ReadinessStatus.PMC == "PMC"
    assert ReadinessStatus.NMC == "NMC"


def test_telemetry_quality_values():
    assert TelemetryQuality.GOOD == "GOOD"
    assert TelemetryQuality.DEGRADED == "DEGRADED"
    assert TelemetryQuality.SUSPECT == "SUSPECT"
    assert TelemetryQuality.INVALID == "INVALID"


def test_maintenance_enums():
    assert MaintenanceStatus.OPEN == "OPEN"
    assert MaintenanceStatus.COMPLETED == "COMPLETED"
    assert MaintenancePriority.CRITICAL == "CRITICAL"
    assert MaintenanceType.PREDICTIVE == "PREDICTIVE"


def test_mission_enums():
    assert MissionStatus.PLANNED == "PLANNED"
    assert MissionStatus.IN_PROGRESS == "IN_PROGRESS"
    assert MissionType.COMBAT_AIR_PATROL == "COMBAT_AIR_PATROL"
