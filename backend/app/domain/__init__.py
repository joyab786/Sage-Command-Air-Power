"""
SageCommand Air Power System (Aero) — Canonical Domain Package.
Exposes aerospace domain models, contracts, and enumerations.
"""

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

from app.domain.aircraft import (
    AircraftBase,
    AircraftCreate,
    AircraftUpdate,
    AircraftResponse,
)

from app.domain.component import (
    ComponentBase,
    ComponentCreate,
    ComponentUpdate,
    ComponentResponse,
)

from app.domain.telemetry import TelemetryObservation

from app.domain.maintenance import (
    MaintenanceEventBase,
    MaintenanceEventCreate,
    MaintenanceEventUpdate,
    MaintenanceEventResponse,
)

from app.domain.readiness import (
    ReadinessAssessmentBase,
    ReadinessAssessmentCreate,
    ReadinessAssessmentResponse,
)

from app.domain.mission import (
    MissionBase,
    MissionCreate,
    MissionUpdate,
    MissionResponse,
)

__all__ = [
    # Enums
    "AircraftStatus",
    "ComponentHealth",
    "ComponentType",
    "TelemetryQuality",
    "MaintenanceStatus",
    "MaintenancePriority",
    "MaintenanceType",
    "ReadinessStatus",
    "MissionStatus",
    "MissionType",
    # Aircraft
    "AircraftBase",
    "AircraftCreate",
    "AircraftUpdate",
    "AircraftResponse",
    # Component
    "ComponentBase",
    "ComponentCreate",
    "ComponentUpdate",
    "ComponentResponse",
    # Telemetry
    "TelemetryObservation",
    # Maintenance
    "MaintenanceEventBase",
    "MaintenanceEventCreate",
    "MaintenanceEventUpdate",
    "MaintenanceEventResponse",
    # Readiness
    "ReadinessAssessmentBase",
    "ReadinessAssessmentCreate",
    "ReadinessAssessmentResponse",
    # Mission
    "MissionBase",
    "MissionCreate",
    "MissionUpdate",
    "MissionResponse",
]
