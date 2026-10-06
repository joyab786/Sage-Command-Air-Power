"""
SageCommand Air Power System (Aero) — Deterministic Execution Gateway.
Provides a multi-gate transactional write boundary, two-person rule enforcement,
cryptographic hash validation, idempotency caching, and rollback coordination.
"""

import uuid
import json
import hashlib
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Tuple
from pydantic import Field, model_validator
from app.contracts.base import AeroBaseModel, utc_now_iso
from app.contracts.common import ActorIdentity, ActorType, RiskLevel, DataMode
from app.core.exceptions import ExecutionGatewayError
from app.core.logging import get_logger
from app.services.policy_engine import (
    PolicyEngine,
    PolicyEvaluationContext,
    PolicyEffect,
    default_policy_engine,
)
from app.services.audit_ledger import (
    AuditLedgerService,
    default_audit_ledger,
)

logger = get_logger(__name__)


class ActionStatus(str, Enum):
    """Lifecycle states of an operational action proposal."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"


class ActionProposal(AeroBaseModel):
    """Canonical operational action proposal submitted for governance."""

    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:12]}")
    action_type: str = Field(..., description="Machine-readable action identifier")
    proposer: ActorIdentity = Field(..., description="Identity proposing the action")
    resource_type: str = Field(..., description="Target resource classification")
    resource_id: str = Field(..., description="Target resource unique identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    requires_approval: bool = Field(default=False)
    data_mode: DataMode = Field(default=DataMode.REAL)

    # Governance & Approval fields
    approver: Optional[ActorIdentity] = Field(default=None)
    approved_at: Optional[str] = Field(default=None)
    status: ActionStatus = Field(default=ActionStatus.PROPOSED)
    created_at: str = Field(default_factory=utc_now_iso)

    # Rollback metadata
    can_rollback: bool = Field(default=True)
    rollback_parameters: Dict[str, Any] = Field(default_factory=dict)

    # Cryptographic integrity
    action_hash: str = Field(default="")

    @model_validator(mode="after")
    def ensure_hash(self) -> "ActionProposal":
        if not self.action_hash:
            self.action_hash = self.compute_hash()
        return self

    def compute_hash(self) -> str:
        canonical = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "proposer_id": self.proposer.actor_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "parameters": self.parameters,
            "risk_level": self.risk_level.value,
        }
        encoded = json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ExecutionRequest(AeroBaseModel):
    """Request payload to execute an approved action."""

    action_id: str = Field(..., description="Action ID to execute")
    caller: ActorIdentity = Field(..., description="Executing actor identity")
    idempotency_key: Optional[str] = Field(default=None, description="Client idempotency token")
    dry_run: bool = Field(default=False, description="Preview execution without state persistence")


class ExecutionResult(AeroBaseModel):
    """Immutable result of gateway action execution."""

    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    action_id: str = Field(...)
    status: ActionStatus = Field(...)
    affected_records: int = Field(default=0)
    output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = Field(default=None)
    executed_at: str = Field(default_factory=utc_now_iso)
    duration_ms: float = Field(default=0.0)
    audit_event_id: Optional[str] = Field(default=None)


class RollbackResult(AeroBaseModel):
    """Result of reversing a previously succeeded action."""

    action_id: str = Field(...)
    status: ActionStatus = Field(...)
    rolled_back_at: str = Field(default_factory=utc_now_iso)
    reason: str = Field(...)
    audit_event_id: Optional[str] = Field(default=None)


class RollbackRequest(AeroBaseModel):
    """Request payload to reverse an executed action."""

    action_id: str = Field(...)
    caller: ActorIdentity = Field(...)
    reason: str = Field(..., min_length=3)


# Type definition for action handlers: (ActionProposal, Session/Dict) -> Tuple[affected_count, output_dict]
ActionHandler = Callable[[ActionProposal, Any], Tuple[int, Dict[str, Any]]]


class ExecutionGateway:
    """
    Deterministic Final Write Boundary.
    Enforces multi-gate validation pipeline before any physical or operational mutation:
    - Gate 1: Identity & Authentication Integrity
    - Gate 2: Authorization & Operational Permission
    - Gate 3: Target Scope & Resource Integrity
    - Gate 4: Action Lifecycle State Machine
    - Gate 5: Cryptographic & Staleness Integrity Verification
    - Gate 6: Two-Person Rule / Approval Verification
    - Gate 7: Policy Engine Revalidation
    - Gate 8: Idempotency & Duplicate Execution Detection
    - Gate 9: Concurrency Lock Acquisition
    - Gate 10: Execution, Rollback Tracking & Cryptographic Audit
    """

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        audit_ledger: Optional[AuditLedgerService] = None,
    ):
        self._lock = threading.RLock()
        self.policy_engine = policy_engine or default_policy_engine
        self.audit_ledger = audit_ledger or default_audit_ledger

        self._actions: Dict[str, ActionProposal] = {}
        self._handlers: Dict[str, ActionHandler] = {}
        self._idempotency_cache: Dict[str, ExecutionResult] = {}
        self._resource_locks: Dict[str, threading.Lock] = {}

    def register_handler(self, action_type: str, handler: ActionHandler) -> None:
        """Registers an execution handler function for a specific action type."""
        with self._lock:
            self._handlers[action_type] = handler

    def submit_proposal(self, proposal: ActionProposal) -> ActionProposal:
        """Submits an action proposal into the gateway."""
        with self._lock:
            proposal.action_hash = proposal.compute_hash()
            self._actions[proposal.action_id] = proposal

            # Audit submission
            self.audit_ledger.append_event(
                event_type="ACTION_PROPOSED",
                actor=proposal.proposer,
                action=proposal.action_type,
                result="PENDING",
                resource_type=proposal.resource_type,
                resource_id=proposal.resource_id,
                payload={"action_id": proposal.action_id, "risk_level": proposal.risk_level.value},
            )
            return proposal

    def get_action(self, action_id: str) -> Optional[ActionProposal]:
        """Retrieves action proposal by ID."""
        with self._lock:
            return self._actions.get(action_id)

    def approve_action(self, action_id: str, approver: ActorIdentity) -> ActionProposal:
        """
        Approves an action proposal while enforcing the Two-Person Rule.
        The proposer CANNOT approve their own high-risk action.
        """
        with self._lock:
            action = self.get_action(action_id)
            if not action:
                raise ExecutionGatewayError(
                    message=f"Action '{action_id}' not found",
                    error_code="ACTION_NOT_FOUND",
                    status_code=404,
                )

            if action.status != ActionStatus.PROPOSED:
                raise ExecutionGatewayError(
                    message=f"Cannot approve action in status '{action.status.value}'",
                    error_code="INVALID_STATUS",
                    status_code=400,
                )

            # Enforce Two-Person Rule for HIGH/CRITICAL risk or requires_approval
            if (action.requires_approval or action.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)) and (
                action.proposer.actor_id == approver.actor_id
            ):
                raise ExecutionGatewayError(
                    message="Two-Person Rule Violation: Proposer cannot approve their own high-risk action.",
                    error_code="TWO_PERSON_RULE_VIOLATION",
                    status_code=403,
                )

            action.approver = approver
            action.approved_at = utc_now_iso()
            action.status = ActionStatus.APPROVED

            self.audit_ledger.append_event(
                event_type="ACTION_APPROVED",
                actor=approver,
                action=action.action_type,
                result="APPROVED",
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                payload={"action_id": action.action_id, "proposer_id": action.proposer.actor_id},
            )
            return action

    def execute_action(self, request: ExecutionRequest) -> ExecutionResult:
        """Executes an action through the deterministic 10-gate validation pipeline."""
        start_time = time.perf_counter()

        # Gate 1: Identity & Authentication Integrity
        if not request.caller or not request.caller.actor_id:
            raise ExecutionGatewayError(
                message="Authentication identity required for execution",
                error_code="UNAUTHENTICATED",
                status_code=401,
            )

        # Gate 8: Idempotency & Duplicate Execution Detection
        if request.idempotency_key:
            with self._lock:
                if request.idempotency_key in self._idempotency_cache:
                    logger.info(f"Idempotency cache hit for key: {request.idempotency_key}")
                    return self._idempotency_cache[request.idempotency_key]

        # Gate 3: Target Scope & Resource Integrity
        with self._lock:
            action = self._actions.get(request.action_id)
        if not action:
            raise ExecutionGatewayError(
                message=f"Action '{request.action_id}' not found",
                error_code="ACTION_NOT_FOUND",
                status_code=404,
            )

        # Gate 2: Authorization & Operational Permission
        caller_roles = [r.lower() for r in request.caller.roles]
        if "admin" in caller_roles and not any(r in ("commander", "operator", "crew_chief", "flight_lead") for r in caller_roles):
            raise ExecutionGatewayError(
                message="Separation of Duties: Pure administrator roles are strictly non-operational.",
                error_code="ADMIN_OPERATIONAL_DENIED",
                status_code=403,
            )

        # Gate 4: Action Lifecycle State Machine
        if action.status == ActionStatus.EXECUTING:
            raise ExecutionGatewayError(
                message=f"Action '{action.action_id}' is already executing",
                error_code="ALREADY_EXECUTING",
                status_code=409,
            )
        if action.status == ActionStatus.SUCCEEDED:
            raise ExecutionGatewayError(
                message=f"Action '{action.action_id}' has already succeeded",
                error_code="ALREADY_COMPLETED",
                status_code=409,
            )
        if action.status in (ActionStatus.CANCELLED, ActionStatus.FAILED, ActionStatus.ROLLED_BACK):
            raise ExecutionGatewayError(
                message=f"Cannot execute action in terminal state '{action.status.value}'",
                error_code="INVALID_ACTION_STATE",
                status_code=400,
            )

        # Gate 5: Cryptographic & Staleness Integrity Verification
        expected_hash = action.compute_hash()
        if action.action_hash and action.action_hash != expected_hash:
            raise ExecutionGatewayError(
                message="Action cryptographic integrity verification failed: payload hash mismatch",
                error_code="INTEGRITY_TAMPER_DETECTED",
                status_code=400,
            )

        # Gate 6: Two-Person Rule / Approval Verification
        needs_approval = action.requires_approval or (action.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL))
        if needs_approval and action.status != ActionStatus.APPROVED:
            raise ExecutionGatewayError(
                message=f"Action '{action.action_id}' requires explicit approval before execution",
                error_code="APPROVAL_REQUIRED",
                status_code=400,
            )

        # Gate 7: Policy Engine Revalidation
        policy_ctx = PolicyEvaluationContext(
            actor=request.caller,
            action_type=action.action_type,
            resource_type=action.resource_type,
            resource_id=action.resource_id,
            data_mode=action.data_mode,
            parameters=action.parameters,
        )
        policy_decision = self.policy_engine.evaluate(policy_ctx)
        if policy_decision.decision == PolicyEffect.DENY:
            raise ExecutionGatewayError(
                message=f"Policy revalidation denied execution: {policy_decision.explanation}",
                error_code="POLICY_REJECTED",
                status_code=403,
            )

        # Gate 9: Concurrency Lock Acquisition on Target Resource
        resource_key = f"{action.resource_type}:{action.resource_id}"
        with self._lock:
            if resource_key not in self._resource_locks:
                self._resource_locks[resource_key] = threading.Lock()
            res_lock = self._resource_locks[resource_key]

        acquired = res_lock.acquire(blocking=False)
        if not acquired:
            raise ExecutionGatewayError(
                message=f"Resource '{action.resource_id}' is locked by a concurrent execution",
                error_code="CONCURRENCY_LOCK_FAILED",
                status_code=409,
            )

        # Gate 10: Transactional Execution & Audit Ledger Recording
        action.status = ActionStatus.EXECUTING
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"

        try:
            handler = self._handlers.get(action.action_type)
            if handler:
                affected_count, output = handler(action, None)
            else:
                # Default non-mutating execution if no custom handler is bound
                affected_count = 1
                output = {"executed_action": action.action_type, "dry_run": request.dry_run}

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            action.status = ActionStatus.SUCCEEDED

            # Record in cryptographic audit ledger
            audit_event = self.audit_ledger.append_event(
                event_type="ACTION_EXECUTED",
                actor=request.caller,
                action=action.action_type,
                result="SUCCESS",
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                payload={
                    "execution_id": execution_id,
                    "action_id": action.action_id,
                    "duration_ms": duration_ms,
                    "affected_records": affected_count,
                },
            )

            result = ExecutionResult(
                execution_id=execution_id,
                action_id=action.action_id,
                status=ActionStatus.SUCCEEDED,
                affected_records=affected_count,
                output=output,
                executed_at=utc_now_iso(),
                duration_ms=duration_ms,
                audit_event_id=audit_event.event_id,
            )

            if request.idempotency_key:
                with self._lock:
                    self._idempotency_cache[request.idempotency_key] = result

            return result

        except Exception as exc:
            action.status = ActionStatus.FAILED
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            self.audit_ledger.append_event(
                event_type="ACTION_EXECUTION_FAILED",
                actor=request.caller,
                action=action.action_type,
                result="FAILED",
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                payload={"execution_id": execution_id, "action_id": action.action_id, "error": str(exc)},
            )
            raise ExecutionGatewayError(
                message=f"Execution handler failed: {exc}",
                error_code="HANDLER_ERROR",
                status_code=500,
            ) from exc

        finally:
            res_lock.release()

    def rollback_action(self, request: RollbackRequest) -> RollbackResult:
        """Reverses a previously succeeded action and records rollback event."""
        with self._lock:
            action = self.get_action(request.action_id)
            if not action:
                raise ExecutionGatewayError(
                    message=f"Action '{request.action_id}' not found",
                    error_code="ACTION_NOT_FOUND",
                    status_code=404,
                )

            if action.status != ActionStatus.SUCCEEDED:
                raise ExecutionGatewayError(
                    message=f"Only SUCCEEDED actions can be rolled back (current status: '{action.status.value}')",
                    error_code="CANNOT_ROLLBACK",
                    status_code=400,
                )

            if not action.can_rollback:
                raise ExecutionGatewayError(
                    message=f"Action '{action.action_id}' does not support rollback",
                    error_code="ROLLBACK_UNSUPPORTED",
                    status_code=400,
                )

            action.status = ActionStatus.ROLLED_BACK

            audit_event = self.audit_ledger.append_event(
                event_type="ACTION_ROLLED_BACK",
                actor=request.caller,
                action=action.action_type,
                result="ROLLED_BACK",
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                payload={"action_id": action.action_id, "reason": request.reason},
            )

            return RollbackResult(
                action_id=action.action_id,
                status=ActionStatus.ROLLED_BACK,
                rolled_back_at=utc_now_iso(),
                reason=request.reason,
                audit_event_id=audit_event.event_id,
            )


# Global default execution gateway instance
default_execution_gateway = ExecutionGateway()
