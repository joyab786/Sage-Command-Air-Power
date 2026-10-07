"""
SageCommand Air Power System (Aero) — Statistical Anomaly Detector.
Computes deterministic rolling mean, standard deviation, and z-score bounds
scoped by aircraft asset and signal without external ML dependencies.
"""

import math
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from collections import defaultdict, deque
from app.telemetry.models import NormalizedTelemetry, QualityStatus
from app.digital_twin.models import AircraftTwinState, TwinSubsystemType
from app.intelligence.models import (
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    AnomalyStatus,
)
from app.intelligence.anomaly.base import BaseAnomalyDetector


class RollingBaseline:
    """Rolling window accumulator calculating running mean and sample standard deviation."""

    def __init__(self, max_samples: int = 50):
        self.max_samples = max_samples
        self.values: deque[float] = deque(maxlen=max_samples)

    def add(self, val: float) -> None:
        if not math.isnan(val) and not math.isinf(val):
            self.values.append(val)

    @property
    def count(self) -> int:
        return len(self.values)

    def stats(self) -> Tuple[float, float]:
        """Returns (mean, std). If count < 2 or variance is 0, std is 0.0."""
        n = len(self.values)
        if n == 0:
            return 0.0, 0.0
        mean = sum(self.values) / n
        if n < 2:
            return mean, 0.0
        var = sum((x - mean) ** 2 for x in self.values) / (n - 1)
        return mean, math.sqrt(max(0.0, var))


class StatisticalAnomalyDetector(BaseAnomalyDetector):
    """
    Evaluates telemetry against a rolling z-score baseline.
    Safe against zero-variance divisions and insufficient sample sizes.
    """

    def __init__(
        self,
        min_samples: int = 5,
        window_size: int = 30,
        z_threshold: float = 3.0,
    ):
        self.min_samples = min_samples
        self.window_size = window_size
        self.z_threshold = z_threshold
        # In-memory rolling history cache keyed by (aircraft_id, signal)
        self._history: Dict[Tuple[str, str], RollingBaseline] = defaultdict(
            lambda: RollingBaseline(max_samples=self.window_size)
        )

    @property
    def detector_name(self) -> str:
        return "STATISTICAL_ZSCORE_DETECTOR"

    def detect(
        self,
        telemetry: NormalizedTelemetry,
        twin_state: Optional[AircraftTwinState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """Evaluates telemetry values against rolling baseline."""
        anomalies: List[Anomaly] = []
        aid = telemetry.aircraft_id
        fid = telemetry.flight_id
        t = telemetry.timestamp

        signals_to_check = [
            ("engine_temperature_c", telemetry.engine_temperature_c, TwinSubsystemType.PROPULSION, AnomalyType.THERMAL_ANOMALY),
            ("vibration_ips", telemetry.vibration_ips, TwinSubsystemType.PROPULSION, AnomalyType.VIBRATION_ANOMALY),
            ("engine_pressure_kpa", telemetry.engine_pressure_kpa, TwinSubsystemType.PROPULSION, AnomalyType.PRESSURE_ANOMALY),
            ("airspeed_mps", telemetry.airspeed_mps, TwinSubsystemType.FLIGHT_CONTROLS, AnomalyType.FLIGHT_ENVELOPE_ANOMALY),
        ]

        for signal_name, val, subsystem, anom_type in signals_to_check:
            if val is None or math.isnan(val) or math.isinf(val):
                continue

            baseline = self._history[(aid, signal_name)]
            mean, std = baseline.stats()

            # Only evaluate z-score if we have gathered sufficient observations
            if baseline.count >= self.min_samples:
                # Safe against near-zero variance
                if std > 1e-4:
                    z_score = (val - mean) / std

                    if abs(z_score) >= self.z_threshold:
                        # Determine severity from degree of statistical deviation
                        severity = AnomalySeverity.CRITICAL if abs(z_score) >= 4.5 else AnomalySeverity.HIGH
                        conf = min(0.95, round(0.70 + (0.01 * baseline.count), 4))

                        anom_id = f"anom_stat_{aid}_{signal_name}_{int(t.timestamp() * 1000)}"
                        anomalies.append(
                            Anomaly(
                                anomaly_id=anom_id,
                                aircraft_id=aid,
                                flight_id=fid,
                                timestamp=t,
                                subsystem=subsystem,
                                anomaly_type=anom_type,
                                severity=severity,
                                status=AnomalyStatus.NEW,
                                confidence=conf,
                                detector=self.detector_name,
                                signal=signal_name,
                                observed_value=round(val, 3),
                                expected_range=f"μ={mean:.1f} ± {self.z_threshold:.1f}σ (σ={std:.2f})",
                                deviation=round(z_score, 2),
                                description=f"Statistical outlier on '{signal_name}': z={z_score:.2f} (|z| ≥ {self.z_threshold:.1f})",
                                evidence={
                                    "z_score": round(z_score, 2),
                                    "rolling_mean": round(mean, 2),
                                    "rolling_std": round(std, 2),
                                    "sample_count": baseline.count,
                                },
                                occurrence_count=1,
                                first_detected_at=t,
                                last_detected_at=t,
                            )
                        )

            # Accumulate this reading into rolling history baseline
            baseline.add(val)

        return anomalies

    def seed_baseline(self, aircraft_id: str, signal: str, samples: List[float]) -> None:
        """Helper to pre-seed rolling baseline for testing and warm starts."""
        baseline = self._history[(aircraft_id, signal)]
        for s in samples:
            baseline.add(s)

    def clear_baseline(self, aircraft_id: Optional[str] = None) -> None:
        """Purges cached rolling baselines."""
        if aircraft_id:
            keys_to_del = [k for k in self._history if k[0] == aircraft_id]
            for k in keys_to_del:
                del self._history[k]
        else:
            self._history.clear()
