"""
SageCommand Air Power System (Aero) — Mission & Sortie API Routes.
Exposes endpoints for creating, scheduling, and reviewing operational missions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.contracts.base import ApiResponse
from app.db.database import get_db
from app.domain.mission import MissionCreate, MissionResponse
from app.domain.enums import MissionStatus, MissionType
from app.services.mission_service import MissionService

router = APIRouter(prefix="/missions", tags=["Missions & Sorties"])


@router.get(
    "",
    response_model=ApiResponse[List[MissionResponse]],
    summary="List Missions",
    description="Returns scheduled and active missions with optional filtering by status or mission type.",
)
def list_missions(
    status: Optional[MissionStatus] = Query(default=None, description="Filter by mission status"),
    mission_type: Optional[MissionType] = Query(default=None, description="Filter by mission type"),
    db: Session = Depends(get_db),
) -> ApiResponse[List[MissionResponse]]:
    missions = MissionService.list_missions(db, status=status, mission_type=mission_type)
    return ApiResponse(
        data=missions,
        message=f"Retrieved {len(missions)} mission records",
    )


@router.post(
    "",
    response_model=ApiResponse[MissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Plan and Register Mission",
    description="Creates a new operational mission requirement and schedule commitment.",
)
def create_mission(
    payload: MissionCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[MissionResponse]:
    created = MissionService.create_mission(db, payload)
    return ApiResponse(
        data=created,
        message=f"Mission '{created.mission_id}' registered successfully",
    )


@router.get(
    "/{mission_id}",
    response_model=ApiResponse[MissionResponse],
    summary="Get Mission by ID",
    description="Retrieves a specific operational mission commitment by its unique identifier.",
)
def get_mission(
    mission_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[MissionResponse]:
    mission = MissionService.get_mission(db, mission_id)
    return ApiResponse(
        data=mission,
        message=f"Mission '{mission_id}' found",
    )
