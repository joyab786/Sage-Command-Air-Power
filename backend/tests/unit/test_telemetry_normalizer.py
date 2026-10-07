"""
Unit tests for TelemetryNormalizer.
Validates unit conversions (feet->meters, knots->m/s, F->C, psi->kPa, etc.)
and error handling on unsupported units.
"""

import pytest
from app.telemetry.normalizer import (
    TelemetryNormalizer,
    convert_altitude,
    convert_airspeed,
    convert_temperature,
    convert_pressure,
    convert_vibration,
    convert_fuel_flow,
)
from app.telemetry.models import TelemetryInput


def test_altitude_conversions():
    # Feet to meters: 10,000 ft = 3048 m
    assert round(convert_altitude(10000.0, "ft"), 2) == 3048.0
    assert round(convert_altitude(10000.0, "feet"), 2) == 3048.0
    # Meters to meters
    assert convert_altitude(5000.0, "m") == 5000.0
    # Kilometers to meters
    assert convert_altitude(12.0, "km") == 12000.0


def test_airspeed_conversions():
    # Knots to m/s: 100 kts = 51.4444 m/s
    assert round(convert_airspeed(100.0, "kts"), 2) == 51.44
    assert round(convert_airspeed(100.0, "knots"), 2) == 51.44
    # km/h to m/s: 360 km/h = 100 m/s
    assert round(convert_airspeed(360.0, "km/h"), 2) == 100.0
    assert round(convert_airspeed(360.0, "kmh"), 2) == 100.0
    # m/s to m/s
    assert convert_airspeed(250.0, "m/s") == 250.0


def test_temperature_conversions():
    # Celsius to Celsius
    assert convert_temperature(650.0, "c") == 650.0
    # Fahrenheit to Celsius: 212 F = 100 C, 32 F = 0 C
    assert round(convert_temperature(212.0, "f"), 2) == 100.0
    assert round(convert_temperature(32.0, "fahrenheit"), 2) == 0.0
    # Kelvin to Celsius: 300 K = 26.85 C
    assert round(convert_temperature(300.0, "k"), 2) == 26.85


def test_pressure_conversions():
    # kPa to kPa
    assert convert_pressure(300.0, "kpa") == 300.0
    # Pa to kPa: 100,000 Pa = 100 kPa
    assert convert_pressure(100000.0, "pa") == 100.0
    # bar to kPa: 2 bar = 200 kPa
    assert convert_pressure(2.0, "bar") == 200.0
    # psi to kPa: 50 psi = 344.74 kPa
    assert round(convert_pressure(50.0, "psi"), 2) == 344.74


def test_vibration_and_fuel_conversions():
    # ips
    assert convert_vibration(0.25, "ips") == 0.25
    # mm/s to ips: 25.4 mm/s = 1.0 ips
    assert round(convert_vibration(25.4, "mm/s"), 2) == 1.0
    # fuel flow: kg/h
    assert convert_fuel_flow(2400.0, "kg/h") == 2400.0
    # lbs/h to kg/h: 1000 lbs/h = 453.59 kg/h
    assert round(convert_fuel_flow(1000.0, "lbs/h"), 2) == 453.59


def test_unsupported_unit_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported altitude unit"):
        convert_altitude(100.0, "parsecs")

    with pytest.raises(ValueError, match="Unsupported airspeed unit"):
        convert_airspeed(100.0, "furlongs_per_fortnight")


def test_full_frame_normalization():
    raw = TelemetryInput(
        aircraft_id="ac_su30_01",
        flight_id="flt_sort_101",
        altitude=32808.4,  # ~10,000 m
        airspeed=485.96,   # ~250 m/s
        mach=0.82,
        g_load=1.1,
        engine_temperature=1202.0, # 1202 F = 650 C
        engine_pressure=50.0,      # 50 psi = 344.74 kPa
        vibration=0.22,
        fuel_flow=2400.0,
        units={
            "altitude": "ft",
            "airspeed": "kts",
            "temperature": "f",
            "pressure": "psi",
            "vibration": "ips",
            "fuel_flow": "kg/h",
        },
    )
    normalized = TelemetryNormalizer.normalize(raw)
    assert normalized.aircraft_id == "ac_su30_01"
    assert round(normalized.altitude_m, 0) == 10000.0
    assert round(normalized.airspeed_mps, 0) == 250.0
    assert round(normalized.engine_temperature_c, 0) == 650.0
    assert round(normalized.engine_pressure_kpa, 0) == 345.0
    assert normalized.mach == 0.82
    assert normalized.g_load == 1.1
