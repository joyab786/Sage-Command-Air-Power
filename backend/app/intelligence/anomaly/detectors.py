"""
SageCommand Air Power System (Aero) — Composite Anomaly Detector Engine.
Orchestrates threshold and statistical detectors, aggregating multi-signal findings.
"""

from typing import List, Optional, Dict, Any
from app.telemetry.models import NormalizedTelemetry
from app.digital_twin.models import AircraftTwinState
from app.intelligence.models import Anomaly
from app.intelligence.anomaly.base import BaseAnomalyDetector
from app.intelligence.anomaly.threshold import ThresholdAnomalyDetector
from app.intelligence.anomaly.statistical import StatisticalAnomalyDetector


class CompositeAnomalyDetector:
    """Aggregates and executes all registered anomaly detection engines."""

    def __init__(
        self,
        detectors: Optional[List[BaseAnomalyDetector]] = None,
    ):
        self.detectors: List[BaseAnomalyDetector] = detectors or [
            ThresholdAnomalyDetector(),
            StatisticalAnomalyDetector(),
        ]

    def detect_all(
        self,
        telemetry: NormalizedTelemetry,
        twin_state: Optional[AircraftTwinState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """Runs all detectors and returns aggregated anomaly detections."""
        findings: List[Anomaly] = []
        for det in self.detectors:
            try:
                results = det.detect(telemetry, twin_state, context)
                findings.extend(results)
            except Exception:
                # Detector failure must never crash the ingestion pipeline
                pass
        return findings


default_composite_detector = CompositeAnomalyDetector()
