"""
End-to-End Synthetic Demonstration Scenarios for Phase 6 Predictive Maintenance & RUL Prognostics (SIH MVP).
Implements the six required demonstration scenarios:
1. Scenario A — Healthy Aircraft: Stable health, high confidence, long RUL, MONITOR.
2. Scenario B — Gradual Degradation: Health declines gradually, measurable negative slope, finite RUL, PLAN_MAINTENANCE/INSPECT_SOON.
3. Scenario C — Rapid Degradation: Health drops fast, steep slope, short RUL, PRIORITY_INSPECTION/GROUND_FOR_REVIEW.
4. Scenario D — Repeated Anomaly + Degradation: Declining trend + Phase 5 anomalies, truncated RUL, elevated urgency.
5. Scenario E — Insufficient History: Only 1-2 observations, INSUFFICIENT_DATA, low confidence, explicit explanation.
6. Scenario F — Poor Data Quality: Degraded telemetry history, penalized confidence, expanded uncertainty intervals.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    AnomalyModel,
)


def _seed_aircraft(db_session: Session, aircraft_id: str, tail: str) -> str:
    """Helper to create and commit an aircraft."""
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number=tail,
        aircraft_type="HAL Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="Flying Daggers",
        status="ACTIVE",
        total_flight_hours=150.0,
        total_flight_cycles=75,
    )
    db_session.add(ac)
    db_session.commit()
    return aircraft_id


def _seed_twin_states(
    db_session: Session,
    aircraft_id: str,
    health_sequence: list[float],
    wear_sequence: list[float] | None = None,
    dq: str = "VALID",
    subsystem: str = "PROPULSION",
) -> None:
    """Seeds historical twin states chronologically."""
    t0 = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    for i, h in enumerate(health_sequence):
        w = wear_sequence[i] if wear_sequence else 0.05
        state = AircraftTwinStateModel(
            state_id=f"state-{aircraft_id}-{i}",
            aircraft_id=aircraft_id,
            timestamp=t0 + timedelta(hours=i),
            operational_status="ACTIVE",
            health_score=h,
            wear_index=w,
            flight_hours=150.0 + i,
            flight_cycles=75 + i,
            subsystem_states={
                subsystem: {"health": h, "wear": w},
            },
            data_quality=dq,
        )
        db_session.add(state)
    db_session.commit()


# -----------------------------------------------------------------------------
# Scenario A — Healthy Aircraft
# -----------------------------------------------------------------------------

def test_scenario_a_healthy_aircraft(test_client: TestClient, db_session: Session):
    """
    Scenario A: Healthy Aircraft
    Stable health profile across multiple observations.
    Expected: STABLE, high confidence, long/healthy RUL horizon, MONITOR forecast.
    """
    aid = _seed_aircraft(db_session, "SCENARIO-A", "TA-01")
    _seed_twin_states(db_session, aid, [98.5, 98.4, 98.5, 98.5, 98.5])

    resp = test_client.get(f"/api/v1/aircraft/{aid}/prognostics")
    assert resp.status_code == 200
    body = resp.json()["data"]

    # Trend verification
    assert body["trend"]["trend_direction"] == "STABLE"
    assert body["trend"]["degradation_rate"] == 0.0

    # RUL verification
    assert body["rul"]["estimated_rul_hours"] == 1000.0
    assert body["rul"]["confidence"] >= 0.80

    # Forecast & Readiness
    assert body["forecast"]["priority"] == "MONITOR"
    assert body["readiness_impact"] == "FMC_SUPPORTED"
    assert "operating nominally" in body["forecast"]["action"]


# -----------------------------------------------------------------------------
# Scenario B — Gradual Degradation
# -----------------------------------------------------------------------------

def test_scenario_b_gradual_degradation(test_client: TestClient, db_session: Session):
    """
    Scenario B: Gradual Degradation
    Health declines steadily over multiple observations.
    Expected: DEGRADING, measurable negative slope, finite RUL estimate, PLAN_MAINTENANCE / INSPECT_SOON.
    """
    aid = _seed_aircraft(db_session, "SCENARIO-B", "TB-01")
    # Declines ~2.5 points per hour: 95, 92.5, 90, 87.5, 85
    _seed_twin_states(db_session, aid, [95.0, 92.5, 90.0, 87.5, 85.0])

    resp = test_client.get(f"/api/v1/aircraft/{aid}/prognostics")
    assert resp.status_code == 200
    body = resp.json()["data"]

    # Trend verification
    assert body["trend"]["trend_direction"] == "DEGRADING"
    assert body["trend"]["slope"] < -1.0
    assert body["trend"]["degradation_rate"] > 0.0

    # RUL calculation: (85 - 25) / 2.5 = 24 hours (or in range 20-30 hours)
    rul_hrs = body["rul"]["estimated_rul_hours"]
    assert 0.0 < rul_hrs < 100.0
    assert body["rul"]["lower_bound_hours"] <= rul_hrs <= body["rul"]["upper_bound_hours"]

    # Forecast verification: either PRIORITY_INSPECTION or INSPECT_SOON or PLAN_MAINTENANCE based on 24h
    assert body["forecast"]["priority"] in ["PRIORITY_INSPECTION", "INSPECT_SOON", "PLAN_MAINTENANCE"]
    assert len(body["rul"]["limiting_factors"]) > 0


# -----------------------------------------------------------------------------
# Scenario C — Rapid Degradation
# -----------------------------------------------------------------------------

def test_scenario_c_rapid_degradation(test_client: TestClient, db_session: Session):
    """
    Scenario C: Rapid Degradation
    Health declines precipitously over observations.
    Expected: strong degradation trend, short RUL, PRIORITY_INSPECTION or GROUND_FOR_REVIEW.
    """
    aid = _seed_aircraft(db_session, "SCENARIO-C", "TC-01")
    # Drops 18 points per hour: 95, 77, 59, 41
    _seed_twin_states(db_session, aid, [95.0, 77.0, 59.0, 41.0])

    resp = test_client.get(f"/api/v1/aircraft/{aid}/prognostics")
    assert resp.status_code == 200
    body = resp.json()["data"]

    # Trend verification
    assert body["trend"]["trend_direction"] == "DEGRADING"
    assert body["trend"]["degradation_rate"] >= 15.0

    # RUL verification: (41 - 25) / 18 = ~0.88 hours
    rul_hrs = body["rul"]["estimated_rul_hours"]
    assert rul_hrs < 15.0

    # Forecast & Readiness
    assert body["forecast"]["priority"] == "GROUND_FOR_REVIEW"
    assert body["readiness_impact"] == "NMC_GROUNDED"
    assert "Ground airframe" in body["forecast"]["action"]


# -----------------------------------------------------------------------------
# Scenario D — Repeated Anomaly + Degradation
# -----------------------------------------------------------------------------

def test_scenario_d_repeated_anomaly_and_degradation(test_client: TestClient, db_session: Session):
    """
    Scenario D: Repeated Anomaly + Degradation
    Combines Phase 5 active anomalies with a declining health trend.
    Expected: anomaly-aware prognostics, truncated RUL, elevated maintenance priority, explainable evidence.
    """
    aid = _seed_aircraft(db_session, "SCENARIO-D", "TD-01")
    # Declines moderately: 92, 90, 88, 86
    _seed_twin_states(db_session, aid, [92.0, 90.0, 88.0, 86.0])

    # Insert an active CRITICAL anomaly in intelligence records
    anom = AnomalyModel(
        anomaly_id="ANOM-SCEN-D-01",
        aircraft_id=aid,
        timestamp=datetime.now(timezone.utc),
        subsystem="PROPULSION",
        anomaly_type="VIBRATION_ANOMALY",
        severity="CRITICAL",
        status="NEW",
        confidence=0.92,
        detector="THRESHOLD_RULE_DETECTOR",
        signal="vibration_ips",
        observed_value=3.1,
        expected_range="[0.0, 0.8]",
        deviation=2.3,
        description="Turbine rotor imbalance causing critical vibration spike",
        evidence=["vibration_amplitude: 3.1 ips"],
        occurrence_count=3,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(anom)
    db_session.commit()

    resp = test_client.get(f"/api/v1/aircraft/{aid}/prognostics")
    assert resp.status_code == 200
    body = resp.json()["data"]

    # RUL must be truncated by critical anomaly modifier (<= 15 hrs)
    assert body["rul"]["estimated_rul_hours"] <= 15.0
    assert any("CRITICAL" in factor for factor in body["rul"]["limiting_factors"])
    assert "CRITICAL" in body["rul"]["explanation"]

    # Forecast priority must reflect urgent review
    assert body["forecast"]["priority"] == "GROUND_FOR_REVIEW"
    assert "ANOM-SCEN-D-01" in body["forecast"]["related_anomalies"]
    assert body["readiness_impact"] == "NMC_GROUNDED"


# -----------------------------------------------------------------------------
# Scenario E — Insufficient History
# -----------------------------------------------------------------------------

def test_scenario_e_insufficient_history(test_client: TestClient, db_session: Session):
    """
    Scenario E: Insufficient History
    Only 1 or 2 historical snapshots.
    Expected: INSUFFICIENT_DATA, low confidence, nominal fallback ceiling, no fabricated RUL.
    """
    aid = _seed_aircraft(db_session, "SCENARIO-E", "TE-01")
    # Only 2 observations
    _seed_twin_states(db_session, aid, [94.0, 93.0])

    resp = test_client.get(f"/api/v1/aircraft/{aid}/prognostics")
    assert resp.status_code == 200
    body = resp.json()["data"]

    # Trend verification
    assert body["trend"]["trend_direction"] == "INSUFFICIENT_DATA"
    assert body["trend"]["sample_count"] == 2
    assert body["trend"]["fit_quality"] is None
    assert "At least 3" in body["trend"]["explanation"]

    # RUL fallback
    assert body["rul"]["prediction_method"] == "INSUFFICIENT_HISTORY_FALLBACK"
    assert body["rul"]["confidence"] <= 0.25
    assert any("Insufficient" in f for f in body["rul"]["limiting_factors"])


# -----------------------------------------------------------------------------
# Scenario F — Poor Data Quality
# -----------------------------------------------------------------------------

def test_scenario_f_poor_data_quality(test_client: TestClient, db_session: Session):
    """
    Scenario F: Poor Data Quality
    Telemetry history marked with DEGRADED data quality.
    Expected: lower confidence, wider uncertainty intervals, explicit data-quality limitation.
    """
    aid_good = _seed_aircraft(db_session, "SCENARIO-F-GOOD", "TF-01")
    aid_bad = _seed_aircraft(db_session, "SCENARIO-F-BAD", "TF-02")

    # Identical health slope: 95, 93, 91, 89, 87
    health_seq = [95.0, 93.0, 91.0, 89.0, 87.0]
    _seed_twin_states(db_session, aid_good, health_seq, dq="VALID")
    _seed_twin_states(db_session, aid_bad, health_seq, dq="DEGRADED")

    resp_good = test_client.get(f"/api/v1/aircraft/{aid_good}/prognostics")
    resp_bad = test_client.get(f"/api/v1/aircraft/{aid_bad}/prognostics")

    assert resp_good.status_code == 200
    assert resp_bad.status_code == 200

    data_good = resp_good.json()["data"]
    data_bad = resp_bad.json()["data"]

    # Data quality verification
    assert data_bad["trend"]["data_quality"] == "DEGRADED"

    # Confidence must be lower for degraded data
    assert data_bad["confidence"] < data_good["confidence"]

    # Uncertainty interval must be wider for degraded data
    interval_good = data_good["rul"]["upper_bound_hours"] - data_good["rul"]["lower_bound_hours"]
    interval_bad = data_bad["rul"]["upper_bound_hours"] - data_bad["rul"]["lower_bound_hours"]
    assert interval_bad > interval_good

    # Limiting factor explanation present
    assert any("Degraded telemetry quality" in f for f in data_bad["rul"]["limiting_factors"])
