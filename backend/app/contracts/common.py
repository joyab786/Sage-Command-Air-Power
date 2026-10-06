"""
SageCommand Air Power System (Aero) — Common Cross-Cutting Contracts.
Provides pagination, operational modes, risk levels, and actor identity contracts.
"""

from enum import Enum
from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import Field
from app.contracts.base import AeroBaseModel, utc_now_iso

T = TypeVar("T")


class DataMode(str, Enum):
    """Operational data isolation mode."""

    REAL = "REAL"
    SIMULATION = "SIMULATION"
    HYBRID = "HYBRID"


class RiskLevel(str, Enum):
    """Normalized operational risk severity classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActorType(str, Enum):
    """Classification of an entity performing an action or generating an event."""

    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    SCHEDULER = "SCHEDULER"
    SIMULATOR = "SIMULATOR"
    ADMIN = "ADMIN"
    UNKNOWN = "UNKNOWN"


class ActorIdentity(AeroBaseModel):
    """Authoritative representation of an authenticated actor."""

    actor_id: str = Field(..., description="Unique caller or agent identifier")
    actor_type: ActorType = Field(default=ActorType.USER, description="Actor classification")
    roles: List[str] = Field(default_factory=list, description="Assigned RBAC roles")
    acting_user_id: Optional[str] = Field(default=None, description="Human identity when an agent acts on delegation")
    tenant_id: str = Field(default="tenant_default", description="Authoritative tenant partition")
    unit_id: Optional[str] = Field(default=None, description="Operational unit or squadron identifier")
    clearance_level: Optional[str] = Field(default=None, description="Security clearance level")


class ResourceReference(AeroBaseModel):
    """Generic reference to a system resource."""

    resource_type: str = Field(..., description="Canonical resource category")
    resource_id: str = Field(..., description="Unique resource identifier")
    unit_id: Optional[str] = Field(default=None, description="Operational unit context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary resource metadata")


class PaginationParams(AeroBaseModel):
    """Query parameters for paginated API collections."""

    page: int = Field(default=1, ge=1, description="1-indexed page number")
    page_size: int = Field(default=50, ge=1, le=500, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(AeroBaseModel, Generic[T]):
    """Standard pagination wrapper for collection responses."""

    items: List[T] = Field(default_factory=list, description="Page item records")
    total: int = Field(..., ge=0, description="Total matching items across all pages")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Page capacity")
    total_pages: int = Field(..., ge=0, description="Total computed pages")

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> "PaginatedResponse[T]":
        total_pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )
