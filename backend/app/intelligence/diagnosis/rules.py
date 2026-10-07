"""
SageCommand Air Power System (Aero) — Diagnosis Rules Configuration.
Defines rule weights, correlation factors, and diagnosis catalog references.
"""

from typing import Dict, Any

DIAGNOSIS_RULE_CATALOG: Dict[str, Dict[str, Any]] = {
    "PROPULSION_MULTI_SIGNAL": {
        "subsystem": "PROPULSION",
        "min_signals": 2,
        "base_confidence": 0.94,
        "description": "Concurrent thermal and vibration exceedance on rotating machinery",
    },
    "PROPULSION_THERMAL": {
        "subsystem": "PROPULSION",
        "min_signals": 1,
        "base_confidence": 0.90,
        "description": "Turbine/combustor hot gas path temperature elevation",
    },
    "PROPULSION_VIBRATION": {
        "subsystem": "PROPULSION",
        "min_signals": 1,
        "base_confidence": 0.90,
        "description": "Spool/bearing rotational assembly mechanical imbalance",
    },
    "STRUCTURE_G_LOAD": {
        "subsystem": "STRUCTURE",
        "min_signals": 1,
        "base_confidence": 0.92,
        "description": "High-G aerodynamic maneuver exceeding airframe limits",
    },
    "FLIGHT_CONTROLS_SURFACE": {
        "subsystem": "FLIGHT_CONTROLS",
        "min_signals": 1,
        "base_confidence": 0.84,
        "description": "Control surface excessive deflection or actuator anomaly",
    },
    "AVIONICS_STREAM_QUALITY": {
        "subsystem": "AVIONICS",
        "min_signals": 1,
        "base_confidence": 0.80,
        "description": "Telemetry stream degradation or frame jitter",
    },
}
