# Aero Codebase Reconnaissance
**SageCommand Air Power System — Aero**  
**Architectural Audit & Baseline Assessment**  
*Document Version:* 1.0.0  
*Date:* 2026-10-06  
*Status:* COMPLETE  

---

## 1. Executive Summary

This reconnaissance document establishes the architectural baseline for **SageCommand Air Power System — Aero** prior to any feature implementation. 

### Operational Context & Findings:
1. **Target Workspace State (`e:\js\Sage-Command-Air-Power`):**
   - The workspace is a newly initialized Git repository linked to `https://github.com/joyab786/Sage-Command-Air-Power.git` on branch `main`.
   - Prior to this audit, no codebase commits existed in this repository.
   - An environment wrapper (`powershell.cmd`) was introduced to enable Antigravity shell execution under Windows runner constraints.
   - **Zero Aero domain capabilities** are currently implemented within the workspace repository.

2. **Predecessor Reference Codebase (`E:\js\sage_command_production`):**
   - The predecessor project contains an enterprise-grade, production-hardened implementation of **SageCommand V3** (1,214 automated test cases across 38 test suites).
   - Features include a FastAPI backend, Next.js 16/React 19 Obsidian Command Center frontend, a multi-agent LangGraph orchestration network, a 10-gate deterministic Execution Gateway, policy enforcement engine, RBAC/ABAC authorization, SHA-256 cryptographic audit ledger, and 18 specialized intelligence services (Multimodal Sensor Fusion, What-If Counterfactual Simulation, Anomaly Detection, Blast Radius Analysis, Root Cause Analysis, Predictive Maintenance, etc.).

3. **Core Transition Challenge (Industrial to Aerospace):**
   - The underlying mathematical engines, event streaming, graph structures, bitemporal ledgers, and governance guardrails are **fully mature and reusable**.
   - However, 100% of the domain ontologies, schemas, entity types, and simulation scenarios in the predecessor codebase are hardcoded to **industrial discrete manufacturing** (factories, plants, pumps, PLCs, conveyor belts, warehouse inventory, supply chain stockouts, commercial customer SLAs).
   - The Aero system requires pivoting these core capabilities to **military/defense air operations**: airframes, flight squadrons, air wings, sorties, avionics, turbofan propulsion, weapons stations/munitions, electronic warfare suites, BIT/BITE telemetry, flight envelopes, air tasking orders (ATOs), and flight lead/mission commander governance.

---

## 2. Workspace Structure

### 2.1 Workspace Comparison Layout

```
E:\js\
├── Sage-Command-Air-Power\            <-- CURRENT ANTIGRAVITY WORKSPACE (Aero Project Root)
│   ├── .git/                          <-- Git repository (remote: joyab786/Sage-Command-Air-Power.git)
│   ├── docs/                          <-- Documentation root (Created during audit)
│   │   └── AERO_CODEBASE_RECONNAISSANCE.md  <-- This architectural audit document
│   └── powershell.cmd                 <-- Windows runner execution proxy
│
└── sage_command_production\           <-- SAGECOMMAND V3 REUSABLE REFERENCE BASELINE
    ├── backend/                       <-- FastAPI Python Backend (Python 3.12)
    │   ├── agents/                    <-- LangGraph agent worker nodes
    │   ├── api/                       <-- REST & WebSocket API routing endpoints (26 routers)
    │   ├── core/                      <-- Authentication, configuration, LLM clients, agent state
    │   ├── data/                      <-- Database context & Pydantic domain contracts (28 schemas)
    │   ├── gateway/                   <-- Live DB connection gateway, secret manager, network policies
    │   ├── governance/                <-- RBAC, guardrails, security monitor, middleware, audit
    │   ├── graph/                     <-- LangGraph workflow builder, state compiler, SQLite checkpointer
    │   ├── services/                  <-- 38 domain services and analytical repositories
    │   ├── tools/                     <-- LangChain tool definitions (database, inventory, action, search)
    │   ├── server.py                  <-- FastAPI application entrypoint
    │   └── requirements.txt           <-- Backend Python dependencies
    ├── frontend/                      <-- Next.js 16 / React 19 Frontend
    │   ├── app/                       <-- Next.js App Router (Obsidian Command Console)
    │   │   ├── components/            <-- 30 UI components & intelligence modal dashboards
    │   │   ├── layout.tsx             <-- Root layout & metadata
    │   │   └── page.tsx               <-- Central Command Center single-page application
    │   ├── lib/                       <-- API client utilities
    │   └── package.json               <-- Frontend Node.js dependencies
    └── docs/                          <-- 45 architectural baseline specifications & ADRs
```

### 2.2 Deep-Dive: SageCommand Backend Subsystems

```
sage_command_production/backend/
├── agents/
│   ├── copilot.py                    # Strategic Copilot conversational agent
│   ├── evaluator.py                  # Multi-strategy utility scoring agent
│   ├── execution.py                  # Transaction commit execution agent node
│   ├── observe_detect.py             # Vision diagnostics & anomaly discovery agents
│   ├── research.py                   # External market/tavily researcher agent
│   ├── risk_analysis.py              # Operational risk & blast-radius agent
│   ├── strategy.py                   # Strategy synthesis worker
│   └── supervisor.py                 # Dynamic routing supervisor node
├── api/                              # 26 modular REST router suites + WebSocket nervous system
│   ├── action_routes.py              # Structured action proposal, evaluation, and approval
│   ├── anomaly_routes.py             # Anomaly baseline creation and assessment runs
│   ├── audit_routes.py               # Cryptographic audit ledger query API
│   ├── blast_radius_routes.py        # Blast-radius graph traversal and impact API
│   ├── digital_twin_routes.py        # Twin entity snapshot, scenario, and diff API
│   ├── event_bus_routes.py           # Subscription, delivery, and dead-letter queue API
│   ├── incident_routes.py            # Incident lifecycle state machine API
│   ├── knowledge_graph_routes.py     # Bitemporal graph traversals, paths, and neighbors
│   ├── ontology_routes.py            # Controlled entity taxonomy and verification API
│   ├── policy_routes.py              # Deterministic policy rules and evaluation API
│   ├── predictive_maintenance_routes.py # Asset degradation and maintenance assessment API
│   ├── rca_routes.py                 # Root-cause analysis causality graph API
│   ├── sensor_fusion_routes.py       # Multimodal sensor alignment and fusion API
│   ├── what_if_simulation_routes.py  # Counterfactual what-if simulation API
│   └── websocket.py                  # Real-time WebSocket `/ws/sage` streaming hub
├── core/
│   ├── auth.py                       # Identity, role extraction, JWT validation
│   ├── config.py                     # Central environment configuration & safety bounds
│   ├── llm.py                        # Model factory (Gemini 1.5/2.0, Groq Llama 3)
│   └── state.py                      # SageOSState (12-stage operational state model)
├── data/schemas/                     # 28 Canonical domain contracts (Pydantic v2)
│   ├── action_contract.py            # Structured action proposal lifecycle
│   ├── anomaly_contract.py           # Statistical anomaly baselines & detections
│   ├── authorization_contract.py     # RBAC/ABAC role, permission, and scope contracts
│   ├── blast_radius_contract.py      # Bounded blast radius graphs & impact paths
│   ├── digital_twin_contract.py      # Virtual state property, version, and snapshot models
│   ├── event_contract.py             # Canonical CloudEvents-compliant event schema
│   ├── incident_contract.py          # Incident lifecycle, timeline, and evidence contracts
│   ├── knowledge_graph_contract.py   # Bitemporal facts, edges, and provenance models
│   ├── ontology_contract.py          # Industrial entity taxonomies and compatibility matrices
│   ├── policy_contract.py            # Deterministic policy rules, conditions, and effects
│   ├── predictive_maintenance_contract.py # Risk score, degradation, and evidence models
│   ├── rca_contract.py               # Causal candidates, relationships, and hypotheses
│   ├── sensor_fusion_contract.py     # Multimodal sensor observations, units, and fusion models
│   └── what_if_simulation_contract.py# Counterfactual simulation scenarios and deltas
├── gateway/
│   ├── db_adapters.py                # Multi-engine DB connectivity (SQLite, Postgres, MySQL)
│   ├── db_gateway.py                 # Session-scoped DB connection gateway
│   ├── network_policy.py             # CIDR allowlisting and loopback security policies
│   └── secret_provider.py            # Credential redaction and secret management
├── governance/
│   ├── audit.py                      # Security event logger with secret redaction
│   ├── custody.py                    # Chain-of-custody tracking across agent hops
│   ├── guardrails.py                 # SQL AST parser, write restriction, parameterization
│   ├── middleware.py                 # Security headers and request size limiters
│   ├── rbac.py                       # High-risk action classification rules
│   └── security.py                   # Intrusion detection and prompt injection scanner
├── graph/
│   ├── builder.py                    # LangGraph StateGraph compilation with HITL interrupt
│   └── checkpointer.py               # Persistent SQLite checkpoint saver
└── services/                         # 38 domain business logic services and SQLite repositories
```

---

## 3. Technology Stack

### 3.1 Backend Stack
- **Language / Runtime:** Python 3.12 (CPython x86-64)
- **Web API Framework:** FastAPI `>=0.115.0`, Uvicorn `>=0.32.0` (Standard ASGI)
- **Agent Orchestration:** LangGraph `>=0.2.56`, LangChain `>=0.3.20`, LangChain-Core `>=0.3.24`
- **State Checkpointing:** `langgraph-checkpoint-sqlite >=2.0.3`
- **LLM Integrations:** `langchain-google-genai >=2.0.7`, `langchain-tavily >=0.1.6`, Groq
- **Data Validation & Schemas:** Pydantic `>=2.10.0`
- **Database / ORM:** SQLAlchemy `>=2.0.0`, Pandas `>=2.2.0`, SQLite3 (standard library), PyMySQL, Psycopg2-binary
- **Security & Cryptography:** PyJWT `>=2.8.0`, Cryptography `>=43.0.0` (SHA-256 state hashes)
- **Async Networking:** HTTPX `>=0.28.0`, Requests `>=2.32.0`, Aiofiles `>=24.1.0`

### 3.2 Frontend Stack
- **Framework:** Next.js `16.2.7` (App Router, React Server Components enabled)
- **UI Core:** React `19.2.4`, React-DOM `19.2.4`
- **Graph & Workflow Visualization:** ReactFlow `^11.11.4` (`@xyflow/react`)
- **Animation & Transitions:** Framer Motion `^12.40.0`
- **Component Styling:** Tailwind CSS `^3.4.19` / `@tailwindcss/postcss ^4`, Tailwind Merge `^3.6.0`, Clsx `^2.1.1`
- **Icons & Visuals:** Lucide React `^1.17.0`
- **Dates & Formatting:** Date-fns `^4.4.0`
- **Language:** TypeScript `^5.0.0`

---

## 4. Current System Architecture

The existing architecture establishes a **strict architectural boundary** between purely observational/analytical intelligence and deterministic write execution.

```
                              [ Operator Web Console (Next.js 16) ]
                                             ▲  │
                                WebSocket    │  │  REST API Calls
                                Stream /ws   │  ▼
                     ┌──────────────────────────────────────────────────┐
                     │          FastAPI Nervous System Gateway          │
                     │  - SecurityHeaders & RequestSizeLimiter          │
                     │  - JWT Authentication & RBAC/ABAC Context        │
                     └─────────────────────────┬────────────────────────┘
                                               │
                                               ▼
                     ┌──────────────────────────────────────────────────┐
                     │         LangGraph Agent Orchestration Hub        │
                     │  - Security Intrusion Gate                       │
                     │  - Vision Diagnostics (Multimodal)               │
                     │  - Strategic Copilot                             │
                     │  - Autonomous Pipeline (Discovery -> Risk Agent) │
                     │  - Supervisor Dynamic Routing                    │
                     │  - Strategy Worker & Market Researcher           │
                     │  - Evaluator Utility Scoring                     │
                     └─────────────┬──────────────────────┬─────────────┘
                                   │                      │
                  Observational    │                      │ Interrupt Before Execution
                  Read Operations  │                      │ (HITL Approval Gate)
                                   ▼                      ▼
┌───────────────────────────────────────────────┐  ┌───────────────────────────────────┐
│     Pure Analytical Intelligence Services     │  │   Deterministic Execution Gateway │
│     (Strictly Prohibited from Writes)         │  │   (10-Gate Mutation Boundary)     │
├───────────────────────────────────────────────┤  ├───────────────────────────────────┤
│ • Multimodal Sensor Fusion Service            │  │ Gate 1: Auth & Identity           │
│ • Real Anomaly Detection Engine               │  │ Gate 2: Operational Permissions  │
│ • Root Cause Analysis (Causal Graphs)         │  │ Gate 3: Target Scope Match        │
│ • Blast Radius Intelligence Service           │  │ Gate 4: State Machine Lifecycle   │
│ • Predictive Maintenance Intelligence         │  │ Gate 5: SHA-256 Staleness Hash    │
│ • What-If Counterfactual Simulator            │  │ Gate 6: Two-Person Approval       │
│ • Operational Knowledge Graph (Bitemporal)    │  │ Gate 7: Policy Engine Check       │
│ • Digital Twin State & Scenario Manager       │  │ Gate 8: Idempotency Key Lock      │
│ • Industrial Ontology Semantic Verifier       │  │ Gate 9: Concurrency Lock          │
│ • Data Quality Engine (Completeness/Drift)    │  │ Gate 10: Physical DB Transaction  │
└───────────────────────┬───────────────────────┘  └─────────────────┬─────────────────┘
                        │                                            │
                        ▼                                            ▼
┌───────────────────────────────────────────────┐  ┌───────────────────────────────────┐
│  State Ledger & Storage Layer (SQLite/Memory) │  │  Authoritative Audit & Custody    │
│  - SQLite Bitemporal Event/Fact Stores        │  │  - Append-Only SHA-256 Ledger     │
│  - LangGraph Memory Checkpoints               │  │  - Chain of Custody Tracker       │
│  - Dynamic DataCore Operational Telemetry     │  │  - Sanitized Secret Redaction     │
└───────────────────────────────────────────────┘  └───────────────────────────────────┘
```

---

## 5. SageCommand Reusable Foundations

The following components from the predecessor system represent high-value architectural assets that can be reused directly or adapted for Aero:

| Component | Path | Purpose | Status | Reuse Strategy | Dependencies | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LangGraph Orchestrator** | `backend/graph/builder.py` | Multi-agent DAG routing with native HITL interrupts | Production-Ready | Reuse as-is with Aero-specific agent nodes | LangGraph, LangChain, SQLite | Medium: Agent prompt and state payload adaptation |
| **Deterministic Execution Gateway** | `backend/services/execution_gateway.py` | 10-gate transactional write boundary with rollback | Production-Ready | Reuse as-is (strict invariant enforcement) | SQLAlchemy, SQLite, Pydantic | Low: Well-tested deterministic gate pipeline |
| **Deterministic Policy Engine** | `backend/services/policy_service.py` | Evaluates declarative rules (DENY > APPROVAL > HOLD > ALLOW) | Production-Ready | Reuse engine, replace industrial rules with air combat doctrine | SQLite, Pydantic | Low: Rule definitions decoupled from engine logic |
| **RBAC / ABAC Authorization Service** | `backend/services/authorization_service.py` | Acyclic role hierarchy, capability evaluation, scope checks | Production-Ready | Adapt roles (`operator` -> `pilot`, `maintenance_lead` -> `crew_chief`, `manager` -> `squadron_commander`) | SQLite, Pydantic, Hashlib | Low: Core permission evaluator is generic |
| **Authoritative Audit Ledger** | `backend/services/audit_ledger.py` | Append-only cryptographically chained (SHA-256) event ledger | Production-Ready | Reuse as-is | Pydantic, Hashlib | Very Low: Zero operational side effects |
| **Multimodal Sensor Fusion Service** | `backend/services/sensor_fusion_service.py` | Temporal alignment, unit conversion, cross-modal agreement | Production-Ready | Adapt modality weights to avionics, radar, turbine telemetry | Pydantic, Math | Medium: Calibrating sensor weights for flight envelopes |
| **Real Anomaly Detection Engine** | `backend/services/anomaly_detection_service.py` | Z-score, rolling statistical anomaly baselining | Production-Ready | Reuse statistical algorithms, retarget to flight telemetry | Digital Twin, Data Quality | Medium: High-frequency flight data baseline drifts |
| **Root-Cause Analysis Service** | `backend/services/rca_service.py` | Causal dependency graphs, temporal reasoning, hypotheses | Production-Ready | Retarget causal rules from pumps/lines to aircraft subsystems | Knowledge Graph, Twin | Medium: Building aeronautical causal failure graph |
| **Blast-Radius Intelligence Service** | `backend/services/blast_radius_service.py` | BFS/DFS cascading failure propagation over graphs | Production-Ready | Adapt to airframe subsystem cascading failures | Knowledge Graph | Low: Graph traversal algorithms are domain-agnostic |
| **Predictive Maintenance Service** | `backend/services/predictive_maintenance_service.py` | Asset health, degradation scores, failure probability | Partial / Heuristic | Heavy Aero adaptation: compute RUL in Flight Hours and Cycles | Knowledge Graph, Twin | High: Current logic relies on heuristic asset name matching |
| **What-If Simulation Engine** | `backend/services/what_if_simulation_service.py` | Counterfactual scenario branching, constraint verification | Production-Ready | Retarget scenario variables to fuel, munitions, weather, sorties | Pydantic, Sensor Fusion | Medium: Aerodynamic / combat constraint modeling |
| **Digital Twin Foundation** | `backend/services/digital_twin_service.py` | Bitemporal virtual state, property versioning, snapshots | Production-Ready | Replace industrial entity types with Aircraft Twin models | Ontology Service, KG | High: Industrial schema tightly coupled in current contracts |
| **Operational Knowledge Graph** | `backend/services/knowledge_graph_service.py` | Bitemporal fact/edge traversal, freshness validation | Production-Ready | Reuse engine, populate with aerospace fleet topology | Ontology Service, SQLite | Low: Core graph traversal engine is robust |
| **Industrial Ontology Engine** | `backend/services/ontology_service.py` | Semantic taxonomy validation & compatibility matrix | Production-Ready | Replace taxonomy with Aero Domain Ontology | Pydantic, Regex | High: Current taxonomy is 100% manufacturing entities |
| **Internal Event Bus** | `backend/services/event_bus.py` | Bounded async queue, worker pool, dead-letter dispatch | Production-Ready | Reuse as-is | Asyncio, Pydantic | Very Low: Transport agnostic |
| **Incident Management Service** | `backend/services/incident_service.py` | Finite state machine for incidents with timeline & notes | Production-Ready | Adapt categories (`SAFETY` -> `IN_FLIGHT_EMERGENCY`, `ABORT`) | SQLite, Pydantic | Low: State machine logic is universal |
| **WebSocket Nervous System** | `backend/api/websocket.py` | Real-time bidirectional telemetry & guardrail interrupts | Production-Ready | Adapt payloads for combat radar and tactical feeds | FastAPI WebSocket | Low: Protocol is proven and responsive |
| **Obsidian UI & Neural Flow** | `frontend/app/` | ReactFlow agent visualizer, dark-mode command console | Production-Ready | Adapt dashboard cards to Air Power Command views | React 19, ReactFlow, Framer | Medium: UI theme requires tactical HUD styling |

---

## 6. Current Aero Capabilities

### 6.1 Assessment of Current Aero-Specific Code
- **Workspace Repository (`Sage-Command-Air-Power`):** **0% implemented.** The repository is clean and uncommitted.
- **Reference Predecessor (`sage_command_production`):** **0% Aero-specific semantics.**
  - There are NO models for `Aircraft`, `Airframe`, `Squadron`, `Sortie`, `FlightHours`, `Avionics`, `Munitions`, or `AirTaskingOrder`.
  - All existing domain entities are: `PLANT`, `PRODUCTION_LINE`, `WORK_CELL`, `MACHINE`, `PUMP`, `PLC`, `INVENTORY`, `SUPPLIER`, `CUSTOMER`.
  - Existing telemetry simulator (`services/simulator.py`) generates mock supply chain inventory and shipment tracking codes (`TRK-8821-ALPHA`), not flight or engine telemetry.

### 6.2 Conclusion
The Aero system must be constructed by porting the proven architectural foundations while building the **Aero Air Power System domain model from the ground up**.

---

## 7. Operational Intelligence Loop Mapping

Evaluating existing components against the conceptual Aero operational loop:

```
OBSERVE → DETECT → UNDERSTAND → PREDICT → DIAGNOSE → SIMULATE → OPTIMIZE → RECOMMEND → HUMAN GOVERNANCE → MAINTENANCE → VERIFY → LEARN
```

| Stage | Status | Existing Implementation | Evidence | Gap |
| :--- | :--- | :--- | :--- | :--- |
| **1. OBSERVE** | PARTIALLY IMPLEMENTED | `SensorFusionService`, `gateway/db_gateway.py`, `services/simulator.py` | Heterogeneous sensor alignment, unit conversion in `sensor_fusion_service.py` | Telemetry is factory-oriented (pumps, inventory); missing real-time flight telemetry stream (ARINC 429, MIL-STD-1553, GPS, pitch/roll/yaw, EGT, N1/N2 RPM). |
| **2. DETECT** | PARTIALLY IMPLEMENTED | `AnomalyDetectionService`, `observe_detect.py` | Z-score statistical evaluation on twin properties in `anomaly_detection_service.py` | Detectors tuned to static plant baselines; missing dynamic flight envelope anomaly detection and sensor freeze detection. |
| **3. UNDERSTAND** | PARTIALLY IMPLEMENTED | `OntologyService`, `KnowledgeGraphService` | Bitemporal entity-relationship graph in `knowledge_graph_service.py` | Ontological taxonomy is factory-based (`MACHINE`, `PLC`); missing aircraft structural decomposition (ATA 100 / S1000D chapters, avionics, hydraulics, weapons). |
| **4. PREDICT** | PARTIALLY IMPLEMENTED | `PredictiveMaintenanceService`, `demand_forecasting_service.py` | Health scores, failure probabilities in `predictive_maintenance_service.py` | Predictor uses string matching (`"pump" in asset_id`); missing physics-based Remaining Useful Life (RUL) in flight hours/cycles. |
| **5. DIAGNOSE** | PARTIALLY IMPLEMENTED | `RcaService`, `BlastRadiusService` | Causal dependency graphs, hypothesis ranking in `rca_service.py` | Causal relationships lack aircraft fault isolation trees, Built-In Test (BIT) code mapping, and aerodynamic degradation models. |
| **6. SIMULATE** | PARTIALLY IMPLEMENTED | `WhatIfSimulationService`, `DigitalTwinService` | Counterfactual scenario variable evaluation in `what_if_simulation_service.py` | Simulates supply chain price/lead-time deltas; missing flight profile simulation, combat mission sortie execution, and weather impact. |
| **7. OPTIMIZE** | NOT IMPLEMENTED | `agents/strategy.py`, `agents/evaluator.py` | Prompt-based strategy generation in `strategy.py`; simple utility ranking | Missing mathematical air fleet sortie generation optimization, maintenance crew scheduling, and weapons loadout allocation. |
| **8. RECOMMEND** | PARTIALLY IMPLEMENTED | `PredictiveMaintenanceService`, `agents/evaluator.py` | Generates text-based recommendation cards with evidence links | Recommendations are factory work orders; missing Air Tasking Order (ATO) recommendations and Go/No-Go sortie clearance. |
| **9. HUMAN GOVERNANCE** | IMPLEMENTED | `graph/builder.py`, `ExecutionGateway`, `policy_service.py` | LangGraph `interrupt_before=["execution"]`, 10-gate `execution_gateway.py` | The governance engine itself is production-grade; only requires aerospace authority roles (`FlightLead`, `MissionCommander`, `CrewChief`). |
| **10. MAINTENANCE** | PARTIALLY IMPLEMENTED | `services/incident_service.py`, `action_store.py` | Incident lifecycle state machine, work order action proposals | Missing Line Replaceable Unit (LRU) tracking, maintenance turnaround tracking, and hangar bay scheduling. |
| **11. VERIFY** | PARTIALLY IMPLEMENTED | `core/state.py` (`IndustrialStage.VERIFY`), `ExecutionGateway` | Post-transaction database verification step | Missing post-maintenance Built-In-Test-Equipment (BITE) run-up verification and post-flight debrief telemetry validation. |
| **12. LEARN** | PARTIALLY IMPLEMENTED | `services/audit_ledger.py`, `governance/custody.py` | Append-only audit ledger and chain-of-custody recording in `audit_ledger.py` | Logs events accurately, but lacks automated feedback loop into fleet-wide reliability parameters or predictive model retraining. |

---

## 8. Aero Architecture Layer Mapping

Mapping existing components against the 11 target Aero layers:

| Layer | Current Status | Existing Components | Missing Components |
| :--- | :--- | :--- | :--- |
| **1. Command Center** | PARTIALLY IMPLEMENTED | Next.js 16 Obsidian UI, ReactFlow graph, execution feed, 15 modals | Tactical HUD / Air Operations Center (AOC) interface, interactive theater/base map, fleet status matrix, mission timeline |
| **2. Mission Manager** | NOT IMPLEMENTED | `data/schemas/mission.py` (basic schema) | Mission lifecycle manager, Air Tasking Order (ATO) parser/generator, sortie dispatcher, flight lead assignment engine |
| **3. Intelligence Layer** | PARTIALLY IMPLEMENTED | `SensorFusionService`, `AnomalyDetectionService`, `RcaService`, `BlastRadiusService` | Aircraft subsystem intelligence, tactical threat assessment, combat readiness scoring, mission risk calculator |
| **4. Aircraft Digital Twin** | PARTIALLY IMPLEMENTED | `DigitalTwinService`, `digital_twin_repository.py` | Aircraft Twin contract (airframe hours, landing cycles, engine core temps, avionics bus state, weapons payload config) |
| **5. Knowledge Layer** | PARTIALLY IMPLEMENTED | `KnowledgeGraphService`, `OntologyService` | Aerospace domain ontology, NATO/DoD operational doctrine graph, aircraft maintenance technical manuals (IETM) RAG |
| **6. Data Fabric** | PARTIALLY IMPLEMENTED | `DatabaseConnectionGateway`, `EventBus`, `db_adapters.py` | Real-time flight telemetry ingestion pipeline, MIL-STD-1553 bus parser, bitemporal flight time-series repository |
| **7. AI/ML Services** | PARTIALLY IMPLEMENTED | Gemini/Groq LLM factory, Z-score statistical engine | Physics-informed neural network (PINN) / turbofan degradation models, flight envelope anomaly models, vision BDA |
| **8. Simulation & Optimization** | PARTIALLY IMPLEMENTED | `WhatIfSimulationService`, `services/simulator.py` | Aerodynamic flight profile simulation, mission combat attrition simulation, sortie turnaround fleet optimizer |
| **9. Human-in-the-Loop Governance** | IMPLEMENTED | LangGraph interrupt gate, `ExecutionGateway`, `PolicyService` | Tactical rules of engagement (ROE), flight safety limits, multi-commander consensus protocols |
| **10. Security / RBAC** | IMPLEMENTED | `AuthorizationService`, `governance/rbac.py`, `core/auth.py` | Military clearance classification levels (UNCLASSIFIED, SECRET, TOP SECRET), compartmented mission access control |
| **11. Audit & Observability** | IMPLEMENTED | `AuditLedgerService`, `governance/custody.py` | Mission flight data recorder (black box) audit trails, cryptographically sealed sortie logs |

---

## 9. Data Flow

### 9.1 Supported Real Data Flow (Operator / Command Console)

```
[ Operator / Commander ]
         │
         ▼
[ Next.js 16 UI (ObsidianCommandCenter) ]
         │
         │  1. WebSocket Connect (/ws/sage?token=...)
         │  2. User Prompt / Diagnostics Upload / Scan Command
         ▼
[ FastAPI WebSocket Nervous System (backend/api/websocket.py) ]
         │
         │  3. Authenticate Identity & Role (core/auth.py)
         │  4. Mount Database Context (services/connection_manager.py)
         ▼
[ LangGraph StateGraph (backend/graph/builder.py) ]
         │
         ├─► Security Agent Node: Intrusion & SQL injection check (governance/security.py)
         ├─► Strategic Copilot / Autonomous Discovery Node
         ├─► Risk Agent / Blast Radius Calculation
         ├─► Supervisor: Dynamic routing to Strategy / Evaluator
         ▼
[ LangGraph Interrupt Before Execution (HITL Gate) ]
         │
         │  5. Emits `guardrail_interrupt` JSON event to WebSocket
         ▼
[ Operator Console (ExecutionFeed.tsx) ]
         │
         │  6. Operator clicks "Authorize" or "Abort"
         ▼
[ FastAPI WebSocket Endpoint ]
         │
         │  7. If "Authorize": Validates RBAC & Action Context
         ▼
[ Deterministic Execution Gateway (backend/services/execution_gateway.py) ]
         │
         │  8. Evaluates 10-gate validation pipeline
         │  9. Revalidates Policy Engine (services/policy_service.py)
         │ 10. Commits write to database target
         │ 11. Records append-only event to Audit Ledger (services/audit_ledger.py)
         ▼
[ Operator Console ]
         │  12. Receives execution confirmation & updated telemetry
```

### 9.2 Telemetry Data Flow (Current vs Target Aero)

**Current Implemented Flow:**
```
[ Mock SQLite Simulator (services/simulator.py) ]
         │
         ▼ (Simulates factory inventory rows)
[ Database Connection Gateway (gateway/db_gateway.py) ]
         │
         ▼
[ Data Quality Service -> Sensor Fusion Service -> Anomaly Engine ]
         │
         ▼
[ Operator Notification via WebSocket ]
```

**Target Aero Telemetry Flow:**
```
[ Aircraft Telemetry Source (Flight Sensors, Avionics, Turbofan FADEC) ]
         │
         ▼
[ High-Throughput Telemetry Ingestion (Data Fabric / Event Bus) ]
         │
         ▼
[ Data Quality & Unit Normalization (Sensor Fusion Service) ]
         │
         ├─► Real-Time Flight Time-Series Store
         ├─► Aircraft Digital Twin (Virtual State & Flight Hour Updates)
         │
         ▼
[ Anomaly Detection & Subsystem Diagnostics (Z-score, BIT Codes, RCA) ]
         │
         ▼
[ Predictive Maintenance (RUL Calculation) & Tactical Blast Radius ]
         │
         ▼
[ Command Center Alert / Sortie Recommendation -> Mission Commander ]
```

---

## 10. Dependency Analysis

Classification of major workspace dependencies:

### 10.1 Backend (Python)
- **CORE:**
  - `fastapi` (`>=0.115.0`), `uvicorn` (`>=0.32.0`): Core HTTP/WebSocket server.
  - `langgraph` (`>=0.2.56`), `langchain` (`>=0.3.20`), `langchain-core` (`>=0.3.24`): Agent DAG orchestration.
  - `langgraph-checkpoint-sqlite` (`>=2.0.3`): Persistent graph state saving.
  - `pydantic` (`>=2.10.0`): Type contracts and data validation.
  - `sqlalchemy` (`>=2.0.0`): Database abstraction layer.
  - `pyjwt` (`>=2.8.0`), `cryptography` (`>=43.0.0`): Security, RBAC, SHA-256 ledgers.
- **OPTIONAL:**
  - `langchain-google-genai` (`>=2.0.7`): Google Gemini model provider (can swap for local/air-gapped LLM).
  - `langchain-tavily` (`>=0.1.6`), `tavily-python` (`>=0.5.0`): Live web research (optional for air-gapped military deployments).
  - `psycopg2-binary`, `PyMySQL`: External production database adapters.
- **LEGACY / DEPRECATED:**
  - `langchain-community` (`>=0.3.11`): Emits sunset deprecation warnings in Python 3.12 (`langchain-community is being sunset...`). Should migrate to standalone packages.
  - Pydantic v1-style `@validator`: Used in `authorization_contract.py` (`@validator("permission_id")`), emitting `PydanticDeprecatedSince20` warnings. Should be refactored to `@field_validator`.
  - FastAPI `@app.on_event("startup")` / `"shutdown"`: Deprecated in modern FastAPI in favor of `lifespan` context managers.
- **DUPLICATED / CONFLICTING:** None in backend runtime, but relative vs absolute imports (`backend.core` vs `core`) cause test suite runner conflicts depending on `PYTHONPATH`.

### 10.2 Frontend (Node.js)
- **CORE:**
  - `next` (`16.2.7`), `react` (`19.2.4`), `react-dom` (`19.2.4`): Next.js App Router core.
  - `reactflow` (`^11.11.4`): Agent DAG visualizer.
  - `framer-motion` (`^12.40.0`): UI micro-animations and status transitions.
  - `lucide-react` (`^1.17.0`): Icon system.
- **POTENTIALLY CONFLICTING / DUPLICATED:**
  - `@tailwindcss/postcss` (`^4`) AND `tailwindcss` (`^3.4.19`): In `package.json`, both Tailwind v4 PostCSS plugin and Tailwind v3 package are specified simultaneously.
  - `postcss.config.js` AND `postcss.config.mjs`: Redundant configuration files in `frontend/` root.

---

## 11. Architecture Gap Analysis

### Category A: Already Implemented
- Multi-agent LangGraph orchestration with deterministic routing.
- Human-in-the-Loop (HITL) interrupt gate before write execution.
- 10-gate Deterministic Execution Gateway with cryptographic hash checks and rollback.
- Deterministic Policy Enforcement Engine with strict precedence (`DENY > APPROVAL > HOLD > ALLOW`).
- Authoritative append-only Audit Ledger with SHA-256 event chaining.
- Multimodal Sensor Fusion service with unit conversion and cross-modal agreement scoring.
- Bitemporal Knowledge Graph traversal and freshness evaluation.
- WebSocket real-time nervous system with JWT authentication and threat intercept.

### Category B: Reusable SageCommand Foundation
- `EventBus` asynchronous message queue and dead-letter dispatcher.
- `DatabaseConnectionGateway` session-scoped connection manager.
- Statistical Anomaly Detection engine (Z-score and baseline windows).
- Causal Root-Cause Analysis (RCA) engine with temporal reasoning.
- Blast-Radius graph traversal algorithms.
- What-If counterfactual scenario evaluation framework.
- ReactFlow interactive DAG node visualizer (`NeuralFlowGraph.tsx`).

### Category C: Partially Implemented
- **Digital Twin:** Architecture exists (`TwinEntity`, `TwinStateProperty`, `TwinSnapshot`), but schemas only support manufacturing machinery.
- **Predictive Maintenance:** Health score and risk assessment framework exists, but mathematical RUL calculation is heuristic.
- **Incident Management:** Incident lifecycle and timeline engine exists, but categories must be adapted to flight emergencies.
- **RBAC / ABAC:** Role evaluation engine exists, but military operational roles are absent.

### Category D: Missing Aero Functionality
- **Aeronautical Domain Ontology:** Airframe, avionics, turbofan propulsion, weapons station, munition, squadron, wing, air base, sortie models.
- **Flight Telemetry Ingestion Pipeline:** High-frequency flight data recording (pitch/roll/yaw, altitude, airspeed, Mach, G-load, EGT, fuel flow).
- **Subsystem Fault Isolation & BIT Mapping:** Translation of Built-In Test (BIT/BITE) codes to causal graphs.
- **Remaining Useful Life (RUL) Engine:** Physics-informed degradation models calculated in Flight Hours (FH) and Flight Cycles (FC).
- **Mission Manager & Air Tasking Order (ATO) Pipeline:** Sortie generation, mission lifecycle, flight lead assignment, weapons loadout authorization.
- **Tactical Command Center UI:** Tactical theater/base view, aircraft readiness status grid, sortie dispatch Kanban, air combat governance approvals.

### Category E: Architecture Decisions Required
1. **Telemetry Protocol:** Whether to standardize on WebSocket streaming or integrate MQTT / gRPC for aircraft telemetry ingestion.
2. **Time-Series Storage:** Whether SQLite is sufficient for Aero flight time-series data or if TimescaleDB / Parquet files should back high-frequency flight logs.
3. **Geospatial / Tactical Map Engine:** Selecting between CesiumJS (3D globe), Mapbox GL, or a lightweight tactical SVG/Canvas map component for base and airspace visualization.
4. **Air Doctrine Standards:** Aligning terminology with NATO / DoD standard definitions (ATO, Sortie, BDA, ROE, LRU, FMC/PMC/NMC readiness).
5. **Air-Gapped LLM Strategy:** Deciding whether the system will rely on cloud LLM APIs (Gemini/Groq) or integrate local open-weights models (Ollama/vLLM with Llama-3) for air-gapped military deployments.

### Category F: Technical Debt / Risks
- **Subprocess Runner on Windows:** The IDE execution daemon requires `powershell.cmd` in the workspace root to execute shell commands reliably.
- **Module Import Namespace:** Inconsistent imports (`backend.core` vs `core`) in test files cause collection errors if `PYTHONPATH` is not explicitly set to the `backend/` directory.
- **Tailwind Version Mismatch:** Coexistence of Tailwind v3 and v4 dependencies in `package.json` must be normalized.

---

## 12. Technical Risks

1. **Domain Over-Coupling Risk:** Attempting to force Aero concepts into existing manufacturing tables/enums could result in brittle abstractions. *Mitigation:* Create a dedicated, clean `aero_` domain namespace while reusing the underlying computational engines.
2. **High-Frequency Telemetry Ingestion Contention:** High-rate flight telemetry updates could cause SQLite database locks (`database is locked`). *Mitigation:* Use WAL mode (`PRAGMA journal_mode=WAL;`), in-memory queues (`asyncio.Queue`), and batched append-only writes.
3. **Heuristic vs Physics-Informed Predictive Maintenance:** Military aircraft maintenance demands defensible, auditable RUL calculations, not keyword heuristics. *Mitigation:* Implement flight hour/cycle wear formulas based on manufacturer flight envelope limits.
4. **Safety & Governance Compliance:** Aircraft weapons release and sortie scrambles require non-bypassable multi-officer governance. *Mitigation:* Leverage the existing two-person rule in the 10-gate Execution Gateway.

---

## 13. Recommended Development Sequence

To ensure high architectural integrity and systematic delivery, the Aero system should be developed in the following dependency-ordered sequence:

```
Phase 1: Foundation & Workspace Scaffolding
   │     • Clean scaffolding of Aero workspace
   │     • Resolve Windows runner execution proxy & import paths
   ▼
Phase 2: Aeronautical Domain Model & Ontology
   │     • Define Airframe, Avionics, Propulsion, Munitions, Squadron, Sortie
   │     • Aerospace ontology validation matrix (ATA/MIL-STD taxonomy)
   ▼
Phase 3: Telemetry Ingestion & Data Fabric
   │     • Flight telemetry parser (pitch/roll/yaw, G-load, EGT, Mach, fuel)
   │     • High-throughput telemetry bus & time-series storage
   ▼
Phase 4: Aircraft Digital Twin Layer
   │     • Aircraft Twin virtual state, flight hours/cycles counter, subsystem states
   │     • Bitemporal twin snapshots and scenario branching
   ▼
Phase 5: Subsystem Intelligence & Diagnostics
   │     • Multimodal Avionics & Engine Sensor Fusion
   │     • Flight Envelope Anomaly Detection
   │     • Subsystem Root Cause Analysis & Built-In Test (BIT) code isolation
   │     • Cascading Subsystem Blast Radius
   ▼
Phase 6: Prognostics & Remaining Useful Life (RUL)
   │     • Physics-informed component degradation models
   │     • Flight hours / cycles RUL estimation
   │     • Unscheduled maintenance prediction & Line Replaceable Unit (LRU) alerts
   ▼
Phase 7: Mission Manager & Air Tasking Order (ATO) Pipeline
   │     • Sortie generator & flight readiness scoring (FMC / PMC / NMC)
   │     • Mission route, weapons loadout, and fuel profile planning
   ▼
Phase 8: What-If Tactical Simulation & Fleet Optimization
   │     • Counterfactual mission simulation (weather, threat, diversion)
   │     • Fleet turnaround and maintenance schedule optimization
   ▼
Phase 9: Tactical Command Center UI (Obsidian Aero Console)
   │     • Fleet status grid, tactical theater/base map, sortie Kanban
   │     • Subsystem telemetry gauges & real-time radar/flight stream
   ▼
Phase 10: Human Governance & Mission Execution Gates
   │     • Flight Lead & Mission Commander approval workflows
   │     • Rules of Engagement (ROE) policy enforcement
   │     • 10-gate Execution Gateway integration for mission & maintenance actions
   ▼
Phase 11: Verification, Flight Debrief & Fleet Learning
         • Post-maintenance Built-In-Test-Equipment (BITE) run-up verification
         • Post-sortie debrief telemetry audit
         • Fleet health learning loop & cryptographically sealed black box audit
```

### Sequence Rationale:
- Building from **data model → telemetry → digital twin → intelligence → mission management → command center → governance** ensures that higher-level decision automation always operates on verified, typed, and deterministically grounded physical state.

---

## 14. Open Architecture Decisions

1. **ADR-AERO-001: Telemetry Streaming Standard**
   - *Option A:* WebSocket JSON stream (compatible with current UI).
   - *Option B:* Binary Protobuf / gRPC stream (higher bandwidth efficiency for 100Hz flight data).
   - *Status:* Pending user review.

2. **ADR-AERO-002: Flight Time-Series Persistence Engine**
   - *Option A:* SQLite with WAL mode and partitioned monthly files.
   - *Option B:* Embedded DuckDB / Parquet columnar storage for rapid analytical flight trajectory queries.
   - *Status:* Pending user review.

3. **ADR-AERO-003: Tactical Map Component Architecture**
   - *Option A:* ReactFlow customized node layout (consistent with current UI aesthetic).
   - *Option B:* Leaflet / OpenLayers tactical military symbology (MIL-STD-2525D) overlay.
   - *Status:* Pending user review.

4. **ADR-AERO-004: Military Clearance & Classification RBAC Model**
   - *Option A:* Role-based access control with static clearances (`Operator`, `CrewChief`, `FlightLead`, `MissionCommander`).
   - *Option B:* Multi-Level Security (MLS) / Bell-LaPadula model with compartmented security labels (`UNCLASSIFIED`, `SECRET`, `TOP SECRET`).
   - *Status:* Pending user review.

---
*End of Reconnaissance Report.*
