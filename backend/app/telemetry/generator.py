"""
SageCommand Air Power System (Aero) — Synthetic Flight Profile Generator.
Generates reproducible, realistic aerodynamic and propulsion sensor telemetry streams
for Smart India Hackathon (SIH) demonstration scenarios.
"""

import math
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.telemetry.models import TelemetryInput


class SyntheticFlightGenerator:
    """
    Deterministic synthetic flight generator.
    Produces repeatable time-series flight sequences based on operational profiles.
    """

    SUPPORTED_PROFILES = {
        "NORMAL_CRUISE",
        "TAKEOFF_CLIMB",
        "HIGH_G_TURN",
        "SUPERSONIC_CRUISE",
        "THERMAL_SPIKE",
        "VIBRATION_SPIKE",
    }

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_flight_sequence(
        self,
        aircraft_id: str,
        profile: str = "NORMAL_CRUISE",
        count: int = 10,
        start_time: Optional[datetime] = None,
        flight_id: Optional[str] = None,
        interval_seconds: float = 1.0,
    ) -> List[TelemetryInput]:
        """
        Generates a sequence of TelemetryInput frames for the given profile.
        """
        if profile not in self.SUPPORTED_PROFILES:
            raise ValueError(f"Unknown flight profile '{profile}'. Supported: {sorted(self.SUPPORTED_PROFILES)}")

        t0 = start_time or datetime.now(timezone.utc)
        fid = flight_id or f"flt_sim_{profile.lower()[:6]}"
        observations: List[TelemetryInput] = []

        for step in range(count):
            t_curr = t0 + timedelta(seconds=step * interval_seconds)
            obs_id = f"sim_{profile.lower()}_{step:04d}_{self.rng.randint(1000, 9999)}"

            # Profile-specific physical simulation parameters
            if profile == "NORMAL_CRUISE":
                # High altitude, steady sub-Mach cruise, 1G normal load
                noise = self.rng.uniform(-0.02, 0.02)
                alt_ft = 32000.0 + self.rng.uniform(-50.0, 50.0)
                spd_kts = 480.0 + self.rng.uniform(-5.0, 5.0)
                mach = round(0.82 + noise, 3)
                g_load = round(1.0 + self.rng.uniform(-0.05, 0.05), 2)
                fuel_flow = round(2400.0 + self.rng.uniform(-30.0, 30.0), 1)
                temp_c = round(650.0 + self.rng.uniform(-5.0, 5.0), 1)
                press_psi = round(45.0 + self.rng.uniform(-0.5, 0.5), 1)
                vib_ips = round(0.18 + self.rng.uniform(-0.02, 0.02), 3)
                surf_deg = round(0.5 + self.rng.uniform(-0.2, 0.2), 1)

            elif profile == "TAKEOFF_CLIMB":
                # Accelerating climb out from airfield
                progress = (step + 1) / max(count, 1)
                alt_ft = 1000.0 + progress * 15000.0 + self.rng.uniform(-30.0, 30.0)
                spd_kts = 220.0 + progress * 240.0 + self.rng.uniform(-5.0, 5.0)
                mach = round(0.35 + progress * 0.40, 3)
                g_load = round(1.35 + self.rng.uniform(-0.1, 0.1), 2)
                fuel_flow = round(4800.0 - progress * 800.0 + self.rng.uniform(-50.0, 50.0), 1)
                temp_c = round(720.0 + self.rng.uniform(-8.0, 8.0), 1)
                press_psi = round(52.0 + self.rng.uniform(-1.0, 1.0), 1)
                vib_ips = round(0.25 + self.rng.uniform(-0.03, 0.03), 3)
                surf_deg = round(5.0 - progress * 3.5, 1)

            elif profile == "HIGH_G_TURN":
                # High-G tactical maneuver, elevated G-load and control surface deflection
                g_peak = 7.8 if step < count // 2 else 5.2
                alt_ft = 22000.0 + self.rng.uniform(-100.0, 100.0)
                spd_kts = 510.0 + self.rng.uniform(-10.0, 10.0)
                mach = round(0.88 + self.rng.uniform(-0.02, 0.02), 3)
                g_load = round(g_peak + self.rng.uniform(-0.3, 0.3), 2)
                fuel_flow = round(5200.0 + self.rng.uniform(-80.0, 80.0), 1)
                temp_c = round(740.0 + self.rng.uniform(-6.0, 6.0), 1)
                press_psi = round(50.0 + self.rng.uniform(-1.0, 1.0), 1)
                vib_ips = round(0.38 + self.rng.uniform(-0.04, 0.04), 3)
                surf_deg = round(16.5 + self.rng.uniform(-1.5, 1.5), 1)

            elif profile == "SUPERSONIC_CRUISE":
                # High altitude supercruise Mach 1.45+
                alt_ft = 45000.0 + self.rng.uniform(-80.0, 80.0)
                spd_kts = 850.0 + self.rng.uniform(-15.0, 15.0)
                mach = round(1.48 + self.rng.uniform(-0.03, 0.03), 3)
                g_load = round(1.0 + self.rng.uniform(-0.05, 0.05), 2)
                fuel_flow = round(6400.0 + self.rng.uniform(-100.0, 100.0), 1)
                temp_c = round(765.0 + self.rng.uniform(-5.0, 5.0), 1)
                press_psi = round(58.0 + self.rng.uniform(-1.0, 1.0), 1)
                vib_ips = round(0.32 + self.rng.uniform(-0.03, 0.03), 3)
                surf_deg = round(1.2 + self.rng.uniform(-0.3, 0.3), 1)

            elif profile == "THERMAL_SPIKE":
                # Turbine over-temperature divergence (useful for predictive maintenance trigger)
                temp_base = 680.0 + (step * 25.0)  # Ascending thermal progression
                alt_ft = 28000.0 + self.rng.uniform(-50.0, 50.0)
                spd_kts = 490.0 + self.rng.uniform(-5.0, 5.0)
                mach = 0.84
                g_load = 1.05
                fuel_flow = 3600.0
                temp_c = round(temp_base + self.rng.uniform(-4.0, 4.0), 1)
                press_psi = round(44.0 + self.rng.uniform(-1.0, 1.0), 1)
                vib_ips = round(0.22 + self.rng.uniform(-0.02, 0.02), 3)
                surf_deg = 0.8

            elif profile == "VIBRATION_SPIKE":
                # Mechanical fatigue or bearing vibration oscillation
                vib_val = 0.20 + (step * 0.075)  # Climbing vibration amplitude
                alt_ft = 30000.0 + self.rng.uniform(-50.0, 50.0)
                spd_kts = 475.0 + self.rng.uniform(-5.0, 5.0)
                mach = 0.81
                g_load = 1.0
                fuel_flow = 2500.0
                temp_c = 660.0
                press_psi = round(42.0 - (step * 1.5), 1)  # Pressure drop
                vib_ips = round(vib_val + self.rng.uniform(-0.02, 0.02), 3)
                surf_deg = 0.5

            frame = TelemetryInput(
                observation_id=obs_id,
                timestamp=t_curr,
                aircraft_id=aircraft_id,
                flight_id=fid,
                altitude=alt_ft,
                airspeed=spd_kts,
                mach=mach,
                g_load=g_load,
                fuel_flow=fuel_flow,
                engine_temperature=temp_c,
                engine_pressure=press_psi,
                vibration=vib_ips,
                control_surface_angle=surf_deg,
                units={
                    "altitude": "ft",
                    "airspeed": "kts",
                    "temperature": "C",
                    "pressure": "psi",
                    "vibration": "ips",
                    "fuel_flow": "kg/h",
                },
                source="synthetic_demo",
            )
            observations.append(frame)

        return observations
