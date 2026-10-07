"""
SageCommand Air Power System (Aero) — Digital Twin State Estimator.
Consumes normalized flight telemetry frames and constructs continuously updated,
explainable digital twin states while preserving previous observations across sparse frames.
"""

from typing import Optional
from app.telemetry.models import NormalizedTelemetry, QualityStatus
from app.digital_twin.models import (
    AircraftTwinState,
    TwinHealthState,
    utc_now,
)
from app.digital_twin.health import AircraftHealthEstimator
from app.digital_twin.wear import WearEstimator


class DigitalTwinEstimator:
    """
    Deterministic state estimation engine.
    Fuses normalized telemetry observations with previous state history.
    """

    @classmethod
    def estimate_state(
        cls,
        telemetry: NormalizedTelemetry,
        previous_state: Optional[AircraftTwinState] = None,
        flight_hours: float = 0.0,
        flight_cycles: int = 0,
    ) -> AircraftTwinState:
        """
        Derives an updated AircraftTwinState from incoming telemetry.
        Preserves valid previous state values when incoming frame lacks specific channels.
        """
        # Channel persistence: incoming non-None takes precedence, otherwise retain previous
        altitude = (
            telemetry.altitude_m
            if telemetry.altitude_m is not None
            else (previous_state.altitude if previous_state else None)
        )
        airspeed = (
            telemetry.airspeed_mps
            if telemetry.airspeed_mps is not None
            else (previous_state.airspeed if previous_state else None)
        )
        mach = (
            telemetry.mach
            if telemetry.mach is not None
            else (previous_state.mach if previous_state else None)
        )
        g_load = (
            telemetry.g_load
            if telemetry.g_load is not None
            else (previous_state.g_load if previous_state else None)
        )
        fuel_flow = (
            telemetry.fuel_flow_kg_h
            if telemetry.fuel_flow_kg_h is not None
            else (previous_state.fuel_flow if previous_state else None)
        )
        engine_temp = (
            telemetry.engine_temperature_c
            if telemetry.engine_temperature_c is not None
            else (previous_state.engine_temperature if previous_state else None)
        )
        engine_pressure = (
            telemetry.engine_pressure_kpa
            if telemetry.engine_pressure_kpa is not None
            else (previous_state.engine_pressure if previous_state else None)
        )
        vibration = (
            telemetry.vibration_ips
            if telemetry.vibration_ips is not None
            else (previous_state.vibration if previous_state else None)
        )

        flight_id = telemetry.flight_id or (previous_state.current_flight_id if previous_state else None)

        # Operational status determination
        if airspeed is not None and airspeed > 30.0:
            operational_status = "IN_FLIGHT"
        elif previous_state:
            operational_status = previous_state.operational_status
        else:
            operational_status = "ACTIVE"

        # 1. Evaluate health and subsystem health
        health_score, health_state, health_reasons, subsystems, warnings = (
            AircraftHealthEstimator.evaluate_health(
                telemetry=telemetry,
                previous_twin=previous_state,
                flight_hours=flight_hours,
                flight_cycles=flight_cycles,
                now=telemetry.timestamp,
            )
        )

        # 2. Evaluate wear indices
        prev_wear = previous_state.wear_index if previous_state else 0.0
        composite_wear = WearEstimator.calculate_wear(
            telemetry=telemetry,
            flight_hours=flight_hours,
            flight_cycles=flight_cycles,
            previous_wear_index=prev_wear,
        )
        WearEstimator.apply_subsystem_wear(
            subsystems=subsystems,
            telemetry=telemetry,
            flight_hours=flight_hours,
            flight_cycles=flight_cycles,
        )

        # Quality indicator string
        quality_str = telemetry.quality_status.value if hasattr(telemetry.quality_status, "value") else str(telemetry.quality_status)

        return AircraftTwinState(
            aircraft_id=telemetry.aircraft_id,
            timestamp=telemetry.timestamp,
            operational_status=operational_status,
            altitude=altitude,
            airspeed=airspeed,
            mach=mach,
            g_load=g_load,
            fuel_flow=fuel_flow,
            engine_temperature=engine_temp,
            engine_pressure=engine_pressure,
            vibration=vibration,
            flight_hours=round(flight_hours, 2),
            flight_cycles=flight_cycles,
            current_flight_id=flight_id,
            health_state=health_state,
            health_score=health_score,
            wear_index=composite_wear,
            subsystem_states=subsystems,
            health_reasons=health_reasons,
            active_warnings=warnings,
            data_quality=quality_str,
            last_updated_at=utc_now(),
        )
