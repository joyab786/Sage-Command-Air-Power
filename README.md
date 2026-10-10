# ✈️ SageCommand Air Power System — Aero

**Intelligent Fleet Telemetry, Aircraft Digital Twin & Operational Decision Support Platform**  
*Smart India Hackathon (SIH) Prototype Initiative*

[![SIH Status](https://img.shields.io/badge/SIH%20Status-Active%20Prototype-blue?style=for-the-badge)](https://sih.gov.in)
[![Development Stage](https://img.shields.io/badge/Stage-%F0%9F%9A%A7%20Early%20Development-amber?style=for-the-badge)](#-current-status)
[![License](https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge)](#)

> **SageCommand Air Power System (Aero)** is an intelligent, mission-critical decision support platform designed to transform heterogeneous aircraft telemetry, structural sensor streams, maintenance logs, and mission availability data into unified, actionable operational intelligence for aerospace commanders and maintenance leads.

---

## 🎯 Vision

The long-term vision of **Aero** is to create a continuously synchronized operational picture of individual aircraft and fleet-wide combat readiness. Aero acts as an explainable cognitive copilot for defense aviation personnel, delivering assistive intelligence for:

* **Aircraft Health Assessment:** Continuous tracking of structural, thermodynamic, and avionics subsystem integrity.
* **Predictive Maintenance:** Early warning of component fatigue before mission degradation occurs.
* **Anomaly Detection:** Real-time identification of subtle parameter drifts outside standard flight envelopes.
* **Root-Cause Analysis (RCA):** Rapid causal isolation across interconnected hydraulic, electrical, and avionics buses.
* **Remaining Useful Life (RUL) Estimation:** Physics- and statistical-based life consumption metrics in Flight Hours (FH) and Flight Cycles (FC).
* **Mission Readiness & Availability:** Translating current fleet health into verifiable sortie capacity.
* **Sortie Planning & Turnaround Support:** Optimizing hangar turnaround schedules and Line Replaceable Unit (LRU) allocation.
* **What-If Simulation:** Scenario forecasting under degraded operational states.
* **Fleet-Level Optimization:** Balancing maintenance workload across squadrons and air bases.

### 🔄 The Operational Paradigm:
$$\text{\bf Observe} \longrightarrow \text{\bf Understand} \longrightarrow \text{\bf Predict} \longrightarrow \text{\bf Decide} \longrightarrow \text{\bf Act} \longrightarrow \text{\bf Learn}$$

> [!IMPORTANT]
> **Human-in-the-Loop Governance:** Aero is explicitly designed as an **operator decision-support platform**. Aero does not perform autonomous combat operations or bypass human chain-of-command. Human commanders, flight leads, and maintenance officers retain absolute operational authority.

---

## 🇮🇳 SIH Problem Focus

Modern military and state aviation operations face acute challenges in sustaining high aircraft readiness while managing complex modern airframes:

1. **Massive Telemetry Volume:** A single modern aircraft flight produces millions of data points across avionics, engines (FADEC), structural health monitoring (HUMS), and environmental systems.
2. **Fragmented Information Silos:** Flight telemetry, scheduled maintenance databases, supply chain parts catalogs, and pilot debrief records exist across isolated legacy software.
3. **Complex Multi-System Fault Propagation:** Modern aircraft components are deeply coupled. An electrical voltage fluctuation can manifest as an avionics error or radar sensor dropout, obscuring the primary fault.
4. **Reactive vs. Predictive Servicing:** Traditional servicing relies heavily on static calendar intervals or post-failure repairs, resulting in Aircraft on Ground (AOG) downtime and unexpected sortie aborts.
5. **Dynamic Mission Readiness Demands:** Sortie planners must constantly answer: *"Can Squadron 101 scramble 8 fully mission-capable aircraft for a high-G tactical interception in 45 minutes?"*

**The Core Challenge:**  
Fragmented records make it nearly impossible to obtain an instant, unified, predictive view of:
$$\mathbf{\text{Aircraft Health}} \;+\; \mathbf{\text{Maintenance State}} \;+\; \mathbf{\text{Readiness Classification}} \;+\; \mathbf{\text{Mission Availability}}$$

---

## 💡 Our Proposed Solution

**Aero** bridges this gap by acting as an integrated aerospace intelligence layer connecting:

```
[ Flight Telemetry Fabric ] 
            +
[ Aircraft Digital Twin ] 
            +
[ Analytical AI/ML & Predictive Models ] 
            +
[ Root-Cause & Blast-Radius Engine ] 
            +
[ Deterministic Governance & Audit Gateway ] 
            ▼
Signals ──► Insights ──► Predictions ──► Recommendations
```

Aero continuously ingests high-rate aircraft telemetry, updates a virtual bitemporal **Aircraft Digital Twin**, detects emerging statistical anomalies, estimates subsystem wear, and generates defensible recommendations for flight leads and crew chiefs.

> [!NOTE]
> **SIH Demonstration Notice:** For the Smart India Hackathon prototype demonstration, Aero utilizes high-fidelity synthetic aircraft flight profiles, realistic sensor noise models, and simulated engine run-up datasets where real defense telemetry is classified or unavailable.

---

## 🧠 Core SIH Prototype Scope

The practical Minimum Viable Product (MVP) being implemented for SIH demonstrates the critical path of the operational loop:

### 1. Flight Telemetry Data Fabric 🧪
High-throughput ingestion and unit normalization for representative flight parameters:
* **Aerodynamics:** Altitude, True Airspeed (TAS), Indicated Airspeed (IAS), Mach Number, Normal Acceleration ($G_z$), Angle of Attack (AoA).
* **Propulsion / FADEC:** Engine Core RPM (N1/N2), Exhaust Gas Temperature (EGT), Fuel Flow Rate, Oil Pressure.
* **Subsystems:** Hydraulic Pressure, Core Avionics Bus Voltage, Cabin Pressurization.
* **Diagnostics:** Built-In Test Equipment (BITE) status flags and discrete fault codes.

### 2. Aircraft Digital Twin 🧪
A bitemporal software representation maintaining live aircraft state:
* Tail number, squadron assignment, and airframe serial identity.
* Cumulative Flight Hours (FH) and Landing/Stress Cycles (FC).
* Real-time subsystem state vector and recent telemetry buffer.
* Active anomalies, maintenance work status, and sortie readiness classification.

### 3. Anomaly Detection 🧪
Statistical baselining (Z-score, rolling variance, flight envelope boundary evaluation) to automatically flag out-of-nominal deviations before catastrophic subsystem failure occurs.

### 4. Predictive Maintenance & RUL 🧪
Prognostics estimating component degradation and Remaining Useful Life (RUL).  
*Scope Constraint:* To ensure technical defensibility, the SIH prototype focuses on a **representative subset of high-impact subsystems** (turbofan thermal fatigue and hydraulic pump pressure degradation) rather than attempting to model every aircraft component.

### 5. Root Cause Analysis (RCA) 🧪
Causal graph reasoning linking telemetry anomalies and subsystem dependencies to isolate root failure mechanisms from downstream symptoms.

### 6. Standardized Aircraft Readiness Classification 🧪
Classifies each aircraft using standard defense aviation categories:
* **FMC (Fully Mission Capable):** All flight, avionics, and operational subsystems fully operational.
* **PMC (Partially Mission Capable):** Minor non-flight-critical fault; cleared for restricted training or ferry sorties.
* **NMC (Non-Mission Capable):** Flight safety or mission-critical defect; grounded pending maintenance.

### 7. Mission Readiness Assessment 🧪
Aggregates individual aircraft readiness states into actionable squadron-level sortie generation assessments.

### 8. Aero Command Center UI 🧪
A modern, dark-mode tactical command console providing:
* Fleet status overview and squadron readiness summary.
* Individual aircraft health indicators and real-time telemetry gauges.
* Anomaly alert feed and causal diagnosis breakdown.
* Maintenance turnaround priority recommendations.

---

## 🔄 Operational Intelligence Loop

Aero executes along a closed-loop operational lifecycle:

```mermaid
graph TD
    OBSERVE["1. OBSERVE (Telemetry & Sensor Ingestion)"] --> DETECT["2. DETECT (Anomaly & Envelope Drift)"]
    DETECT --> UNDERSTAND["3. UNDERSTAND (Aircraft Subsystem Context)"]
    UNDERSTAND --> PREDICT["4. PREDICT (Degradation & RUL Estimation)"]
    PREDICT --> DIAGNOSE["5. DIAGNOSE (Causal Graph Root-Cause Analysis)"]
    DIAGNOSE --> SIMULATE["6. SIMULATE (Counterfactual What-If Scenarios)"]
    SIMULATE --> RECOMMEND["7. RECOMMEND (Maintenance Priority & Sortie Advisory)"]
    RECOMMEND --> DECIDE["8. HUMAN DECISION (Commander / Flight Lead Gate)"]
    DECIDE --> ACT["9. ACT (Validated Maintenance / Dispatch Action)"]
    ACT --> VERIFY["10. VERIFY (Post-Flight BITE / Post-Maintenance Run-Up)"]
    VERIFY --> LEARN["11. LEARN (Cryptographic Audit & Fleet Health Feedback)"]
    LEARN -->|Continuous Feedback| OBSERVE
```

*For the SIH MVP, Aero focuses on demonstrating stages 1 through 8 (Observe through Human Decision).*

---

## 🏗️ Target Architecture

```
                    ┌─────────────────────────────────────────────────────┐
                    │               AERO COMMAND CENTER UI                │
                    │        (Next.js 16 / React 19 Obsidian Console)     │
                    └──────────────────────────┬──────────────────────────┘
                                               │
                               WebSocket / REST API
                                               │
                    ┌──────────────────────────▼──────────────────────────┐
                    │             API GATEWAY & GOVERNANCE                │
                    │      (FastAPI, RBAC, Request Tracing, CORS)         │
                    └─────────────┬─────────────────────────┬─────────────┘
                                  │                         │
                  Read Inquiries  │                         │ Transaction Commit
                                  ▼                         ▼
┌─────────────────────────────────────────────────┐  ┌───────────────────────────────────┐
│              AI INTELLIGENCE LAYER              │  │   DETERMINISTIC EXECUTION GATEWAY │
│   (Purely Analytical — Zero Mutation Rights)    │  │   (10-Gate Write Boundary)        │
├─────────────────────────────────────────────────┤  ├───────────────────────────────────┤
│ • Multimodal Sensor Fusion Service              │  │ • Two-Person Rule Authorization   │
│ • Flight Envelope Anomaly Detection             │  │ • Policy Precedence Enforcement   │
│ • Component Degradation & RUL Estimator         │  │ • SHA-256 Tamper Verification     │
│ • Subsystem Root-Cause Analysis (Causal Graphs) │  │ • Idempotency Deduplication       │
│ • Counterfactual What-If Simulation Engine      │  │ • Atomic Action Rollback          │
└─────────────────────────┬───────────────────────┘  └─────────────────┬─────────────────┘
                          │                                            │
                          ▼                                            ▼
┌─────────────────────────────────────────────────┐  ┌───────────────────────────────────┐
│              AIRCRAFT DIGITAL TWIN              │  │    CRYPTOGRAPHIC AUDIT LEDGER     │
│  - Virtual Aircraft State & Flight Cycles       │  │  - Append-Only SHA-256 Chain      │
│  - FMC / PMC / NMC Readiness State Machine      │  │  - Chain of Custody Audit Trail   │
└─────────────────────────┬───────────────────────┘  └───────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              TELEMETRY DATA FABRIC                                     │
│                (High-Concurrency SQLite WAL Engine / Sensor Queue)                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Direction

* **Backend Framework:** Python 3.12, FastAPI `>=0.115.0`, Uvicorn (ASGI)
* **Data Contracts:** Pydantic v2 (Strict typing, zero deprecated v1 validators)
* **Database & Persistence:** SQLAlchemy 2.0, SQLite with Write-Ahead Logging (`WAL` mode, 5000ms busy timeout)
* **Orchestration:** LangGraph (StateGraph multi-agent DAGs with native Human-in-the-Loop interrupts)
* **Security & Auditing:** Cryptography (SHA-256 state hashing), PyJWT (Role-based access control)
* **Frontend Web Console:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons
* **Real-Time Streaming:** WebSockets (Low-latency telemetry streaming and alert interrupts)

---

## 📊 SIH Demonstration Flow

The planned demonstration will walk through an end-to-end operational scenario:

1. **Telemetry Streaming:** Simulated flight telemetry for a fighter aircraft enters the system during a mission sortie.
2. **Ingestion & Normalization:** Telemetry data fabric validates sensor units and checks flight envelope boundaries.
3. **Digital Twin Update:** Cumulative flight hours and engine temperature cycles update on the aircraft's twin.
4. **Anomaly Triggered:** An abnormal EGT thermal divergence combined with high-frequency turbine vibration is flagged.
5. **Intelligence Analysis:** Sensor fusion evaluates cross-modal agreement between temperature and vibration sensors.
6. **Degradation / RUL Estimation:** Prognostic model estimates turbine blade thermal wear and computes remaining safe flight hours.
7. **Root-Cause Analysis:** RCA graph isolates a clogged cooling bleed valve as the primary root failure cause.
8. **Readiness Reclassification:** Aircraft status transitions from **FMC** (Fully Mission Capable) to **PMC** (Partially Mission Capable).
9. **Maintenance Advisory:** A prioritized maintenance work proposal for bleed valve replacement is generated.
10. **Mission Availability Impact:** Squadron mission planner automatically flags that this airframe cannot be scheduled for a high-altitude combat sortie.
11. **Command Dashboard Presentation:** The Aero Command Center visualizes the situation, root cause, and impact for decision-makers.
12. **Human Governance Gate:** A maintenance lead reviews and authorizes the scheduled repair through the Execution Gateway.

---

## 🗺️ Development Roadmap

```
Phase 0: Architecture Reconnaissance & SIH Scope Definition      [✅ Completed]
Phase 1: Technical Foundation & Execution Gateway Scaffolding    [✅ Completed]
Phase 2: Aeronautical Domain Model & Ontology                    [✅ Completed]
Phase 3: Flight Telemetry Data Fabric (Ingestion & Normalizer)   [✅ Completed]
Phase 4: Aircraft Digital Twin State Machine                     [✅ Completed]
Phase 5: Subsystem Intelligence Layer (Anomaly, RCA, Advisory)   [✅ Completed]
Phase 6: Prognostics & Remaining Useful Life (RUL)               [🚧 Next Phase]
Phase 7: Mission Manager & Air Tasking Order (ATO) Pipeline      [🚧 Planned]
Phase 8: What-If Tactical Simulation & Fleet Optimization        [🔭 Future Vision]
Phase 9: Tactical Command Center UI (Obsidian Aero Console)      [🚧 Planned]
Phase 10: Human Governance & Mission Execution Gates             [🚧 Planned]
Phase 11: Verification, Flight Debrief & Fleet Learning          [🔭 Future Vision]
```

### Current SIH MVP Pipeline:
```
Telemetry
    ↓
Data Quality & Normalization
    ↓
Aircraft Digital Twin
    ↓
Subsystem Health
    ↓
Anomaly Detection
    ↓
Root-Cause Diagnosis
    ↓
Maintenance Recommendation
    ↓
Readiness Intelligence
    ↓
Command Center
```

### Current Implemented Capabilities (Phases 1–5):
* **Aero Domain Model:** Canonical aerospace domain aggregates (`Aircraft`, `Component`, `Telemetry`, `ReadinessAssessment`, `Mission`, `MaintenanceEvent`).
* **Telemetry Ingestion:** High-throughput streaming and batch ingest with SI unit normalization and coordinate consistency.
* **Telemetry Quality Assessment:** Real-time data quality classification (`VALID`, `DEGRADED`, `INVALID`) catching clock drift, NaN/Inf, and channel drops.
* **Flight Envelope Monitoring:** Demonstration flight boundary evaluation across altitude, airspeed, Mach, G-load, and turbine temperatures.
* **Aircraft Digital Twin State Estimation:** Bitemporal operational state estimation preserving channel history across sparse telemetry packets.
* **Subsystem Health Scoring:** Explainable rule-based health scoring (0–100) with transparent, structured deduction rationales.
* **Wear & Fatigue Estimation:** Monotonic wear indices derived from operational flight hours, cycles, and dynamic structural stress.
* **Deterministic Anomaly Detection:** Configurable threshold and rolling z-score statistical detectors with zero-variance safety protections.
* **Root-Cause Diagnosis Engine:** Subsystem diagnosis synthesis, multi-signal correlation, and catalog rule weighting.
* **Decision-Support Maintenance Recommendations:** Prioritized advisories (`MONITOR`, `INSPECT`, `SCHEDULE_MAINTENANCE`, `GROUND_FOR_REVIEW`) with clear evidence links.
* **Readiness Integration Boundary:** Direct coupling between active subsystem anomalies and fleet readiness classifications.
* **Explainable Intelligence:** Zero black-box outputs; every anomaly, diagnosis, and recommendation exposes underlying telemetry evidence and confidence ratings ($0.0 \le c \le 1.0$).

> [!NOTE]
> **Prototype Scope Notice:** This platform is an **SIH MVP / Prototype**. While the architectural foundation, data fabric, digital twin, and intelligence pipelines are production-grade and fully tested, physics-informed Remaining Useful Life (RUL) modeling, full Air Tasking Order (ATO) generation, and multi-base tactical HUD interfaces are scheduled for subsequent roadmap phases.

---

## 🔐 Safety Boundary & Human Governance

Aero adheres strictly to non-negotiable safety and defense compliance boundaries:
* **Advisory Decision Support:** Aero is exclusively an analytical decision-support system. It produces recommendations, never autonomous commands.
* **Human-in-the-Loop (HITL):** Flight commanders, flight leads, and maintenance crew chiefs retain full authority.
* **No Autonomous Flight Control:** The system does not interface with autopilot or aircraft flight-control computers.
* **No Weapons Control or Targeting:** Zero weapon targeting, authorization, release, or combat engagement capabilities exist in the platform.
* **Two-Person Rule:** High-risk actions require independent human clearance. Proposing operators cannot approve their own high-risk actions.
* **Deterministic Write Boundary:** AI algorithms cannot mutate persistent state directly. All database writes pass through the 10-gate Execution Gateway.
* **Cryptographic Accountability:** All system recommendations, human approvals, and policy evaluations are committed to an append-only, SHA-256 hash-chained audit ledger.

---

## 📁 Repository Structure

```
Sage-Command-Air-Power/
├── backend/                           # FastAPI Python Backend
│   ├── app/
│   │   ├── api/routes/health.py       # Health diagnostics endpoints
│   │   ├── api/routes/aircraft.py     # Aircraft, twin, anomalies, diagnosis & maintenance endpoints
│   │   ├── api/routes/missions.py     # Mission and sortie planning endpoints
│   │   ├── api/routes/telemetry.py    # Telemetry ingestion & query endpoints
│   │   ├── contracts/                 # Pydantic v2 response envelopes & caller identity
│   │   ├── core/                      # Settings, structured logging, exception hierarchy
│   │   ├── db/database.py             # SQLAlchemy 2.0 & SQLite WAL connection manager
│   │   ├── db/models.py               # Relational ORM models (Aircraft, Telemetry, Twin, Anomalies)
│   │   ├── domain/                    # Canonical aerospace domain entities & enums
│   │   ├── telemetry/                 # Telemetry Data Fabric (Normalizer, Quality, Envelope, Buffer)
│   │   ├── digital_twin/              # Aircraft Digital Twin (Estimator, Health, Wear, Sessions)
│   │   ├── intelligence/              # Subsystem Intelligence (Detectors, Diagnosis, Maintenance)
│   │   ├── prognostics/               # Prognostics & Remaining Useful Life / RUL (Trend, RUL, Forecast)
│   │   ├── services/                  # Business services, policy engine, audit ledger, execution gateway
│   │   └── main.py                    # Application entrypoint & lifespan handlers
│   ├── tests/                         # Automated unit and integration tests (214 passing)
│   └── requirements.txt               # Backend dependencies
├── frontend/                          # Next.js 16 / React 19 Frontend Shell
│   ├── app/
│   │   ├── globals.css                # Obsidian HUD styling
│   │   ├── layout.tsx                 # Root layout
│   │   └── page.tsx                   # System Foundation dashboard shell
│   └── package.json                   # Frontend dependencies
├── docs/                              # Technical Documentation
│   ├── AERO_CODEBASE_RECONNAISSANCE.md # System architecture reconnaissance & baseline audit
│   ├── ARCHITECTURE.md                # System Architecture Baseline Specification (v1.5.0)
│   ├── AERO_DOMAIN_MODEL.md           # Canonical Aerospace Domain Model Specification
│   ├── AERO_TELEMETRY_DATA_FABRIC.md  # Phase 3 Telemetry Data Fabric Specification
│   ├── AERO_DIGITAL_TWIN.md           # Phase 4 Aircraft Digital Twin Specification
│   ├── AERO_INTELLIGENCE.md           # Phase 5 Subsystem Intelligence & Anomaly Detection Specification
│   └── AERO_PROGNOSTICS.md            # Phase 6 Predictive Maintenance & RUL Specification
├── .env.example                       # Safe environment variables template
├── .gitignore                         # Comprehensive git ignore rules
├── powershell.cmd                     # Windows execution proxy
└── README.md                          # This document
```

---

## 📌 Current Status

**Current Status: 🟢 Phase 6 Complete / 214 Tests Verified Passing**

* ✅ Repository established and synchronized on GitHub.
* ✅ Architectural reconnaissance completed ([`docs/AERO_CODEBASE_RECONNAISSANCE.md`](./docs/AERO_CODEBASE_RECONNAISSANCE.md)).
* ✅ Phase 1 Technical Foundation verified ([`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)).
* ✅ Phase 2 Canonical Aerospace Domain Model verified ([`docs/AERO_DOMAIN_MODEL.md`](./docs/AERO_DOMAIN_MODEL.md)).
* ✅ Phase 3 Telemetry Data Fabric verified ([`docs/AERO_TELEMETRY_DATA_FABRIC.md`](./docs/AERO_TELEMETRY_DATA_FABRIC.md)).
* ✅ Phase 4 Aircraft Digital Twin State Estimation verified ([`docs/AERO_DIGITAL_TWIN.md`](./docs/AERO_DIGITAL_TWIN.md)).
* ✅ Phase 5 Subsystem Intelligence & Anomaly Detection verified ([`docs/AERO_INTELLIGENCE.md`](./docs/AERO_INTELLIGENCE.md)).
* ✅ Phase 6 Prognostics & Remaining Useful Life (RUL) verified ([`docs/AERO_PROGNOSTICS.md`](./docs/AERO_PROGNOSTICS.md)).
* ✅ Complete automated test suite: **214 passing tests** with 0 regressions.
* 🚧 Preparing for **Phase 7 (Mission Manager & Air Tasking Order / ATO)**.

---

## 🤝 Development Philosophy

> *"Build robust, reliable infrastructure.  
> Build clean Aero domain models.  
> Prefer deterministic and explainable intelligence.  
> Keep humans firmly in the decision loop.  
> Build the SIH MVP first.  
> Design the architecture for future defense-grade expansion."*

---

## 📚 Documentation Links

* 📄 **[Aero Codebase Reconnaissance Report](./docs/AERO_CODEBASE_RECONNAISSANCE.md)** — System architecture reconnaissance, operational loop mapping, and technical baseline analysis.
* 📄 **[System Architecture Specification](./docs/ARCHITECTURE.md)** — Technical baseline documentation for foundations, contracts, and execution gates (v1.5.0).
* 📄 **[Aero Domain Model Specification](./docs/AERO_DOMAIN_MODEL.md)** — Canonical aerospace domain model, entities, and database mappings.
* 📄 **[Aero Telemetry Data Fabric Specification](./docs/AERO_TELEMETRY_DATA_FABRIC.md)** — Telemetry ingestion, normalization, quality evaluation, and buffering.
* 📄 **[Aero Aircraft Digital Twin Specification](./docs/AERO_DIGITAL_TWIN.md)** — Bitemporal digital twin state estimation, health scoring, and wear estimation.
* 📄 **[Aero Subsystem Intelligence Specification](./docs/AERO_INTELLIGENCE.md)** — Deterministic threshold/statistical anomaly detection, root-cause diagnosis, and maintenance recommendations.
* 📄 **[Aero Prognostics & RUL Specification](./docs/AERO_PROGNOSTICS.md)** — Explainable degradation trends, Remaining Useful Life (RUL), and decision-support maintenance forecasts.

---
*Developed for the Smart India Hackathon (SIH) // SageCommand Air Power System Team*
