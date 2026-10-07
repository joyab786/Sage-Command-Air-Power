"""
SageCommand Air Power System (Aero) — Mission & Sortie Service.
Provides mission planning, scheduling, asset requirement validation,
and operational status tracking.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.exceptions import NotFoundError, AeroException
from app.core.logging import get_logger
from app.db.models import MissionModel, utc_now
from app.domain.mission import MissionCreate, MissionResponse
from app.domain.enums import MissionStatus, MissionType

logger = get_logger(__name__)


class MissionService:
    """Service layer managing tactical missions and airframe requirement commitments."""

    @staticmethod
    def list_missions(
        db: Session,
        status: Optional[MissionStatus] = None,
        mission_type: Optional[MissionType] = None,
    ) -> List[MissionResponse]:
        """Queries missions with optional status and profile filtering."""
        query = select(MissionModel)
        if status:
            query = query.where(MissionModel.status == status.value)
        if mission_type:
            query = query.where(MissionModel.mission_type == mission_type.value)

        results = db.execute(query).scalars().all()
        return [MissionResponse.model_validate(item) for item in results]

    @staticmethod
    def get_mission(db: Session, mission_id: str) -> MissionResponse:
        """Retrieves a single mission by its unique identifier."""
        mission = db.execute(
            select(MissionModel).where(MissionModel.mission_id == mission_id)
        ).scalar_one_or_none()

        if not mission:
            raise NotFoundError(
                f"Mission '{mission_id}' not found",
                details={"mission_id": mission_id},
            )
        return MissionResponse.model_validate(mission)

    @staticmethod
    def create_mission(db: Session, payload: MissionCreate) -> MissionResponse:
        """Registers a new operational mission commitment with uniqueness checks."""
        existing = db.execute(
            select(MissionModel).where(MissionModel.mission_id == payload.mission_id)
        ).scalar_one_or_none()
        if existing:
            raise AeroException(
                f"Mission '{payload.mission_id}' is already registered",
                error_code="MISSION_EXISTS",
                status_code=409,
                details={"mission_id": payload.mission_id},
            )

        mission = MissionModel(
            mission_id=payload.mission_id,
            mission_name=payload.mission_name,
            mission_type=payload.mission_type.value,
            scheduled_start=payload.scheduled_start,
            scheduled_end=payload.scheduled_end,
            required_aircraft=payload.required_aircraft,
            assigned_aircraft=payload.assigned_aircraft,
            status=payload.status.value,
            readiness_requirement=payload.readiness_requirement.value,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(mission)
        db.commit()
        db.refresh(mission)
        logger.info(f"Registered new mission {mission.mission_id} ({mission.mission_name})")
        return MissionResponse.model_validate(mission)
