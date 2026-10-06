"""Unit tests for Aero base Pydantic contracts."""

from app.contracts.base import ApiResponse, ApiErrorResponse, ApiErrorDetail
from app.contracts.common import (
    PaginationParams,
    PaginatedResponse,
    ActorIdentity,
    ActorType,
    ResourceReference,
    DataMode,
    RiskLevel,
)


def test_api_success_response():
    resp = ApiResponse[dict](
        success=True,
        data={"key": "value"},
        message="Operation completed",
        correlation_id="corr_test_123",
    )
    dumped = resp.model_dump()
    assert dumped["success"] is True
    assert dumped["data"] == {"key": "value"}
    assert dumped["message"] == "Operation completed"
    assert dumped["correlation_id"] == "corr_test_123"
    assert "timestamp" in dumped


def test_api_error_response():
    error_detail = ApiErrorDetail(
        code="UNAUTHORIZED",
        message="Caller lacks operational clearance",
        field="clearance_level",
    )
    resp = ApiErrorResponse(
        success=False,
        error=error_detail,
        correlation_id="corr_err_999",
    )
    dumped = resp.model_dump()
    assert dumped["success"] is False
    assert dumped["error"]["code"] == "UNAUTHORIZED"
    assert dumped["error"]["field"] == "clearance_level"


def test_paginated_response():
    params = PaginationParams(page=2, page_size=10)
    items = [f"item_{i}" for i in range(10)]
    total = 25

    paginated = PaginatedResponse.create(items=items, total=total, params=params)
    assert paginated.page == 2
    assert paginated.page_size == 10
    assert paginated.total == 25
    assert paginated.total_pages == 3
    assert len(paginated.items) == 10


def test_actor_identity():
    actor = ActorIdentity(
        actor_id="pilot_007",
        actor_type=ActorType.USER,
        roles=["flight_lead", "operator"],
        tenant_id="wing_33",
        unit_id="squadron_11",
        clearance_level="SECRET",
    )
    assert actor.actor_id == "pilot_007"
    assert "flight_lead" in actor.roles
    assert actor.clearance_level == "SECRET"
