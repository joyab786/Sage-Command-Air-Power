"""
SageCommand Air Power System (Aero) — Telemetry Normalizer.
Provides deterministic unit conversion, channel mapping, and standardization
to canonical aerospace SI engineering units.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from app.telemetry.models import TelemetryInput, NormalizedTelemetry, QualityStatus, EnvelopeStatus


# Supported unit aliases (case-insensitive)
SUPPORTED_UNITS = {
    "altitude": {"ft", "feet", "foot", "m", "meter", "meters", "km", "kilometer"},
    "airspeed": {"kts", "knot", "knots", "km/h", "kmh", "kph", "m/s", "mps", "mph"},
    "temperature": {"c", "celsius", "deg_c", "f", "fahrenheit", "deg_f", "k", "kelvin"},
    "pressure": {"kpa", "kilopascal", "pa", "pascal", "bar", "psi", "atm"},
    "vibration": {"ips", "mm/s", "mms"},
    "fuel_flow": {"kg/h", "kgh", "kg_h", "lbs/h", "pph", "lb/h"},
}

DEFAULT_UNITS = {
    "altitude": "ft",
    "airspeed": "kts",
    "temperature": "c",
    "pressure": "psi",
    "vibration": "ips",
    "fuel_flow": "kg/h",
}


def convert_altitude(val: float, unit: str) -> float:
    """Converts altitude to canonical meters (m)."""
    u = unit.lower().strip()
    if u in ("m", "meter", "meters"):
        return val
    elif u in ("ft", "feet", "foot"):
        return val * 0.3048
    elif u in ("km", "kilometer"):
        return val * 1000.0
    raise ValueError(f"Unsupported altitude unit '{unit}'. Supported: {sorted(SUPPORTED_UNITS['altitude'])}")


def convert_airspeed(val: float, unit: str) -> float:
    """Converts airspeed to canonical meters per second (m/s)."""
    u = unit.lower().strip()
    if u in ("m/s", "mps"):
        return val
    elif u in ("kts", "knot", "knots"):
        return val * 0.514444
    elif u in ("km/h", "kmh", "kph"):
        return val / 3.6
    elif u in ("mph",):
        return val * 0.44704
    raise ValueError(f"Unsupported airspeed unit '{unit}'. Supported: {sorted(SUPPORTED_UNITS['airspeed'])}")


def convert_temperature(val: float, unit: str) -> float:
    """Converts temperature to canonical degrees Celsius (°C)."""
    u = unit.lower().strip()
    if u in ("c", "celsius", "deg_c"):
        return val
    elif u in ("f", "fahrenheit", "deg_f"):
        return (val - 32.0) * (5.0 / 9.0)
    elif u in ("k", "kelvin"):
        return val - 273.15
    raise ValueError(f"Unsupported temperature unit '{unit}'. Supported: {sorted(SUPPORTED_UNITS['temperature'])}")


def convert_pressure(val: float, unit: str) -> float:
    """Converts pressure to canonical kilopascals (kPa)."""
    u = unit.lower().strip()
    if u in ("kpa", "kilopascal"):
        return val
    elif u in ("pa", "pascal"):
        return val / 1000.0
    elif u in ("bar",):
        return val * 100.0
    elif u in ("psi",):
        return val * 6.894757
    elif u in ("atm",):
        return val * 101.325
    raise ValueError(f"Unsupported pressure unit '{unit}'. Supported: {sorted(SUPPORTED_UNITS['pressure'])}")


def convert_vibration(val: float, unit: str) -> float:
    """Converts vibration amplitude to canonical inches per second (ips)."""
    u = unit.lower().strip()
    if u in ("ips",):
        return val
    elif u in ("mm/s", "mms"):
        return val / 25.4
    raise ValueError(f"Unsupported vibration unit '{unit}'. Supported: {sorted(SUPPORTED_UNITS['vibration'])}")


def convert_fuel_flow(val: float, unit: str) -> float:
    """Converts fuel flow rate to canonical kg/h."""
    u = unit.lower().strip()
    if u in ("kg/h", "kgh", "kg_h"):
        return val
    elif u in ("lbs/h", "pph", "lb/h"):
        return val * 0.453592
    raise ValueError(f"Unsupported fuel flow unit '{unit}'. Supported: {sorted(SUPPORTED_UNITS['fuel_flow'])}")


class TelemetryNormalizer:
    """
    Deterministic engine that maps raw or mixed-unit telemetry observations
    into standardized canonical SI aerospace frames.
    """

    @staticmethod
    def normalize(obs: TelemetryInput) -> NormalizedTelemetry:
        """
        Normalizes an incoming TelemetryInput observation.
        Raises ValueError if explicit unsupported unit is supplied or values are invalid.
        """
        units = obs.units or {}

        # 1. Identity & Timestamps
        obs_id = obs.observation_id or f"obs_{uuid.uuid4().hex[:16]}"
        timestamp = obs.timestamp or datetime.now(timezone.utc)

        # 2. Altitude normalization
        norm_alt = None
        if obs.altitude is not None:
            unit = units.get("altitude") or units.get("alt") or DEFAULT_UNITS["altitude"]
            norm_alt = round(convert_altitude(obs.altitude, unit), 2)

        # 3. Airspeed normalization
        norm_spd = None
        if obs.airspeed is not None:
            unit = units.get("airspeed") or units.get("speed") or DEFAULT_UNITS["airspeed"]
            norm_spd = round(convert_airspeed(obs.airspeed, unit), 2)

        # 4. Temperature normalization
        norm_temp = None
        if obs.engine_temperature is not None:
            unit = units.get("engine_temperature") or units.get("temperature") or units.get("temp") or DEFAULT_UNITS["temperature"]
            norm_temp = round(convert_temperature(obs.engine_temperature, unit), 2)

        # 5. Pressure normalization
        norm_press = None
        if obs.engine_pressure is not None:
            unit = units.get("engine_pressure") or units.get("pressure") or DEFAULT_UNITS["pressure"]
            norm_press = round(convert_pressure(obs.engine_pressure, unit), 2)

        # 6. Vibration normalization
        norm_vib = None
        if obs.vibration is not None:
            unit = units.get("vibration") or units.get("vib") or DEFAULT_UNITS["vibration"]
            norm_vib = round(convert_vibration(obs.vibration, unit), 3)

        # 7. Fuel Flow normalization
        norm_fuel = None
        if obs.fuel_flow is not None:
            unit = units.get("fuel_flow") or units.get("fuel") or DEFAULT_UNITS["fuel_flow"]
            norm_fuel = round(convert_fuel_flow(obs.fuel_flow, unit), 2)

        # 8. Direct standard channels (Mach, G-load, deflection)
        norm_mach = round(obs.mach, 3) if obs.mach is not None else None
        norm_g = round(obs.g_load, 2) if obs.g_load is not None else None
        norm_surf = round(obs.control_surface_angle, 2) if obs.control_surface_angle is not None else None

        return NormalizedTelemetry(
            observation_id=obs_id,
            timestamp=timestamp,
            aircraft_id=obs.aircraft_id,
            flight_id=obs.flight_id,
            altitude_m=norm_alt,
            airspeed_mps=norm_spd,
            mach=norm_mach,
            g_load=norm_g,
            fuel_flow_kg_h=norm_fuel,
            engine_temperature_c=norm_temp,
            engine_pressure_kpa=norm_press,
            vibration_ips=norm_vib,
            control_surface_angle_deg=norm_surf,
            quality_status=QualityStatus.VALID,
            envelope_status=EnvelopeStatus.WITHIN_ENVELOPE,
            source=obs.source or "TELEMETRY_STREAM",
            raw_units=units,
        )
