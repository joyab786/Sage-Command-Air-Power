# SageCommand Air Power System (Aero) — System Architecture
**Phase 1: Foundation Baseline Specification**  
*Document Version:* 1.0.0  
*Date:* 2026-10-06  
*Status:* IMPLEMENTED BASELINE  

---

## 1. Aero Architecture Principles

The **SageCommand Air Power System (Aero)** is designed as an autonomous command, decision-support, and governance platform for military air operations. The architecture strictly follows these foundational principles:

1. **Clean Domain Separation:** The previous SageCommand system was tailored to discrete manufacturing and commercial supply chains (`PLANT`, `MACHINE`, `PUMP`, `INVENTORY`, `SUPPLIER`). Aero rejects all manufacturing domain concepts. Core mechanisms are adapted into a domain-neutral foundation before introducing aerospace entities.
2. **Deterministic Governance Over LLM Output:** Large Language Models and AI agents generate hypotheses, strategies, and advisory intelligence. However, **deterministic systems enforce rules**. Write actions must pass through strict policy engines and execution gates.
3. **Decoupled Analytical vs. Execution Planes:** Analytical intelligence (telemetry fusion, anomaly detection, predictive maintenance, simulation) is strictly read-only. Analytical modules have zero authority to perform physical or operational mutations.
4. **Append-Only Tamper-Evident Auditability:** Every decision, policy evaluation, and operational action is recorded in a cryptographically chained SHA-256 audit ledger.
5. **Two-Person Rule for High-Risk Actions:** High-risk actions require independent human approval. The proposing actor is barred from approving their own high-risk actions.
6. **High-Concurrency Telemetry Preparation:** The database foundation is configured with SQLite Write-Ahead Logging (WAL) mode and asynchronous queues to support high-rate aircraft sensor streams.

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
│   │   │   └── database.py           # SQLAlchemy engine, sessions, and SQLite WAL pragma
│   │   ├── api/
│   │   │   ├── __init__.py           # API exports
│   │   │   └── routes/
│   │   │       ├── __init__.py       # Route exports
│   │   │       └── health.py         # GET /health diagnostics endpoint
│   │   ├── services/
│   │   │   ├── __init__.py           # Services exports
│   │   │   ├── policy_engine.py      # Deterministic policy engine (DENY > APPROVAL > HOLD > ALLOW)
│   │   │   ├── audit_ledger.py       # Append-only cryptographic SHA-256 audit ledger
│   │   │   └── execution_gateway.py  # 10-gate transactional write boundary & two-person rule
│   │   └── graph/
│   │       └── __init__.py           # Agent orchestration graph package (deferred to Phase 5)
│   ├── tests/
│   │   ├── __init__.py               # Test suite package
│   │   ├── conftest.py               # Shared pytest fixtures (in-memory DB, TestClient)
│   │   ├── unit/
│   │   │   ├── test_config.py        # Configuration loading tests
│   │   │   ├── test_contracts.py     # Base contract & envelope tests
│   │   │   ├── test_database.py      # Database transaction commit & rollback tests
│   │   │   ├── test_policy_engine.py # Policy precedence & anti-code injection tests
│   │   │   ├── test_audit_ledger.py  # Audit append & tamper detection tests
│   │   │   └── test_execution_gateway.py # Execution gates, two-person rule & rollback tests
│   │   └── integration/
│   │       ├── test_health_api.py    # GET /health & correlation header tests
│   │       └── test_application_lifecycle.py # Startup & shutdown lifecycle tests
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
│   └── ARCHITECTURE.md               # This architectural specification document
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
│ Reusable Core Infrastructure & Contracts               │
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

The test suite in `backend/tests/` provides automated verification:
- **Unit Tests (20 tests):** Configuration loading, Pydantic contracts, database commit/rollback, policy engine precedence, audit ledger hash chaining/tamper detection, execution gateway gates.
- **Integration Tests (5 tests):** FastAPI application lifecycle, `/health` and `/api/v1/health` diagnostic responses, request correlation ID propagation, 404 handling.
- **Test Results:** 25 passed in 0.25 seconds.

---

## 11. Reuse Strategy

| Reused Mechanism | SageCommand Origin | Aero Adaptation | Rationale |
| :--- | :--- | :--- | :--- |
| **Deterministic Policy Engine** | `backend/services/policy_service.py` | `backend/app/services/policy_engine.py` | Removed all plant/factory rules; created domain-neutral rule condition evaluator. |
| **Cryptographic Audit Ledger** | `backend/services/audit_ledger.py` | `backend/app/services/audit_ledger.py` | Removed `plant_id` coupling; preserved SHA-256 chaining and tamper verification. |
| **Execution Gateway** | `backend/services/execution_gateway.py` | `backend/app/services/execution_gateway.py` | Stripped manufacturing action types; preserved 10-gate pipeline and two-person rule. |
| **Database Connection Model** | `backend/gateway/db_gateway.py` | `backend/app/db/database.py` | Replaced complex dynamic hot-swapping with robust SQLite WAL session manager. |
| **Pydantic Envelope Pattern** | `backend/data/schemas/` | `backend/app/contracts/` | Modernized from Pydantic v1 validators to clean Pydantic v2 contracts. |

---

## 12. Current Limitations

1. **In-Memory Service Registries:** Policy Engine, Audit Ledger, and Execution Gateway currently maintain state in thread-safe memory caches. SQLite persistence will be attached during Phase 2.
2. **Synchronous Execution Handlers:** Action execution handlers are in-process callable functions; distributed worker task queues (e.g., Celery/Redis) are not yet integrated.
3. **No Domain Entities:** No aircraft, sortie, mission, or telemetry models exist in this baseline.

---

## 13. Deferred Aero Domain Features

The following capabilities are **explicitly planned and deferred** to subsequent phases:

| Feature Area | Planned Phase | Scope |
| :--- | :--- | :--- |
| **Aerospace Domain Model** | Phase 2 | Airframe, Squadron, Wing, Air Base, Sortie, Flight, Propulsion, Avionics, Munitions |
| **Flight Telemetry Fabric** | Phase 3 | Telemetry ingestion bus, ARINC 429 / MIL-STD-1553 parser, flight time-series store |
| **Aircraft Digital Twin** | Phase 4 | Bitemporal aircraft twin state, flight hours/cycles counters, component wear tracking |
| **Subsystem Intelligence** | Phase 5 | Avionics & turbine sensor fusion, flight envelope anomaly detection, BIT code RCA |
| **Remaining Useful Life (RUL)** | Phase 6 | Physics-informed component degradation models, unscheduled maintenance prediction |
| **Mission Manager & ATO** | Phase 7 | Air Tasking Order (ATO) pipeline, sortie generator, mission route & loadout planning |
| **What-If Mission Simulation** | Phase 8 | Counterfactual mission simulation, fleet turnaround optimization |
| **Tactical Command HUD** | Phase 9 | Tactical map overlay, aircraft readiness grid, squadron Kanban |
| **Governance Gates** | Phase 10 | Rules of Engagement (ROE) policy rules, weapon release two-person gate |
| **Verification & Debrief** | Phase 11 | Post-maintenance BITE run-up test verification, post-sortie debrief learning loop |
