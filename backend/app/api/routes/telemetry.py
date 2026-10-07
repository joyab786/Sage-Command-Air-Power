"""
SageCommand Air Power System (Aero) — Telemetry API Routes.
Exposes endpoints for high-throughput single and batch telemetry ingestion,
recent signal queries, and synthetic demonstration flight generation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.contracts.base import ApiResponse
from app.db.database import get_db
from app.telemetry.models import (
    TelemetryInput,
    NormalizedTelemetry,
    TelemetryIngestResult,
    BatchIngestRequest,
    BatchIngestResult,
    DemoGenerateRequest,
)
from app.telemetry.service import default_telemetry_service

router = APIRouter(prefix="/telemetry", tags=["Telemetry Data Fabric"])


@router.post(
    "",
    response_model=ApiResponse[TelemetryIngestResult],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Telemetry Frame",
    description="Ingests, validates, normalizes to SI units, checks envelope limits, buffers, and persists a flight observation.",
)
def ingest_telemetry(
    payload: TelemetryInput,
    db: Session = Depends(get_db),
) -> ApiResponse[TelemetryIngestResult]:
    result = default_telemetry_service.ingest_observation(db, payload, persist=True)
    msg = (
        f"Telemetry accepted for aircraft '{result.aircraft_id}'"
        if result.accepted
        else f"Telemetry rejected for aircraft '{result.aircraft_id}': {', '.join(result.quality.reasons)}"
    )
    return ApiResponse(
        data=result,
        message=msg,
    )


@router.post(
    "/batch",
    response_model=ApiResponse[BatchIngestResult],
    status_code=status.HTTP_201_CREATED,
    summary="Batch Ingest Telemetry Frames",
    description="Ingests and processes a batch of multiple incoming telemetry observations.",
)
def ingest_batch(
    payload: BatchIngestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[BatchIngestResult]:
    result = default_telemetry_service.ingest_batch(db, payload, persist=True)
    return ApiResponse(
        data=result,
        message=f"Batch processed: {result.total_accepted} accepted, {result.total_rejected} rejected out of {result.total_received}",
    )


@router.get(
    "/recent",
    response_model=ApiResponse[List[NormalizedTelemetry]],
    summary="Get Recent Telemetry",
    description="Retrieves the most recent telemetry frames from the in-memory buffer and database.",
)
def get_recent_telemetry(
    limit: int = Query(default=50, ge=1, le=500, description="Max observations to return"),
    aircraft_id: Optional[str] = Query(default=None, description="Optional aircraft filter"),
    db: Session = Depends(get_db),
) -> ApiResponse[List[NormalizedTelemetry]]:
    recent = default_telemetry_service.get_recent(db, limit=limit, aircraft_id=aircraft_id)
    return ApiResponse(
        data=recent,
        message=f"Retrieved {len(recent)} recent telemetry frames",
    )


@router.post(
    "/demo/generate",
    response_model=ApiResponse[BatchIngestResult],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Synthetic Demonstration Telemetry",
    description="Deterministically generates and ingests synthetic flight telemetry for demonstration scenarios (e.g. NORMAL_CRUISE, HIGH_G_TURN, THERMAL_SPIKE).",
)
def generate_demo_telemetry(
    payload: DemoGenerateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[BatchIngestResult]:
    result = default_telemetry_service.generate_and_ingest_demo(db, payload)
    return ApiResponse(
        data=result,
        message=f"Generated and ingested {result.total_accepted} synthetic demo frames for profile '{payload.profile}'",
    )
