"""
SageCommand Air Power System (Aero) — Root-Cause Diagnosis Engine.
Synthesizes detected anomalies, telemetry quality, and digital twin health
into explainable subsystem diagnoses with transparent probable causes.
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timezone
from app.telemetry.models import NormalizedTelemetry, QualityStatus
from app.digital_twin.models import (
    AircraftTwinState,
    TwinSubsystemType,
    TwinHealthState,
    utc_now,
)
from app.intelligence.models import (
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    Diagnosis,
)


class RootCauseDiagnosisEngine:
    """
    Deterministic diagnostic reasoning engine.
    Applies explainable probable-cause inference rules and multi-signal fusion.
    """

    def diagnose(
        self,
        active_anomalies: Optional[List[Anomaly]] = None,
        twin_state: Optional[AircraftTwinState] = None,
        telemetry: Optional[NormalizedTelemetry] = None,
        aircraft_id: Optional[str] = None,
        now: Optional[datetime] = None,
        anomalies: Optional[List[Anomaly]] = None,
    ) -> Diagnosis:
        """
        Synthesizes active anomalies and digital twin health into an explainable Diagnosis.
        Supports both active_anomalies and anomalies kwargs.
        """
        candidate_anomalies = active_anomalies if active_anomalies is not None else (anomalies or [])
        eval_time = now or utc_now()
        aid = aircraft_id or (candidate_anomalies[0].aircraft_id if candidate_anomalies else "UNKNOWN")
        diag_id = f"diag_{aid}_{int(eval_time.timestamp() * 1000)}"

        if not candidate_anomalies:
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.PROPULSION,
                probable_causes=[
                    "Nominal operational state: all observed telemetry channels reside within standard demonstration limits."
                ],
                supporting_anomalies=[],
                confidence=1.0,
                explanation="Continuous telemetry and digital twin state evaluation indicates healthy subsystem operation with no active anomalies.",
                signals_involved=[],
            )

        # Collect anomaly signals and types
        signals = [a.signal for a in candidate_anomalies]
        anom_ids = [a.anomaly_id for a in candidate_anomalies]
        anom_types = set(a.anomaly_type for a in candidate_anomalies)

        has_thermal = any(a.anomaly_type == AnomalyType.THERMAL_ANOMALY for a in candidate_anomalies)
        has_vibration = any(a.anomaly_type == AnomalyType.VIBRATION_ANOMALY for a in candidate_anomalies)
        has_pressure = any(a.anomaly_type == AnomalyType.PRESSURE_ANOMALY for a in candidate_anomalies)
        has_g_load = any(a.anomaly_type == AnomalyType.G_LOAD_ANOMALY for a in candidate_anomalies)
        has_control = any(a.anomaly_type == AnomalyType.CONTROL_SURFACE_ANOMALY for a in candidate_anomalies)
        has_quality = any(a.anomaly_type == AnomalyType.TELEMETRY_QUALITY_ANOMALY for a in candidate_anomalies)

        is_degraded = (
            (telemetry is not None and telemetry.quality_status == QualityStatus.DEGRADED)
            or has_quality
        )
        quality_penalty = 0.15 if is_degraded else 0.0
        degraded_note = " Telemetry quality was DEGRADED during observation; sensor fidelity exhibits reduced confidence." if is_degraded else ""

        # -------------------------------------------------------------
        # Multi-Signal Correlation Rule: Thermal + Vibration (+ Pressure)
        # -------------------------------------------------------------
        if has_thermal and has_vibration:
            extra_msg = " and pressure deviation" if has_pressure else ""
            causes = [
                f"Multi-signal compound propulsion anomaly: concurrent turbine thermal elevation and mechanical vibration{extra_msg}.",
                "Probable turbine blade thermal fatigue with associated rotor dynamic unbalance. Requires urgent borescope inspection.",
                "Possible combustor hot streak inducing localized thermal gradient and bearing housing stress.",
            ]
            base_conf = 0.96 if has_pressure else 0.93
            conf = max(0.40, round(base_conf - quality_penalty, 4))
            explanation = (
                f"High-confidence compound anomaly detected on PROPULSION subsystem. "
                f"Concurrent abnormal signals observed: turbine temperature, mechanical vibration{extra_msg}. "
                f"Multi-signal correlation significantly elevates diagnostic confidence over individual single-signal observations."
                + degraded_note
            )
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.PROPULSION,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation=explanation,
                signals_involved=signals,
            )

        # -------------------------------------------------------------
        # Thermal Anomaly Diagnosis
        # -------------------------------------------------------------
        if has_thermal:
            causes = [
                "Probable turbine nozzle guide vane erosion or cooling duct blockage.",
                "Possible combustor liner degradation or bleed valve failure.",
                "Requires ground visual and thermal imaging inspection prior to next sortie.",
            ]
            conf = max(0.40, round(0.90 - quality_penalty, 4))
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.PROPULSION,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation="Turbine/exhaust gas temperature exceeded configured demonstration operational bounds. Evidence indicates possible thermal distress in hot gas path." + degraded_note,
                signals_involved=signals,
            )

        # -------------------------------------------------------------
        # Vibration Anomaly Diagnosis
        # -------------------------------------------------------------
        if has_vibration:
            causes = [
                "Probable high-pressure turbine/compressor bearing race mechanical fatigue.",
                "Possible rotor blade leading-edge foreign object damage (FOD) or imbalance.",
                "Requires spectral vibration analysis and chip detector inspection.",
            ]
            conf = max(0.40, round(0.90 - quality_penalty, 4))
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.PROPULSION,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation="Mechanical vibration amplitude exceeded caution/limit thresholds, indicating possible rotational assembly imbalance or bearing wear." + degraded_note,
                signals_involved=signals,
            )

        # -------------------------------------------------------------
        # Engine Pressure Anomaly Diagnosis
        # -------------------------------------------------------------
        if has_pressure:
            causes = [
                "Probable compressor stall margin degradation or variable stator vane mistiming.",
                "Possible engine fuel metering unit (FMU) pressure regulator oscillation.",
                "Requires engine control unit (FADEC) diagnostic log readout.",
            ]
            conf = max(0.40, round(0.86 - quality_penalty, 4))
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.PROPULSION,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation="Engine core pressure deviated from nominal operational envelope, indicating possible compressor or fuel regulation instability." + degraded_note,
                signals_involved=signals,
            )

        # -------------------------------------------------------------
        # Structural G-Load Anomaly Diagnosis
        # -------------------------------------------------------------
        if has_g_load:
            causes = [
                "Aerodynamic loading breached operational G-envelope limits during aggressive maneuvering.",
                "Probable airframe wing root, bulkhead, and spar structural fatigue stress.",
                "Requires airframe non-destructive testing (NDT) and structural strain verification.",
            ]
            conf = max(0.40, round(0.92 - quality_penalty, 4))
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.STRUCTURE,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation="Normal acceleration exceeded structural caution/hard limits, indicating high dynamic load on the airframe structure." + degraded_note,
                signals_involved=signals,
            )

        # -------------------------------------------------------------
        # Flight Controls Anomaly Diagnosis
        # -------------------------------------------------------------
        if has_control:
            causes = [
                "Probable flight control surface actuator servo valve restriction.",
                "Possible primary flight control computer bus latency or feedback transducer drift.",
                "Requires pre-flight built-in test (BIT) actuation sweep.",
            ]
            conf = max(0.40, round(0.84 - quality_penalty, 4))
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.FLIGHT_CONTROLS,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation="Control surface deflection angle exceeded nominal limits, indicating potential control actuator or feedback anomaly." + degraded_note,
                signals_involved=signals,
            )

        # -------------------------------------------------------------
        # Data Quality Anomaly Diagnosis
        # -------------------------------------------------------------
        if has_quality:
            causes = [
                "Telemetry stream packet dropped frames or channel omission.",
                "Possible avionics interface bus jitter or edge sensor transceiver degradation.",
            ]
            conf = max(0.40, round(0.80 - quality_penalty, 4))
            return Diagnosis(
                diagnosis_id=diag_id,
                aircraft_id=aid,
                timestamp=eval_time,
                primary_subsystem=TwinSubsystemType.AVIONICS,
                probable_causes=causes,
                supporting_anomalies=anom_ids,
                confidence=conf,
                explanation="Degraded telemetry signal fidelity detected. Sensor values may exhibit reduced confidence." + degraded_note,
                signals_involved=signals,
            )

        # Fallback generic diagnosis
        subsys = candidate_anomalies[0].subsystem if candidate_anomalies else TwinSubsystemType.PROPULSION
        conf = max(0.40, round(0.75 - quality_penalty, 4))
        return Diagnosis(
            diagnosis_id=diag_id,
            aircraft_id=aid,
            timestamp=eval_time,
            primary_subsystem=subsys,
            probable_causes=["Unclassified operational parameter deviation requiring engineering review."],
            supporting_anomalies=anom_ids,
            confidence=conf,
            explanation=f"Detected {len(candidate_anomalies)} parameter anomalies on {subsys.value}." + degraded_note,
            signals_involved=signals,
        )


default_diagnosis_engine = RootCauseDiagnosisEngine()
