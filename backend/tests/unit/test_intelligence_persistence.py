"""
Unit tests for Intelligence Persistence, Correlation/Deduplication,
and Anomaly Lifecycle State Transitions.
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models import AircraftModel, AnomalyModel
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus
from app.intelligence.models import (
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
)
from app.intelligence.service import IntelligenceService


def _create_aircraft(db: Session, aircraft_id: str = "AERO-PERST-01") -> AircraftModel:
    ac = AircraftModel(
        aircraft_id=aircraft_id,
        tail_number=f"T-{aircraft_id}",
        aircraft_type="HAL Tejas Mk1A",
        air_base="Sulur AFS",
        squadron="No. 45 Squadron Flying Daggers",
        status="ACTIVE",
        total_flight_hours=100.0,
        total_flight_cycles=50,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _create_telemetry(
    aircraft_id: str,
    timestamp: datetime,
    engine_temp: float = 650.0,
    vibration: float = 0.2,
    obs_id: str = "obs-01",
) -> NormalizedTelemetry:
    return NormalizedTelemetry(
        observation_id=obs_id,
        aircraft_id=aircraft_id,
        flight_id="SORTIE-P01",
        timestamp=timestamp,
        altitude_m=9000.0,
        airspeed_mps=250.0,
        mach=0.82,
        g_load=1.0,
        fuel_flow_kg_h=2300.0,
        engine_temperature_c=engine_temp,
        engine_pressure_kpa=350.0,
        vibration_ips=vibration,
        control_surface_angle_deg=5.0,
        quality_status=QualityStatus.VALID,
        envelope_status=EnvelopeStatus.WITHIN_ENVELOPE,
        source="TEST_PERSISTENCE",
    )


def test_anomaly_persistence_and_correlation(db_session: Session):
    """
    Verifies that repeated anomalous observations of the same condition
    within the correlation window update the existing record rather than creating duplicates.
    """
    service = IntelligenceService(correlation_window_seconds=300.0)
    ac = _create_aircraft(db_session, "AERO-CORR-01")

    t0 = datetime.now(timezone.utc)
    # Frame 1: Thermal spike (890 °C > 850 °C critical threshold)
    telem1 = _create_telemetry(ac.aircraft_id, t0, engine_temp=890.0, obs_id="obs-c1")
    res1 = service.process_telemetry(db_session, telem1)
    assert res1["anomalies_detected"] >= 1

    # Check database: 1 anomaly record created
    anomalies, total = service.get_anomalies(db_session, ac.aircraft_id)
    assert total == 1
    rec1 = anomalies[0]
    assert rec1.occurrence_count == 1
    assert rec1.status == AnomalyStatus.NEW
    initial_conf = rec1.confidence

    # Frame 2: 10 seconds later, same persistent condition (905 °C)
    t1 = t0 + timedelta(seconds=10)
    telem2 = _create_telemetry(ac.aircraft_id, t1, engine_temp=905.0, obs_id="obs-c2")
    res2 = service.process_telemetry(db_session, telem2)

    # Check database: still total == 1 (deduplicated!), occurrence_count == 2
    anomalies2, total2 = service.get_anomalies(db_session, ac.aircraft_id)
    assert total2 == 1
    rec2 = anomalies2[0]
    assert rec2.anomaly_id == rec1.anomaly_id
    assert rec2.occurrence_count == 2
    assert rec2.observed_value == 905.0
    # Confidence increased due to persistence
    assert rec2.confidence >= initial_conf


def test_different_conditions_create_separate_anomalies(db_session: Session):
    """Verifies that distinct signals/subsystems create independent anomaly records."""
    service = IntelligenceService()
    ac = _create_aircraft(db_session, "AERO-MULTI-01")

    t0 = datetime.now(timezone.utc)
    # Frame with both thermal spike and vibration spike
    telem = _create_telemetry(ac.aircraft_id, t0, engine_temp=890.0, vibration=4.5, obs_id="obs-m1")
    service.process_telemetry(db_session, telem)

    anomalies, total = service.get_anomalies(db_session, ac.aircraft_id)
    assert total >= 2
    types = {a.anomaly_type for a in anomalies}
    assert AnomalyType.THERMAL_ANOMALY in types
    assert AnomalyType.VIBRATION_ANOMALY in types


def test_anomaly_lifecycle_transitions(db_session: Session):
    """Verifies state machine transitions: NEW -> ACKNOWLEDGED -> RESOLVED."""
    service = IntelligenceService()
    ac = _create_aircraft(db_session, "AERO-LIFE-01")

    t0 = datetime.now(timezone.utc)
    telem = _create_telemetry(ac.aircraft_id, t0, engine_temp=890.0, obs_id="obs-l1")
    service.process_telemetry(db_session, telem)

    anomalies, _ = service.get_anomalies(db_session, ac.aircraft_id)
    anom = anomalies[0]
    assert anom.status == AnomalyStatus.NEW

    # 1. NEW -> ACKNOWLEDGED
    ack = service.acknowledge_anomaly(db_session, ac.aircraft_id, anom.anomaly_id)
    assert ack.status == AnomalyStatus.ACKNOWLEDGED

    # 2. ACKNOWLEDGED -> RESOLVED
    res = service.resolve_anomaly(db_session, ac.aircraft_id, anom.anomaly_id)
    assert res.status == AnomalyStatus.RESOLVED
    assert res.resolved_at is not None

    # 3. Invalid: RESOLVED -> ACKNOWLEDGED
    with pytest.raises(ValidationError):
        service.acknowledge_anomaly(db_session, ac.aircraft_id, anom.anomaly_id)


def test_anomaly_filtering_and_pagination(db_session: Session):
    """Verifies querying anomalies with severity and status filters."""
    service = IntelligenceService()
    ac = _create_aircraft(db_session, "AERO-FILT-01")

    t0 = datetime.now(timezone.utc)
    # Frame with thermal (CRITICAL) and vibration (HIGH/CRITICAL)
    telem = _create_telemetry(ac.aircraft_id, t0, engine_temp=890.0, vibration=4.5, obs_id="obs-f1")
    service.process_telemetry(db_session, telem)

    # Filter by severity
    crit_anoms, crit_count = service.get_anomalies(db_session, ac.aircraft_id, severity="CRITICAL")
    assert crit_count >= 1
    assert all(a.severity == AnomalySeverity.CRITICAL for a in crit_anoms)

    # Filter by status
    new_anoms, new_count = service.get_anomalies(db_session, ac.aircraft_id, status="NEW")
    assert new_count >= 1
    assert all(a.status == AnomalyStatus.NEW for a in new_anoms)

    # Unknown aircraft raises NotFoundError
    with pytest.raises(NotFoundError):
        service.get_anomalies(db_session, "UNKNOWN-AIRCRAFT")
