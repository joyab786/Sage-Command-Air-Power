# SageCommand Air Power System — Aero
# Aircraft Digital Twin State Estimation Specification (Phase 4 SIH MVP)

**Document Version:** 1.0.0  
**Phase:** Phase 4 — Aircraft Digital Twin State Estimation  
**Status:** IMPLEMENTED & TESTED (129 Total Automated Tests Passing)  
**Date:** 2026-10-06  

---

> [!IMPORTANT]
> **SIH Demonstration Notice:**  
> The health scores, subsystem wear ratings, and degradation models in this implementation are **deterministic engineering demonstration models** designed for Smart India Hackathon (SIH) prototype evaluation. They **DO NOT** represent certified aircraft maintenance algorithms, military OEM lifing models, or civil aviation airworthiness authority certifications (e.g., CEMILAC, DGCA, FAA, EASA).

---

## 1. Digital Twin Purpose & Boundary

The **Aircraft Digital Twin State Estimation Layer** establishes a continuous, deterministic, and explainable representation of an aircraft's operational state by consuming normalized flight telemetry streams from Phase 3.

It acts as an observational and analytical state bridge between raw sensor data and downstream operational intelligence (such as anomaly detection, predictive maintenance, and mission readiness scoring).

### Governance Boundary
The Digital Twin is strictly **observational and analytical**. It does not perform autonomous flight control, flight surface actuation, autopilot commands, weapon targeting, or weapon release.

```
       [ Normalized Telemetry Stream ]
       (Phase 3 Ingestion Pipeline)
                     │
                     ▼
       ┌─────────────────────────────┐
       │   DigitalTwinService        │
       │  - Coordinates updates      │
       │  - Enforces aircraft checks │
       │  - Rejects INVALID packets  │
       └─────────────┬───────────────┘
                     │
                     ▼
       ┌─────────────────────────────┐
       │    DigitalTwinEstimator     │
       │  - State memory / fusion    │
       │  - Retains missing channels │
       │  - Flight session tracking  │
       └──────┬───────────────┬──────┘
              │               │
              ▼               ▼
     ┌─────────────────┐ ┌─────────────────┐
     │ HealthEstimator │ │  WearEstimator  │
     │ - Thermal       │ │ - Flight Hours  │
     │ - Vibration     │ │ - Flight Cycles │
     │ - Pressure      │ │ - Dynamic Stress│
     │ - Structural G  │ │ - [0.0 - 1.0]   │
     │ - Explainability│ │   Wear Index    │
     └────────┬────────┘ └────────┬────────┘
              │                   │
              └─────────┬─────────┘
                        ▼
       ┌─────────────────────────────┐
       │      AircraftTwinState      │
       │  - Airframe state snapshot  │
       │  - Subsystem breakdowns     │
       │  - Structured reasons       │
       └─────────────┬───────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  REST Twin API  │     │   SQLite WAL    │
│  /twin          │     │  - Twin states  │
│  /twin/history  │     │  - Sessions     │
└─────────────────┘     └─────────────────┘
```

---

## 2. State Model (`AircraftTwinState`)

The authoritative operational snapshot is represented by `AircraftTwinState`:

| Field | Type | Description |
| :--- | :--- | :--- |
| `aircraft_id` | `str` | Authoritative aircraft airframe identifier |
| `timestamp` | `datetime` | UTC timestamp of the estimated state snapshot |
| `operational_status` | `str` | Current flight status (`ACTIVE`, `IN_FLIGHT`, etc.) |
| `altitude` | `float?` | Current altitude in meters (m) |
| `airspeed` | `float?` | Current true airspeed in meters/second (m/s) |
| `mach` | `float?` | Current Mach number |
| `g_load` | `float?` | Normal acceleration factor in G units |
| `fuel_flow` | `float?` | Current fuel burn rate in kg/h |
| `engine_temperature` | `float?` | Core engine temperature in Celsius (°C) |
| `engine_pressure` | `float?` | Core engine pressure in kPa |
| `vibration` | `float?` | Mechanical vibration amplitude in ips |
| `flight_hours` | `float` | Cumulative operating flight hours |
| `flight_cycles` | `int` | Cumulative completed flight cycles / sorties |
| `current_flight_id` | `str?` | Active sortie/flight identifier |
| `health_state` | `TwinHealthState` | `HEALTHY`, `DEGRADED`, `WARNING`, `CRITICAL`, `FAILED` |
| `health_score` | `float` | Composite airframe health score (0.0 to 100.0) |
| `wear_index` | `float` | Normalized composite wear index (0.0 to 1.0) |
| `subsystem_states` | `dict` | Conceptual subsystem states map |
| `health_reasons` | `list` | Structured explainability reasons for score degradation |
| `active_warnings` | `list` | Operational alarms or boundary warnings |
| `data_quality` | `str` | Telemetry input quality rating (`VALID`, `DEGRADED`, `BASELINE`) |

---

## 3. Telemetry Integration & State Memory

When telemetry is ingested through `POST /api/v1/telemetry`:
1. **Filtering:** Telemetry evaluated as `INVALID` (e.g. unphysical pressure, NaN values) is **never forwarded to the digital twin**, preventing corrupted state mutations.
2. **State Memory (Sparse Frame Retention):** Real-world telemetry packets may omit non-critical or high-latency channels. The `DigitalTwinEstimator` retains prior valid values rather than overwriting them with defaults:
   - Example: If previous altitude was `8,500m` and a new packet arrives without altitude, the twin **retains 8,500m**.
3. **Operational Transition:** Airspeed $> 30\text{ m/s}$ automatically sets `operational_status = "IN_FLIGHT"` and updates `aircraft.last_flight_at`.

---

## 4. Health Scoring & Explainability

Airframe health is calculated deterministically on a scale of 0 to 100 with strict penalty contributions:

$$Score = \max(0.0, \min(100.0, 100.0 - \sum |Penalty_i|))$$

### Health State Bands
* **90 – 100:** `HEALTHY` (Nominal flight parameters, within envelope)
* **75 – 89:** `DEGRADED` (Minor cautions, missing secondary channels)
* **50 – 74:** `WARNING` (Operating in caution region, elevated heat/vibration)
* **25 – 49:** `CRITICAL` (Single hard limit breached, severe structural stress)
* **0 – 24:** `FAILED` (Multiple simultaneous limit breaches, unphysical stress)

### Deterministic Penalty Rules
* **Thermal Stress:**
  * $T > 1050^\circ\text{C}$: $-35.0$ (Critical turbine thermal exceedance)
  * $T > 950^\circ\text{C}$: $-20.0$ (Elevated engine temperature caution)
  * $T > 900^\circ\text{C}$: $-8.0$ (Engine temperature elevated)
* **Mechanical Vibration:**
  * $V > 1.25\text{ ips}$: $-35.0$ (Severe vibration exceedance)
  * $V > 0.85\text{ ips}$: $-20.0$ (Elevated vibration caution)
  * $V > 0.65\text{ ips}$: $-8.0$ (Vibration above nominal)
* **Core Pressure Anomaly:**
  * $P < 150\text{ kPa}$ or $P > 2100\text{ kPa}$: $-30.0$ (Critical pressure anomaly)
  * $P < 200\text{ kPa}$ or $P > 1800\text{ kPa}$: $-15.0$ (Engine pressure caution)
* **Structural G-Load:**
  * $G > 9.0$ or $G < -3.0$: $-35.0$ (Critical structural G exceedance)
  * $G > 7.5$ or $G < -2.0$: $-18.0$ (Aerodynamic G caution limit)
* **Telemetry Quality:**
  * `DEGRADED`: $-12.0$ (Fidelity degraded or missing optional channels)

### Explainability Output
Every degradation includes a transparent `HealthReason`:
```json
{
  "signal": "engine_temperature",
  "observed": 1070.0,
  "contribution": -35.0,
  "reason": "Critical turbine thermal exceedance (1070.0°C > 1050.0°C limit)"
}
```

---

## 5. Conceptual Subsystem Health Model

The digital twin models 6 conceptual subsystems:

| Subsystem | Contributing Telemetry Signals | Behavior & Handling |
| :--- | :--- | :--- |
| **`PROPULSION`** | `engine_temperature`, `engine_pressure`, `vibration`, `fuel_flow` | Tracks thermal and mechanical stresses; degrades upon hot/vibrating conditions. |
| **`STRUCTURE`** | `g_load`, `flight_hours`, `flight_cycles` | Tracks aerodynamic loads and airframe cumulative fatigue. |
| **`FLIGHT_CONTROLS`** | `control_surface_angle`, `quality_status` | Tracks surface deflections and sensor channel fidelity. |
| **`AVIONICS`** | `telemetry_quality`, `clock_integrity` | Tracks data flow fidelity, packet omissions, and clock skew. |
| **`FUEL`** | `fuel_flow` | Tracks burn rate consistency. Degraded if fuel flow channel is missing. |
| **`HYDRAULIC`** | *(Unobserved)* | **Never manufactures fake sensor data.** Explicitly reports `health_state = UNKNOWN` with warning: *"No dedicated hydraulic sensor telemetry channel present; state unobserved"*. |

---

## 6. Wear Estimation

The `WearEstimator` computes a normalized wear indicator between `0.0` and `1.0`:

* **Base Time Component:** Hours scaled against nominal demonstration TBO of 4,000 hours (max 0.40).
* **Base Cycle Component:** Cycles scaled against nominal demonstration design life of 2,000 cycles (max 0.30).
* **Thermal Stress Increment:** Added when turbine temperatures exceed 950°C.
* **Vibration Fatigue Increment:** Added when vibration amplitudes exceed 0.85 ips.
* **High-G Fatigue Increment:** Added when aerodynamic loading exceeds 7.0 G.
* **Monotonic Wear Retention:** Current wear index never decreases below previously accumulated baseline wear.

---

## 7. Flight Hours, Cycles & Session Tracking

To handle high-rate telemetry without artificial counter inflation:
* **Single Flight Multipacket Safety:** Ingesting 1,000 frames for a single sortie does **not** increment flight cycles 1,000 times.
* **Elapsed Duration Calculation:**
  $$\Delta t = timestamp_{current} - timestamp_{last\_seen}$$
  If $0 < \Delta t \le 3600\text{ seconds}$, $\Delta t$ is added to session duration and $\Delta t / 3600$ is added to cumulative flight hours.
* **Cycle Increment Rule:**
  * When a new `flight_id` arrives, any prior open flight session for that aircraft is closed and marked `cycle_counted = True`, incrementing airframe cycles by 1.
  * Explicitly calling `close_flight()` also closes the active session and increments cycles exactly once.

---

## 8. Relational Persistence

State data is persisted under the existing SQLite WAL infrastructure:
* **`aircraft_twin_states` Table:**
  * Primary key: `state_id`
  * Foreign key: `aircraft_id` references `aircraft.aircraft_id`
  * Composite Index: `ix_twin_aircraft_timestamp` on `(aircraft_id, timestamp)`
  * Stores complete state snapshots, subsystem states (JSON), and explainability reasons (JSON).
* **`flight_sessions` Table:**
  * Composite Index: `ix_session_aircraft_flight` on `(aircraft_id, flight_id)`
  * Tracks start time, last seen time, duration, and cycle count status.

---

## 9. REST API Endpoints

All endpoints use standard `ApiResponse[T]` envelopes:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/aircraft/{aircraft_id}/twin` | Retrieves current estimated digital twin state (or baseline if unobserved). |
| `GET` | `/api/v1/aircraft/{aircraft_id}/twin/history` | Retrieves chronological historical twin snapshots (`limit`, `offset`). |

---

## 10. Synthetic Demonstration Scenarios

The existing Phase 3 synthetic generator exercises the Digital Twin:

1. **`NORMAL_CRUISE`:** Produces `health_score = 100.0`, `health_state = HEALTHY`, nominal wear.
2. **`HIGH_G_TURN`:** Sustained 6.0G–8.2G maneuvers increment structural wear index and trigger G-load caution warnings.
3. **`THERMAL_SPIKE`:** Combustor temperatures reaching 1,070°C degrade composite score to `WARNING`/`CRITICAL` ($<75$) with structured explainability: `"Critical turbine thermal exceedance"`.
4. **`VIBRATION_SPIKE`:** Vibration reaching 1.35 ips degrades propulsion subsystem with reason: `"Severe mechanical vibration exceedance"`.

---

## 11. Limitations & Future Roadmap

1. **Rule-Based vs. Physics-Informed:** Current models use deterministic rules and heuristic lifing curves. Future phases will introduce physics-informed prognostics and Remaining Useful Life (RUL) estimation.
2. **Sensor Coverage:** Subsystems without direct telemetry (e.g., Hydraulic) report `UNKNOWN` rather than simulated sensor readings.
3. **Analytical Isolation:** The twin remains strictly an analytical decision-support tool with zero write authority over flight control or tactical weapons.
