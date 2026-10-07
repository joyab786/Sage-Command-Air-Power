"""
SageCommand Air Power System (Aero) — Telemetry Quality Assessor.
Deterministically inspects telemetry frames for signal corruption,
unphysical quantities, mathematical anomalies, and completeness.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.telemetry.models import (
    TelemetryInput,
    NormalizedTelemetry,
    QualityStatus,
    QualityAssessmentResult,
)


class QualityEvaluator:
    """
    Deterministic quality evaluator classifying observations into
    VALID, DEGRADED, or INVALID with explicit causal reasons.
    """

    MAX_FUTURE_DRIFT_SECONDS = 3600  # 1 hour allowed for clock drift
    MAX_HISTORICAL_AGE_DAYS = 3650   # 10 years historical telemetry allowed

    @classmethod
    def evaluate_input(cls, obs: TelemetryInput) -> QualityAssessmentResult:
        """
        Performs pre-normalization structural and sanity inspection on incoming input.
        """
        reasons: List[str] = []
        warnings: List[str] = []
        metrics_checked = 0

        # 1. Identity validation
        if not obs.aircraft_id or not obs.aircraft_id.strip():
            reasons.append("Missing or empty aircraft_id")
        metrics_checked += 1

        # 2. Timestamp validation
        if obs.timestamp is not None:
            now = datetime.now(timezone.utc)
            ts = obs.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if ts > (now + timedelta(seconds=cls.MAX_FUTURE_DRIFT_SECONDS)):
                reasons.append(f"Timestamp is in the future beyond allowed drift: {ts.isoformat()}")
            elif ts < (now - timedelta(days=cls.MAX_HISTORICAL_AGE_DAYS)):
                warnings.append(f"Telemetry timestamp is older than 10 years: {ts.isoformat()}")
        metrics_checked += 1

        # 3. Numeric validity (NaN, Infinity, negative bounds)
        numeric_channels = [
            ("altitude", obs.altitude, False),      # altitude can technically be below sea level (Death Valley / Caspian)
            ("airspeed", obs.airspeed, True),        # airspeed cannot be negative
            ("mach", obs.mach, True),                # mach cannot be negative
            ("g_load", obs.g_load, False),           # g_load can be negative (pushing nose down)
            ("fuel_flow", obs.fuel_flow, True),      # fuel flow cannot be negative
            ("engine_temperature", obs.engine_temperature, False), # temperature can be sub-zero C
            ("engine_pressure", obs.engine_pressure, True),        # pressure cannot be negative absolute/gauge
            ("vibration", obs.vibration, True),      # vibration amplitude cannot be negative
            ("control_surface_angle", obs.control_surface_angle, False),
        ]

        populated_channels = 0
        for name, val, disallow_negative in numeric_channels:
            if val is not None:
                populated_channels += 1
                metrics_checked += 1

                if math.isnan(val) or math.isinf(val):
                    reasons.append(f"Channel '{name}' contains non-finite value (NaN or Inf)")
                elif disallow_negative and val < 0.0:
                    reasons.append(f"Channel '{name}' has impossible negative value: {val}")

        # 4. Completeness check
        if populated_channels == 0:
            reasons.append("Observation contains zero telemetry channel data")
        elif populated_channels < 3:
            warnings.append(f"Sparse observation: only {populated_channels} channels supplied")

        # 5. Determine overall quality status
        if reasons:
            status = QualityStatus.INVALID
        elif warnings:
            status = QualityStatus.DEGRADED
        else:
            status = QualityStatus.VALID

        return QualityAssessmentResult(
            status=status,
            reasons=reasons,
            warnings=warnings,
            metrics_evaluated=metrics_checked,
        )

    @classmethod
    def evaluate_normalized(cls, norm: NormalizedTelemetry) -> QualityAssessmentResult:
        """
        Evaluates normalized telemetry record after unit conversion.
        """
        reasons: List[str] = []
        warnings: List[str] = []
        metrics_checked = 0

        # Physical limit checks in normalized SI units
        if norm.airspeed_mps is not None:
            metrics_checked += 1
            if norm.airspeed_mps < 0.0:
                reasons.append(f"Normalized airspeed cannot be negative: {norm.airspeed_mps} m/s")

        if norm.mach is not None:
            metrics_checked += 1
            if norm.mach < 0.0:
                reasons.append(f"Normalized Mach cannot be negative: {norm.mach}")

        if norm.engine_temperature_c is not None:
            metrics_checked += 1
            # Absolute zero in Celsius is -273.15
            if norm.engine_temperature_c < -273.15:
                reasons.append(f"Engine temperature below absolute zero: {norm.engine_temperature_c} °C")

        if norm.engine_pressure_kpa is not None:
            metrics_checked += 1
            if norm.engine_pressure_kpa < 0.0:
                reasons.append(f"Engine pressure cannot be negative: {norm.engine_pressure_kpa} kPa")

        if norm.vibration_ips is not None:
            metrics_checked += 1
            if norm.vibration_ips < 0.0:
                reasons.append(f"Vibration amplitude cannot be negative: {norm.vibration_ips} ips")

        status = QualityStatus.INVALID if reasons else (QualityStatus.DEGRADED if warnings else QualityStatus.VALID)

        return QualityAssessmentResult(
            status=status,
            reasons=reasons,
            warnings=warnings,
            metrics_evaluated=metrics_checked,
        )
