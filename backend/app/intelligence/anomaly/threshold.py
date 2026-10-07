"""
SageCommand Air Power System (Aero) — Threshold Anomaly Detector.
Deterministic rule-based detector evaluating flight observations against
propulsion, aerodynamic, control, and data quality boundary thresholds.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import AircraftTwinState, TwinSubsystemType, utc_now
from app.intelligence.models import (
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    AnomalyStatus,
)
from app.intelligence.anomaly.base import BaseAnomalyDetector


class ThresholdAnomalyDetector(BaseAnomalyDetector):
    """Deterministic physical and operational threshold boundary detector."""

    @property
    def detector_name(self) -> str:
        return "THRESHOLD_RULE_DETECTOR"

    def detect(
        self,
        telemetry: NormalizedTelemetry,
        twin_state: Optional[AircraftTwinState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """Evaluates telemetry frame against configured demonstration thresholds."""
        anomalies: List[Anomaly] = []
        t = telemetry.timestamp
        aid = telemetry.aircraft_id
        fid = telemetry.flight_id

        # Confidence modifier based on telemetry data quality
        quality_conf_factor = 1.0 if telemetry.quality_status == QualityStatus.VALID else 0.85

        # -------------------------------------------------------------
        # 1. Propulsion: Turbine / Exhaust Gas Temperature
        # -------------------------------------------------------------
        temp = telemetry.engine_temperature_c
        if temp is not None:
            if temp > 850.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.PROPULSION,
                        atype=AnomalyType.THERMAL_ANOMALY,
                        severity=AnomalySeverity.CRITICAL,
                        confidence=round(0.96 * quality_conf_factor, 4),
                        signal="engine_temperature_c",
                        observed=temp,
                        expected="≤ 780.0 °C (caution), ≤ 850.0 °C (hard limit)",
                        deviation=round(temp - 850.0, 1),
                        desc=f"Critical turbine thermal exceedance: {temp:.1f} °C breached 850.0 °C limit",
                        evidence={"channel": "engine_temperature_c", "observed_c": temp, "limit_c": 850.0},
                    )
                )
            elif temp > 780.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.PROPULSION,
                        atype=AnomalyType.THERMAL_ANOMALY,
                        severity=AnomalySeverity.HIGH,
                        confidence=round(0.90 * quality_conf_factor, 4),
                        signal="engine_temperature_c",
                        observed=temp,
                        expected="≤ 780.0 °C (caution)",
                        deviation=round(temp - 780.0, 1),
                        desc=f"Elevated engine temperature caution: {temp:.1f} °C exceeded 780.0 °C threshold",
                        evidence={"channel": "engine_temperature_c", "observed_c": temp, "caution_c": 780.0},
                    )
                )

        # -------------------------------------------------------------
        # 2. Propulsion: Mechanical Vibration
        # -------------------------------------------------------------
        vib = telemetry.vibration_ips
        if vib is not None:
            if vib > 3.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.PROPULSION,
                        atype=AnomalyType.VIBRATION_ANOMALY,
                        severity=AnomalySeverity.CRITICAL,
                        confidence=round(0.95 * quality_conf_factor, 4),
                        signal="vibration_ips",
                        observed=vib,
                        expected="≤ 0.85 ips (caution), ≤ 3.0 ips (hard limit)",
                        deviation=round(vib - 3.0, 3),
                        desc=f"Severe mechanical vibration exceedance: {vib:.2f} ips breached 3.0 ips limit",
                        evidence={"channel": "vibration_ips", "observed_ips": vib, "limit_ips": 3.0},
                    )
                )
            elif vib > 0.85:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.PROPULSION,
                        atype=AnomalyType.VIBRATION_ANOMALY,
                        severity=AnomalySeverity.HIGH,
                        confidence=round(0.88 * quality_conf_factor, 4),
                        signal="vibration_ips",
                        observed=vib,
                        expected="≤ 0.85 ips (caution)",
                        deviation=round(vib - 0.85, 3),
                        desc=f"Elevated mechanical vibration caution: {vib:.2f} ips exceeded 0.85 ips caution",
                        evidence={"channel": "vibration_ips", "observed_ips": vib, "caution_ips": 0.85},
                    )
                )

        # -------------------------------------------------------------
        # 3. Propulsion: Core Engine Pressure
        # -------------------------------------------------------------
        press = telemetry.engine_pressure_kpa
        if press is not None:
            if press < 150.0 or press > 650.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.PROPULSION,
                        atype=AnomalyType.PRESSURE_ANOMALY,
                        severity=AnomalySeverity.CRITICAL,
                        confidence=round(0.92 * quality_conf_factor, 4),
                        signal="engine_pressure_kpa",
                        observed=press,
                        expected="180.0 - 600.0 kPa",
                        deviation=round(min(press - 150.0, press - 650.0), 1),
                        desc=f"Critical engine core pressure boundary breach: {press:.1f} kPa",
                        evidence={"channel": "engine_pressure_kpa", "observed_kpa": press},
                    )
                )
            elif press < 180.0 or press > 600.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.PROPULSION,
                        atype=AnomalyType.PRESSURE_ANOMALY,
                        severity=AnomalySeverity.HIGH,
                        confidence=round(0.84 * quality_conf_factor, 4),
                        signal="engine_pressure_kpa",
                        observed=press,
                        expected="180.0 - 600.0 kPa (caution band)",
                        deviation=round(min(press - 180.0, press - 600.0), 1),
                        desc=f"Engine core pressure in caution region: {press:.1f} kPa",
                        evidence={"channel": "engine_pressure_kpa", "observed_kpa": press},
                    )
                )

        # -------------------------------------------------------------
        # 4. Structure: Normal Acceleration / G-Load
        # -------------------------------------------------------------
        g = telemetry.g_load
        if g is not None:
            if g > 8.0 or g < -3.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.STRUCTURE,
                        atype=AnomalyType.G_LOAD_ANOMALY,
                        severity=AnomalySeverity.CRITICAL,
                        confidence=round(0.96 * quality_conf_factor, 4),
                        signal="g_load",
                        observed=g,
                        expected="-2.5 G to +8.0 G",
                        deviation=round(g - 8.0 if g > 8.0 else g - (-3.0), 2),
                        desc=f"Critical airframe structural G-load breach: {g:.1f} G",
                        evidence={"channel": "g_load", "observed_g": g, "hard_limit": 8.0 if g > 0 else -3.0},
                    )
                )
            elif g > 7.5 or g < -2.0:
                anomalies.append(
                    self._create_anomaly(
                        aid=aid,
                        fid=fid,
                        timestamp=t,
                        subsystem=TwinSubsystemType.STRUCTURE,
                        atype=AnomalyType.G_LOAD_ANOMALY,
                        severity=AnomalySeverity.HIGH,
                        confidence=round(0.88 * quality_conf_factor, 4),
                        signal="g_load",
                        observed=g,
                        expected="-2.0 G to +7.5 G (caution band)",
                        deviation=round(g - 7.5 if g > 7.5 else g - (-2.0), 2),
                        desc=f"Elevated aerodynamic G-load caution: {g:.1f} G",
                        evidence={"channel": "g_load", "observed_g": g, "caution_limit": 7.5 if g > 0 else -2.0},
                    )
                )

        # -------------------------------------------------------------
        # 5. Flight Controls: Control Surface Deflection
        # -------------------------------------------------------------
        cs = telemetry.control_surface_angle_deg
        if cs is not None and abs(cs) > 30.0:
            anomalies.append(
                self._create_anomaly(
                    aid=aid,
                    fid=fid,
                    timestamp=t,
                    subsystem=TwinSubsystemType.FLIGHT_CONTROLS,
                    atype=AnomalyType.CONTROL_SURFACE_ANOMALY,
                    severity=AnomalySeverity.CRITICAL,
                    confidence=round(0.90 * quality_conf_factor, 4),
                    signal="control_surface_angle_deg",
                    observed=cs,
                    expected="-30.0° to +30.0°",
                    deviation=round(abs(cs) - 30.0, 1),
                    desc=f"Abnormal control surface deflection limit exceeded: {cs:.1f}°",
                    evidence={"channel": "control_surface_angle_deg", "observed_deg": cs, "limit_deg": 30.0},
                )
            )
        elif cs is not None and abs(cs) > 20.0:
            anomalies.append(
                self._create_anomaly(
                    aid=aid,
                    fid=fid,
                    timestamp=t,
                    subsystem=TwinSubsystemType.FLIGHT_CONTROLS,
                    atype=AnomalyType.CONTROL_SURFACE_ANOMALY,
                    severity=AnomalySeverity.HIGH,
                    confidence=round(0.85 * quality_conf_factor, 4),
                    signal="control_surface_angle_deg",
                    observed=cs,
                    expected="-20.0° to +20.0°",
                    deviation=round(abs(cs) - 20.0, 1),
                    desc=f"Elevated control surface deflection caution: {cs:.1f}°",
                    evidence={"channel": "control_surface_angle_deg", "observed_deg": cs, "caution_deg": 20.0},
                )
            )

        # -------------------------------------------------------------
        # 6. Avionics: Telemetry Stream Quality Degradation
        # -------------------------------------------------------------
        if telemetry.quality_status == QualityStatus.DEGRADED:
            anomalies.append(
                self._create_anomaly(
                    aid=aid,
                    fid=fid,
                    timestamp=t,
                    subsystem=TwinSubsystemType.AVIONICS,
                    atype=AnomalyType.TELEMETRY_QUALITY_ANOMALY,
                    severity=AnomalySeverity.MEDIUM,
                    confidence=0.85,
                    signal="telemetry_quality",
                    observed=None,
                    expected="VALID stream fidelity",
                    deviation=None,
                    desc="Degraded telemetry feed detected: sparse or jittered channel inputs",
                    evidence={"channel": "telemetry_quality", "quality_status": "DEGRADED"},
                )
            )

        return anomalies

    def _create_anomaly(
        self,
        aid: str,
        fid: Optional[str],
        timestamp: datetime,
        subsystem: TwinSubsystemType,
        atype: AnomalyType,
        severity: AnomalySeverity,
        confidence: float,
        signal: str,
        observed: Optional[float],
        expected: str,
        deviation: Optional[float],
        desc: str,
        evidence: Dict[str, Any],
    ) -> Anomaly:
        """Helper to construct strongly typed Anomaly record."""
        anom_id = f"anom_{aid}_{signal}_{int(timestamp.timestamp() * 1000)}"
        return Anomaly(
            anomaly_id=anom_id,
            aircraft_id=aid,
            flight_id=fid,
            timestamp=timestamp,
            subsystem=subsystem,
            anomaly_type=atype,
            severity=severity,
            status=AnomalyStatus.NEW,
            confidence=confidence,
            detector=self.detector_name,
            signal=signal,
            observed_value=observed,
            expected_range=expected,
            deviation=deviation,
            description=desc,
            evidence=evidence,
            occurrence_count=1,
            first_detected_at=timestamp,
            last_detected_at=timestamp,
        )
