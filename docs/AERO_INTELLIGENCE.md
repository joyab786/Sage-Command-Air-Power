# SageCommand Air Power System (Aero) — Subsystem Intelligence & Anomaly Detection (SIH MVP)

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Subsystem Intelligence & Anomaly Detection  
**Status:** IMPLEMENTED & VERIFIED BASELINE (166 Automated Tests Passing)  
**Date:** 2026-10-06  

---

> **CRITICAL DISCLAIMER:**  
> Phase 5 intelligence is deterministic and explainable. Thresholds and statistical baselines are SIH demonstration models and are not certified aircraft diagnostic algorithms. Recommendations produced by this system are advisory decision-support outputs and do not execute autonomous flight controls, weapon targeting, or maintenance actions.

---

## 1. Executive Summary & SIH Value Proposition

The **SageCommand Air Power System (Aero)** Subsystem Intelligence Layer translates raw flight telemetry and real-time digital twin state estimation into actionable, explainable operational intelligence:

```text
Telemetry + Digital Twin State
              ↓
      Anomaly Detection
(Threshold & Statistical Detectors)
              ↓
  Correlation & Deduplication
(Alert-Storm Suppression Window)
              ↓
     Subsystem Diagnosis
(Multi-Signal Root-Cause Synthesis)
              ↓
   Confidence & Evidence
(Explainable Bounded Assessment)
              ↓
  Maintenance Recommendations
 (Advisory Urgency Prioritization)
              ↓
      Readiness Impact
```

### The SIH Operational Narrative
1. **Host Aircraft:** Aircraft airframe (e.g., `AERO-001`).
2. **Telemetry Stream:** Ingestion of continuous operational parameters.
3. **Physical Deviation:** Turbine temperature exceeds caution band or vibration spikes.
4. **Digital Twin Degradation:** Digital twin updates health score and flags degraded subsystem state.
5. **Deterministic Detection:** Anomaly engine identifies thermal or mechanical violation with exact deviation from nominal demonstration bounds.
6. **Multi-Signal Correlation:** Concurrent thermal and vibration evidence fuses into a `MULTI_SIGNAL_ANOMALY`, boosting diagnostic confidence above $0.90$.
7. **Root-Cause Attribution:** Diagnosis engine isolates probable hot section distress and recommends urgent borescope inspection.
8. **Actionable Recommendation:** Advisory maintenance generator issues a `GROUND_FOR_REVIEW` or `SCHEDULE_MAINTENANCE` advisory with structured justification.
9. **Readiness Reassessment:** Command staff re-evaluate tactical readiness status (`FMC` $\to$ `PMC` or `NMC`).

---

## 2. Intelligence Architecture

The intelligence pipeline is encapsulated within the `app.intelligence` package:

```text
backend/app/intelligence/
├── __init__.py                  # Package exports (models, detectors, engines, service)
├── models.py                    # Strongly typed Pydantic contracts & enums
├── anomaly/
│   ├── __init__.py              # Anomaly package exports
│   ├── base.py                  # BaseAnomalyDetector protocol interface
│   ├── threshold.py             # ThresholdAnomalyDetector (deterministic boundary rules)
│   ├── statistical.py           # StatisticalAnomalyDetector (rolling z-score baseline)
│   └── detectors.py             # CompositeAnomalyDetector (orchestrator)
├── diagnosis/
│   ├── __init__.py              # Diagnosis package exports
│   ├── rules.py                 # Structured probable-cause inference rules catalog
│   └── root_cause.py            # RootCauseDiagnosisEngine (multi-signal fusion)
├── maintenance.py               # MaintenanceRecommendationEngine (decision-support advisories)
└── service.py                   # IntelligenceService (orchestration, correlation, WAL persistence)
```

### Pipeline Execution Lifecycle
1. Telemetry is received via `POST /api/v1/telemetry`.
2. Telemetry is normalized, quality-checked, and checked against flight envelope boundaries.
3. Telemetry is committed to the relational database and the **Digital Twin State Estimator** updates the aircraft twin.
4. Telemetry and current digital twin state are provided to `IntelligenceService.process_telemetry()`.
5. If telemetry is `INVALID`, intelligence processing is safely bypassed (no spurious alerts).
6. Detectors execute in composite isolation; uncaught exceptions are caught cleanly without impeding ingestion.
7. Candidate anomalies are correlated and deduplicated against open database records within a configurable correlation window ($300\text{ s}$).
8. Root-cause diagnostic synthesis and maintenance recommendation generation are evaluated and stored.

---

## 3. Data Model & Controlled Vocabularies

### Controlled Vocabularies

```python
class AnomalySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AnomalyStatus(str, Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class AnomalyType(str, Enum):
    THERMAL_ANOMALY = "THERMAL_ANOMALY"
    VIBRATION_ANOMALY = "VIBRATION_ANOMALY"
    PRESSURE_ANOMALY = "PRESSURE_ANOMALY"
    G_LOAD_ANOMALY = "G_LOAD_ANOMALY"
    FUEL_FLOW_ANOMALY = "FUEL_FLOW_ANOMALY"
    CONTROL_SURFACE_ANOMALY = "CONTROL_SURFACE_ANOMALY"
    TELEMETRY_QUALITY_ANOMALY = "TELEMETRY_QUALITY_ANOMALY"
    FLIGHT_ENVELOPE_ANOMALY = "FLIGHT_ENVELOPE_ANOMALY"
    MULTI_SIGNAL_ANOMALY = "MULTI_SIGNAL_ANOMALY"

class RecommendationPriority(str, Enum):
    MONITOR = "MONITOR"
    INSPECT = "INSPECT"
    SCHEDULE_MAINTENANCE = "SCHEDULE_MAINTENANCE"
    GROUND_FOR_REVIEW = "GROUND_FOR_REVIEW"
```

### Core Schema Models

* **`Anomaly`**: Represents a single detected parameter deviation. Contains `anomaly_id`, `aircraft_id`, `flight_id`, `timestamp`, `subsystem`, `anomaly_type`, `severity`, `status`, `confidence`, `detector`, `signal`, `observed_value`, `expected_range`, `deviation`, `description`, `evidence`, `occurrence_count`, `first_detected_at`, and `last_detected_at`.
* **`Diagnosis`**: Synthesized root-cause assessment. Contains `diagnosis_id`, `aircraft_id`, `timestamp`, `primary_subsystem`, `probable_causes`, `supporting_anomalies`, `confidence`, `explanation`, and `signals_involved`.
* **`MaintenanceRecommendation`**: Advisory decision-support recommendation. Contains `recommendation_id`, `aircraft_id`, `priority`, `action`, `reason`, `related_anomalies`, `affected_subsystem`, and `confidence`.

---

## 4. Anomaly Detectors

### Common Detector Interface
All anomaly detectors adhere to the `BaseAnomalyDetector` protocol:

```python
class BaseAnomalyDetector(ABC):
    @property
    @abstractmethod
    def detector_name(self) -> str: ...

    @abstractmethod
    def detect(
        self,
        telemetry: NormalizedTelemetry,
        twin_state: Optional[AircraftTwinState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]: ...
```

### Threshold Detection Engine (`ThresholdAnomalyDetector`)
Deterministic physical boundary evaluator aligned with demonstration flight envelope limits:

| Subsystem | Signal Channel | Caution Threshold | Hard / Critical Limit | Severity Rating |
| :--- | :--- | :--- | :--- | :--- |
| **PROPULSION** | `engine_temperature_c` | $> 780.0\ ^\circ\text{C}$ | $> 850.0\ ^\circ\text{C}$ | `HIGH` / `CRITICAL` |
| **PROPULSION** | `vibration_ips` | $> 0.85\text{ ips}$ | $> 3.0\text{ ips}$ | `HIGH` / `CRITICAL` |
| **PROPULSION** | `engine_pressure_kpa` | $< 180$ or $> 600\text{ kPa}$ | $< 150$ or $> 650\text{ kPa}$ | `HIGH` / `CRITICAL` |
| **STRUCTURE** | `g_load` | $> 7.5\text{g}$ or $< -2.0\text{g}$ | $> 8.0\text{g}$ or $< -3.0\text{g}$ | `HIGH` / `CRITICAL` |
| **FLIGHT_CONTROLS** | `control_surface_angle_deg`| $|\theta| > 20.0^\circ$ | $|\theta| > 30.0^\circ$ | `HIGH` / `CRITICAL` |
| **AVIONICS** | `telemetry_quality` | `DEGRADED` status | `INVALID` (skipped) | `MEDIUM` |

### Lightweight Statistical Baseline Engine (`StatisticalAnomalyDetector`)
Implements rolling sample mean ($\mu$), sample standard deviation ($\sigma$), and z-score deviation:

$$z = \frac{x - \mu}{\sigma}$$

* **Safety against Zero Variance:** When $\sigma \le 10^{-4}$ (e.g. constant sensor stream), division by zero is safely prevented and no outlier alerts are issued.
* **Sample Gating:** Minimum observations ($N \ge 5$) are required before z-score deviation is activated.
* **Configurable Sensitivity:** Rolling window size (default $30$), minimum observations (default $5$), and z-score threshold (default $2.5$ to $3.0$).

### Baseline Scoping Hierarchy
To avoid cross-aircraft distortion or flight regime mismatch, baselines are scoped in a strict hierarchy:

```text
Level 1: Aircraft ID + Signal Channel + Flight Regime (Phase 6 prognostic extension)
                    ↓
Level 2: Aircraft ID + Signal Channel (Active Phase 5 Implementation)
                    ↓
Level 3: Configured Demonstration Envelope (Fallback Baseline)
```

---

## 5. Correlation & Alert Deduplication

To prevent command-center "alert storms", repeated detections of the same ongoing condition do not spawn redundant database records:

### Correlation Matching Criteria
A new detection is correlated to an existing active anomaly if:
1. `aircraft_id` matches.
2. `status` is currently open (`NEW` or `ACKNOWLEDGED`).
3. `subsystem`, `anomaly_type`, and `signal` match.
4. Elapsed time between `telemetry.timestamp` and `existing.last_detected_at` is $\le 300\text{ s}$ (configurable correlation window).

### Update Behavior on Match
* `occurrence_count` is incremented ($+1$).
* `last_detected_at` is updated to current observation time.
* `observed_value` and `deviation` update to latest readings.
* `confidence` increases gradually ($+0.02$ per confirmation, capped at $0.98$).
* `severity` is upgraded if the incoming severity is of higher rank.
* Novel evidence is merged into the record.

---

## 6. Root-Cause Diagnosis Engine

The `RootCauseDiagnosisEngine` synthesizes active anomalies, telemetry quality, and digital twin health into an explainable diagnosis.

### Multi-Signal Correlation Synthesis
When independent sensors observe correlated degradation, diagnostic confidence increases:
* **Thermal ($T > 780^\circ\text{C}$) + Mechanical Vibration ($V > 0.85\text{ ips}$):** Fuses into compound hot section/rotor dynamic anomaly with diagnostic confidence boosted to $\ge 0.93$.
* **Thermal + Vibration + Pressure Deviation:** Further boosts confidence to $0.96$.

### Telemetry Quality Confidence Penalty
If telemetry is rated `DEGRADED`, diagnostic confidence is discounted by $0.15$ ($15\%$) and transparently annotated:
> *"Telemetry quality was DEGRADED during observation; sensor fidelity exhibits reduced confidence."*

---

## 7. Actionable Maintenance Recommendations

The `MaintenanceRecommendationEngine` translates diagnostic assessments into prioritized decision-support maintenance actions:

```text
Priority Hierarchy:
  GROUND_FOR_REVIEW     (CRITICAL severity OR twin health < 50% OR multi-signal compound)
         ↓
  SCHEDULE_MAINTENANCE  (HIGH severity OR twin health < 75%)
         ↓
  INSPECT               (MEDIUM severity OR twin health < 90%)
         ↓
  MONITOR               (Nominal operating conditions)
```

### Safety & Governance Guardrails
* **Advisory Only:** Actions use transparent recommendation phrasing (*"Advisory: Recommend engineering inspection..."*).
* **Zero Autonomous Grounding:** The system does NOT directly ground aircraft or modify operational rosters without human operator review.

---

## 8. Relational Persistence & SQLite WAL

Anomalies are persisted in SQLite WAL using the `anomalies` table:

```sql
CREATE TABLE anomalies (
    anomaly_id VARCHAR(64) PRIMARY KEY,
    aircraft_id VARCHAR(64) NOT NULL REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
    flight_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    subsystem VARCHAR(64) NOT NULL,
    anomaly_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'NEW',
    confidence FLOAT NOT NULL DEFAULT 0.5,
    detector VARCHAR(128) NOT NULL,
    signal VARCHAR(128) NOT NULL,
    observed_value FLOAT,
    expected_range VARCHAR(128),
    deviation FLOAT DEFAULT 0.0,
    description TEXT NOT NULL,
    evidence JSON NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### Indexes
* `ix_anomalies_aircraft_status` (`aircraft_id`, `status`)
* `ix_anomalies_aircraft_severity` (`aircraft_id`, `severity`)
* `ix_anomalies_aircraft_subsystem` (`aircraft_id`, `subsystem`)
* `ix_anomalies_aircraft_time` (`aircraft_id`, `timestamp`)

---

## 9. API Reference

All routes are versioned under `/api/v1` and wrapped in standard `ApiResponse[T]`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/aircraft/{id}/anomalies` | Query detected anomalies with filters (`severity`, `status`, `subsystem`, `from`, `to`, `limit`, `offset`). |
| `GET` | `/api/v1/aircraft/{id}/anomalies/{anomaly_id}` | Query detailed anomaly record with full evidence context. |
| `POST` | `/api/v1/aircraft/{id}/anomalies/{anomaly_id}/acknowledge` | Acknowledge active anomaly (`NEW` $\to$ `ACKNOWLEDGED`). |
| `POST` | `/api/v1/aircraft/{id}/anomalies/{anomaly_id}/resolve` | Resolve active anomaly (`ACKNOWLEDGED` $\to$ `RESOLVED`). |
| `GET` | `/api/v1/aircraft/{id}/diagnosis` | Retrieve latest synthesized root-cause diagnostic assessment. |
| `GET` | `/api/v1/aircraft/{id}/maintenance-recommendations` | Retrieve actionable decision-support maintenance recommendations. |

---

## 10. Synthetic Demonstration Scenarios

1. **Scenario 1 — Normal Cruise:** Nominal flight parameters ($T = 640^\circ\text{C}$, $V = 0.2\text{ ips}$, $G = 1.0$). Zero anomalies detected; diagnosis nominal; `MONITOR` recommendation.
2. **Scenario 2 — Thermal Spike:** Temperature spikes to $925^\circ\text{C}$. Triggers `THERMAL_ANOMALY` (`CRITICAL`), digital twin degradation, propulsion hot section diagnosis, and `GROUND_FOR_REVIEW` recommendation.
3. **Scenario 3 — Mechanical Vibration Spike:** Vibration increases to $3.8\text{ ips}$. Triggers `VIBRATION_ANOMALY` (`CRITICAL`), rotating machinery diagnosis, and maintenance scheduling.
4. **Scenario 4 — High-G Dynamic Maneuver:** Normal acceleration reaches $+8.6\text{g}$. Triggers `G_LOAD_ANOMALY` (`CRITICAL`), airframe structural stress diagnosis, and inspection recommendation.
5. **Scenario 5 — Compound Multi-Signal Fusion:** Concurrent thermal ($910^\circ\text{C}$), vibration ($3.6\text{ ips}$), and pressure deviation ($660\text{ kPa}$). Synthesizes compound multi-signal correlation, boosting diagnostic confidence $\ge 0.90$, with immediate `GROUND_FOR_REVIEW` advisory.

---

## 11. Limitations & Future Evolution

* **Scope Boundaries:** Phase 5 is deterministic and rule-guided. It does not train deep neural networks or execute opaque black-box machine learning models.
* **Prognostics & RUL:** Remaining Useful Life (RUL) estimation and predictive component degradation models belong to future phases (Phase 6).
* **Certified Algorithms:** All threshold and statistical baselines represent engineering demonstration envelopes designed for the SIH prototype.
