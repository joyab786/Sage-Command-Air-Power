"""
SageCommand Air Power System (Aero) — Subsystem Intelligence & Anomaly Detection Package (SIH MVP).
Provides explainable anomaly detection, statistical baselines, active anomaly correlation/deduplication,
root-cause diagnostic synthesis, and decision-support maintenance recommendations.
"""

from app.intelligence.models import (
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    RecommendationPriority,
    Anomaly,
    Diagnosis,
    MaintenanceRecommendation,
)
from app.intelligence.anomaly import (
    BaseAnomalyDetector,
    ThresholdAnomalyDetector,
    StatisticalAnomalyDetector,
    CompositeAnomalyDetector,
    default_composite_detector,
)
from app.intelligence.diagnosis import (
    RootCauseDiagnosisEngine,
    default_diagnosis_engine,
)
from app.intelligence.maintenance import (
    MaintenanceRecommendationEngine,
    default_maintenance_engine,
)
from app.intelligence.service import (
    IntelligenceService,
    default_intelligence_service,
)

__all__ = [
    "AnomalySeverity",
    "AnomalyStatus",
    "AnomalyType",
    "RecommendationPriority",
    "Anomaly",
    "Diagnosis",
    "MaintenanceRecommendation",
    "BaseAnomalyDetector",
    "ThresholdAnomalyDetector",
    "StatisticalAnomalyDetector",
    "CompositeAnomalyDetector",
    "default_composite_detector",
    "RootCauseDiagnosisEngine",
    "default_diagnosis_engine",
    "MaintenanceRecommendationEngine",
    "default_maintenance_engine",
    "IntelligenceService",
    "default_intelligence_service",
]
