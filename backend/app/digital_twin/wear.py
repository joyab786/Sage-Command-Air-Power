"""
SageCommand Air Power System (Aero) — Wear Estimator.
Calculates transparent, bounded normalized wear indices (0.0 to 1.0)
for airframes and subsystems based on operational hours, cycles, and stress exposures.

Note:
Wear indices are engineering demonstration indicators intended to support
future prognostic models and do not represent certified structural fatigue limits.
"""

from typing import Dict, Optional
from app.telemetry.models import NormalizedTelemetry
from app.digital_twin.models import (
    TwinSubsystemType,
    SubsystemState,
    AircraftTwinState,
)


class WearEstimator:
    """
    Deterministic wear index calculator for the SIH Decision-Support Prototype.
    Maps operational history and dynamic stress factors into bounded [0.0, 1.0] wear ratings.
    """

    # Baseline demonstration lifing parameters
    NOMINAL_TBO_HOURS = 4000.0    # Nominal hours to depot overhaul
    NOMINAL_DESIGN_CYCLES = 2000   # Nominal design airframe cycles

    @classmethod
    def calculate_wear(
        cls,
        telemetry: Optional[NormalizedTelemetry],
        flight_hours: float,
        flight_cycles: int,
        previous_wear_index: float = 0.0,
    ) -> float:
        """
        Calculates composite airframe wear index in the range [0.0, 1.0].
        Incorporates cumulative operational time plus active stress factors.
        """
        # 1. Base accumulated time wear (Max contribution: 0.40)
        hours_fraction = min(1.0, max(0.0, flight_hours / cls.NOMINAL_TBO_HOURS))
        hours_wear = hours_fraction * 0.40

        # 2. Base accumulated cycle wear (Max contribution: 0.30)
        cycles_fraction = min(1.0, max(0.0, flight_cycles / cls.NOMINAL_DESIGN_CYCLES))
        cycles_wear = cycles_fraction * 0.30

        # 3. Dynamic sensor stress increments
        thermal_wear = 0.0
        vibration_wear = 0.0
        high_g_wear = 0.0

        if telemetry:
            # Thermal stress above 950°C caution threshold
            if telemetry.engine_temperature_c and telemetry.engine_temperature_c > 950.0:
                excess_temp = (telemetry.engine_temperature_c - 950.0) / 100.0
                thermal_wear = min(0.12, excess_temp * 0.06)

            # Vibration mechanical fatigue above 0.85 ips caution threshold
            if telemetry.vibration_ips and telemetry.vibration_ips > 0.85:
                excess_vib = (telemetry.vibration_ips - 0.85) / 0.40
                vibration_wear = min(0.12, excess_vib * 0.06)

            # High-G structural loading above 7.0 G
            if telemetry.g_load and abs(telemetry.g_load) > 7.0:
                excess_g = (abs(telemetry.g_load) - 7.0) / 2.0
                high_g_wear = min(0.12, excess_g * 0.06)

        # Retain previous baseline wear if current calculation is slightly lower due to instantaneous relief
        calculated_wear = hours_wear + cycles_wear + thermal_wear + vibration_wear + high_g_wear
        final_wear = max(previous_wear_index, calculated_wear)

        return round(min(1.0, max(0.0, final_wear)), 4)

    @classmethod
    def apply_subsystem_wear(
        cls,
        subsystems: Dict[str, SubsystemState],
        telemetry: Optional[NormalizedTelemetry],
        flight_hours: float,
        flight_cycles: int,
    ) -> None:
        """
        Updates individual subsystem wear indices in-place based on their specific wear drivers.
        """
        hours_ratio = min(1.0, max(0.0, flight_hours / cls.NOMINAL_TBO_HOURS))
        cycles_ratio = min(1.0, max(0.0, flight_cycles / cls.NOMINAL_DESIGN_CYCLES))

        # Dynamic increments
        thermal_inc = 0.0
        vib_inc = 0.0
        g_inc = 0.0

        if telemetry:
            if telemetry.engine_temperature_c and telemetry.engine_temperature_c > 950.0:
                thermal_inc = min(0.20, ((telemetry.engine_temperature_c - 950.0) / 100.0) * 0.10)
            if telemetry.vibration_ips and telemetry.vibration_ips > 0.85:
                vib_inc = min(0.20, ((telemetry.vibration_ips - 0.85) / 0.40) * 0.10)
            if telemetry.g_load and abs(telemetry.g_load) > 7.0:
                g_inc = min(0.20, ((abs(telemetry.g_load) - 7.0) / 2.0) * 0.10)

        # Propulsion: Engine hours + thermal + vibration
        if TwinSubsystemType.PROPULSION.value in subsystems:
            p_wear = (hours_ratio * 0.40) + thermal_inc + vib_inc
            subsystems[TwinSubsystemType.PROPULSION.value].wear_index = round(min(1.0, max(0.0, p_wear)), 4)

        # Structure: Airframe cycles + flight hours + high-G
        if TwinSubsystemType.STRUCTURE.value in subsystems:
            s_wear = (cycles_ratio * 0.45) + (hours_ratio * 0.25) + g_inc
            subsystems[TwinSubsystemType.STRUCTURE.value].wear_index = round(min(1.0, max(0.0, s_wear)), 4)

        # Flight Controls: Operating hours + general cycle usage
        if TwinSubsystemType.FLIGHT_CONTROLS.value in subsystems:
            fc_wear = (hours_ratio * 0.35) + (cycles_ratio * 0.15)
            subsystems[TwinSubsystemType.FLIGHT_CONTROLS.value].wear_index = round(min(1.0, max(0.0, fc_wear)), 4)

        # Avionics: Operating hours
        if TwinSubsystemType.AVIONICS.value in subsystems:
            av_wear = hours_ratio * 0.40
            subsystems[TwinSubsystemType.AVIONICS.value].wear_index = round(min(1.0, max(0.0, av_wear)), 4)

        # Fuel: Operating hours
        if TwinSubsystemType.FUEL.value in subsystems:
            fuel_wear = hours_ratio * 0.30
            subsystems[TwinSubsystemType.FUEL.value].wear_index = round(min(1.0, max(0.0, fuel_wear)), 4)

        # Hydraulic: Unobserved channel
        if TwinSubsystemType.HYDRAULIC.value in subsystems:
            subsystems[TwinSubsystemType.HYDRAULIC.value].wear_index = 0.0
