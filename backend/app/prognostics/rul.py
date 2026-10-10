"""
SageCommand Air Power System (Aero) — Remaining Useful Life (RUL) Predictor.
Implements the BaseRULPredictor protocol and deterministic trend-based RUL estimation
with wear bounding, uncertainty intervals, and Phase 5 anomaly modifier integration.
"""

from typing import List, Optional, Protocol, runtime_checkable
from datetime import datetime, timezone
import math

from app.digital_twin.models import AircraftTwinState, TwinSubsystemType
from app.intelligence.models import Anomaly, AnomalySeverity
from app.prognostics.models import (
    DegradationTrend,
    PredictionMethod,
    RULPrediction,
    TrendDirection,
)


@runtime_checkable
class BaseRULPredictor(Protocol):
    """Protocol defining the extensible interface for Remaining Useful Life (RUL) estimators."""

    def predict(
        self,
        trend: DegradationTrend,
        current_state: Optional[AircraftTwinState] = None,
        active_anomalies: Optional[List[Anomaly]] = None,
    ) -> RULPrediction:
        """Computes explainable Remaining Useful Life prediction from degradation trend and context."""
        ...


class DeterministicRULPredictor:
    """
    Deterministic trend-based RUL predictor for the SIH MVP.
    Combines health degradation rate, digital twin wear limits, and active anomaly evidence.
    """

    HEALTH_FAILURE_THRESHOLD: float = 25.0    # Demonstration threshold where component is depleted
    WEAR_FAILURE_THRESHOLD: float = 1.0        # Normalized wear limit (1.0 = full design life consumed)
    NOMINAL_MAX_RUL_HOURS: float = 1000.0      # Nominal demonstration ceiling for healthy airframe components
    NOMINAL_MAX_RUL_CYCLES: int = 500

    def predict(
        self,
        trend: DegradationTrend,
        current_state: Optional[AircraftTwinState] = None,
        active_anomalies: Optional[List[Anomaly]] = None,
    ) -> RULPrediction:
        """
        Computes an explainable, bounded RUL prediction.
        """
        subsystem = trend.subsystem
        aircraft_id = trend.aircraft_id
        active_anoms = active_anomalies or []
        limiting_factors: List[str] = []

        cur_health = trend.current_health
        cur_wear = current_state.wear_index if current_state else 0.0

        # ---------------------------------------------------------------------
        # 1. Base RUL Calculation by Trend Direction
        # ---------------------------------------------------------------------
        if trend.trend_direction == TrendDirection.INSUFFICIENT_DATA:
            estimated_rul = self.NOMINAL_MAX_RUL_HOURS
            prediction_method = PredictionMethod.INSUFFICIENT_HISTORY_FALLBACK
            confidence = min(0.25, trend.confidence)
            limiting_factors.append("Insufficient historical observations to establish degradation slope")
            explanation = (
                f"Insufficient historical data ({trend.sample_count} observations). "
                f"RUL estimate set to nominal demonstration ceiling ({self.NOMINAL_MAX_RUL_HOURS:.0f} hrs) "
                f"with low confidence pending observation accumulation."
            )
            recommended_action = "Continue automated telemetry monitoring until sufficient observations accumulate."

        elif trend.trend_direction in (TrendDirection.STABLE, TrendDirection.IMPROVING):
            estimated_rul = self.NOMINAL_MAX_RUL_HOURS
            prediction_method = PredictionMethod.BASELINE_NOMINAL
            confidence = trend.confidence

            # Wear index bounding if significantly worn
            if cur_wear > 0.4:
                wear_margin = max(0.0, self.WEAR_FAILURE_THRESHOLD - cur_wear)
                wear_based_rul = wear_margin * self.NOMINAL_MAX_RUL_HOURS
                if wear_based_rul < estimated_rul:
                    estimated_rul = wear_based_rul
                    prediction_method = PredictionMethod.COMPOSITE_CONSERVATIVE_BOUND
                    limiting_factors.append(f"Cumulative structural wear index ({cur_wear:.2f}) limits design margin")

            explanation = (
                f"Subsystem condition is {trend.trend_direction.value.lower()} at health score {cur_health:.1f}. "
                f"No active degradation trajectory detected. Subsystem operates within nominal envelope."
            )
            recommended_action = "Continue standard operational monitoring within normal maintenance intervals."

        else:
            # TrendDirection.DEGRADING
            prediction_method = PredictionMethod.TREND_LINEAR_EXTRAPOLATION
            confidence = trend.confidence

            # Primary trend-based extrapolation to critical threshold
            health_margin = max(0.0, cur_health - self.HEALTH_FAILURE_THRESHOLD)
            if trend.degradation_rate > 0.0:
                trend_rul = health_margin / trend.degradation_rate
            else:
                trend_rul = self.NOMINAL_MAX_RUL_HOURS

            # Conservative wear bound
            wear_margin = max(0.0, self.WEAR_FAILURE_THRESHOLD - cur_wear)
            wear_rul = wear_margin * self.NOMINAL_MAX_RUL_HOURS

            if wear_rul < trend_rul:
                estimated_rul = wear_rul
                prediction_method = PredictionMethod.COMPOSITE_CONSERVATIVE_BOUND
                limiting_factors.append(f"Cumulative subsystem wear ({cur_wear:.2f}) is more restrictive than health trend")
            else:
                estimated_rul = trend_rul
                limiting_factors.append(
                    f"Health degradation rate ({trend.degradation_rate:.2f} pts/hr) toward failure threshold ({self.HEALTH_FAILURE_THRESHOLD:.0f})"
                )

            explanation = (
                f"Subsystem is degrading at {trend.degradation_rate:.2f} points/hr (current health: {cur_health:.1f}). "
                f"Projected remaining useful flight hours until demonstration caution threshold "
                f"({self.HEALTH_FAILURE_THRESHOLD:.0f}) is {estimated_rul:.1f} hours."
            )
            recommended_action = "Schedule preventative turnaround inspection and review subsystem sensor telemetry."

        # ---------------------------------------------------------------------
        # 2. Phase 5 Anomaly Modifier Integration
        # ---------------------------------------------------------------------
        has_critical = any(a.severity == AnomalySeverity.CRITICAL for a in active_anoms)
        has_high = any(a.severity == AnomalySeverity.HIGH for a in active_anoms)
        has_multi = any(a.anomaly_type.value == "MULTI_SIGNAL_ANOMALY" for a in active_anoms)

        if has_critical:
            # Critical anomaly severely restricts safe remaining operational horizon
            estimated_rul = min(estimated_rul * 0.50, 15.0)
            confidence = max(0.10, confidence - 0.10)
            limiting_factors.append("Active CRITICAL anomaly drastically accelerates degradation risk")
            explanation += " CRITICAL anomaly presence significantly truncates the operational safety horizon."
            recommended_action = "Ground aircraft for immediate engineering inspection prior to next flight."
        elif has_high:
            estimated_rul = min(estimated_rul * 0.75, 80.0)
            confidence = max(0.10, confidence - 0.05)
            limiting_factors.append("Active HIGH anomaly detected on subsystem")
            explanation += " HIGH severity anomaly reduces remaining useful life margin."
            if recommended_action.startswith("Continue"):
                recommended_action = "Prioritize subsystem inspection in next scheduled turnaround."

        if has_multi:
            limiting_factors.append("Multi-signal anomaly correlation confirms compounded physical stress")

        # Guarantee non-negative RUL
        estimated_rul = max(0.0, round(estimated_rul, 2))

        # ---------------------------------------------------------------------
        # 3. Uncertainty Interval Bounds
        # ---------------------------------------------------------------------
        uncertainty_fraction = 0.10 + (1.0 - confidence) * 0.40
        if trend.data_quality != "VALID":
            uncertainty_fraction += 0.15
            limiting_factors.append("Degraded telemetry quality expands prognostic uncertainty bounds")
        if trend.sample_count < 5:
            uncertainty_fraction += 0.10

        uncertainty_margin = estimated_rul * uncertainty_fraction
        lower_bound = max(0.0, round(estimated_rul - uncertainty_margin, 2))
        upper_bound = round(estimated_rul + uncertainty_margin, 2)

        # Bounded cycles estimation (approx 2 flight hours per sortie cycle)
        estimated_cycles = int(max(0, math.floor(estimated_rul * 0.5)))

        return RULPrediction(
            aircraft_id=aircraft_id,
            subsystem=subsystem,
            prediction_timestamp=datetime.now(timezone.utc),
            estimated_rul_hours=estimated_rul,
            estimated_rul_cycles=estimated_cycles,
            lower_bound_hours=lower_bound,
            upper_bound_hours=upper_bound,
            health_score=cur_health,
            wear_index=cur_wear,
            degradation_rate=trend.degradation_rate,
            confidence=round(confidence, 4),
            prediction_method=prediction_method,
            data_quality=trend.data_quality,
            limiting_factors=limiting_factors,
            explanation=explanation,
            recommended_action=recommended_action,
        )


default_rul_predictor = DeterministicRULPredictor()
