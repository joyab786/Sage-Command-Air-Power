"""
SageCommand Air Power System (Aero) — Application Entry Point.
Initializes FastAPI, mounts lifespan handlers, establishes structured logging,
configures CORS middleware, binds correlation tracing, and registers API routers.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import Settings, get_settings
from app.core.logging import (
    setup_logging,
    get_logger,
    bind_correlation_id,
    get_correlation_id,
)
from app.core.exceptions import AeroException
from app.contracts.base import ApiErrorResponse, ApiErrorDetail, utc_now_iso
from app.db.database import init_db, close_db
from app.api.routes.health import router as health_router
from app.api.routes.aircraft import router as aircraft_router
from app.api.routes.missions import router as missions_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.ato import ato_router, proposals_router

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Clean asynchronous application startup and shutdown lifecycle management."""
    settings = getattr(app.state, "settings", None) or get_settings()

    # 1. Initialize structured logging
    setup_logging(settings)
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION}",
        extra={"env": settings.ENV, "debug": settings.DEBUG},
    )

    # 2. Initialize database connection pool and SQLite WAL mode
    try:
        init_db(settings=settings)
    except Exception as exc:
        logger.critical(f"Fatal error during database startup: {exc}", exc_info=True)
        raise

    yield

    # 3. Clean application shutdown
    logger.info("Initiating graceful shutdown of Aero services...")
    close_db()
    logger.info("Aero application shutdown complete")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Factory function to build and configure the Aero FastAPI application."""
    resolved_settings = settings or get_settings()

    app = FastAPI(
        title=resolved_settings.APP_NAME,
        version=resolved_settings.APP_VERSION,
        description="Air Power Command & Autonomous Decision Governance Platform",
        docs_url="/docs" if not resolved_settings.is_production else None,
        redoc_url="/redoc" if not resolved_settings.is_production else None,
        openapi_url="/openapi.json" if not resolved_settings.is_production else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    # -------------------------------------------------------------------------
    # Middleware: Request Correlation Tracing
    # -------------------------------------------------------------------------
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or f"corr_{uuid.uuid4().hex[:12]}"
        bind_correlation_id(corr_id)

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000.0

        response.headers["X-Correlation-ID"] = corr_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        return response

    # -------------------------------------------------------------------------
    # Middleware: CORS Allowlist
    # -------------------------------------------------------------------------
    origins = (
        resolved_settings.CORS_ORIGINS
        if isinstance(resolved_settings.CORS_ORIGINS, list)
        else ["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Exception Handlers: Standardized Error Envelopes
    # -------------------------------------------------------------------------
    @app.exception_handler(AeroException)
    async def aero_exception_handler(request: Request, exc: AeroException):
        corr_id = get_correlation_id()
        logger.warning(
            f"Aero business exception [{exc.error_code}]: {exc.message}",
            extra={"error_code": exc.error_code, "status_code": exc.status_code, "details": exc.details},
        )
        error_resp = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                code=exc.error_code,
                message=exc.message,
                details=exc.details,
            ),
            correlation_id=corr_id,
            timestamp=utc_now_iso(),
        )
        return JSONResponse(status_code=exc.status_code, content=error_resp.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        corr_id = get_correlation_id()
        error_details = []
        for error in exc.errors():
            loc = " -> ".join(str(p) for p in error.get("loc", []))
            error_details.append(
                ApiErrorDetail(
                    code="REQUEST_VALIDATION_ERROR",
                    message=error.get("msg", "Validation error"),
                    field=loc,
                )
            )

        error_resp = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                code="VALIDATION_FAILED",
                message="Request payload failed contract schema validation",
            ),
            details=error_details,
            correlation_id=corr_id,
            timestamp=utc_now_iso(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_resp.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        corr_id = get_correlation_id()
        logger.error(f"Unhandled system exception: {exc}", exc_info=True)
        error_resp = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected system error occurred",
            ),
            correlation_id=corr_id,
            timestamp=utc_now_iso(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_resp.model_dump(),
        )

    # -------------------------------------------------------------------------
    # Route Registration
    # -------------------------------------------------------------------------
    # Direct /health root endpoint (required by orchestrators/probes)
    app.include_router(health_router, prefix="")

    # Versioned API routes under /api/v1
    app.include_router(health_router, prefix=resolved_settings.API_PREFIX)
    app.include_router(aircraft_router, prefix=resolved_settings.API_PREFIX)
    app.include_router(missions_router, prefix=resolved_settings.API_PREFIX)
    app.include_router(telemetry_router, prefix=resolved_settings.API_PREFIX)
    app.include_router(ato_router, prefix=resolved_settings.API_PREFIX)
    app.include_router(proposals_router, prefix=resolved_settings.API_PREFIX)

    @app.get("/", tags=["Root"])
    async def get_root():
        return {
            "app": resolved_settings.APP_NAME,
            "version": resolved_settings.APP_VERSION,
            "status": "OPERATIONAL",
            "docs": "/docs" if not resolved_settings.is_production else "DISABLED",
        }

    return app


# Authoritative FastAPI ASGI app entrypoint
app = create_app()
