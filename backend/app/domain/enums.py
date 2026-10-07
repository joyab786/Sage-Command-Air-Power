"""
SageCommand Air Power System (Aero) — Domain Enumerations.
Provides strongly typed enums for aircraft lifecycle, component health,
telemetry quality, maintenance workflows, readiness ratings, and mission states.
"""

from enum import Enum


class AircraftStatus(str, Enum):
    """Authoritative lifecycle status for an airframe asset."""

    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    GROUNDED = "GROUNDED"
    RETIRED = "RETIRED"


class ComponentHealth(str, Enum):
    """Normalized health condition assessment for aircraft subsystems."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"


class ComponentType(str, Enum):
    """Standardized subsystem classification for aerospace equipment."""

    TURBOFAN_ENGINE = "TURBOFAN_ENGINE"
    HYDRAULICS = "HYDRAULICS"
    AVIONICS = "AVIONICS"
    ELECTRICAL = "ELECTRICAL"
    RADAR = "RADAR"
    LANDING_GEAR = "LANDING_GEAR"
    FUEL_SYSTEM = "FUEL_SYSTEM"
    AIRFRAME = "AIRFRAME"
    FLIGHT_CONTROL = "FLIGHT_CONTROL"
    OTHER = "OTHER"


class TelemetryQuality(str, Enum):
    """Quality and fidelity indicator for ingested sensor signals."""

    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    SUSPECT = "SUSPECT"
    INVALID = "INVALID"


class MaintenanceStatus(str, Enum):
    """Lifecycle progression of a maintenance event or work package."""

    OPEN = "OPEN"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MaintenancePriority(str, Enum):
    """Operational urgency classification for maintenance intervention."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenanceType(str, Enum):
    """Classification of maintenance action origin."""

    SCHEDULED = "SCHEDULED"
    UNSCHEDULED = "UNSCHEDULED"
    PREDICTIVE = "PREDICTIVE"
    INSPECTION = "INSPECTION"
    CORRECTIVE = "CORRECTIVE"


class ReadinessStatus(str, Enum):
    """Standard aerospace military mission capability classification."""

    FMC = "FMC"  # Fully Mission Capable
    PMC = "PMC"  # Partially Mission Capable
    NMC = "NMC"  # Non-Mission Capable


class MissionStatus(str, Enum):
    """Operational status of a planned or executing sortie/mission."""

    PLANNED = "PLANNED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    CANCELLED = "CANCELLED"


class MissionType(str, Enum):
    """Operational mission profile classification."""

    COMBAT_AIR_PATROL = "COMBAT_AIR_PATROL"
    INTERCEPTION = "INTERCEPTION"
    STRIKE = "STRIKE"
    RECONNAISSANCE = "RECONNAISSANCE"
    TRAINING = "TRAINING"
    ESCORT = "ESCORT"
    FERRY = "FERRY"
