"""
SageCommand Air Power System (Aero) — Aircraft Health Estimator.
Provides deterministic, explainable rule-based health scoring for airframes
and conceptual subsystems based on normalized telemetry and operational bounds.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.digital_twin.models import (
    TwinHealthState,
    TwinSubsystemType,
    SubsystemState,
    HealthReason,
    AircraftTwinState,
    utc_now,
)


class AircraftHealthEstimator:
    """
    Deterministic rule-based health estimator for the SIH Decision-Support Prototype.
    Computes explainable scores (0-100) and structured reasons for degradation.
    """

    @classmethod
    def score_to_health_state(cls, score: float) -> TwinHealthState:
        """Maps a 0-100 score to a categorical health classification."""
        if score >= 90.0:
            return TwinHealthState.HEALTHY
        elif score >= 75.0:
            return TwinHealthState.DEGRADED
        elif score >= 50.0:
            return TwinHealthState.WARNING
        elif score >= 25.0:
            return TwinHealthState.CRITICAL
        else:
            return TwinHealthState.FAILED

    @classmethod
    def evaluate_health(
        cls,
        telemetry: NormalizedTelemetry,
        previous_twin: Optional[AircraftTwinState] = None,
        flight_hours: float = 0.0,
        flight_cycles: int = 0,
        now: Optional[datetime] = None,
    ) -> Tuple[float, TwinHealthState, List[HealthReason], Dict[str, SubsystemState], List[str]]:
        """
        Evaluates composite airframe health and individual conceptual subsystem states.

        Returns:
            (composite_score, composite_state, health_reasons, subsystem_states, active_warnings)
        """
        eval_time = now or utc_now()
        reasons: List[HealthReason] = []
        warnings: List[str] = []

        propulsion_penalties: List[HealthReason] = []
        structure_penalties: List[HealthReason] = []
        flight_control_penalties: List[HealthReason] = []
        avionics_penalties: List[HealthReason] = []
        fuel_penalties: List[HealthReason] = []

        # 1. Thermal Condition (Propulsion / Turbine)
        temp = telemetry.engine_temperature_c
        if temp is not None:
            if temp > 1050.0:
                p = HealthReason(
                    signal="engine_temperature",
                    observed=temp,
                    contribution=-35.0,
                    reason=f"Critical turbine thermal exceedance ({temp:.1f}°C > 1050.0°C limit)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)
                warnings.append(f"Turbine thermal exceedance: {temp:.1f}°C")
            elif temp > 950.0:
                p = HealthReason(
                    signal="engine_temperature",
                    observed=temp,
                    contribution=-20.0,
                    reason=f"Elevated engine temperature caution ({temp:.1f}°C > 950.0°C caution)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)
                warnings.append(f"Engine temperature caution: {temp:.1f}°C")
            elif temp > 900.0:
                p = HealthReason(
                    signal="engine_temperature",
                    observed=temp,
                    contribution=-8.0,
                    reason=f"Engine temperature elevated ({temp:.1f}°C > 900.0°C nominal)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)

        # 2. Vibration Condition (Propulsion / Mechanical)
        vib = telemetry.vibration_ips
        if vib is not None:
            if vib > 1.25:
                p = HealthReason(
                    signal="vibration",
                    observed=vib,
                    contribution=-35.0,
                    reason=f"Severe mechanical vibration exceedance ({vib:.2f} ips > 1.25 ips limit)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)
                warnings.append(f"Mechanical vibration spike: {vib:.2f} ips")
            elif vib > 0.85:
                p = HealthReason(
                    signal="vibration",
                    observed=vib,
                    contribution=-20.0,
                    reason=f"Elevated mechanical vibration caution ({vib:.2f} ips > 0.85 ips caution)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)
                warnings.append(f"Mechanical vibration elevated: {vib:.2f} ips")
            elif vib > 0.65:
                p = HealthReason(
                    signal="vibration",
                    observed=vib,
                    contribution=-8.0,
                    reason=f"Mechanical vibration above nominal ({vib:.2f} ips > 0.65 ips)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)

        # 3. Engine Core Pressure Condition
        press = telemetry.engine_pressure_kpa
        if press is not None:
            if press < 150.0 or press > 2100.0:
                p = HealthReason(
                    signal="engine_pressure",
                    observed=press,
                    contribution=-30.0,
                    reason=f"Critical engine pressure anomaly ({press:.1f} kPa outside 150-2100 kPa limit)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)
                warnings.append(f"Engine pressure anomaly: {press:.1f} kPa")
            elif press < 200.0 or press > 1800.0:
                p = HealthReason(
                    signal="engine_pressure",
                    observed=press,
                    contribution=-15.0,
                    reason=f"Engine pressure in caution region ({press:.1f} kPa outside 200-1800 kPa caution)",
                )
                reasons.append(p)
                propulsion_penalties.append(p)

        # 4. Normal Acceleration / G-Load Condition (Structure)
        g = telemetry.g_load
        if g is not None:
            if g > 9.0 or g < -3.0:
                p = HealthReason(
                    signal="g_load",
                    observed=g,
                    contribution=-35.0,
                    reason=f"Critical structural G-load exceedance ({g:.1f} G outside -3.0G to 9.0G limit)",
                )
                reasons.append(p)
                structure_penalties.append(p)
                warnings.append(f"High-G exceedance: {g:.1f} G")
            elif g > 7.5 or g < -2.0:
                p = HealthReason(
                    signal="g_load",
                    observed=g,
                    contribution=-18.0,
                    reason=f"Elevated aerodynamic G-load caution ({g:.1f} G outside -2.0G to 7.5G caution)",
                )
                reasons.append(p)
                structure_penalties.append(p)
                warnings.append(f"G-load caution: {g:.1f} G")

        # 5. Envelope Status Assessment
        if telemetry.envelope_status == EnvelopeStatus.EXCEEDED:
            # Check if an individual channel already flagged a critical reason
            critical_signals = [r.signal for r in reasons if r.contribution <= -30.0]
            if not critical_signals:
                p = HealthReason(
                    signal="flight_envelope",
                    observed=None,
                    contribution=-15.0,
                    reason="Composite flight envelope hard limits exceeded",
                )
                reasons.append(p)
                warnings.append("Flight envelope limit exceeded")
        elif telemetry.envelope_status == EnvelopeStatus.CAUTION:
            caution_signals = [r.signal for r in reasons if r.contribution < 0]
            if not caution_signals:
                p = HealthReason(
                    signal="flight_envelope",
                    observed=None,
                    contribution=-5.0,
                    reason="Flight telemetry operating within caution envelope band",
                )
                reasons.append(p)

        # 6. Telemetry Quality Status
        if telemetry.quality_status == QualityStatus.DEGRADED:
            p = HealthReason(
                signal="telemetry_quality",
                observed=None,
                contribution=-12.0,
                reason="Telemetry stream degraded: optional channels absent or high signal variance",
            )
            reasons.append(p)
            avionics_penalties.append(p)
            warnings.append("Telemetry feed degraded")

        # 7. Fuel Flow Subsystem Check
        fuel = telemetry.fuel_flow_kg_h
        if fuel is None:
            p = HealthReason(
                signal="fuel_flow",
                observed=None,
                contribution=-5.0,
                reason="Fuel flow telemetry channel unpopulated",
            )
            fuel_penalties.append(p)
        elif fuel < 0.0:
            p = HealthReason(
                signal="fuel_flow",
                observed=fuel,
                contribution=-25.0,
                reason=f"Unphysical negative fuel flow rate ({fuel:.1f} kg/h)",
            )
            reasons.append(p)
            fuel_penalties.append(p)

        # Calculate composite airframe health score
        total_deduction = sum(abs(r.contribution) for r in reasons)
        composite_score = round(max(0.0, min(100.0, 100.0 - total_deduction)), 1)
        composite_state = cls.score_to_health_state(composite_score)

        # -------------------------------------------------------------
        # Subsystem-Specific Health Evaluations
        # -------------------------------------------------------------
        subsystems: Dict[str, SubsystemState] = {}

        # Propulsion
        prop_deduction = sum(abs(p.contribution) for p in propulsion_penalties)
        prop_score = round(max(0.0, min(100.0, 100.0 - prop_deduction)), 1)
        prop_state = cls.score_to_health_state(prop_score)
        subsystems[TwinSubsystemType.PROPULSION.value] = SubsystemState(
            subsystem=TwinSubsystemType.PROPULSION,
            health_state=prop_state,
            health_score=prop_score,
            wear_index=0.0,  # Updated by WearEstimator
            last_updated_at=eval_time,
            contributing_signals=["engine_temperature", "engine_pressure", "vibration", "fuel_flow"],
            warnings=[p.reason for p in propulsion_penalties],
        )

        # Structure
        struct_deduction = sum(abs(p.contribution) for p in structure_penalties)
        struct_score = round(max(0.0, min(100.0, 100.0 - struct_deduction)), 1)
        struct_state = cls.score_to_health_state(struct_score)
        subsystems[TwinSubsystemType.STRUCTURE.value] = SubsystemState(
            subsystem=TwinSubsystemType.STRUCTURE,
            health_state=struct_state,
            health_score=struct_score,
            wear_index=0.0,  # Updated by WearEstimator
            last_updated_at=eval_time,
            contributing_signals=["g_load", "flight_hours", "flight_cycles"],
            warnings=[p.reason for p in structure_penalties],
        )

        # Flight Controls
        fc_deduction = sum(abs(p.contribution) for p in flight_control_penalties)
        if telemetry.quality_status == QualityStatus.DEGRADED:
            fc_deduction += 10.0
        fc_score = round(max(0.0, min(100.0, 100.0 - fc_deduction)), 1)
        fc_state = cls.score_to_health_state(fc_score)
        subsystems[TwinSubsystemType.FLIGHT_CONTROLS.value] = SubsystemState(
            subsystem=TwinSubsystemType.FLIGHT_CONTROLS,
            health_state=fc_state,
            health_score=fc_score,
            wear_index=0.0,
            last_updated_at=eval_time,
            contributing_signals=["control_surface_angle", "telemetry_quality"],
            warnings=[p.reason for p in flight_control_penalties],
        )

        # Avionics
        av_deduction = sum(abs(p.contribution) for p in avionics_penalties)
        av_score = round(max(0.0, min(100.0, 100.0 - av_deduction)), 1)
        av_state = cls.score_to_health_state(av_score)
        subsystems[TwinSubsystemType.AVIONICS.value] = SubsystemState(
            subsystem=TwinSubsystemType.AVIONICS,
            health_state=av_state,
            health_score=av_score,
            wear_index=0.0,
            last_updated_at=eval_time,
            contributing_signals=["telemetry_quality", "clock_integrity"],
            warnings=[p.reason for p in avionics_penalties],
        )

        # Fuel
        fuel_deduction = sum(abs(p.contribution) for p in fuel_penalties)
        fuel_score = round(max(0.0, min(100.0, 100.0 - fuel_deduction)), 1)
        fuel_state = cls.score_to_health_state(fuel_score)
        subsystems[TwinSubsystemType.FUEL.value] = SubsystemState(
            subsystem=TwinSubsystemType.FUEL,
            health_state=fuel_state,
            health_score=fuel_score,
            wear_index=0.0,
            last_updated_at=eval_time,
            contributing_signals=["fuel_flow"],
            warnings=[p.reason for p in fuel_penalties],
        )

        # Hydraulic (No direct sensor channel in baseline telemetry)
        # Note: We NEVER manufacture fake data. Explicitly report UNKNOWN.
        subsystems[TwinSubsystemType.HYDRAULIC.value] = SubsystemState(
            subsystem=TwinSubsystemType.HYDRAULIC,
            health_state=TwinHealthState.UNKNOWN,
            health_score=100.0,
            wear_index=0.0,
            last_updated_at=eval_time,
            contributing_signals=[],
            warnings=["No dedicated hydraulic sensor telemetry channel present; state unobserved"],
        )

        return composite_score, composite_state, reasons, subsystems, warnings
