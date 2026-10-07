"""
SageCommand Air Power System (Aero) — Base Anomaly Detector Interface.
Defines the common protocol for modular, deterministic anomaly detection engines.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.telemetry.models import NormalizedTelemetry
from app.digital_twin.models import AircraftTwinState
from app.intelligence.models import Anomaly


class BaseAnomalyDetector(ABC):
    """Abstract protocol for deterministic telemetry and twin anomaly detectors."""

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Unique identifier name of this detector."""
        pass

    @abstractmethod
    def detect(
        self,
        telemetry: NormalizedTelemetry,
        twin_state: Optional[AircraftTwinState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """
        Evaluates incoming telemetry and digital twin state to detect anomalies.

        Args:
            telemetry: Canonical normalized flight telemetry frame.
            twin_state: Estimated aircraft digital twin state (if available).
            context: Additional contextual signals (e.g. rolling historical observations).

        Returns:
            List of detected Anomaly records.
        """
        pass
