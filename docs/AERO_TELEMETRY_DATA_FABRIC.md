# SageCommand Air Power System — Aero
# Telemetry Data Fabric Specification (Phase 3 SIH MVP)

**Document Version:** 1.0.0  
**Phase:** Phase 3 — Telemetry Data Fabric  
**Status:** IMPLEMENTED & TESTED (100% Automated Test Coverage)  
**Date:** 2026-10-06  

---

## 1. Architectural Overview

The **Telemetry Data Fabric** provides a deterministic, modular pipeline for ingesting, normalizing, evaluating, buffering, and persisting real-time and synthetic flight telemetry within the **SageCommand Air Power System (Aero)**.

Designed specifically for the **Smart India Hackathon (SIH)** operational demonstration, the fabric establishes a decoupled, highly reliable data plane that bridges raw observation feeds with downstream analytical layers (such as Digital Twin state estimation, subsystem anomaly detection, and predictive maintenance).

```
                      [ Raw Flight Observations ]
                     (Synthetic Demo / Edge Feed)
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │   TelemetryNormalizer   │
                     │  - Unit standardisation │
                     │  - Timestamp validation │
                     │  - Identity correlation │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │    QualityEvaluator     │
                     │  - VALID / DEGRADED /   │
                     │    INVALID              │
                     │  - Physical constraints │
                     │  - Clock drift bounds   │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  FlightEnvelopeChecker  │
                     │  - WITHIN_ENVELOPE      │
                     │  - CAUTION              │
                     │  - EXCEEDED             │
                     │  - Structured violations│
                     └────────────┬────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────┐                       ┌─────────────────────────┐
│     TelemetryBuffer     │                       │   SQLite WAL Storage    │
│  - Bounded ring buffer  │                       │  - Indexed persistence  │
│  - Thread-safe deque    │                       │  - (aircraft, timestamp)│
│  - In-memory cache      │                       │  - Canonical snapshot   │
└─────────────────────────┘                       └─────────────────────────┘
         │                                                 │
         └────────────────────────┬────────────────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │    TelemetryService     │
                     │  - Orchestration façade │
                     │  - Query and extraction │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │     REST Query API      │
                     │  /telemetry             │
                     │  /telemetry/batch       │
                     │  /telemetry/recent      │
                     │  /aircraft/{id}/telemetry│
                     │  /telemetry/demo/gen    │
                     └─────────────────────────┘
```

---

## 2. Canonical Normalized Representation

All observations are mapped into a standardized `NormalizedTelemetry` schema. Regardless of the originating sensor or format, internal components consume uniform SI/metric data types:

```python
class NormalizedTelemetry(AeroBaseModel):
    aircraft_id: str                      # Aircraft UUID or identifier
    flight_id: str | None = None          # Active flight/sortie identifier
    timestamp: datetime                   # Canonical ISO-8601 UTC timestamp
    altitude_m: float                     # Altitude in meters (m)
    airspeed_mps: float                   # True airspeed in meters per second (m/s)
    mach: float                           # Mach number
    g_load: float                         # G-force factor
    engine_temp_c: float                  # Core engine temperature in Celsius (°C)
    engine_pressure_kpa: float            # Engine pressure in kilopascals (kPa)
    vibration_ips: float                  # Subsystem vibration in inches per second (ips)
    fuel_flow_kg_h: float | None = None   # Fuel burn rate in kg/h
    heading_deg: float | None = None      # Compass heading (0-360°)
    pitch_deg: float | None = None        # Pitch attitude (-90° to +90°)
    roll_deg: float | None = None         # Roll angle (-180° to +180°)
    source: str = "telemetry_input"       # Observation origin/tag
    source_metadata: dict[str, Any]       # Raw units, sensor IDs, packet markers
```

---

## 3. Supported Units and Deterministic Conversion

To ensure strict deterministic behavior without relying on large external unit libraries, the `TelemetryNormalizer` enforces mathematically exact conversion tables:

| Measurement | Input Units Supported | Target Normalized Unit | Conversion Formula |
| :--- | :--- | :--- | :--- |
| **Altitude** | `feet` / `ft` | `meters` (`m`) | $m = \text{feet} \times 0.3048$ |
| | `m` / `meters` | `meters` (`m`) | $m = m \times 1.0$ |
| | `km` / `kilometers` | `meters` (`m`) | $m = km \times 1000.0$ |
| **Airspeed** | `knots` / `kts` | `meters/second` (`m/s`) | $v = \text{knots} \times 0.514444$ |
| | `km/h` / `kmh` | `meters/second` (`m/s`) | $v = \text{km/h} / 3.6$ |
| | `mph` | `meters/second` (`m/s`) | $v = \text{mph} \times 0.44704$ |
| | `m/s` / `mps` | `meters/second` (`m/s`) | $v = v \times 1.0$ |
| **Temperature** | `Celsius` / `C` | `Celsius` (`°C`) | $T = T$ |
| | `Fahrenheit` / `F` | `Celsius` (`°C`) | $T = (F - 32.0) \times \frac{5}{9}$ |
| | `Kelvin` / `K` | `Celsius` (`°C`) | $T = K - 273.15$ |
| **Pressure** | `kPa` | `kilopascals` (`kPa`) | $P = P$ |
| | `Pa` | `kilopascals` (`kPa`) | $P = \text{Pa} / 1000.0$ |
| | `bar` | `kilopascals` (`kPa`) | $P = \text{bar} \times 100.0$ |
| | `psi` | `kilopascals` (`kPa`) | $P = \text{psi} \times 6.894757$ |
| | `atm` | `kilopascals` (`kPa`) | $P = \text{atm} \times 101.325$ |
| **Vibration** | `ips` / `in/s` | `inches/second` (`ips`) | $V = V$ |
| | `mm/s` | `inches/second` (`ips`) | $V = \text{mm/s} / 25.4$ |
| **Fuel Flow** | `kg/h` / `kg_h` | `kg/h` | $F = F$ |
| | `lbs/h` / `pph` | `kg/h` | $F = \text{lbs/h} \times 0.45359237$ |

*Rules:*
- If an unsupported unit is supplied, `TelemetryNormalizer` raises a deterministic validation error.
- Silent unit guessing is strictly forbidden.

---

## 4. Telemetry Quality Assessment

The `QualityEvaluator` deterministically inspects each observation and returns a structured `QualityAssessmentResult` categorizing it into:

* `VALID`: All channels conform to physical ranges, valid timestamps, valid identities, and required parameters. Usable for high-fidelity state estimation.
* `DEGRADED`: The core state is physically intact, but optional secondary telemetry channels (e.g., fuel flow, attitude angles) are missing or secondary quality thresholds were flagged. Usable for basic flight tracking.
* `INVALID`: Corrupted data. Observations fail physical boundaries (negative absolute pressure, negative Kelvin equivalent), contain `NaN`/`Infinity`, suffer severe clock drift (> 1 hour skew), or lack required identification. Rejected from database persistence.

### Diagnostic Reason Codes
- `ERR_NAN_INF_VALUE`: Field contains NaN or infinite values.
- `ERR_INVALID_ALTITUDE`: Altitude falls outside physical bounds (-500m to 35,000m).
- `ERR_NEGATIVE_AIRSPEED`: Airspeed is negative (< 0 m/s).
- `ERR_NEGATIVE_MACH`: Mach is negative (< 0.0).
- `ERR_PRESSURE_NON_POSITIVE`: Engine pressure is non-positive (≤ 0 kPa).
- `ERR_TEMP_BELOW_ABSOLUTE_ZERO`: Engine temperature is below absolute zero (< -273.15°C).
- `ERR_NEGATIVE_VIBRATION`: Vibration amplitude is negative (< 0 ips).
- `ERR_NEGATIVE_FUEL_FLOW`: Fuel burn rate is negative (< 0 kg/h).
- `ERR_INVALID_HEADING`: Compass heading outside 0° - 360°.
- `ERR_INVALID_PITCH`: Pitch angle outside -90° to +90°.
- `ERR_INVALID_ROLL`: Roll angle outside -180° to +180°.
- `ERR_CLOCK_DRIFT_EXCESSIVE`: Packet timestamp skews > 1 hour from current UTC time.
- `WARN_OPTIONAL_CHANNEL_MISSING`: Non-critical telemetry channels omitted.

---

## 5. Demonstration Flight Envelope Evaluation

The `FlightEnvelopeChecker` evaluates flight dynamics against configurable flight boundaries. Envelope configurations are injected dynamically and are fully decoupled from core algorithms.

### Demonstration Limits (Generic Baseline)

> [!IMPORTANT]
> **Explicit Boundary Notice:** Limits documented here represent **generic educational/demonstration thresholds** tailored for SIH prototype evaluation. They **DO NOT** represent real-world military specifications, NATO STANAG certifications, or OEM manufacturer flight envelopes (e.g., Sukhoi Su-30MKI, Dassault Rafale, LCA Tejas).

| Parameter | Caution Min | Caution Max | Exceeded Min | Exceeded Max |
| :--- | :--- | :--- | :--- | :--- |
| **Altitude** | 0 m | 18,000 m | -200 m | 22,000 m |
| **Airspeed** | 60 m/s | 650 m/s | 40 m/s | 750 m/s |
| **Mach** | 0.0 | 2.0 | 0.0 | 2.35 |
| **G-Load** | -2.0 G | +7.5 G | -3.0 G | +9.0 G |
| **Engine Temp** | 300 °C | 950 °C | 200 °C | 1,050 °C |
| **Engine Pressure** | 200 kPa | 1,800 kPa | 150 kPa | 2,100 kPa |
| **Vibration** | 0.0 ips | 0.85 ips | 0.0 ips | 1.25 ips |

### Envelope Status Classification
* `WITHIN_ENVELOPE`: All parameters reside strictly within standard operational caution boundaries.
* `CAUTION`: One or more parameters exceed caution limits, signaling near-envelope operation (e.g., G-load 7.8G, engine temp 980°C).
* `EXCEEDED`: One or more parameters cross hard physical limits (e.g., G-load 9.2G, vibration 1.4 ips), generating critical alerts with severity levels `HIGH` or `CRITICAL`.

---

## 6. Synthetic Flight Profile Generator

To support reproducible SIH evaluations without hardware-in-the-loop dependencies, `SyntheticFlightGenerator` produces deterministic flight sequences parameterized by random seeds.

### Supported Demonstration Profiles
1. `NORMAL_CRUISE`: Stable high-altitude cruise (Mach 0.82, 10,500m, 1.0G, benign thermal/vibration footprint).
2. `TAKEOFF_CLIMB`: High-power ascent from sea level (0 to 6,000m, high fuel burn, moderate 1.3G load).
3. `HIGH_G_TURN`: High-energy defensive/offensive maneuvering (Mach 0.95, 6.0G to 8.2G loading, transient vibration increase).
4. `SUPERSONIC_CRUISE`: High-altitude supersonic dash (Mach 1.45 to 1.75, 14,000m, elevated turbine temps).
5. `THERMAL_SPIKE`: In-flight thermal anomaly simulation (combustor temperatures rising from 800°C to 1,020°C).
6. `VIBRATION_SPIKE`: Bearing or turbine blade imbalance anomaly simulation (vibration escalating from 0.4 ips to 1.35 ips).

All generated records are tagged with:
```json
{
  "source": "synthetic_demo"
}
```
Synthetic generation is strictly on-demand via test fixtures or `POST /api/v1/telemetry/demo/generate`. No synthetic data is inserted during system startup.

---

## 7. In-Memory Telemetry Buffer

The `TelemetryBuffer` provides a thread-safe, bounded in-memory ring buffer implemented using `collections.deque` and `threading.Lock`:

- **Capacity Management:** Configured via `AERO_TELEMETRY_BUFFER_SIZE` (default: 5,000 records). When full, the oldest records are safely evicted without blocking ingest.
- **Thread Safety:** All append, retrieve, and flush operations synchronize under a mutual exclusion lock.
- **Chronological Sorting:** Extracted records are returned strictly in timestamp order.
- **Batch Extraction & Flushing:** Supports transactional queue draining for streaming bridges.

---

## 8. Persistence Strategy

Telemetry records are committed to the existing SQLite Write-Ahead Logging (WAL) database:

- **Target Table:** `telemetry_records`
- **Primary Key:** UUID `id`
- **Foreign Key:** `aircraft_id` references `aircraft.id`
- **Performance Indexes:**
  - `ix_telemetry_records_aircraft_id`
  - `ix_telemetry_records_timestamp`
  - Composite Index: `ix_telemetry_aircraft_timestamp` on `(aircraft_id, timestamp)`
- **Safety Policy:** Telemetry categorized as `INVALID` by the `QualityEvaluator` is **never committed** to the persistence layer, safeguarding database integrity.

---

## 9. REST API Endpoints

All endpoints conform to the standard `ApiResponse[T]` envelope and provide full correlation tracking:

| Method | Endpoint | Description | Request Payload | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/telemetry` | Ingest single flight observation | `TelemetryInput` | `ApiResponse[TelemetryIngestResult]` |
| `POST` | `/api/v1/telemetry/batch` | Ingest multiple flight frames | `BatchIngestRequest` | `ApiResponse[BatchIngestResult]` |
| `GET` | `/api/v1/telemetry/recent` | Retrieve latest buffered telemetry | Query params: `limit`, `aircraft_id` | `ApiResponse[list[NormalizedTelemetry]]` |
| `POST` | `/api/v1/telemetry/demo/generate` | Generate synthetic flight sequence | `DemoGenerateRequest` | `ApiResponse[BatchIngestResult]` |
| `GET` | `/api/v1/aircraft/{id}/telemetry` | Query persisted telemetry history | Query params: `limit`, `offset` | `ApiResponse[list[NormalizedTelemetry]]` |

---

## 10. Future Migration to Distributed Streaming

The Phase 3 Telemetry Data Fabric is deliberately designed with clean dependency boundaries:

```
[ Edge Aircraft / Kafka Topic ] ──▶ [ TelemetryNormalizer ] ──▶ [ QualityEvaluator ]
                                                                       │
                                                                       ▼
                                                          [ FlightEnvelopeChecker ]
                                                                       │
                                                                       ▼
                                                     ┌─────────────────────────────────┐
                                                     │ Streaming Sink Abstract Adapter │
                                                     ├────────────────┬────────────────┤
                                                     │ Current (SIH)  │ Future Prod    │
                                                     │ TelemetryBuffer│ Kafka / Pulsar │
                                                     │ SQLite WAL     │ TimescaleDB    │
                                                     └────────────────┴────────────────┘
```

When upgrading to high-throughput production infrastructure:
1. Replace `TelemetryBuffer` with an external distributed message bus producer (e.g., Apache Kafka, Redpanda, or NATS JetStream).
2. Replace SQLite WAL persistence with a partitioned time-series engine (e.g., TimescaleDB, ClickHouse, or Apache IoTDB).
3. The `TelemetryNormalizer`, `QualityEvaluator`, and `FlightEnvelopeChecker` classes remain 100% reusable and framework-agnostic.

---

## 11. Security and Operational Governance

This telemetry fabric is strictly an **observational, analytical, and diagnostic intelligence pipeline**. It does not perform autonomous flight control, flight surface actuation, weapon arming, or fire-control interlocks. All data handling adheres to fail-safe, read-only operational boundaries.
