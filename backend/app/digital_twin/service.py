"""
SageCommand Air Power System (Aero) — Digital Twin Service.
Coordinates digital twin state estimation, flight session tracking,
cumulative flight hours/cycles, and persistence under SQLite WAL.
"""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    FlightSessionModel,
    utc_now,
)
from app.telemetry.models import NormalizedTelemetry, QualityStatus
from app.digital_twin.models import (
    AircraftTwinState,
    SubsystemState,
    TwinSubsystemType,
    TwinHealthState,
    HealthReason,
    FlightSession,
)
from app.digital_twin.estimator import DigitalTwinEstimator

logger = get_logger(__name__)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime instance is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class DigitalTwinService:
    """Service layer managing aircraft digital twin lifecycles and state estimates."""

    def process_telemetry(
        self,
        db: Session,
        telemetry: NormalizedTelemetry,
    ) -> AircraftTwinState:
        """
        Processes normalized telemetry to update the aircraft's estimated digital twin state.
        Guarantees:
        1. Target aircraft exists in authoritative registry.
        2. Rejects INVALID telemetry without state mutation.
        3. Updates flight session and elapsed flight hours.
        4. Increments flight cycles on session transitions without double-counting frames.
        5. Persists the derived state snapshot.
        """
        if telemetry.quality_status == QualityStatus.INVALID:
            raise ValidationError(
                f"Cannot update digital twin from INVALID telemetry observation '{telemetry.observation_id}'",
                details={"quality": telemetry.quality_status.value},
            )

        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == telemetry.aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{telemetry.aircraft_id}' not found for digital twin state update",
                details={"aircraft_id": telemetry.aircraft_id},
            )

        # 1. Retrieve the latest prior twin state for continuity
        prior_record = db.execute(
            select(AircraftTwinStateModel)
            .where(AircraftTwinStateModel.aircraft_id == telemetry.aircraft_id)
            .order_by(desc(AircraftTwinStateModel.timestamp))
        ).scalars().first()

        prior_state: Optional[AircraftTwinState] = None
        if prior_record:
            prior_state = self._record_to_schema(prior_record)

        # 2. Flight Session & Cumulative Hours/Cycles Management
        flight_hours = aircraft.total_flight_hours or 0.0
        flight_cycles = aircraft.total_flight_cycles or 0

        t_telemetry = ensure_utc(telemetry.timestamp)

        if telemetry.flight_id:
            session = db.execute(
                select(FlightSessionModel).where(
                    FlightSessionModel.aircraft_id == telemetry.aircraft_id,
                    FlightSessionModel.flight_id == telemetry.flight_id,
                )
            ).scalar_one_or_none()

            if not session:
                # Close any existing open session for a different flight
                open_prior_sessions = db.execute(
                    select(FlightSessionModel).where(
                        FlightSessionModel.aircraft_id == telemetry.aircraft_id,
                        FlightSessionModel.cycle_counted.is_(False),
                        FlightSessionModel.flight_id != telemetry.flight_id,
                    )
                ).scalars().all()
                for old_sess in open_prior_sessions:
                    old_sess.ended_at = old_sess.last_seen_at
                    old_sess.cycle_counted = True
                    flight_cycles += 1
                    aircraft.total_flight_cycles = flight_cycles

                # Create new flight session
                session_id = f"sess_{telemetry.aircraft_id}_{telemetry.flight_id}_{int(t_telemetry.timestamp())}"
                session = FlightSessionModel(
                    session_id=session_id,
                    aircraft_id=telemetry.aircraft_id,
                    flight_id=telemetry.flight_id,
                    started_at=t_telemetry,
                    last_seen_at=t_telemetry,
                    duration_seconds=0.0,
                    cycle_counted=False,
                )
                db.add(session)
            else:
                # Update existing session duration and calculate flight hours increment
                t_last_seen = ensure_utc(session.last_seen_at)
                delta_sec = (t_telemetry - t_last_seen).total_seconds()
                if 0.0 < delta_sec <= 3600.0:  # Valid contiguous frame progression
                    session.duration_seconds += delta_sec
                    flight_hours += (delta_sec / 3600.0)
                    aircraft.total_flight_hours = round(flight_hours, 4)
                session.last_seen_at = t_telemetry

        # 3. Derive updated state using DigitalTwinEstimator
        twin_state = DigitalTwinEstimator.estimate_state(
            telemetry=telemetry,
            previous_state=prior_state,
            flight_hours=flight_hours,
            flight_cycles=flight_cycles,
        )

        # 4. Update Aircraft airframe operational markers
        if twin_state.operational_status == "IN_FLIGHT":
            aircraft.last_flight_at = telemetry.timestamp

        # 5. Persist twin state record
        state_id = f"twin_{telemetry.aircraft_id}_{int(telemetry.timestamp.timestamp() * 1000)}"
        state_record = AircraftTwinStateModel(
            state_id=state_id,
            aircraft_id=twin_state.aircraft_id,
            timestamp=twin_state.timestamp,
            operational_status=twin_state.operational_status,
            altitude=twin_state.altitude,
            airspeed=twin_state.airspeed,
            mach=twin_state.mach,
            g_load=twin_state.g_load,
            fuel_flow=twin_state.fuel_flow,
            engine_temperature=twin_state.engine_temperature,
            engine_pressure=twin_state.engine_pressure,
            vibration=twin_state.vibration,
            flight_hours=twin_state.flight_hours,
            flight_cycles=twin_state.flight_cycles,
            current_flight_id=twin_state.current_flight_id,
            health_state=twin_state.health_state.value,
            health_score=twin_state.health_score,
            wear_index=twin_state.wear_index,
            subsystem_states={k: v.model_dump(mode="json") for k, v in twin_state.subsystem_states.items()},
            health_reasons=[r.model_dump(mode="json") for r in twin_state.health_reasons],
            active_warnings=twin_state.active_warnings,
            data_quality=twin_state.data_quality,
            last_updated_at=utc_now(),
        )
        db.add(state_record)
        db.commit()

        logger.debug(
            f"Updated digital twin for {telemetry.aircraft_id}: health={twin_state.health_score} ({twin_state.health_state.value})"
        )
        return twin_state

    def get_current_state(self, db: Session, aircraft_id: str) -> AircraftTwinState:
        """
        Retrieves the current estimated state for an aircraft.
        If no telemetry has been ingested yet, returns a baseline nominal twin state.
        """
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id},
            )

        latest_record = db.execute(
            select(AircraftTwinStateModel)
            .where(AircraftTwinStateModel.aircraft_id == aircraft_id)
            .order_by(desc(AircraftTwinStateModel.timestamp))
        ).scalars().first()

        if latest_record:
            return self._record_to_schema(latest_record)

        # Baseline initial state when no telemetry has arrived
        now = utc_now()
        nominal_subsystems = {
            s.value: SubsystemState(
                subsystem=s,
                health_state=TwinHealthState.HEALTHY if s != TwinSubsystemType.HYDRAULIC else TwinHealthState.UNKNOWN,
                health_score=100.0,
                wear_index=0.0,
                last_updated_at=now,
                contributing_signals=[] if s == TwinSubsystemType.HYDRAULIC else ["baseline_init"],
                warnings=["No dedicated hydraulic sensor telemetry channel present; state unobserved"] if s == TwinSubsystemType.HYDRAULIC else [],
            )
            for s in TwinSubsystemType
        }

        return AircraftTwinState(
            aircraft_id=aircraft_id,
            timestamp=now,
            operational_status=aircraft.status,
            flight_hours=round(aircraft.total_flight_hours or 0.0, 2),
            flight_cycles=aircraft.total_flight_cycles or 0,
            health_state=TwinHealthState.HEALTHY,
            health_score=100.0,
            wear_index=0.0,
            subsystem_states=nominal_subsystems,
            health_reasons=[],
            active_warnings=[],
            data_quality="BASELINE",
            last_updated_at=now,
        )

    def get_state_history(
        self,
        db: Session,
        aircraft_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AircraftTwinState]:
        """Returns chronological historical state snapshots for an aircraft."""
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id},
            )

        records = db.execute(
            select(AircraftTwinStateModel)
            .where(AircraftTwinStateModel.aircraft_id == aircraft_id)
            .order_by(desc(AircraftTwinStateModel.timestamp))
            .offset(offset)
            .limit(limit)
        ).scalars().all()

        return [self._record_to_schema(r) for r in records]

    def close_flight(
        self,
        db: Session,
        aircraft_id: str,
        flight_id: Optional[str] = None,
    ) -> Optional[FlightSession]:
        """
        Explicitly concludes an active flight session, marking cycle increment completed.
        """
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found",
                details={"aircraft_id": aircraft_id},
            )

        query = select(FlightSessionModel).where(
            FlightSessionModel.aircraft_id == aircraft_id,
            FlightSessionModel.cycle_counted.is_(False),
        )
        if flight_id:
            query = query.where(FlightSessionModel.flight_id == flight_id)

        session = db.execute(query.order_by(desc(FlightSessionModel.last_seen_at))).scalars().first()
        if not session:
            return None

        now = utc_now()
        session.ended_at = now
        session.cycle_counted = True
        aircraft.total_flight_cycles += 1
        db.commit()
        db.refresh(session)

        return FlightSession(
            session_id=session.session_id,
            aircraft_id=session.aircraft_id,
            flight_id=session.flight_id,
            started_at=session.started_at,
            last_seen_at=session.last_seen_at,
            ended_at=session.ended_at,
            duration_seconds=session.duration_seconds,
            cycle_counted=session.cycle_counted,
        )

    def reset_state(self, db: Session, aircraft_id: str) -> None:
        """Purges twin state history and flight sessions for the given aircraft."""
        records = db.execute(
            select(AircraftTwinStateModel).where(AircraftTwinStateModel.aircraft_id == aircraft_id)
        ).scalars().all()
        for r in records:
            db.delete(r)

        sessions = db.execute(
            select(FlightSessionModel).where(FlightSessionModel.aircraft_id == aircraft_id)
        ).scalars().all()
        for s in sessions:
            db.delete(s)

        db.commit()

    def _record_to_schema(self, record: AircraftTwinStateModel) -> AircraftTwinState:
        """Converts an ORM model instance into the typed AircraftTwinState contract."""
        subsystems: dict[str, SubsystemState] = {}
        if record.subsystem_states and isinstance(record.subsystem_states, dict):
            for k, v in record.subsystem_states.items():
                try:
                    subsystems[k] = SubsystemState(**v)
                except Exception:
                    pass

        reasons: list[HealthReason] = []
        if record.health_reasons and isinstance(record.health_reasons, list):
            for r in record.health_reasons:
                try:
                    reasons.append(HealthReason(**r))
                except Exception:
                    pass

        health_state_enum = TwinHealthState.HEALTHY
        try:
            health_state_enum = TwinHealthState(record.health_state)
        except Exception:
            pass

        return AircraftTwinState(
            aircraft_id=record.aircraft_id,
            timestamp=ensure_utc(record.timestamp),
            operational_status=record.operational_status,
            altitude=record.altitude,
            airspeed=record.airspeed,
            mach=record.mach,
            g_load=record.g_load,
            fuel_flow=record.fuel_flow,
            engine_temperature=record.engine_temperature,
            engine_pressure=record.engine_pressure,
            vibration=record.vibration,
            flight_hours=record.flight_hours,
            flight_cycles=record.flight_cycles,
            current_flight_id=record.current_flight_id,
            health_state=health_state_enum,
            health_score=record.health_score,
            wear_index=record.wear_index,
            subsystem_states=subsystems,
            health_reasons=reasons,
            active_warnings=record.active_warnings or [],
            data_quality=record.data_quality,
            last_updated_at=ensure_utc(record.last_updated_at),
        )


# Singleton default service instance
default_digital_twin_service = DigitalTwinService()
