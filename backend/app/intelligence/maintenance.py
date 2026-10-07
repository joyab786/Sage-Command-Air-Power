"""
SageCommand Air Power System (Aero) — Maintenance Recommendation Engine.
Translates anomaly detections, root-cause diagnoses, and digital twin health
into actionable, explainable decision-support maintenance recommendations.
"""

from typing import List, Optional
from datetime import datetime, timezone
from app.digital_twin.models import AircraftTwinState, TwinSubsystemType, utc_now
from app.intelligence.models import (
    Anomaly,
    AnomalySeverity,
    Diagnosis,
    MaintenanceRecommendation,
    RecommendationPriority,
)


class MaintenanceRecommendationEngine:
    """
    Deterministic maintenance decision-support generator.
    Produces prioritized servicing recommendations with transparent justification.
    """

    def recommend(
        self,
        anomalies: List[Anomaly],
        diagnosis: Optional[Diagnosis] = None,
        twin_state: Optional[AircraftTwinState] = None,
        aircraft_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[MaintenanceRecommendation]:
        """
        Derives an operational maintenance recommendation list.
        """
        eval_time = now or utc_now()
        aid = aircraft_id or (diagnosis.aircraft_id if diagnosis else "UNKNOWN")
        rec_id = f"rec_{aid}_{int(eval_time.timestamp() * 1000)}"
        anom_ids = [a.anomaly_id for a in anomalies]
        subsystem = diagnosis.primary_subsystem if diagnosis else TwinSubsystemType.PROPULSION

        severities = [a.severity for a in anomalies]
        has_critical = AnomalySeverity.CRITICAL in severities
        has_high = AnomalySeverity.HIGH in severities
        has_medium = AnomalySeverity.MEDIUM in severities

        twin_health = twin_state.health_score if twin_state else 100.0

        # -------------------------------------------------------------
        # 1. GROUND_FOR_REVIEW
        # -------------------------------------------------------------
        if has_critical or twin_health < 50.0 or (diagnosis and diagnosis.confidence >= 0.93 and len(anomalies) >= 2):
            return [
                MaintenanceRecommendation(
                    recommendation_id=rec_id,
                    aircraft_id=aid,
                    priority=RecommendationPriority.GROUND_FOR_REVIEW,
                    action="Advisory: Recommend engineering inspection and ground review before next sortie. Perform borescope and system diagnostics.",
                    reason=f"Critical operational condition detected on {subsystem.value}. {diagnosis.explanation if diagnosis else ''}",
                    related_anomalies=anom_ids,
                    affected_subsystem=subsystem,
                    confidence=round(diagnosis.confidence, 4) if diagnosis else 0.95,
                    created_at=eval_time,
                )
            ]

        # -------------------------------------------------------------
        # 2. SCHEDULE_MAINTENANCE
        # -------------------------------------------------------------
        if has_high or twin_health < 75.0:
            return [
                MaintenanceRecommendation(
                    recommendation_id=rec_id,
                    aircraft_id=aid,
                    priority=RecommendationPriority.SCHEDULE_MAINTENANCE,
                    action="Schedule unscheduled maintenance inspection and subsystem bench testing prior to next planned sortie.",
                    reason=f"Significant parameter deviation on {subsystem.value} exceeding standard caution thresholds.",
                    related_anomalies=anom_ids,
                    affected_subsystem=subsystem,
                    confidence=round(diagnosis.confidence, 4) if diagnosis else 0.88,
                    created_at=eval_time,
                )
            ]

        # -------------------------------------------------------------
        # 3. INSPECT
        # -------------------------------------------------------------
        if has_medium or twin_health < 90.0:
            return [
                MaintenanceRecommendation(
                    recommendation_id=rec_id,
                    aircraft_id=aid,
                    priority=RecommendationPriority.INSPECT,
                    action="Conduct line maintenance visual walkaround and run pre-flight built-in test (BIT) interrogation.",
                    reason=f"Parameter operating in caution envelope boundary on {subsystem.value}.",
                    related_anomalies=anom_ids,
                    affected_subsystem=subsystem,
                    confidence=round(diagnosis.confidence, 4) if diagnosis else 0.80,
                    created_at=eval_time,
                )
            ]

        # -------------------------------------------------------------
        # 4. MONITOR (Nominal)
        # -------------------------------------------------------------
        return [
            MaintenanceRecommendation(
                recommendation_id=rec_id,
                aircraft_id=aid,
                priority=RecommendationPriority.MONITOR,
                action="Continue routine flight telemetry trend monitoring. No physical maintenance intervention required.",
                reason="Subsystem operating parameters reside stably within standard demonstration baseline limits.",
                related_anomalies=anom_ids,
                affected_subsystem=subsystem,
                confidence=0.99,
                created_at=eval_time,
            )
        ]


default_maintenance_engine = MaintenanceRecommendationEngine()
