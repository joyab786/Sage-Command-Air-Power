"""
SageCommand Air Power System (Aero) — SQLAlchemy 2.0 Database Models.
Implements relational persistence for core aerospace domain entities:
Aircraft, Components, Maintenance Events, Readiness Assessments, and Missions.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
    func,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AircraftModel(Base):
    """Authoritative relational record of an aircraft airframe asset."""

    __tablename__ = "aircraft"

    aircraft_id = Column(String(64), primary_key=True, index=True)
    tail_number = Column(String(32), unique=True, nullable=False, index=True)
    aircraft_type = Column(String(64), nullable=False, index=True)
    variant = Column(String(64), nullable=True)
    air_base = Column(String(64), nullable=False, index=True)
    squadron = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    total_flight_hours = Column(Float, nullable=False, default=0.0)
    total_flight_cycles = Column(Integer, nullable=False, default=0)
    last_flight_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    components = relationship(
        "ComponentModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    maintenance_events = relationship(
        "MaintenanceEventModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    readiness_assessments = relationship(
        "ReadinessAssessmentModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ReadinessAssessmentModel.assessed_at)",
    )
    telemetry_records = relationship(
        "TelemetryRecordModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(TelemetryRecordModel.timestamp)",
    )
    twin_states = relationship(
        "AircraftTwinStateModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(AircraftTwinStateModel.timestamp)",
    )
    flight_sessions = relationship(
        "FlightSessionModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(FlightSessionModel.started_at)",
    )
    anomalies = relationship(
        "AnomalyModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(AnomalyModel.timestamp)",
    )
    prognostic_records = relationship(
        "PrognosticRecordModel",
        back_populates="aircraft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(PrognosticRecordModel.timestamp)",
    )


class ComponentModel(Base):
    """Relational record of an aircraft subsystem or Line Replaceable Unit (LRU)."""

    __tablename__ = "components"

    component_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    component_type = Column(String(64), nullable=False, index=True)
    serial_number = Column(String(64), nullable=False, unique=True, index=True)
    health_state = Column(String(32), nullable=False, default="HEALTHY", index=True)
    installation_date = Column(DateTime(timezone=True), nullable=True)
    accumulated_hours = Column(Float, nullable=False, default=0.0)
    accumulated_cycles = Column(Integer, nullable=False, default=0)
    last_maintenance_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    aircraft = relationship("AircraftModel", back_populates="components")
    maintenance_events = relationship("MaintenanceEventModel", back_populates="component")


class MaintenanceEventModel(Base):
    """Relational record of maintenance servicing actions and predictive work packages."""

    __tablename__ = "maintenance_events"

    maintenance_event_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    component_id = Column(String(64), ForeignKey("components.component_id", ondelete="SET NULL"), nullable=True, index=True)
    maintenance_type = Column(String(32), nullable=False, default="SCHEDULED")
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    priority = Column(String(32), nullable=False, default="MEDIUM", index=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=False)
    source = Column(String(64), nullable=False, default="MANUAL")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    aircraft = relationship("AircraftModel", back_populates="maintenance_events")
    component = relationship("ComponentModel", back_populates="maintenance_events")


class ReadinessAssessmentModel(Base):
    """Relational record of aircraft mission readiness state evaluations."""

    __tablename__ = "readiness_assessments"

    assessment_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    readiness_status = Column(String(16), nullable=False, default="FMC", index=True)
    assessed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    reasons = Column(JSON, nullable=False, default=list)
    limiting_components = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    aircraft = relationship("AircraftModel", back_populates="readiness_assessments")


class MissionModel(Base):
    """Relational record of planned and executing operational sorties and missions."""

    __tablename__ = "missions"

    mission_id = Column(String(64), primary_key=True, index=True)
    mission_name = Column(String(128), nullable=True)
    mission_type = Column(String(64), nullable=False, default="TRAINING", index=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    required_aircraft = Column(Integer, nullable=False, default=1)
    assigned_aircraft = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="PLANNED", index=True)
    readiness_requirement = Column(String(16), nullable=False, default="FMC")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class TelemetryRecordModel(Base):
    """
    Relational record for persistent storage of normalized flight telemetry frames.
    Optimized for high-concurrency ingestion and time-series retrieval.
    """

    __tablename__ = "telemetry_records"
    __table_args__ = (
        Index("ix_telemetry_aircraft_timestamp", "aircraft_id", "timestamp"),
    )

    record_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    flight_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Normalized SI channel values
    altitude_m = Column(Float, nullable=True)
    airspeed_mps = Column(Float, nullable=True)
    mach = Column(Float, nullable=True)
    g_load = Column(Float, nullable=True)
    fuel_flow_kg_h = Column(Float, nullable=True)
    engine_temperature_c = Column(Float, nullable=True)
    engine_pressure_kpa = Column(Float, nullable=True)
    vibration_ips = Column(Float, nullable=True)
    control_surface_angle_deg = Column(Float, nullable=True)

    # Assessment & Signal Metadata
    quality = Column(String(16), nullable=False, default="VALID", index=True)
    envelope_status = Column(String(32), nullable=False, default="WITHIN_ENVELOPE", index=True)
    source = Column(String(64), nullable=False, default="TELEMETRY_STREAM")
    raw_units = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    aircraft = relationship("AircraftModel", back_populates="telemetry_records")


class AircraftTwinStateModel(Base):
    """
    Relational record for persistent storage of Aircraft Digital Twin states.
    Stores historical snapshots and facilitates fast retrieval of current estimated state.
    """

    __tablename__ = "aircraft_twin_states"
    __table_args__ = (
        Index("ix_twin_aircraft_timestamp", "aircraft_id", "timestamp"),
    )

    state_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    operational_status = Column(String(32), nullable=False, default="ACTIVE", index=True)

    altitude = Column(Float, nullable=True)
    airspeed = Column(Float, nullable=True)
    mach = Column(Float, nullable=True)
    g_load = Column(Float, nullable=True)
    fuel_flow = Column(Float, nullable=True)
    engine_temperature = Column(Float, nullable=True)
    engine_pressure = Column(Float, nullable=True)
    vibration = Column(Float, nullable=True)

    flight_hours = Column(Float, nullable=False, default=0.0)
    flight_cycles = Column(Integer, nullable=False, default=0)
    current_flight_id = Column(String(64), nullable=True, index=True)

    health_state = Column(String(32), nullable=False, default="HEALTHY", index=True)
    health_score = Column(Float, nullable=False, default=100.0)
    wear_index = Column(Float, nullable=False, default=0.0)
    subsystem_states = Column(JSON, nullable=False, default=dict)
    health_reasons = Column(JSON, nullable=False, default=list)
    active_warnings = Column(JSON, nullable=False, default=list)
    data_quality = Column(String(32), nullable=False, default="VALID")
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    aircraft = relationship("AircraftModel", back_populates="twin_states")


class FlightSessionModel(Base):
    """
    Relational tracking record for flight/sortie sessions.
    Maintains elapsed duration and guarantees idempotency of cycle counting.
    """

    __tablename__ = "flight_sessions"
    __table_args__ = (
        Index("ix_session_aircraft_flight", "aircraft_id", "flight_id"),
    )

    session_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    flight_id = Column(String(64), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    cycle_counted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    aircraft = relationship("AircraftModel", back_populates="flight_sessions")


class AnomalyModel(Base):
    """
    Relational record for detected subsystem anomalies.
    Provides persistence, historical auditability, deduplication tracking, and lifecycle status.
    """

    __tablename__ = "anomalies"
    __table_args__ = (
        Index("ix_anomalies_aircraft_status", "aircraft_id", "status"),
        Index("ix_anomalies_aircraft_severity", "aircraft_id", "severity"),
        Index("ix_anomalies_aircraft_subsystem", "aircraft_id", "subsystem"),
        Index("ix_anomalies_aircraft_time", "aircraft_id", "timestamp"),
    )

    anomaly_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    flight_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    subsystem = Column(String(64), nullable=False, index=True)
    anomaly_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="NEW", index=True)
    confidence = Column(Float, nullable=False, default=0.5)
    detector = Column(String(128), nullable=False)
    signal = Column(String(128), nullable=False)
    observed_value = Column(Float, nullable=True)
    expected_range = Column(String(128), nullable=True)
    deviation = Column(Float, nullable=True, default=0.0)
    description = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True, default=list)
    occurrence_count = Column(Integer, nullable=False, default=1)
    first_detected_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_detected_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    aircraft = relationship("AircraftModel", back_populates="anomalies")


class PrognosticRecordModel(Base):
    """
    Relational persistence for prognostic assessments and RUL predictions.
    Preserves historical degradation trends, uncertainty intervals, and maintenance forecasts.
    """

    __tablename__ = "prognostic_records"
    __table_args__ = (
        Index("ix_prognostics_aircraft_time", "aircraft_id", "timestamp"),
        Index("ix_prognostics_aircraft_priority", "aircraft_id", "forecast_priority"),
        Index("ix_prognostics_aircraft_subsystem", "aircraft_id", "subsystem"),
    )

    record_id = Column(String(64), primary_key=True, index=True)
    aircraft_id = Column(String(64), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    subsystem = Column(String(64), nullable=False, index=True)
    health_score = Column(Float, nullable=False, default=100.0)
    wear_index = Column(Float, nullable=False, default=0.0)
    trend_direction = Column(String(32), nullable=False, default="STABLE")
    degradation_rate = Column(Float, nullable=False, default=0.0)
    slope = Column(Float, nullable=False, default=0.0)
    estimated_rul_hours = Column(Float, nullable=False)
    estimated_rul_cycles = Column(Integer, nullable=True)
    lower_bound_hours = Column(Float, nullable=False)
    upper_bound_hours = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False, default=0.85)
    forecast_priority = Column(String(32), nullable=False, default="MONITOR", index=True)
    prediction_method = Column(String(64), nullable=False)
    limiting_factors = Column(JSON, nullable=True, default=list)
    explanation = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    aircraft = relationship("AircraftModel", back_populates="prognostic_records")

