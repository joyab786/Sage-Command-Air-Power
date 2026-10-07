# Aero Domain Model Specification — SIH Canonical Baseline

**Document Version:** 1.0.0  
**Phase:** Phase 2 — Aero SIH Canonical Domain Model  
**Status:** ✅ Implemented & Verified  
**Scope:** Smart India Hackathon (SIH) Prototype Domain Foundation  

---

## 1. Domain Boundary

The **SageCommand Air Power System (Aero)** domain models aerospace assets, telemetry signals, physical component health, maintenance workflows, combat readiness states, and sortie mission commitments.

### Aerospace-First Domain Scope
Aero adheres strictly to a dedicated aerospace-first domain boundary. The architecture introduces purpose-built aeronautical primitives:
* `Aircraft`, `Subsystem Component (LRU)`, `Telemetry Observation`, `Maintenance Event`, `Readiness Assessment`, and `Mission / Sortie`.

---

## 2. Core Architecture & Entity Hierarchy

```
                            Aircraft
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
       Components          Telemetry      Health / Readiness
            │                  │                  │
      Maintenance              │                  ▼
                               │         Mission Availability
                               ▼
                   Prognostics & Insights
```

### Detailed Structural Mapping:
```
Aircraft (Airframe Asset)
│
├── Components (Subsystems & LRUs: Engine, Hydraulics, Avionics, Radar)
│      │
│      └── Maintenance (Servicing, Inspections, Predictive Work Orders)
│
├── Telemetry (Aerodynamic, Propulsion, Mechanical observations)
│
├── Health / Readiness (FMC, PMC, NMC Classification)
│
└── Mission Availability (Operational sorties, required vs assigned airframes)
```

---

## 3. Core Entities

### 3.1 Aircraft (`app.domain.aircraft.AircraftBase`)
Represents an authoritative airframe asset, its registration, home base, squadron assignment, lifecycle status, and cumulative operational metrics.
* `aircraft_id` (`str`): Unique aircraft identifier (e.g., `ac_su30_01`).
* `tail_number` (`str`): Tactical tail / registration code (e.g., `SB-021`). Unique across fleet.
* `aircraft_type` (`str`): Aircraft type/platform (e.g., `Su-30MKI`, `Rafale`, `Tejas Mk1A`).
* `variant` (`Optional[str]`): Sub-variant or block standard (e.g., `Super Sukhoi`, `FOC`).
* `air_base` (`str`): Stationed operational air base (e.g., `Pune AFS`, `Sulur AFS`).
* `squadron` (`str`): Assigned operational squadron unit designation (e.g., `No. 20 Lightnings`).
* `status` (`AircraftStatus`): Airframe lifecycle state (`ACTIVE`, `MAINTENANCE`, `GROUNDED`, `RETIRED`).
* `total_flight_hours` (`float`): Cumulative flight hours logged ($\ge 0.0$).
* `total_flight_cycles` (`int`): Cumulative take-off/landing/stress cycles logged ($\ge 0$).
* `last_flight_at` (`Optional[datetime]`): Timestamp of most recent flight sortie.
* `created_at` / `updated_at` (`datetime`): Bitemporal registration timestamps.

### 3.2 Component (`app.domain.component.ComponentBase`)
Represents an aircraft subsystem or Line Replaceable Unit (LRU), tracking serial identity, parent airframe link, operational hours/cycles, and condition.
* `component_id` (`str`): Unique component identifier (e.g., `comp_al31fp_01`).
* `aircraft_id` (`str`): Foreign identifier of host airframe.
* `component_type` (`ComponentType`): Standardized subsystem classification (`TURBOFAN_ENGINE`, `HYDRAULICS`, `AVIONICS`, `RADAR`, `ELECTRICAL`, `LANDING_GEAR`, `FUEL_SYSTEM`, `AIRFRAME`, `FLIGHT_CONTROL`).
* `serial_number` (`str`): Manufacturer serial number (unique).
* `health_state` (`ComponentHealth`): Subsystem health (`HEALTHY`, `DEGRADED`, `WARNING`, `CRITICAL`, `FAILED`).
* `installation_date` (`Optional[datetime]`): Date of airframe integration.
* `accumulated_hours` (`float`): Subsystem operational hours ($\ge 0.0$).
* `accumulated_cycles` (`int`): Thermal / operational stress cycles ($\ge 0$).
* `last_maintenance_at` (`Optional[datetime]`): Timestamp of most recent service.

### 3.3 Telemetry Observation (`app.domain.telemetry.TelemetryObservation`)
Represents a normalized sensor observation frame across avionics, propulsion, and flight envelope parameters.
* `observation_id` (`str`): Unique telemetry frame identifier.
* `timestamp` (`datetime`): Timestamp of sensor acquisition.
* `aircraft_id` (`str`): Foreign identifier of generating aircraft.
* `flight_id` (`Optional[str]`): Active flight/sortie identifier.
* `altitude_ft` (`Optional[float]`): Altitude in feet.
* `airspeed_kts` (`Optional[float]`): Airspeed in knots ($\ge 0.0$).
* `mach` (`Optional[float]`): Flight Mach ratio ($\ge 0.0$).
* `g_load` (`Optional[float]`): Normal acceleration ($G_z$).
* `fuel_flow_kg_h` (`Optional[float]`): Fuel burn rate ($\ge 0.0$).
* `engine_temperature_c` (`Optional[float]`): Exhaust Gas Temperature (EGT) in Celsius.
* `engine_pressure_psi` (`Optional[float]`): Engine oil/hydraulic pressure in PSI.
* `vibration_ips` (`Optional[float]`): Vibration amplitude in inches per second ($\ge 0.0$).
* `control_surface_angle_deg` (`Optional[float]`): Deflection angle in degrees.
* `quality` (`TelemetryQuality`): Signal integrity indicator (`GOOD`, `DEGRADED`, `SUSPECT`, `INVALID`).
* `source` (`str`): Origin (`SIMULATION`, `TELEMETRY_STREAM`, `FDR`).
* `unit_metadata` (`Optional[Dict[str, str]]`): Explicit engineering unit metadata.

### 3.4 Maintenance Event (`app.domain.maintenance.MaintenanceEventBase`)
Represents maintenance servicing actions, inspections, and predictive work orders.
* `maintenance_event_id` (`str`): Unique maintenance event identifier.
* `aircraft_id` (`str`): Target airframe identifier.
* `component_id` (`Optional[str]`): Affected subsystem or LRU identifier.
* `maintenance_type` (`MaintenanceType`): Classification (`SCHEDULED`, `UNSCHEDULED`, `PREDICTIVE`, `INSPECTION`, `CORRECTIVE`).
* `status` (`MaintenanceStatus`): State (`OPEN`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`).
* `priority` (`MaintenancePriority`): Urgency (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
* `detected_at` (`datetime`): Timestamp when maintenance need was recognized.
* `scheduled_at` / `completed_at` (`Optional[datetime]`): Execution schedule timestamps.
* `description` (`str`): Diagnostic issue explanation and required remediation.
* `source` (`str`): Detection origin (`MANUAL`, `PREDICTIVE_RUL`, `ANOMALY_DETECTOR`, `PILOT_DEBRIEF`).

### 3.5 Readiness Assessment (`app.domain.readiness.ReadinessAssessmentBase`)
Represents standardized military mission readiness evaluations.
* `assessment_id` (`str`): Unique evaluation identifier.
* `aircraft_id` (`str`): Target airframe identifier.
* `readiness_status` (`ReadinessStatus`): Status classification (`FMC`, `PMC`, `NMC`).
* `assessed_at` (`datetime`): Timestamp of evaluation.
* `reasons` (`List[str]`): Defensible causal justification or degradation factors.
* `limiting_components` (`List[str]`): Subsystems preventing full capability.
* `confidence` (`float`): Assessment confidence score ($0.0 \le \text{confidence} \le 1.0$).

### 3.6 Mission / Sortie (`app.domain.mission.MissionBase`)
Represents tactical mission commitments and airframe demand.
* `mission_id` (`str`): Unique mission identifier.
* `mission_name` (`Optional[str]`): Tactical operation or exercise codename.
* `mission_type` (`MissionType`): Profile (`COMBAT_AIR_PATROL`, `INTERCEPTION`, `STRIKE`, `RECONNAISSANCE`, `TRAINING`, `ESCORT`, `FERRY`).
* `scheduled_start` / `scheduled_end` (`datetime`): Mission launch and recovery bounds.
* `required_aircraft` (`int`): Minimum number of mission-capable airframes ($> 0$).
* `assigned_aircraft` (`List[str]`): List of allocated aircraft IDs / tail numbers.
* `status` (`MissionStatus`): Execution status (`PLANNED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `ABORTED`, `CANCELLED`).
* `readiness_requirement` (`ReadinessStatus`): Minimum required airframe capability (`FMC`, `PMC`, `NMC`).

---

## 4. Enumerations (`app.domain.enums`)

| Enum Name | Allowed Values | Semantic Definition |
| :--- | :--- | :--- |
| **`AircraftStatus`** | `ACTIVE`, `MAINTENANCE`, `GROUNDED`, `RETIRED` | Operational lifecycle of airframe |
| **`ComponentHealth`** | `HEALTHY`, `DEGRADED`, `WARNING`, `CRITICAL`, `FAILED` | Condition of physical subsystem |
| **`ComponentType`** | `TURBOFAN_ENGINE`, `HYDRAULICS`, `AVIONICS`, `ELECTRICAL`, `RADAR`, `LANDING_GEAR`, `FUEL_SYSTEM`, `AIRFRAME`, `FLIGHT_CONTROL`, `OTHER` | LRU classification |
| **`TelemetryQuality`**| `GOOD`, `DEGRADED`, `SUSPECT`, `INVALID` | Signal fidelity and transmission health |
| **`MaintenanceStatus`**| `OPEN`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | Work order progression |
| **`MaintenancePriority`**| `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Turnaround urgency |
| **`MaintenanceType`** | `SCHEDULED`, `UNSCHEDULED`, `PREDICTIVE`, `INSPECTION`, `CORRECTIVE` | Origin classification |
| **`ReadinessStatus`** | `FMC`, `PMC`, `NMC` | Defense aviation mission readiness rating |
| **`MissionStatus`**   | `PLANNED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `ABORTED`, `CANCELLED` | Sortie scheduling and execution state |
| **`MissionType`**     | `COMBAT_AIR_PATROL`, `INTERCEPTION`, `STRIKE`, `RECONNAISSANCE`, `TRAINING`, `ESCORT`, `FERRY` | Tactical sortie category |

---

## 5. Domain Invariants and Validation Rules

All validation rules are strictly enforced at the Pydantic schema layer and verified at database commit:
1. **Total Flight Hours & Cycles:** `total_flight_hours >= 0.0` and `total_flight_cycles >= 0`. Negative values are rejected with schema validation errors.
2. **Whitespace Stripping:** All string identifiers (`aircraft_id`, `tail_number`, `air_base`, `squadron`, `component_id`, `serial_number`, `mission_id`) automatically trim leading/trailing whitespace. Purely empty or whitespace strings are rejected.
3. **Component Wear Bounds:** `accumulated_hours >= 0.0` and `accumulated_cycles >= 0`.
4. **Maintenance Temporal Ordering:** If `completed_at` is present, it cannot precede `detected_at`.
5. **Mission Scheduling Boundaries:** `scheduled_end >= scheduled_start`. A mission cannot conclude before launch.
6. **Mission Airframe Demand:** `required_aircraft > 0`. A mission cannot demand 0 airframes.
7. **Readiness Evaluation Confidence:** $0.0 \le \text{confidence} \le 1.0$.
8. **Physical Telemetry Limits:** `airspeed_kts >= 0.0`, `mach >= 0.0`, `fuel_flow_kg_h >= 0.0`, and `vibration_ips >= 0.0`.

---

## 6. Database Mapping (`app.db.models`)

The domain entities are persisted in SQLite WAL using SQLAlchemy 2.0 declarative models:

```
┌────────────────────────┐         1:N         ┌────────────────────────┐
│        aircraft        │────────────────────<│       components       │
├────────────────────────┤                     ├────────────────────────┤
│ PK aircraft_id         │                     │ PK component_id        │
│ UK tail_number         │                     │ FK aircraft_id (CASCADE)│
│    aircraft_type       │                     │ UK serial_number       │
│    status              │                     │    health_state        │
│    total_flight_hours  │                     │    accumulated_hours   │
└───────────┬────────────┘                     └───────────┬────────────┘
            │                                              │
            │ 1:N                                          │ 1:N
            ▼                                              ▼
┌────────────────────────┐                     ┌────────────────────────┐
│ readiness_assessments  │                     │   maintenance_events   │
├────────────────────────┤                     ├────────────────────────┤
│ PK assessment_id       │                     │ PK maintenance_event_id│
│ FK aircraft_id (CASCADE)│                    │ FK aircraft_id (CASCADE)│
│    readiness_status    │                     │ FK component_id (SET NULL)
│    assessed_at (DESC)  │                     │    status, priority    │
│    reasons (JSON)      │                     │    detected_at         │
│    limiting_comps(JSON)│                     └────────────────────────┘
└────────────────────────┘
```

* **Cascading Deletions:** Deleting an airframe cascades to its installed components, historical readiness assessments, and maintenance work orders.
* **Component Uncoupling:** Removing a component sets `component_id` to `NULL` on historical maintenance events to preserve audit trail integrity.
* **JSON Array Storage:** Complex lists (`reasons`, `limiting_components`, `assigned_aircraft`) are serialized via SQLAlchemy's cross-dialect `JSON` type.

---

## 7. REST API Mapping

All domain endpoints return standardized `ApiResponse[T]` envelopes with ISO-8601 UTC timestamps and request correlation tracking.

| HTTP Method | Route | Description | Response Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/aircraft` | Query aircraft assets (filters: `status`, `squadron`, `air_base`) | `200 OK` |
| `POST` | `/api/v1/aircraft` | Register a new aircraft airframe asset | `201 Created` / `409 Conflict` |
| `GET` | `/api/v1/aircraft/{id}` | Retrieve specific aircraft by identifier | `200 OK` / `404 Not Found` |
| `GET` | `/api/v1/aircraft/{id}/components` | Retrieve installed subsystem components | `200 OK` / `404 Not Found` |
| `POST` | `/api/v1/aircraft/{id}/components` | Install/register subsystem component | `201 Created` / `409 Conflict` |
| `GET` | `/api/v1/aircraft/{id}/readiness` | Retrieve latest/derived readiness evaluation | `200 OK` / `404 Not Found` |
| `POST` | `/api/v1/aircraft/{id}/readiness` | Record explicit readiness evaluation | `201 Created` |
| `GET` | `/api/v1/missions` | Query operational missions (filters: `status`, `mission_type`) | `200 OK` |
| `POST` | `/api/v1/missions` | Register tactical mission schedule commitment | `201 Created` / `409 Conflict` |
| `GET` | `/api/v1/missions/{id}` | Retrieve specific mission by identifier | `200 OK` / `404 Not Found` |

---

## 8. SIH Relevance & Alignment

Every domain entity directly supports the Smart India Hackathon operational walkthrough:
1. **`Aircraft`**: Provides asset identity and baseline fleet availability.
2. **`Component`**: Provides physical wear targets for thermal stress and hydraulic pressure degradation.
3. **`TelemetryObservation`**: Ingests multi-channel flight envelopes and flags abnormal parameter drift.
4. **`MaintenanceEvent`**: Converts analytical predictions into actionable servicing work packages.
5. **`ReadinessAssessment`**: Reclassifies airframe capability (`FMC` $\to$ `PMC` $\to$ `NMC`) based on detected faults.
6. **`Mission`**: Demonstrates the ultimate operational consequence—verifying whether a squadron has sufficient capable airframes to launch scheduled sorties.

---

## 9. Explicitly Deferred Concepts

The following features are intentionally out of scope for Phase 2:
* ⚠️ **High-Frequency Ingestion Pipelines:** Timeseries streaming databases and Kafka queues (deferred to Phase 3 — Telemetry Data Fabric).
* ⚠️ **Autonomous Anomaly Detection Models:** Z-score baselines and ML classifiers (deferred to Phase 5 — Intelligence Layer).
* ⚠️ **Predictive RUL Algorithms:** Physics-informed degradation models (deferred to Phase 5).
* ⚠️ **Weapons & Tactical Combat Targeting:** Purely civil-defense and readiness focused; offensive engagement logic is out of scope.
* ⚠️ **Maintenance Optimization Scheduling Solvers:** Heuristic dispatch engines (deferred to Phase 6+).
