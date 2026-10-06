"""
SageCommand Air Power System (Aero) — Base Pydantic Contracts.
Provides standard API response envelopes, error structures, and base model configurations.
"""

from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def utc_now_iso() -> str:
    """Generates standard UTC ISO-8601 timestamp string ending in 'Z'."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AeroBaseModel(BaseModel):
    """Canonical base model for all Aero Pydantic contracts."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        validate_assignment=True,
    )


class ApiErrorDetail(AeroBaseModel):
    """Structured detail for individual error diagnostics."""

    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable explanation of error")
    field: Optional[str] = Field(default=None, description="Field path if error is field-specific")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Supplementary diagnostic metadata")


class ApiErrorResponse(AeroBaseModel):
    """Standardized top-level API error response envelope."""

    success: bool = Field(default=False, description="Always False for error responses")
    error: ApiErrorDetail = Field(..., description="Primary error detail")
    details: Optional[List[ApiErrorDetail]] = Field(default=None, description="Additional error items if multiple")
    correlation_id: Optional[str] = Field(default=None, description="Correlation identifier for tracing")
    timestamp: str = Field(default_factory=utc_now_iso, description="UTC ISO timestamp of error generation")


class ApiResponse(AeroBaseModel, Generic[T]):
    """Standardized top-level API success response envelope."""

    success: bool = Field(default=True, description="Indicates successful execution")
    data: Optional[T] = Field(default=None, description="Typed response payload")
    message: Optional[str] = Field(default=None, description="Optional informational or status message")
    correlation_id: Optional[str] = Field(default=None, description="Correlation identifier for tracing")
    timestamp: str = Field(default_factory=utc_now_iso, description="UTC ISO timestamp of response generation")
