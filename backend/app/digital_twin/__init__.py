"""
SageCommand Air Power System (Aero) — Aircraft Digital Twin Package.
Provides state estimation, conceptual subsystem health tracking,
explainable degradation scoring, and operational flight session lifecycles.
"""

from app.digital_twin.models import (
    TwinSubsystemType,
    TwinHealthState,
    HealthReason,
    SubsystemState,
    AircraftTwinState,
    FlightSession,
)
from app.digital_twin.health import AircraftHealthEstimator
from app.digital_twin.wear import WearEstimator
from app.digital_twin.estimator import DigitalTwinEstimator
from app.digital_twin.service import DigitalTwinService, default_digital_twin_service

__all__ = [
    "TwinSubsystemType",
    "TwinHealthState",
    "HealthReason",
    "SubsystemState",
    "AircraftTwinState",
    "FlightSession",
    "AircraftHealthEstimator",
    "WearEstimator",
    "DigitalTwinEstimator",
    "DigitalTwinService",
    "default_digital_twin_service",
]
