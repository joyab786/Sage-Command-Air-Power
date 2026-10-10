"""
SageCommand Air Power System (Aero) — Maintenance Forecast Engine.
Synthesizes Remaining Useful Life (RUL) horizons, degradation rates, and
Phase 5 intelligence outputs into prioritized, actionable maintenance forecasts.
"""

from typing import List, Optional
from datetime import datetime, timezone

from app.intelligence.models import Anomaly, AnomalySeverity, MaintenanceRecommendation, RecommendationPriority
from app.prognostics.models import (
    MaintenanceForecast,
    MaintenanceForecastPriority,
    RULPrediction,
    TwinSubsystemType,
)


class MaintenanceForecaster:
    """
    Evaluates prognostic RUL horizons alongside Phase 5 recommendations
    to generate consolidated, defensible maintenance forecasts.
    """

    @classmethod
    def generate_forecast(
        cls,
        rul: RULPrediction,
        active_anomalies: Optional[List[Anomaly]] = None,
        recommendations: Optional[List[MaintenanceRecommendation]] = None,
    ) -> MaintenanceForecast:
        """
        Derives an operational maintenance forecast from RUL predictions and diagnostic evidence.
        """
        aircraft_id = rul.aircraft_id
        active_anoms = active_anomalies or []
        recs = recommendations or []
        related_anomaly_ids = [a.anomaly_id for a in active_anoms]

        has_critical = any(a.severity == AnomalySeverity.CRITICAL for a in active_anoms)
        has_high = any(a.severity == AnomalySeverity.HIGH for a in active_anoms)
        has_ground_rec = any(r.priority == RecommendationPriority.GROUND_FOR_REVIEW for r in recs)

        # ---------------------------------------------------------------------
        # Consolidated Priority Determination
        # ---------------------------------------------------------------------
        if has_critical or has_ground_rec or rul.estimated_rul_hours < 15.0:
            priority = MaintenanceForecastPriority.GROUND_FOR_REVIEW
            recommended_window = "Immediate prior to next flight"
            action = (
                f"Ground airframe '{aircraft_id}' for engineering diagnostic inspection of "
                f"{rul.subsystem.value} subsystem."
            )
            driver = "Critical subsystem anomaly or imminent RUL exhaustion"
            explanation = (
                f"Prognostic analysis identifies urgent maintenance risk on {rul.subsystem.value}. "
                f"Estimated RUL is {rul.estimated_rul_hours:.1f} hours. Immediate human review required."
            )

        elif has_high or rul.estimated_rul_hours < 60.0 or rul.degradation_rate > 2.0:
            priority = MaintenanceForecastPriority.PRIORITY_INSPECTION
            recommended_window = "Within next 10 flight hours / immediate turnaround"
            action = (
                f"Conduct high-priority turnaround inspection on {rul.subsystem.value} "
                f"and verify telemetry sensor integrity."
            )
            driver = f"Accelerated degradation rate ({rul.degradation_rate:.2f} pts/hr) or HIGH anomaly"
            explanation = (
                f"Elevated degradation observed on {rul.subsystem.value}. Projected RUL horizon "
                f"is {rul.estimated_rul_hours:.1f} hours [{rul.lower_bound_hours:.1f} - {rul.upper_bound_hours:.1f} h]. "
                f"High-priority turnaround inspection advised."
            )

        elif rul.estimated_rul_hours < 150.0 or any(a.severity == AnomalySeverity.MEDIUM for a in active_anoms):
            priority = MaintenanceForecastPriority.INSPECT_SOON
            recommended_window = "Within next 50 flight hours"
            action = f"Perform BITE and visual diagnostic inspection of {rul.subsystem.value} during next turnaround."
            driver = f"RUL horizon within caution window ({rul.estimated_rul_hours:.1f} hrs)"
            explanation = (
                f"Subsystem {rul.subsystem.value} degradation trajectory indicates inspection is warranted "
                f"within {rul.estimated_rul_hours:.0f} hours to prevent operational disruption."
            )

        elif rul.estimated_rul_hours < 300.0 or rul.degradation_rate > 0.2:
            priority = MaintenanceForecastPriority.PLAN_MAINTENANCE
            recommended_window = "Within next 150 flight hours"
            action = f"Schedule preventative component servicing for {rul.subsystem.value} in upcoming maintenance cycle."
            driver = "Moderate long-term degradation trend"
            explanation = (
                f"Subsystem {rul.subsystem.value} is exhibiting gradual degradation. Maintenance can be scheduled "
                f"within standard squadron maintenance availability windows."
            )

        else:
            priority = MaintenanceForecastPriority.MONITOR
            recommended_window = "Standard periodic depot inspection"
            action = f"Continue standard telemetry monitoring; {rul.subsystem.value} is operating nominally."
            driver = "Subsystem operating within nominal baseline envelope"
            explanation = (
                f"Subsystem {rul.subsystem.value} health is stable with an estimated RUL of "
                f"{rul.estimated_rul_hours:.0f} flight hours. No immediate maintenance intervention required."
            )

        return MaintenanceForecast(
            aircraft_id=aircraft_id,
            timestamp=datetime.now(timezone.utc),
            priority=priority,
            urgency_horizon_hours=rul.estimated_rul_hours,
            affected_subsystems=[rul.subsystem],
            primary_driver=driver,
            recommended_window=recommended_window,
            action=action,
            confidence=rul.confidence,
            explanation=explanation,
            related_anomalies=related_anomaly_ids,
        )


default_maintenance_forecaster = MaintenanceForecaster()
