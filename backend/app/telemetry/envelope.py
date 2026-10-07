"""
SageCommand Air Power System (Aero) — Flight Envelope Checker.
Evaluates normalized flight telemetry against configurable aerodynamic,
structural, and propulsion demonstration flight-envelope boundaries.
"""

from typing import List, Optional, Dict
from pydantic import Field
from app.contracts.base import AeroBaseModel
from app.telemetry.models import (
    NormalizedTelemetry,
    EnvelopeStatus,
    EnvelopeViolation,
    EnvelopeAssessmentResult,
)


class ChannelBoundary(AeroBaseModel):
    """Configurable caution and hard limits for an individual telemetry parameter."""

    caution_high: Optional[float] = None
    limit_high: Optional[float] = None
    caution_low: Optional[float] = None
    limit_low: Optional[float] = None


class FlightEnvelopeProfile(AeroBaseModel):
    """
    Demonstration flight envelope limits profile.
    NOTE: These values represent generic demonstration parameters for SIH prototyping
    and do not reflect classified or operational military airframe certification limits.
    """

    profile_name: str = Field(default="GENERIC_TACTICAL_FIGHTER_DEMO")
    # Altitude in meters
    altitude_m: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(caution_high=16000.0, limit_high=18500.0, limit_low=-100.0)
    )
    # Airspeed in m/s
    airspeed_mps: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(caution_high=650.0, limit_high=700.0)
    )
    # Mach number
    mach: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(caution_high=2.0, limit_high=2.25)
    )
    # Normal Acceleration in G units
    g_load: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(
            caution_high=7.5, limit_high=9.0, caution_low=-2.5, limit_low=-3.0
        )
    )
    # Exhaust Gas / Turbine Temp in Celsius
    engine_temperature_c: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(caution_high=780.0, limit_high=850.0)
    )
    # Core Engine Pressure in kPa
    engine_pressure_kpa: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(
            caution_high=600.0, limit_high=650.0, caution_low=180.0, limit_low=150.0
        )
    )
    # Airframe/Turbine Vibration in inches per second (ips)
    vibration_ips: ChannelBoundary = Field(
        default_factory=lambda: ChannelBoundary(caution_high=0.5, limit_high=0.8)
    )


# Standard default demonstration envelope
DEFAULT_DEMO_ENVELOPE = FlightEnvelopeProfile()


class FlightEnvelopeChecker:
    """
    Deterministic checker that evaluates normalized observations against
    configured envelope profiles and tags CAUTION or EXCEEDED violations.
    """

    def __init__(self, profile: Optional[FlightEnvelopeProfile] = None):
        self.profile = profile or DEFAULT_DEMO_ENVELOPE

    def evaluate(self, norm: NormalizedTelemetry) -> EnvelopeAssessmentResult:
        """
        Evaluates a normalized observation frame and returns structured violations.
        """
        violations: List[EnvelopeViolation] = []
        checked_count = 0

        # Helper evaluation closure
        def check_channel(param_name: str, val: Optional[float], bounds: ChannelBoundary, unit_label: str):
            nonlocal checked_count
            if val is None:
                return
            checked_count += 1

            # 1. High Limit (Exceeded)
            if bounds.limit_high is not None and val > bounds.limit_high:
                violations.append(
                    EnvelopeViolation(
                        parameter=param_name,
                        observed_value=val,
                        limit=bounds.limit_high,
                        direction="ABOVE",
                        severity="CRITICAL",
                        message=f"{param_name} ({val} {unit_label}) exceeded hard limit ({bounds.limit_high} {unit_label})",
                    )
                )
            # 2. High Caution
            elif bounds.caution_high is not None and val > bounds.caution_high:
                violations.append(
                    EnvelopeViolation(
                        parameter=param_name,
                        observed_value=val,
                        limit=bounds.caution_high,
                        direction="ABOVE",
                        severity="CAUTION",
                        message=f"{param_name} ({val} {unit_label}) entered caution threshold ({bounds.caution_high} {unit_label})",
                    )
                )

            # 3. Low Limit (Exceeded)
            if bounds.limit_low is not None and val < bounds.limit_low:
                violations.append(
                    EnvelopeViolation(
                        parameter=param_name,
                        observed_value=val,
                        limit=bounds.limit_low,
                        direction="BELOW",
                        severity="CRITICAL",
                        message=f"{param_name} ({val} {unit_label}) fell below minimum limit ({bounds.limit_low} {unit_label})",
                    )
                )
            # 4. Low Caution
            elif bounds.caution_low is not None and val < bounds.caution_low:
                violations.append(
                    EnvelopeViolation(
                        parameter=param_name,
                        observed_value=val,
                        limit=bounds.caution_low,
                        direction="BELOW",
                        severity="CAUTION",
                        message=f"{param_name} ({val} {unit_label}) fell below caution threshold ({bounds.caution_low} {unit_label})",
                    )
                )

        # Check all envelope parameters
        check_channel("altitude", norm.altitude_m, self.profile.altitude_m, "m")
        check_channel("airspeed", norm.airspeed_mps, self.profile.airspeed_mps, "m/s")
        check_channel("mach", norm.mach, self.profile.mach, "Mach")
        check_channel("g_load", norm.g_load, self.profile.g_load, "G")
        check_channel("engine_temperature", norm.engine_temperature_c, self.profile.engine_temperature_c, "°C")
        check_channel("engine_pressure", norm.engine_pressure_kpa, self.profile.engine_pressure_kpa, "kPa")
        check_channel("vibration", norm.vibration_ips, self.profile.vibration_ips, "ips")

        # Determine overall envelope status
        status = EnvelopeStatus.WITHIN_ENVELOPE
        if any(v.severity == "CRITICAL" for v in violations):
            status = EnvelopeStatus.EXCEEDED
        elif any(v.severity == "CAUTION" for v in violations):
            status = EnvelopeStatus.CAUTION

        return EnvelopeAssessmentResult(
            status=status,
            violations=violations,
            parameters_checked=checked_count,
        )
