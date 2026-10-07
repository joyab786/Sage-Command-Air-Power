"""
SageCommand Air Power System (Aero) — Aircraft & Fleet Service.
Provides business logic, validation, and relational persistence workflows
for aircraft airframe assets, installed components, and readiness status.
"""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.exceptions import NotFoundError, AeroException
from app.core.logging import get_logger
from app.db.models import (
    AircraftModel,
    ComponentModel,
    ReadinessAssessmentModel,
    utc_now,
)
from app.domain.aircraft import AircraftCreate, AircraftResponse
from app.domain.component import ComponentCreate, ComponentResponse
from app.domain.readiness import ReadinessAssessmentCreate, ReadinessAssessmentResponse
from app.domain.enums import AircraftStatus, ReadinessStatus, ComponentHealth

logger = get_logger(__name__)


class AircraftService:
    """Service layer managing aircraft airframes, subsystem components, and readiness."""

    @staticmethod
    def list_aircraft(
        db: Session,
        status: Optional[AircraftStatus] = None,
        squadron: Optional[str] = None,
        air_base: Optional[str] = None,
    ) -> List[AircraftResponse]:
        """Queries aircraft assets with optional operational filtering."""
        query = select(AircraftModel)
        if status:
            query = query.where(AircraftModel.status == status.value)
        if squadron:
            query = query.where(AircraftModel.squadron == squadron)
        if air_base:
            query = query.where(AircraftModel.air_base == air_base)

        results = db.execute(query).scalars().all()
        return [AircraftResponse.model_validate(item) for item in results]

    @staticmethod
    def get_aircraft(db: Session, aircraft_id: str) -> AircraftResponse:
        """Retrieves a single aircraft by its authoritative identifier."""
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()

        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' does not exist in registry",
                details={"aircraft_id": aircraft_id},
            )
        return AircraftResponse.model_validate(aircraft)

    @staticmethod
    def create_aircraft(db: Session, payload: AircraftCreate) -> AircraftResponse:
        """Registers a new aircraft airframe asset with uniqueness checks."""
        existing_id = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == payload.aircraft_id)
        ).scalar_one_or_none()
        if existing_id:
            raise AeroException(
                f"Aircraft with ID '{payload.aircraft_id}' already registered",
                error_code="AIRCRAFT_EXISTS",
                status_code=409,
                details={"aircraft_id": payload.aircraft_id},
            )

        existing_tail = db.execute(
            select(AircraftModel).where(AircraftModel.tail_number == payload.tail_number)
        ).scalar_one_or_none()
        if existing_tail:
            raise AeroException(
                f"Aircraft with tail number '{payload.tail_number}' already registered",
                error_code="TAIL_NUMBER_EXISTS",
                status_code=409,
                details={"tail_number": payload.tail_number},
            )

        aircraft = AircraftModel(
            aircraft_id=payload.aircraft_id,
            tail_number=payload.tail_number,
            aircraft_type=payload.aircraft_type,
            variant=payload.variant,
            air_base=payload.air_base,
            squadron=payload.squadron,
            status=payload.status.value,
            total_flight_hours=payload.total_flight_hours,
            total_flight_cycles=payload.total_flight_cycles,
            last_flight_at=payload.last_flight_at,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(aircraft)
        db.commit()
        db.refresh(aircraft)
        logger.info(f"Registered new aircraft asset: {aircraft.aircraft_id} ({aircraft.tail_number})")
        return AircraftResponse.model_validate(aircraft)

    @staticmethod
    def get_aircraft_components(db: Session, aircraft_id: str) -> List[ComponentResponse]:
        """Retrieves all installed subsystem components for a given aircraft."""
        # Validate aircraft exists
        AircraftService.get_aircraft(db, aircraft_id)

        components = db.execute(
            select(ComponentModel).where(ComponentModel.aircraft_id == aircraft_id)
        ).scalars().all()
        return [ComponentResponse.model_validate(comp) for comp in components]

    @staticmethod
    def create_component(db: Session, payload: ComponentCreate) -> ComponentResponse:
        """Installs and registers a subsystem component on an aircraft."""
        # Validate aircraft exists
        AircraftService.get_aircraft(db, payload.aircraft_id)

        existing = db.execute(
            select(ComponentModel).where(ComponentModel.component_id == payload.component_id)
        ).scalar_one_or_none()
        if existing:
            raise AeroException(
                f"Component '{payload.component_id}' is already registered",
                error_code="COMPONENT_EXISTS",
                status_code=409,
                details={"component_id": payload.component_id},
            )

        existing_serial = db.execute(
            select(ComponentModel).where(ComponentModel.serial_number == payload.serial_number)
        ).scalar_one_or_none()
        if existing_serial:
            raise AeroException(
                f"Component with serial '{payload.serial_number}' is already registered",
                error_code="SERIAL_NUMBER_EXISTS",
                status_code=409,
                details={"serial_number": payload.serial_number},
            )

        component = ComponentModel(
            component_id=payload.component_id,
            aircraft_id=payload.aircraft_id,
            component_type=payload.component_type.value,
            serial_number=payload.serial_number,
            health_state=payload.health_state.value,
            installation_date=payload.installation_date,
            accumulated_hours=payload.accumulated_hours,
            accumulated_cycles=payload.accumulated_cycles,
            last_maintenance_at=payload.last_maintenance_at,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(component)
        db.commit()
        db.refresh(component)
        logger.info(f"Registered component {component.component_id} on aircraft {component.aircraft_id}")
        return ComponentResponse.model_validate(component)

    @staticmethod
    def record_readiness_assessment(
        db: Session, payload: ReadinessAssessmentCreate
    ) -> ReadinessAssessmentResponse:
        """Records an explicit readiness evaluation for an aircraft."""
        AircraftService.get_aircraft(db, payload.aircraft_id)

        assessment = ReadinessAssessmentModel(
            assessment_id=payload.assessment_id,
            aircraft_id=payload.aircraft_id,
            readiness_status=payload.readiness_status.value,
            assessed_at=payload.assessed_at,
            reasons=payload.reasons,
            limiting_components=payload.limiting_components,
            confidence=payload.confidence,
            created_at=utc_now(),
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        logger.info(f"Recorded readiness assessment for {assessment.aircraft_id}: {assessment.readiness_status}")
        return ReadinessAssessmentResponse.model_validate(assessment)

    @staticmethod
    def get_aircraft_readiness(db: Session, aircraft_id: str) -> ReadinessAssessmentResponse:
        """
        Retrieves the latest readiness assessment for an aircraft.
        If no explicit evaluation has been recorded, generates an authoritative baseline
        derived from the aircraft's lifecycle status and component health conditions.
        """
        aircraft = AircraftService.get_aircraft(db, aircraft_id)

        latest_assessment = db.execute(
            select(ReadinessAssessmentModel)
            .where(ReadinessAssessmentModel.aircraft_id == aircraft_id)
            .order_by(ReadinessAssessmentModel.assessed_at.desc())
        ).scalars().first()

        if latest_assessment:
            return ReadinessAssessmentResponse.model_validate(latest_assessment)

        # Baseline evaluation derivation
        limiting_components = []
        reasons = []
        status = ReadinessStatus.FMC

        if aircraft.status == AircraftStatus.GROUNDED:
            status = ReadinessStatus.NMC
            reasons.append("Aircraft is in GROUNDED status")
        elif aircraft.status == AircraftStatus.MAINTENANCE:
            status = ReadinessStatus.NMC
            reasons.append("Aircraft is in MAINTENANCE status")
        elif aircraft.status == AircraftStatus.RETIRED:
            status = ReadinessStatus.NMC
            reasons.append("Aircraft is in RETIRED status")
        else:
            # Check installed components
            components = db.execute(
                select(ComponentModel).where(ComponentModel.aircraft_id == aircraft_id)
            ).scalars().all()

            for comp in components:
                if comp.health_state in (ComponentHealth.CRITICAL.value, ComponentHealth.FAILED.value):
                    status = ReadinessStatus.NMC
                    limiting_components.append(comp.component_id)
                    reasons.append(f"Subsystem {comp.component_id} condition is {comp.health_state}")
                elif comp.health_state in (ComponentHealth.DEGRADED.value, ComponentHealth.WARNING.value):
                    if status != ReadinessStatus.NMC:
                        status = ReadinessStatus.PMC
                    limiting_components.append(comp.component_id)
                    reasons.append(f"Subsystem {comp.component_id} condition is {comp.health_state}")

            if not reasons:
                reasons.append("All primary subsystems within standard operating envelope")

        now = datetime.now(timezone.utc)
        return ReadinessAssessmentResponse(
            assessment_id=f"eval_baseline_{aircraft_id}",
            aircraft_id=aircraft_id,
            readiness_status=status,
            assessed_at=now,
            reasons=reasons,
            limiting_components=limiting_components,
            confidence=1.0,
            created_at=now,
        )
