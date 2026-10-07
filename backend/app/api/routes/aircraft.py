"""
SageCommand Air Power System (Aero) — Aircraft API Routes.
Exposes endpoints for querying, creating, and inspecting aircraft airframe assets,
subsystem components, and tactical readiness assessments.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.contracts.base import ApiResponse
from app.db.database import get_db
from app.domain.aircraft import AircraftCreate, AircraftResponse
from app.domain.component import ComponentCreate, ComponentResponse
from app.domain.readiness import ReadinessAssessmentCreate, ReadinessAssessmentResponse
from app.domain.enums import AircraftStatus
from app.services.aircraft_service import AircraftService

router = APIRouter(prefix="/aircraft", tags=["Aircraft & Fleet"])


@router.get(
    "",
    response_model=ApiResponse[List[AircraftResponse]],
    summary="List Aircraft Assets",
    description="Returns registered aircraft airframes with optional filtering by lifecycle status, squadron, or air base.",
)
def list_aircraft(
    status: Optional[AircraftStatus] = Query(default=None, description="Filter by lifecycle status"),
    squadron: Optional[str] = Query(default=None, description="Filter by squadron designation"),
    air_base: Optional[str] = Query(default=None, description="Filter by home air base"),
    db: Session = Depends(get_db),
) -> ApiResponse[List[AircraftResponse]]:
    aircraft_list = AircraftService.list_aircraft(db, status=status, squadron=squadron, air_base=air_base)
    return ApiResponse(
        data=aircraft_list,
        message=f"Retrieved {len(aircraft_list)} aircraft records",
    )


@router.post(
    "",
    response_model=ApiResponse[AircraftResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Aircraft Asset",
    description="Registers a new aircraft airframe asset into the fleet database.",
)
def create_aircraft(
    payload: AircraftCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[AircraftResponse]:
    created = AircraftService.create_aircraft(db, payload)
    return ApiResponse(
        data=created,
        message=f"Aircraft '{created.aircraft_id}' registered successfully",
    )


@router.get(
    "/{aircraft_id}",
    response_model=ApiResponse[AircraftResponse],
    summary="Get Aircraft by ID",
    description="Retrieves a specific aircraft airframe by its unique identifier.",
)
def get_aircraft(
    aircraft_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[AircraftResponse]:
    aircraft = AircraftService.get_aircraft(db, aircraft_id)
    return ApiResponse(
        data=aircraft,
        message=f"Aircraft '{aircraft_id}' found",
    )


@router.get(
    "/{aircraft_id}/components",
    response_model=ApiResponse[List[ComponentResponse]],
    summary="Get Installed Aircraft Components",
    description="Retrieves all installed subsystem components and LRUs for an aircraft.",
)
def get_aircraft_components(
    aircraft_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[List[ComponentResponse]]:
    components = AircraftService.get_aircraft_components(db, aircraft_id)
    return ApiResponse(
        data=components,
        message=f"Retrieved {len(components)} components for aircraft '{aircraft_id}'",
    )


@router.post(
    "/{aircraft_id}/components",
    response_model=ApiResponse[ComponentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Install Subsystem Component",
    description="Registers and links a subsystem component to an aircraft.",
)
def install_component(
    aircraft_id: str,
    payload: ComponentCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[ComponentResponse]:
    # Ensure aircraft_id path parameter consistency
    if payload.aircraft_id != aircraft_id:
        payload = payload.model_copy(update={"aircraft_id": aircraft_id})
    created = AircraftService.create_component(db, payload)
    return ApiResponse(
        data=created,
        message=f"Component '{created.component_id}' registered on aircraft '{aircraft_id}'",
    )


@router.get(
    "/{aircraft_id}/readiness",
    response_model=ApiResponse[ReadinessAssessmentResponse],
    summary="Get Aircraft Readiness Assessment",
    description="Retrieves the current mission readiness evaluation (FMC, PMC, NMC) for an aircraft.",
)
def get_aircraft_readiness(
    aircraft_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[ReadinessAssessmentResponse]:
    readiness = AircraftService.get_aircraft_readiness(db, aircraft_id)
    return ApiResponse(
        data=readiness,
        message=f"Current readiness status: {readiness.readiness_status}",
    )


@router.post(
    "/{aircraft_id}/readiness",
    response_model=ApiResponse[ReadinessAssessmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record Explicit Readiness Assessment",
    description="Stores a new explicit mission readiness assessment for an aircraft.",
)
def record_readiness(
    aircraft_id: str,
    payload: ReadinessAssessmentCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[ReadinessAssessmentResponse]:
    if payload.aircraft_id != aircraft_id:
        payload = payload.model_copy(update={"aircraft_id": aircraft_id})
    recorded = AircraftService.record_readiness_assessment(db, payload)
    return ApiResponse(
        data=recorded,
        message=f"Readiness assessment recorded for '{aircraft_id}': {recorded.readiness_status}",
    )


@router.get(
    "/{aircraft_id}/telemetry",
    summary="Get Aircraft Telemetry History",
    description="Retrieves historical normalized flight telemetry frames for a specific aircraft.",
)
def get_aircraft_telemetry(
    aircraft_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Max observations to return"),
    offset: int = Query(default=0, ge=0, description="Offset index for pagination"),
    db: Session = Depends(get_db),
):
    from app.telemetry.service import default_telemetry_service
    records = default_telemetry_service.get_for_aircraft(db, aircraft_id=aircraft_id, limit=limit, offset=offset)
    return ApiResponse(
        data=records,
        message=f"Retrieved {len(records)} telemetry frames for aircraft '{aircraft_id}'",
    )


@router.get(
    "/{aircraft_id}/twin",
    summary="Get Aircraft Digital Twin State",
    description="Retrieves the current estimated operational digital twin state for a specific aircraft.",
)
def get_aircraft_twin_state(
    aircraft_id: str,
    db: Session = Depends(get_db),
):
    from app.digital_twin.service import default_digital_twin_service
    from app.digital_twin.models import AircraftTwinState

    twin_state = default_digital_twin_service.get_current_state(db, aircraft_id=aircraft_id)
    return ApiResponse[AircraftTwinState](
        data=twin_state,
        message=f"Current digital twin state for aircraft '{aircraft_id}' retrieved",
    )


@router.get(
    "/{aircraft_id}/twin/history",
    summary="Get Aircraft Digital Twin History",
    description="Retrieves chronological historical digital twin state snapshots for a specific aircraft.",
)
def get_aircraft_twin_history(
    aircraft_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Max snapshots to return"),
    offset: int = Query(default=0, ge=0, description="Offset index for pagination"),
    db: Session = Depends(get_db),
):
    from app.digital_twin.service import default_digital_twin_service
    from app.digital_twin.models import AircraftTwinState

    history = default_digital_twin_service.get_state_history(db, aircraft_id=aircraft_id, limit=limit, offset=offset)
    return ApiResponse[List[AircraftTwinState]](
        data=history,
        message=f"Retrieved {len(history)} digital twin historical snapshots for aircraft '{aircraft_id}'",
    )


# -------------------------------------------------------------------------
# Subsystem Intelligence & Anomaly Detection (SIH MVP)
# -------------------------------------------------------------------------

@router.get(
    "/{aircraft_id}/anomalies",
    summary="Get Aircraft Subsystem Anomalies",
    description="Retrieves detected anomalies for an aircraft with optional filtering by severity, status, subsystem, or time window.",
)
def get_aircraft_anomalies(
    aircraft_id: str,
    severity: Optional[str] = Query(default=None, description="Filter by severity (INFO, LOW, MEDIUM, HIGH, CRITICAL)"),
    status: Optional[str] = Query(default=None, description="Filter by status (NEW, ACKNOWLEDGED, RESOLVED)"),
    subsystem: Optional[str] = Query(default=None, description="Filter by subsystem name"),
    from_time: Optional[str] = Query(default=None, alias="from", description="ISO 8601 start timestamp"),
    to_time: Optional[str] = Query(default=None, alias="to", description="ISO 8601 end timestamp"),
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    from app.intelligence.service import default_intelligence_service
    from app.intelligence.models import Anomaly

    parsed_from = datetime.fromisoformat(from_time) if from_time else None
    parsed_to = datetime.fromisoformat(to_time) if to_time else None

    anomalies, total = default_intelligence_service.get_anomalies(
        db=db,
        aircraft_id=aircraft_id,
        severity=severity,
        status=status,
        subsystem=subsystem,
        from_time=parsed_from,
        to_time=parsed_to,
        limit=limit,
        offset=offset,
    )
    return ApiResponse[List[Anomaly]](
        data=anomalies,
        message=f"Retrieved {len(anomalies)} anomalies (total {total}) for aircraft '{aircraft_id}'",
    )


@router.get(
    "/{aircraft_id}/anomalies/{anomaly_id}",
    summary="Get Anomaly Detail",
    description="Retrieves a specific anomaly observation record with complete explainable evidence.",
)
def get_aircraft_anomaly_detail(
    aircraft_id: str,
    anomaly_id: str,
    db: Session = Depends(get_db),
):
    from app.intelligence.service import default_intelligence_service
    from app.intelligence.models import Anomaly

    anomaly = default_intelligence_service.get_anomaly(db, aircraft_id=aircraft_id, anomaly_id=anomaly_id)
    return ApiResponse[Anomaly](
        data=anomaly,
        message=f"Anomaly '{anomaly_id}' retrieved",
    )


@router.post(
    "/{aircraft_id}/anomalies/{anomaly_id}/acknowledge",
    summary="Acknowledge Anomaly",
    description="Transitions an anomaly lifecycle status from NEW to ACKNOWLEDGED.",
)
def acknowledge_aircraft_anomaly(
    aircraft_id: str,
    anomaly_id: str,
    db: Session = Depends(get_db),
):
    from app.intelligence.service import default_intelligence_service
    from app.intelligence.models import Anomaly

    acknowledged = default_intelligence_service.acknowledge_anomaly(db, aircraft_id=aircraft_id, anomaly_id=anomaly_id)
    return ApiResponse[Anomaly](
        data=acknowledged,
        message=f"Anomaly '{anomaly_id}' acknowledged",
    )


@router.post(
    "/{aircraft_id}/anomalies/{anomaly_id}/resolve",
    summary="Resolve Anomaly",
    description="Transitions an active anomaly lifecycle status to RESOLVED via explicit operator action.",
)
def resolve_aircraft_anomaly(
    aircraft_id: str,
    anomaly_id: str,
    db: Session = Depends(get_db),
):
    from app.intelligence.service import default_intelligence_service
    from app.intelligence.models import Anomaly

    resolved = default_intelligence_service.resolve_anomaly(db, aircraft_id=aircraft_id, anomaly_id=anomaly_id)
    return ApiResponse[Anomaly](
        data=resolved,
        message=f"Anomaly '{anomaly_id}' resolved",
    )


@router.get(
    "/{aircraft_id}/diagnosis",
    summary="Get Aircraft Subsystem Diagnosis",
    description="Retrieves synthesized root-cause diagnostic assessment with probable causes and supporting evidence.",
)
def get_aircraft_diagnosis(
    aircraft_id: str,
    db: Session = Depends(get_db),
):
    from app.intelligence.service import default_intelligence_service
    from app.intelligence.models import Diagnosis

    diagnosis = default_intelligence_service.get_latest_diagnosis(db, aircraft_id=aircraft_id)
    return ApiResponse[Diagnosis](
        data=diagnosis,
        message=f"Synthesized diagnosis for aircraft '{aircraft_id}' retrieved",
    )


@router.get(
    "/{aircraft_id}/maintenance-recommendations",
    summary="Get Aircraft Maintenance Recommendations",
    description="Retrieves advisory decision-support maintenance recommendations prioritized by severity and operational urgency.",
)
def get_aircraft_maintenance_recommendations(
    aircraft_id: str,
    db: Session = Depends(get_db),
):
    from app.intelligence.service import default_intelligence_service
    from app.intelligence.models import MaintenanceRecommendation

    recommendations = default_intelligence_service.get_maintenance_recommendations(db, aircraft_id=aircraft_id)
    return ApiResponse[List[MaintenanceRecommendation]](
        data=recommendations,
        message=f"Retrieved {len(recommendations)} maintenance recommendations for aircraft '{aircraft_id}'",
    )
