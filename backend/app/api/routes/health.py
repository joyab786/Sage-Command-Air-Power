"""
SageCommand Air Power System (Aero) — Health Check Endpoints.
Provides diagnostic health checks for application status, runtime environment, and database connectivity.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import Field
from app.contracts.base import AeroBaseModel, ApiResponse, utc_now_iso
from app.core.config import get_settings
from app.db.database import check_database_health

router = APIRouter(tags=["Health"])


class DatabaseHealthStatus(AeroBaseModel):
    """Database connectivity and configuration diagnostics."""

    status: str = Field(..., description="HEALTHY | DEGRADED | UNHEALTHY")
    connected: bool = Field(...)
    driver: Optional[str] = Field(default=None)
    wal_mode: Optional[bool] = Field(default=None)


class SystemHealthData(AeroBaseModel):
    """Authoritative system health status payload."""

    status: str = Field(default="HEALTHY", description="Overall system operational status")
    app_name: str = Field(...)
    version: str = Field(...)
    environment: str = Field(...)
    database: DatabaseHealthStatus = Field(...)
    timestamp: str = Field(default_factory=utc_now_iso)


@router.get(
    "/health",
    response_model=ApiResponse[SystemHealthData],
    summary="Application Health Diagnostics",
    description="Returns real-time health verification including database connectivity and SQLite WAL state.",
)
async def get_health() -> ApiResponse[SystemHealthData]:
    settings = get_settings()
    db_health_dict = check_database_health()

    db_health = DatabaseHealthStatus(
        status=db_health_dict.get("status", "UNHEALTHY"),
        connected=db_health_dict.get("connected", False),
        driver=db_health_dict.get("driver"),
        wal_mode=db_health_dict.get("wal_mode"),
    )

    overall_status = "HEALTHY" if db_health.connected else "DEGRADED"

    health_data = SystemHealthData(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENV,
        database=db_health,
        timestamp=utc_now_iso(),
    )

    return ApiResponse(
        success=True,
        data=health_data,
        message="System operational",
    )
