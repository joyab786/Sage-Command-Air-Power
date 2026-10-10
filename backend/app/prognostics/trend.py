"""
SageCommand Air Power System (Aero) — Degradation Trend Engine.
Performs deterministic Ordinary Least Squares (OLS) linear regression over
chronological health observations to determine degradation slope, rate, direction, and fit quality.
"""

from typing import List, Optional
import math
from app.prognostics.models import (
    ComponentHealthSnapshot,
    DegradationTrend,
    TrendDirection,
    TwinSubsystemType,
)


class DegradationTrendEstimator:
    """
    Deterministic trend estimator evaluating component/subsystem degradation trajectories.
    Enforces minimum data requirements and protects against spurious false prognostics.
    """

    MIN_SAMPLES: int = 3
    STABLE_SLOPE_THRESHOLD: float = 0.10  # Health points per hour threshold for stability (<= 1 pt / 10 hrs)

    @classmethod
    def estimate_trend(
        cls,
        snapshots: List[ComponentHealthSnapshot],
        subsystem: Optional[TwinSubsystemType] = None,
    ) -> DegradationTrend:
        """
        Estimates degradation trend across a chronological sequence of health snapshots.
        """
        target_subsystem = subsystem or (snapshots[0].subsystem if snapshots else TwinSubsystemType.PROPULSION)
        aircraft_id = snapshots[0].aircraft_id if snapshots else "UNKNOWN"

        # 1. Guard against insufficient data
        if not snapshots or len(snapshots) < cls.MIN_SAMPLES:
            cur_health = snapshots[-1].health_score if snapshots else 100.0
            init_health = snapshots[0].health_score if snapshots else 100.0
            return DegradationTrend(
                aircraft_id=aircraft_id,
                subsystem=target_subsystem,
                observation_start=snapshots[0].timestamp if snapshots else None,
                observation_end=snapshots[-1].timestamp if snapshots else None,
                sample_count=len(snapshots),
                current_health=cur_health,
                initial_health=init_health,
                degradation_rate=0.0,
                slope=0.0,
                trend_direction=TrendDirection.INSUFFICIENT_DATA,
                fit_quality=None,
                confidence=0.20,
                data_quality="SPARSE",
                explanation=(
                    f"Insufficient historical observations ({len(snapshots)} samples). "
                    f"At least {cls.MIN_SAMPLES} chronological observations are required to estimate a degradation trend."
                ),
            )

        # 2. Extract chronological time coordinates
        t0 = snapshots[0].timestamp
        time_hours: List[float] = []
        for s in snapshots:
            dt_sec = (s.timestamp - t0).total_seconds()
            time_hours.append(dt_sec / 3600.0)

        # Check if timestamps are degenerate (e.g., sub-second synthetic frames)
        time_span = time_hours[-1] - time_hours[0]
        if time_span < 0.01:
            # Use discrete demonstration steps (each observation = 1 hour step)
            time_hours = [float(i) for i in range(len(snapshots))]
            effective_time_basis = "discrete observation steps"
        else:
            effective_time_basis = "elapsed flight hours"

        health_scores = [s.health_score for s in snapshots]
        n = len(snapshots)

        # 3. Ordinary Least Squares (OLS) Regression
        mean_t = sum(time_hours) / n
        mean_y = sum(health_scores) / n

        ss_tt = sum((t - mean_t) ** 2 for t in time_hours)
        ss_ty = sum((time_hours[i] - mean_t) * (health_scores[i] - mean_y) for i in range(n))
        ss_yy = sum((y - mean_y) ** 2 for y in health_scores)

        if ss_tt < 1e-9:
            slope = 0.0
            intercept = mean_y
            ss_res = ss_yy
        else:
            slope = ss_ty / ss_tt
            intercept = mean_y - slope * mean_t
            ss_res = sum(
                (health_scores[i] - (slope * time_hours[i] + intercept)) ** 2
                for i in range(n)
            )

        # 4. Trend direction and degradation rate
        slope = round(slope, 4)
        if slope < -cls.STABLE_SLOPE_THRESHOLD:
            trend_direction = TrendDirection.DEGRADING
            degradation_rate = round(abs(slope), 4)
            if ss_yy < 1e-6:
                fit_quality = 1.0
            else:
                raw_r2 = 1.0 - (ss_res / ss_yy)
                fit_quality = round(max(0.0, min(1.0, raw_r2)), 4)
            fit_factor = 0.5 + 0.5 * (fit_quality if fit_quality is not None else 0.8)

        elif slope > cls.STABLE_SLOPE_THRESHOLD:
            trend_direction = TrendDirection.IMPROVING
            degradation_rate = 0.0
            if ss_yy < 1e-6:
                fit_quality = 1.0
            else:
                raw_r2 = 1.0 - (ss_res / ss_yy)
                fit_quality = round(max(0.0, min(1.0, raw_r2)), 4)
            fit_factor = 0.5 + 0.5 * (fit_quality if fit_quality is not None else 0.8)

        else:
            trend_direction = TrendDirection.STABLE
            degradation_rate = 0.0
            # For stable series, fit quality measures consistency/tightness around nominal mean
            variance = ss_yy / n
            fit_quality = round(max(0.0, min(1.0, 1.0 - (math.sqrt(variance) / 5.0))), 4)
            fit_factor = 0.85 + 0.15 * fit_quality

        # 5. Data quality and confidence assessment
        degraded_count = sum(1 for s in snapshots if s.data_quality != "VALID")
        overall_dq = "DEGRADED" if (degraded_count / n) > 0.3 else "VALID"

        sample_factor = min(1.0, 0.4 + 0.1 * min(n, 6))
        raw_conf = sample_factor * fit_factor

        if overall_dq == "DEGRADED":
            raw_conf -= 0.20

        confidence = round(max(0.10, min(1.0, raw_conf)), 4)

        # 7. Human-readable explanation
        init_health = snapshots[0].health_score
        cur_health = snapshots[-1].health_score

        if trend_direction == TrendDirection.DEGRADING:
            expl = (
                f"Health degraded from {init_health:.1f} to {cur_health:.1f} across {n} observations "
                f"({effective_time_basis}). Degradation rate is estimated at {degradation_rate:.2f} points/hr "
                f"(slope: {slope:.3f}, R²: {fit_quality:.2f})."
            )
        elif trend_direction == TrendDirection.IMPROVING:
            expl = (
                f"Health improved from {init_health:.1f} to {cur_health:.1f} across {n} observations "
                f"(slope: +{abs(slope):.3f} pts/hr). Subsystem condition is recovering."
            )
        else:
            expl = (
                f"Health remained stable at approximately {cur_health:.1f} across {n} observations "
                f"(slope: {slope:.3f} pts/hr). Subsystem operating within nominal baseline."
            )

        if overall_dq == "DEGRADED":
            expl += " Note: Confidence reduced due to degraded telemetry observations in history."

        return DegradationTrend(
            aircraft_id=aircraft_id,
            subsystem=target_subsystem,
            observation_start=snapshots[0].timestamp,
            observation_end=snapshots[-1].timestamp,
            sample_count=n,
            current_health=cur_health,
            initial_health=init_health,
            degradation_rate=degradation_rate,
            slope=slope,
            trend_direction=trend_direction,
            fit_quality=fit_quality,
            confidence=confidence,
            data_quality=overall_dq,
            explanation=expl,
        )
