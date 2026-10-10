# SageCommand Air Power System (Aero) — System Architecture
**Phase 6: Predictive Maintenance & Remaining Useful Life (RUL) Prognostics (SIH MVP) Specification**  
*Document Version:* 1.5.0  
*Date:* 2026-10-07  
*Status:* IMPLEMENTED BASELINE (Phases 1-6 Verified: 213 Passing Automated Tests)  

---

## 1. Aero Architecture Principles

The **SageCommand Air Power System (Aero)** is designed as an autonomous command, decision-support, and governance platform for military air operations. The architecture strictly follows these foundational principles:

1. **Aerospace Domain Modeling:** Aero establishes a purpose-built aerospace domain foundation. Core mechanisms are constructed on a clean, domain-neutral foundation tailored specifically for defense aviation operational intelligence.
2. **Deterministic Governance Over LLM Output:** Large Language Models and AI agents generate hypotheses, strategies, and advisory intelligence. However, **deterministic systems enforce rules**. Write actions must pass through strict policy engines and execution gates.
3. **Decoupled Analytical vs. Execution Planes:** Analytical intelligence (telemetry fusion, anomaly detection, predictive maintenance, simulation) is strictly read-only. Analytical modules have zero authority to perform physical or operational mutations.
4. **Append-Only Tamper-Evident Auditability:** Every decision, policy evaluation, and operational action is recorded in a cryptographically chained SHA-256 audit ledger.
5. **Two-Person Rule for High-Risk Actions:** High-risk actions require independent human approval. The proposing actor is barred from approving their own high-risk actions.
6. **High-Concurrency Telemetry Preparation:** The database foundation is configured with SQLite Write-Ahead Logging (WAL) mode and asynchronous queues to support high-rate aircraft sensor streams.
7. **Clean Telemetry Data Fabric:** Ingest, normalize, validate, and buffer flight telemetry deterministically before state estimation or persistence.
8. **Explainable Digital Twin State Estimation:** Continuous operational representation with memory retention, rule-based health scoring, and transparent reasons.
9. **Explainable Subsystem Intelligence:** Deterministic threshold and statistical anomaly detection, correlation/deduplication windows, multi-signal root-cause synthesis, and advisory maintenance recommendations.
10. **Explainable Trend-Based Prognostics:** Defensible health degradation slopes (OLS regression), bounded Remaining Useful Life (RUL) estimation with explicit uncertainty intervals, and consolidated maintenance forecasting.

---

## 2. Repository Structure

```
Sage-Command-Air-Power/
├── backend/
│   ├── app/
│   │   ├── __init__.py                # Application package
│   │   ├── main.py                   # FastAPI ASGI entrypoint, lifespan & exception handlers
│   │   ├── core/
│   │   │   ├── __init__.py           # Core exports
│   │   │   ├── config.py             # Pydantic Settings configuration system
│   │   │   ├── logging.py            # Structured JSON / console logger with correlation IDs
│   │   │   └── exceptions.py         # Standardized AeroException hierarchy
│   │   ├── contracts/
│   │   │   ├── __init__.py           # Contracts exports
│   │   │   ├── base.py               # ApiResponse, ApiErrorResponse, AeroBaseModel
│   │   │   └── common.py             # ActorIdentity, DataMode, RiskLevel, Pagination
│   │   ├── db/
│   │   │   ├── __init__.py           # Database exports
│   │   │   ├── database.py           # SQLAlchemy engine, sessions, and SQLite WAL pragma
│   │   │   └── models.py             # SQLAlchemy ORM models (Aircraft, Telemetry, Twin, Sessions, Prognostics)
│   │   ├── domain/                   # Canonical Aerospace Domain Layer (Phase 2)
│   │   │   ├── __init__.py           # Domain exports
│   │   │   ├── enums.py              # Domain enums (Readiness, AircraftType, Subsystems)
│   │   │   ├── aircraft.py           # Aircraft schemas & domain aggregates
│   │   │   ├── components.py         # Component & subsystem tracking schemas
│   │   │   ├── readiness.py          # Operational readiness assessment schemas
│   │   │   ├── missions.py           # Sortie & mission lifecycle schemas
│   │   │   ├── maintenance.py        # Maintenance log & work order schemas
│   │   │   └── telemetry.py          # Telemetry observation base schemas
│   │   ├── telemetry/                # Telemetry Data Fabric (Phase 3)
│   │   │   ├── __init__.py           # Telemetry exports
│   │   │   ├── models.py             # NormalizedTelemetry, IngestResult, Quality/Envelope schemas
│   │   │   ├── normalizer.py         # TelemetryNormalizer (unit conversion & standardization)
│   │   │   ├── quality.py            # QualityEvaluator (VALID / DEGRADED / INVALID)
│   │   │   ├── envelope.py           # FlightEnvelopeChecker (generic demo envelope limits)
│   │   │   ├── buffer.py             # Thread-safe in-memory TelemetryBuffer
│   │   │   ├── generator.py          # SyntheticFlightGenerator (deterministic demo flight profiles)
│   │   │   └── service.py            # TelemetryService orchestration layer
│   │   ├── digital_twin/             # Aircraft Digital Twin State Estimation (Phase 4)
│   │   │   ├── __init__.py           # Digital Twin exports
│   │   │   ├── models.py             # AircraftTwinState, SubsystemState, HealthReason, FlightSession
│   │   │   ├── estimator.py          # DigitalTwinEstimator (state fusion & channel memory)
│   │   │   ├── health.py             # AircraftHealthEstimator (explainable rule-based scoring)
│   │   │   ├── wear.py               # WearEstimator (normalized wear index & dynamic fatigue)
│   │   │   └── service.py            # DigitalTwinService (lifecycle, sessions, hours/cycles)
│   │   ├── intelligence/             # Subsystem Intelligence & Anomaly Detection (Phase 5)
│   │   │   ├── __init__.py           # Intelligence package exports
│   │   │   ├── models.py             # Strongly typed Anomaly, Diagnosis & Recommendation models
│   │   │   ├── anomaly/              # Detectors (Threshold, Statistical z-score, Composite)
│   │   │   ├── diagnosis/            # Root-cause synthesis & multi-signal correlation rules
│   │   │   ├── maintenance.py        # Decision-support maintenance recommendation engine
│   │   │   └── service.py            # IntelligenceService (correlation, deduplication & WAL)
│   │   ├── prognostics/              # Predictive Maintenance & RUL Prognostics (Phase 6)
│   │   │   ├── __init__.py           # Prognostics package exports
│   │   │   ├── models.py             # ComponentHealthSnapshot, DegradationTrend, RULPrediction, Forecast
│   │   │   ├── health_history.py     # HealthHistoryAggregator (digital-twin history queries)
│   │   │   ├── trend.py              # DegradationTrendEstimator (OLS regression, slope, R²)
│   │   │   ├── rul.py                # BaseRULPredictor protocol & DeterministicRULPredictor
│   │   │   ├── forecast.py           # MaintenanceForecaster (5 priority tiers & operational windows)
│   │   │   └── service.py            # PrognosticsService orchestration & SQLite WAL persistence
│   │   ├── api/
│   │   │   ├── __init__.py           # API exports
│   │   │   └── routes/
│   │   │       ├── __init__.py       # Route exports
│   │   │       ├── health.py         # GET /health diagnostics endpoint
│   │   │       ├── aircraft.py       # Aircraft, twin, anomalies, prognostics & maintenance endpoints
│   │   │       ├── missions.py       # Mission & sortie management endpoints
│   │   │       └── telemetry.py      # Telemetry ingestion & query endpoints
│   │   ├── services/
│   │   │   ├── __init__.py           # Services exports
│   │   │   ├── policy_engine.py      # Deterministic policy engine (DENY > APPROVAL > HOLD > ALLOW)
│   │   │   ├── audit_ledger.py       # Append-only cryptographic SHA-256 audit ledger
│   │   │   └── execution_gateway.py  # 10-gate transactional write boundary & two-person rule
│   │   └── graph/
│   │       └── __init__.py           # Agent orchestration graph package (deferred to future phases)
│   ├── tests/
│   │   ├── __init__.py               # Test suite package
│   │   ├── conftest.py               # Shared pytest fixtures (in-memory DB, TestClient)
│   │   ├── unit/                     # Unit test suites (162 tests)
│   │   └── integration/              # Integration test suites (52 tests)
│   └── requirements.txt              # Backend dependencies
├── frontend/
│   ├── app/
│   │   ├── globals.css               # Obsidian theme and HUD pattern styles
│   │   ├── layout.tsx                # Next.js App Router root layout
│   │   └── page.tsx                  # System Foundation dashboard shell
│   ├── package.json                  # Next.js 16 / React 19 dependencies
│   ├── tsconfig.json                 # TypeScript compiler configuration
│   ├── next.config.ts                # Next.js framework configuration
│   ├── tailwind.config.js            # Obsidian theme color palette configuration
│   └── postcss.config.js             # PostCSS processing configuration
├── docs/
│   ├── AERO_CODEBASE_RECONNAISSANCE.md # Initial architectural audit
│   ├── ARCHITECTURE.md               # This architectural specification document
│   ├── AERO_DOMAIN_MODEL.md          # Canonical aerospace domain specification
│   ├── AERO_TELEMETRY_DATA_FABRIC.md # Phase 3 Telemetry Data Fabric specification
│   └── AERO_DIGITAL_TWIN.md          # Phase 4 Aircraft Digital Twin specification
├── .env.example                      # Safe environment variables template
└── powershell.cmd                    # Windows runner execution proxy
```

---

## 3. Backend Architecture

### 3.1 Layered Architecture Pattern
```
[ Client / Web Console / Edge Probes ]
                 │
                 ▼ (HTTP / REST / WebSocket)
┌────────────────────────────────────────────────────────┐
│ FastAPI Application Boundary (main.py)                 │
│  - Correlation ID Middleware (X-Correlation-ID)        │
│  - CORS Middleware (Allowlist)                         │
│  - Global Exception Handlers (ApiErrorResponse)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ API Routers (api/routes/)                              │
│  - Health Diagnostics (/health, /api/v1/health)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Aero Domain Services (services/)                       │
│  - Deterministic Policy Engine (policy_engine.py)      │
│  - Cryptographic Audit Ledger (audit_ledger.py)        │
│  - Deterministic Execution Gateway (execution_gateway) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Aero Core Infrastructure & Contracts                   │
│  - Base Pydantic Contracts (contracts/base, common)    │
│  - Structured Logging & Tracing (core/logging.py)      │
│  - Environment Configuration (core/config.py)          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Database Foundation (db/database.py)                   │
│  - SQLAlchemy 2.0 Engine & Sessionmaker                │
│  - SQLite WAL Mode & Busy Timeout (5000ms)             │
│  - Atomic Transaction Context Manager                  │
└────────────────────────────────────────────────────────┘
```

---

## 4. Frontend Architecture

The frontend application is constructed with **Next.js 16** (App Router) and **React 19**:
- **Application Shell (`frontend/app/page.tsx`):** Provides a high-contrast, dark-mode Obsidian Command Console interface.
- **Top Navigation Bar:** Features system status badges, operational environment indicator, and a real-time `/health` probe heartbeat.
- **Foundation Matrix:** Displays live status cards for API Gateway, Database WAL engine, Policy Engine, Audit Ledger, and Execution Gateway.
- **Zero Fake Domain Elements:** Adheres to Phase 1 constraints—does not contain simulated aircraft, fake tactical maps, or fabricated weapons data.

---

## 5. Configuration

The configuration system in `app/core/config.py` uses `pydantic-settings.BaseSettings`:
- Type-safe loading with `AERO_` environment variable prefix.
- Sensible defaults for local development.
- Environment detection: `is_production` and `is_testing` property helpers.
- Clean `.env.example` provided with zero hardcoded credentials or secrets.

---

## 6. Database Foundation

The database layer in `app/db/database.py` establishes:
- **Engine Tuning:** Automatic SQLite PRAGMA configuration (`PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, `PRAGMA busy_timeout=5000;`, `PRAGMA foreign_keys=ON;`).
- **Atomic Transactions:** `get_db_session()` context manager automatically commits upon clean exit and performs atomic rollbacks upon uncaught exceptions.
- **FastAPI Injection:** `get_db()` dependency for route-level session management.
- **Test Isolation:** Automatic support for ephemeral `:memory:` databases in pytest.

---

## 7. Policy Engine

The Policy Engine in `app/services/policy_engine.py` implements deterministic rule evaluation:
- **Strict Precedence Hierarchy:**
  ```
  DENY > REQUIRE_APPROVAL > HOLD > ALLOW
  ```
  1. If any matched rule is `DENY` -> Result is `DENY`.
  2. Elif any matched rule is `REQUIRE_APPROVAL` -> Result is `REQUIRE_APPROVAL`.
  3. Elif any matched rule is `HOLD` -> Result is `HOLD`.
  4. Elif any matched rule is `ALLOW` -> Result is `ALLOW`.
  5. Default (fail-closed) -> Result is `HOLD`.
- **Anti-Code Injection Verification:** Rejects condition values containing dangerous Python expressions (`eval`, `exec`, `subprocess`, etc.).
- **Decision Fingerprinting:** Every decision computes an immutable SHA-256 fingerprint for auditability.

---

## 8. Audit Ledger

The Audit Ledger in `app/services/audit_ledger.py` implements an immutable, append-only event log:
- **Monotonic Sequencing:** Sequence numbers strictly increment per partition.
- **Cryptographic Hash Chaining:**
  ```
  event_hash = SHA256(event_id + seq + occurred_at + actor + action + result + previous_event_hash + canonical_payload)
  ```
- **Tamper Evident:** Modifying any historical payload breaks the pointer chain and is immediately flagged by `verify_integrity()`.

---

## 9. Execution Gateway

The Execution Gateway in `app/services/execution_gateway.py` acts as the final transactional write boundary:
- **10-Gate Validation Pipeline:**
  1. Gate 1: Identity & Authentication Integrity
  2. Gate 2: Authorization & Operational Permission
  3. Gate 3: Target Scope & Resource Integrity
  4. Gate 4: Action Lifecycle State Machine
  5. Gate 5: Cryptographic & Staleness Integrity Verification
  6. Gate 6: Two-Person Rule / Approval Verification
  7. Gate 7: Policy Engine Revalidation
  8. Gate 8: Idempotency & Duplicate Execution Detection
  9. Gate 9: Concurrency Lock Acquisition
  10. Gate 10: Execution, Rollback Tracking & Audit Logging
- **Two-Person Rule:** Proposers cannot approve their own high-risk actions.
- **Atomic Rollback:** Reverses succeeded actions with audit logging.

---

## 10. Testing Strategy

The test suite in `backend/tests/` provides exhaustive automated regression verification across all implemented layers:
- **Phase 1 Foundation (25 tests):** Configuration loading, Pydantic contracts, database commit/rollback, policy engine precedence, audit ledger hash chaining/tamper detection, execution gateway gates, health API diagnostics.
- **Phase 2 Domain Model (39 tests):** Aircraft schemas, component hierarchies, readiness scoring, mission/sortie state machine, maintenance records, domain database persistence, domain REST APIs.
- **Phase 3 Telemetry Data Fabric (36 tests):** Deterministic unit conversion (altitude, airspeed, temperature, pressure, vibration), quality assessment (valid, degraded, invalid, NaN/Inf, clock drift), envelope monitoring (normal, caution, exceeded, multi-violation), synthetic profile generator, bounded ring buffer concurrency and eviction, SQLite telemetry persistence, and REST APIs.
- **Phase 4 Aircraft Digital Twin (29 tests):** Digital twin models and bounds, state estimation fusion with channel retention across sparse frames, explainable rule-based health scoring, composite and subsystem wear indices, flight session duration tracking and cycle idempotency, persistence under SQLite WAL, and end-to-end REST API integration.
- **Phase 5 Subsystem Intelligence (37 tests):** Anomaly data models and bounded confidence, threshold detectors (propulsion, structural G-load, control surfaces, telemetry quality), statistical z-score rolling baselines with zero-variance protection, multi-signal correlation and root-cause synthesis, decision-support maintenance recommendation engine, SQLite WAL anomaly persistence with composite indexes, 300s alert correlation/deduplication window, and REST APIs.
- **Phase 6 Predictive Maintenance & RUL (48 tests):** Prognostic model validation, ordinary least-squares linear trend engine with fit quality ($R^2$), insufficient-data protections, deterministic RUL prediction with conservative wear bounds, Phase 5 anomaly modifier integration, uncertainty interval math ($0.0 \le \text{lower} \le \text{est} \le \text{upper}$), 5-tier maintenance forecasting, SQLite WAL persistence (`prognostic_records`), versioned REST APIs, and 6 end-to-end synthetic demonstration scenarios.
- **Current Test Suite Results:** **214 passed in ~6.3 seconds** with 0 regressions.

---

## 11. Core Architectural Modules

| Architectural Mechanism | Implementation Module | Technical Capability |
| :--- | :--- | :--- |
| **Deterministic Policy Engine** | `backend/app/services/policy_engine.py` | Priority-based evaluation ($\text{DENY} > \text{REQUIRE\_APPROVAL} > \text{HOLD} > \text{ALLOW}$) with sandboxed condition checking. |
| **Cryptographic Audit Ledger** | `backend/app/services/audit_ledger.py` | Append-only SHA-256 hash-chained immutable audit trail with tamper detection. |
| **Execution Gateway** | `backend/app/services/execution_gateway.py` | 10-gate write boundary enforcing policy checks, two-person rule authorization, and transactional rollback. |
| **Database Engine** | `backend/app/db/database.py`, `models.py` | SQLite WAL connection management with high-concurrency PRAGMA tuning & indexed tables. |
| **Contract Envelopes** | `backend/app/contracts/` | Pydantic v2 strict typing, standard response envelopes, and actor identities. |
| **Canonical Domain Model** | `backend/app/domain/` | Aircraft, Component, Readiness, Mission/Sortie, Maintenance, and Telemetry aggregates. |
| **Telemetry Normalizer** | `backend/app/telemetry/normalizer.py` | Deterministic unit conversion (SI/metric) and metadata standardisation. |
| **Quality Evaluator** | `backend/app/telemetry/quality.py` | Deterministic evaluation of data validity, boundary physics, and clock drift. |
| **Flight Envelope Checker** | `backend/app/telemetry/envelope.py` | Configurable boundary checking with structured violation classification. |
| **Synthetic Profile Generator**| `backend/app/telemetry/generator.py` | Deterministic pseudo-random generation of 6 flight profiles for SIH demo. |
| **Bounded Telemetry Buffer** | `backend/app/telemetry/buffer.py` | Thread-safe, chronological in-memory ring buffer preventing unbounded memory growth. |
| **Telemetry Service** | `backend/app/telemetry/service.py` | Ingestion orchestration, aircraft verification, buffer dispatch, persistence, and twin hook. |
| **Digital Twin Service** | `backend/app/digital_twin/service.py` | Orchestrates twin state estimation, flight sessions, cumulative hours/cycles, and snapshots. |
| **Digital Twin Estimator** | `backend/app/digital_twin/estimator.py` | Fuses telemetry observations with state memory, preserving previous channel values. |
| **Aircraft Health Estimator** | `backend/app/digital_twin/health.py` | Deterministic rule-based health scoring (0-100) with structured explainability reasons. |
| **Wear Estimator** | `backend/app/digital_twin/wear.py` | Derives normalized wear ratings [0.0 - 1.0] from operational exposure and dynamic stresses. |
| **Anomaly Detectors** | `backend/app/intelligence/anomaly/` | Threshold, statistical z-score, and composite detectors with zero-variance safety. |
| **Root-Cause Diagnosis Engine** | `backend/app/intelligence/diagnosis/` | Explainable subsystem diagnosis, multi-signal correlation, and catalog rule weights. |
| **Maintenance Recommender** | `backend/app/intelligence/maintenance.py` | Advisory maintenance prioritization (MONITOR, INSPECT, SCHEDULE, GROUND) with evidence. |
| **Intelligence Service** | `backend/app/intelligence/service.py` | Pipeline orchestration, correlation/deduplication window, and SQLite WAL persistence. |
| **Health History Aggregator** | `backend/app/prognostics/health_history.py` | Chronological snapshot extraction from twin states without telemetry duplication. |
| **Degradation Trend Estimator**| `backend/app/prognostics/trend.py` | OLS regression over time, degradation rate, direction classification, and fit quality ($R^2$). |
| **Deterministic RUL Predictor** | `backend/app/prognostics/rul.py` | Extensible `BaseRULPredictor` protocol, linear extrapolation, conservative wear bounds, and anomaly modifiers. |
| **Maintenance Forecaster** | `backend/app/prognostics/forecast.py` | Consolidated 5-tier maintenance advisory (MONITOR through GROUND_FOR_REVIEW) with operational windows. |
| **Prognostics Service** | `backend/app/prognostics/service.py` | End-to-end prognostic assessment, readiness impact evaluation, and SQLite WAL persistence. |

---

## 12. Current Architectural State & Limitations

1. **In-Memory Ring Buffer:** Telemetry buffering uses a thread-safe in-memory ring buffer suitable for the SIH demonstration. Production deployment will bridge this to Kafka/Pulsar.
2. **Synchronous Execution Handlers:** Action execution handlers are in-process callable functions; distributed worker task queues (e.g., Celery/Redis) are not yet integrated.
3. **Analytical Boundary:** Telemetry, Digital Twin, Intelligence, and Prognostics processing are strictly observational and diagnostic. No autonomous control or weapon interlocks are implemented.
4. **Heuristic & Trend Lifing:** Health, wear, anomaly, and RUL calculations represent an explainable SIH prototype methodology rather than production-certified aerospace physics models.

---

## 13. Aero Implementation Roadmap

| Feature Area | Target Phase | Status | Scope |
| :--- | :--- | :--- | :--- |
| **Foundation Baseline** | Phase 1 | **COMPLETED** | FastAPI, WAL Database, Policy Engine, Audit Ledger, Execution Gateway |
| **Aerospace Domain Model** | Phase 2 | **COMPLETED** | Airframe, Components, Readiness scoring, Sorties/Missions, Maintenance logs |
| **Flight Telemetry Fabric** | Phase 3 | **COMPLETED** | Unit normalization, quality checking, envelope checks, buffer, persistence, REST APIs |
| **Aircraft Digital Twin** | Phase 4 | **COMPLETED** | Bitemporal aircraft twin state, flight hours/cycles counters, component wear tracking |
| **Subsystem Intelligence** | Phase 5 | **COMPLETED** | Threshold/statistical anomaly detection, root-cause diagnosis, maintenance recommendations |
| **Remaining Useful Life (RUL)** | Phase 6 | **COMPLETED** | Explainable health trends, OLS degradation, bounded RUL, 5-tier forecasts, readiness impact |
| **Mission Manager & ATO** | Phase 7 | *Next Phase* | Air Tasking Order (ATO) pipeline, sortie generator, mission route & loadout planning |
| **What-If Mission Simulation** | Phase 8 | Planned | Counterfactual mission simulation, fleet turnaround optimization |
| **Tactical Command HUD** | Phase 9 | Planned | Tactical map overlay, aircraft readiness grid, squadron Kanban |
| **Governance Gates** | Phase 10 | Planned | Rules of Engagement (ROE) policy rules, weapon release two-person gate |
| **Verification & Debrief** | Phase 11 | Planned | Post-maintenance BITE run-up test verification, post-sortie debrief learning loop |
