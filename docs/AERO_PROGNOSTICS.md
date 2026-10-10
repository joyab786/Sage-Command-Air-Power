# SageCommand Air Power System (Aero) — Predictive Maintenance & RUL Prognostics

**Phase 6 Specification — Explainable Prognostics & Remaining Useful Life (SIH MVP)**  
*Document Version:* 1.0.0  
*Date:* 2026-10-07  
*Status:* IMPLEMENTED BASELINE (48 Phase 6 Tests / 214 Total Automated Tests Passing)

---

## 1. Purpose

The **SageCommand Air Power System (Aero) Prognostics Engine** provides a defensible, explainable, and deterministic foundation for predictive maintenance and Remaining Useful Life (RUL) forecasting.

> [!IMPORTANT]
> **Prototyping & SIH Demonstration Boundary:**  
> The SIH MVP prognostics layer is intentionally designed with deterministic, statistical, and trend-based methods rather than opaque deep-learning models. It does NOT fabricate real-world military aircraft failure data or claim airworthiness certification. All thresholds represent explicit demonstration and prototype baselines that provide end-to-end explainability and decision support.

The prognostics pipeline extends the Aero intelligence fabric:
```text
Normalized Telemetry
        ↓
Digital Twin State & History
        ↓
Subsystem Health & Wear Tracking
        ↓
Subsystem Anomaly Detection & Diagnosis
        ↓
Health Trend Estimation (OLS Regression)
        ↓
Remaining Useful Life (RUL) Prediction & Bounding
        ↓
Maintenance Forecasting & Urgency Window
        ↓
Readiness Impact Decision Support (FMC / PMC / NMC)
```

---

## 2. Prognostics Architecture

The prognostics system is housed in a dedicated, isolated package:
`backend/app/prognostics/`

```
backend/app/prognostics/
├── __init__.py           # Package exports and interface exposure
├── models.py             # Strongly typed Pydantic v2 schemas and enums
├── health_history.py     # Aggregator querying digital twin snapshots without raw telemetry duplication
├── trend.py              # DegradationTrendEstimator (OLS regression, slope, R², direction)
├── rul.py                # BaseRULPredictor protocol & DeterministicRULPredictor implementation
├── forecast.py           # MaintenanceForecaster (5 priority tiers, actions, operational windows)
└── service.py            # PrognosticsService orchestration, SQLite WAL persistence, readiness bridge
```

### Component Decoupling
- **Isolation from Raw Telemetry:** The prognostics layer does not duplicate high-rate raw sensor streams; it consumes aggregated digital-twin state snapshots (`AircraftTwinStateModel`).
- **Isolation from Anomaly Detection:** Anomaly detection remains isolated in `app/intelligence/`. Prognostics consumes anomaly outputs strictly as risk and horizon modifiers.
- **Decision Support Boundary:** Prognostics is strictly an advisory, read-mostly decision-support layer. It has zero authority to issue autonomous flight control, actuator commands, or weapons actions.

---

## 3. Health History Source

Historical observations are aggregated by `HealthHistoryAggregator` in `app/prognostics/health_history.py`:
- **Source Table:** Queries `AircraftTwinStateModel` (`aircraft_twin_states`) chronologically.
- **Subsystem State Extraction:** Parses subsystem-level health scores and wear indices from `subsystem_states` JSON structures.
- **Data Quality Tagging:** Propagates `VALID` or `DEGRADED` telemetry flags from twin history.
- **Anomaly Correlation:** Correlates active and acknowledged anomalies detected during the observation period.

---

## 4. Degradation Model (Ordinary Least Squares Regression)

The `DegradationTrendEstimator` in `app/prognostics/trend.py` implements a transparent mathematical model:

### Minimum Data Requirements
- If sample count $N < 3$: returns `TrendDirection.INSUFFICIENT_DATA`, confidence $\le 0.25$, and explanation stating that at least 3 chronological samples are required. False prognostics are strictly blocked.

### Time Coordinates
- Coordinates $t_i$ are computed in elapsed flight hours: $t_i = (T_i - T_0) / 3600.0$.
- In synthetic test scenarios where samples are generated milliseconds apart ($\Delta t < 0.01$ hrs), the estimator automatically switches to discrete demonstration step hours ($t_i = float(i)$) to preserve numerical stability.

### Regression Equations
For observations $(t_i, y_i)$ where $y_i$ is the health score:
$$\bar{t} = \frac{1}{N} \sum_{i=1}^N t_i, \quad \bar{y} = \frac{1}{N} \sum_{i=1}^N y_i$$
$$SS_{tt} = \sum_{i=1}^N (t_i - \bar{t})^2, \quad SS_{ty} = \sum_{i=1}^N (t_i - \bar{t})(y_i - \bar{y}), \quad SS_{yy} = \sum_{i=1}^N (y_i - \bar{y})^2$$
$$\text{slope} = \frac{SS_{ty}}{SS_{tt}}, \quad \text{intercept} = \bar{y} - \text{slope} \cdot \bar{t}$$
$$SS_{\text{res}} = \sum_{i=1}^N \left(y_i - (\text{slope} \cdot t_i + \text{intercept})\right)^2$$

### Trend Classification
Using a stability threshold ($\delta = 0.10$ health points/hour):
- **DEGRADING:** $\text{slope} < -\delta$. Degradation rate is $|\text{slope}|$. Fit quality $R^2 = 1.0 - (SS_{\text{res}} / SS_{yy})$.
- **IMPROVING:** $\text{slope} > +\delta$. Degradation rate is $0.0$. Subsystem health is recovering.
- **STABLE:** $|\text{slope}| \le \delta$. Degradation rate is $0.0$. Fit quality is evaluated based on variance around nominal: $R^2 = 1.0 - (\sigma_y / 5.0)$.

---

## 5. Remaining Useful Life (RUL) Formula

The deterministic RUL predictor (`DeterministicRULPredictor` in `app/prognostics/rul.py`) combines linear health extrapolation, wear bounding, and anomaly truncation.

### Configurable Demonstration Constants
- Demonstration Health Caution Threshold: $H_{\text{threshold}} = 25.0$ health points.
- Normalized Wear Limit: $W_{\text{threshold}} = 1.0$.
- Nominal Demonstration Horizon Ceiling: $RUL_{\text{nominal}} = 1000.0$ flight hours.

### Trend-Based Extrapolation
When degradation rate $r > 0$:
$$RUL_{\text{trend}} = \frac{\max(0.0, H_{\text{current}} - H_{\text{threshold}})}{r}$$

### Wear-Based Bounding
When cumulative structural wear index $w$ is present:
$$RUL_{\text{wear}} = \max(0.0, W_{\text{threshold}} - w) \times RUL_{\text{nominal}}$$

### Conservative Composite Selection
When both health degradation and physical wear limits exist:
$$RUL_{\text{base}} = \min(RUL_{\text{trend}}, RUL_{\text{wear}})$$

---

## 6. Uncertainty Model & Bounding

RUL predictions must never be presented as absolute scalar truth. The system computes explicit upper and lower uncertainty intervals:

### Mathematical Bounds
$$0.0 \le \text{lower\_bound\_hours} \le \text{estimated\_rul\_hours} \le \text{upper\_bound\_hours}$$

### Uncertainty Expansion Factors
$$\text{uncertainty\_fraction} = 0.10 + (1.0 - \text{confidence}) \times 0.40$$
- If data quality is `DEGRADED`: adds $+0.15$ to uncertainty fraction.
- If sample count $N < 5$: adds $+0.10$ to uncertainty fraction.
$$\text{margin} = RUL_{\text{estimate}} \times \text{uncertainty\_fraction}$$
$$\text{lower\_bound} = \max(0.0, RUL_{\text{estimate}} - \text{margin})$$
$$\text{upper\_bound} = RUL_{\text{estimate}} + \text{margin}$$

---

## 7. Confidence Model

Prognostic confidence $C \in [0.10, 1.00]$ is computed deterministically:
$$C_{\text{sample}} = \min(1.0, 0.40 + 0.10 \times \min(N, 6))$$
$$C_{\text{fit}} = \begin{cases} 0.50 + 0.50 \times R^2 & \text{if DEGRADING or IMPROVING} \\ 0.85 + 0.15 \times R^2 & \text{if STABLE} \end{cases}$$
$$C_{\text{raw}} = C_{\text{sample}} \times C_{\text{fit}}$$
- Degraded telemetry penalty: $C_{\text{raw}} \leftarrow C_{\text{raw}} - 0.20$.
- Bounded: $C = \text{round}(\max(0.10, \min(1.00, C_{\text{raw}})), 4)$.

---

## 8. Phase 5 Anomaly Integration

Active anomalies modify the prognostic horizon and confidence:
- **CRITICAL Anomaly:**
  - Truncates operational horizon: $RUL \leftarrow \min(RUL \times 0.50, 15.0\text{ hrs})$.
  - Decreases confidence by $-0.10$.
  - Appends limiting factor: *"Active CRITICAL anomaly drastically accelerates degradation risk"*.
  - Escalates action to immediate grounding for review.
- **HIGH Anomaly:**
  - Truncates operational horizon: $RUL \leftarrow \min(RUL \times 0.75, 80.0\text{ hrs})$.
  - Decreases confidence by $-0.05$.
  - Appends limiting factor: *"Active HIGH anomaly detected on subsystem"*.
- **MULTI_SIGNAL Correlation:**
  - Appends limiting factor confirming compounded physical stress across correlated sensors.

---

## 9. Maintenance Forecast

`MaintenanceForecaster` in `app/prognostics/forecast.py` derives consolidated advisory recommendations across 5 operational tiers:

| Forecast Priority | Trigger Condition | Recommended Operational Window | Prescribed Action |
| :--- | :--- | :--- | :--- |
| **GROUND_FOR_REVIEW** | CRITICAL anomaly OR Phase 5 ground rec OR $RUL < 15.0$ hrs | Immediate prior to next flight | Ground airframe for engineering diagnostic review |
| **PRIORITY_INSPECTION** | HIGH anomaly OR $RUL < 60.0$ hrs OR rate $> 2.0$ pts/hr | Within next 10 flight hours / turnaround | High-priority turnaround inspection & sensor verification |
| **INSPECT_SOON** | $RUL < 150.0$ hrs OR MEDIUM anomaly | Within next 50 flight hours | BITE test and visual diagnostic turnaround inspection |
| **PLAN_MAINTENANCE** | $RUL < 300.0$ hrs OR rate $> 0.2$ pts/hr | Within next 150 flight hours | Preventative servicing in upcoming squadron maintenance window |
| **MONITOR** | Nominal health ($RUL \ge 300.0$ hrs, stable) | Standard periodic depot inspection | Continue routine telemetry monitoring |

---

## 10. Readiness Integration

Prognostics integrates cleanly with the aerospace readiness model (`readiness_impact`):
- `FMC_SUPPORTED`: Fully Mission Capable. Subsystem is nominal or stable.
- `PMC_RESTRICTED`: Partially Mission Capable. Subsystem requires prioritized inspection within 10–50 hours.
- `NMC_GROUNDED`: Non-Mission Capable (Ground for Review). Critical anomaly or imminent failure horizon.

> [!NOTE]
> **Advisory Nature:** Prognostics outputs provide decision-support recommendations. They do not automatically bypass human-in-the-loop governance or overwrite operational readiness statuses without commander authorization.

---

## 11. Relational Persistence (SQLite WAL)

Prognostic assessments are persisted in `prognostic_records` (`PrognosticRecordModel`):
- Composite Indexes:
  - `(aircraft_id, timestamp)`
  - `(aircraft_id, forecast_priority)`
  - `(aircraft_id, subsystem)`
- Stores: `record_id`, `aircraft_id`, `timestamp`, `subsystem`, `health_score`, `wear_index`, `trend_direction`, `degradation_rate`, `slope`, `estimated_rul_hours`, `estimated_rul_cycles`, `lower_bound_hours`, `upper_bound_hours`, `confidence`, `forecast_priority`, `prediction_method`, `limiting_factors`, `explanation`, `recommended_action`.

---

## 12. REST API Endpoints

| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/aircraft/{aircraft_id}/prognostics` | Get Aircraft Prognostic Assessment | Computes current assessment, trend, RUL, forecast, and persists record |
| `GET` | `/api/v1/aircraft/{aircraft_id}/prognostics/history` | Get Historical Prognostic Records | Retrieves paginated historical assessments |
| `GET` | `/api/v1/aircraft/{aircraft_id}/health-trend` | Get Aircraft Health Degradation Trend | Computes OLS linear regression slope, R², and direction |
| `GET` | `/api/v1/aircraft/{aircraft_id}/maintenance-forecast` | Get Prioritized Maintenance Forecast | Returns prioritized advisory maintenance forecast |

---

## 13. Demonstration Scenarios

Verified via automated end-to-end tests in `backend/tests/integration/test_prognostics_e2e.py`:
1. **Scenario A — Healthy Aircraft:** Constant healthy observations $\to$ `STABLE`, rate 0.0, $RUL = 1000$ hrs, `MONITOR`, `FMC_SUPPORTED`.
2. **Scenario B — Gradual Degradation:** Steady linear decline $\to$ `DEGRADING`, negative slope, finite RUL, `PLAN_MAINTENANCE` / `INSPECT_SOON`.
3. **Scenario C — Rapid Degradation:** Precipitous health drop $\to$ steep slope, $RUL < 15$ hrs, `GROUND_FOR_REVIEW`, `NMC_GROUNDED`.
4. **Scenario D — Repeated Anomaly + Degradation:** Phase 5 anomalies + declining trend $\to$ anomaly-aware RUL truncation, `GROUND_FOR_REVIEW`.
5. **Scenario E — Insufficient History:** $N < 3$ observations $\to$ `INSUFFICIENT_DATA`, fallback ceiling, low confidence, no false prediction.
6. **Scenario F — Poor Data Quality:** Degraded telemetry flags $\to$ reduced confidence, expanded uncertainty intervals.

---

## 14. Extensible Protocol & Future ML Upgrade Path

The architecture defines a clean protocol interface (`BaseRULPredictor` in `app/prognostics/rul.py`):
```python
@runtime_checkable
class BaseRULPredictor(Protocol):
    def predict(
        self,
        trend: DegradationTrend,
        current_state: Optional[AircraftTwinState] = None,
        active_anomalies: Optional[List[Anomaly]] = None,
    ) -> RULPrediction:
        ...
```

Future capabilities can implement `BaseRULPredictor` without altering external API contracts or database schemas:
- **Survival Analysis & Weibull Models:** Fleet-level hazard rate estimation.
- **Kalman & State-Space Filtering:** Dynamic parameter tracking under noisy flight conditions.
- **Sequence Transformers:** Temporal deep learning trained on empirical operational flight data.
- **Fleet-Level Transfer Learning:** Cross-airframe degradation sharing.
