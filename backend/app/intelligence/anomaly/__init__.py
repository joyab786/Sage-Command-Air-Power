"""
SageCommand Air Power System (Aero) — Anomaly Detection Package.
Provides base detector interfaces, threshold detectors, and statistical detectors.
"""

from app.intelligence.anomaly.base import BaseAnomalyDetector
from app.intelligence.anomaly.threshold import ThresholdAnomalyDetector
from app.intelligence.anomaly.statistical import StatisticalAnomalyDetector
from app.intelligence.anomaly.detectors import (
    CompositeAnomalyDetector,
    default_composite_detector,
)

__all__ = [
    "BaseAnomalyDetector",
    "ThresholdAnomalyDetector",
    "StatisticalAnomalyDetector",
    "CompositeAnomalyDetector",
    "default_composite_detector",
]
