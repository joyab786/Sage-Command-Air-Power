"""
SageCommand Air Power System (Aero) — Deterministic Policy Engine.
Provides domain-neutral rule evaluation, anti-injection verification,
and strict deterministic precedence resolution (DENY > REQUIRE_APPROVAL > HOLD > ALLOW).
"""

import re
import uuid
import hashlib
import json
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import Field, field_validator, model_validator
from app.contracts.base import AeroBaseModel, utc_now_iso
from app.contracts.common import ActorIdentity, DataMode

# Pattern to detect arbitrary executable code injection in condition definitions
PROHIBITED_CODE_PATTERNS = re.compile(
    r"(?i)\b(eval|exec|import|__import__|compile|system|popen|subprocess|globals|locals|getattr|setattr|delattr)\b"
)


class PolicyEffect(str, Enum):
    """Deterministic policy evaluation outcome."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    HOLD = "HOLD"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicyLifecycle(str, Enum):
    """Lifecycle status of a policy definition."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DRAFT = "DRAFT"


class PolicyOperator(str, Enum):
    """Supported deterministic comparison operators. Zero arbitrary string execution."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"


class ApprovalRequirement(AeroBaseModel):
    """Structured human-in-the-loop governance requirement."""

    required: bool = Field(default=True, description="Whether approval is required")
    required_role: str = Field(default="commander", description="RBAC role required for authorization")
    minimum_approvers: int = Field(default=1, ge=1, description="Minimum number of approving identities")
    reason_code: str = Field(default="POLICY_APPROVAL_REQUIRED", description="Machine-readable approval code")
    reason: str = Field(..., description="Deterministic human-readable approval justification")
    policy_id: Optional[str] = Field(default=None, description="Policy triggering approval requirement")


class PolicyCondition(AeroBaseModel):
    """Deterministic condition evaluating an attribute against an expected value."""

    field: str = Field(..., description="Target attribute name from evaluation context or parameters")
    operator: PolicyOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Expected value or set of values")

    @field_validator("value")
    @classmethod
    def assert_no_executable_code(cls, v: Any) -> Any:
        if isinstance(v, str) and PROHIBITED_CODE_PATTERNS.search(v):
            raise ValueError(f"Security Policy Violation: Prohibited code pattern detected in value '{v}'.")
        return v


class PolicyRule(AeroBaseModel):
    """Individual rule within a policy. All conditions must match (AND)."""

    rule_id: str = Field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:8]}")
    name: str = Field(..., min_length=2, max_length=128)
    conditions: List[PolicyCondition] = Field(default_factory=list, description="All conditions must match (AND)")
    effect: PolicyEffect = Field(..., description="ALLOW | DENY | HOLD | REQUIRE_APPROVAL")
    approval_requirement: Optional[ApprovalRequirement] = Field(default=None)
    reason_code: str = Field(default="POLICY_RULE_MATCHED")
    explanation: str = Field(..., description="Deterministic human explanation for why rule fired")


class Policy(AeroBaseModel):
    """Canonical versioned policy definition."""

    policy_id: str = Field(..., min_length=3, max_length=64)
    version: str = Field(default="1.0")
    name: str = Field(..., min_length=3, max_length=128)
    description: str = Field(..., max_length=512)
    status: PolicyLifecycle = Field(default=PolicyLifecycle.ACTIVE)
    priority: int = Field(default=50, ge=1, le=100, description="Evaluation priority (1-100, higher evaluated first)")
    scope: Dict[str, Any] = Field(default_factory=dict, description="Scope filters e.g. tenant_id, unit_id")
    rules: List[PolicyRule] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    policy_hash: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def ensure_hash(self) -> "Policy":
        if not self.policy_hash:
            self.policy_hash = self.compute_hash()
        return self

    def compute_hash(self) -> str:
        """Calculates canonical SHA-256 fingerprint over core policy fields."""
        canonical_dict = {
            "policy_id": self.policy_id,
            "version": self.version,
            "priority": self.priority,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "effect": r.effect.value,
                    "conditions": [c.model_dump() for c in r.conditions],
                }
                for r in self.rules
            ],
        }
        encoded = json.dumps(canonical_dict, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class PolicyEvaluationContext(AeroBaseModel):
    """Authoritative input parameters for policy evaluation."""

    actor: ActorIdentity = Field(..., description="Caller identity and assigned roles")
    action_type: str = Field(..., description="Operational action identifier")
    resource_type: str = Field(..., description="Target resource type")
    resource_id: str = Field(..., description="Target resource identifier")
    data_mode: DataMode = Field(default=DataMode.REAL)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters and metadata")


class PolicyDecision(AeroBaseModel):
    """Immutable result of a deterministic policy evaluation."""

    decision: PolicyEffect = Field(..., description="Authoritative outcome: DENY | REQUIRE_APPROVAL | HOLD | ALLOW")
    reason_codes: List[str] = Field(default_factory=list)
    explanation: str = Field(...)
    requires_approval: bool = Field(default=False)
    approval_requirement: Optional[ApprovalRequirement] = Field(default=None)
    matched_rules: List[Dict[str, Any]] = Field(default_factory=list)
    decisive_policy_id: Optional[str] = Field(default=None)
    evaluated_at: str = Field(default_factory=utc_now_iso)
    decision_hash: str = Field(default="")

    def compute_hash(self) -> str:
        canonical = {
            "decision": self.decision.value,
            "reason_codes": self.reason_codes,
            "requires_approval": self.requires_approval,
            "decisive_policy_id": self.decisive_policy_id,
            "evaluated_at": self.evaluated_at,
        }
        return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode("utf-8")).hexdigest()


class PolicyConditionEvaluator:
    """Evaluates individual conditions against context attributes without code execution."""

    @staticmethod
    def extract_value(condition_field: str, context: PolicyEvaluationContext) -> Any:
        field_lower = condition_field.lower()

        # Check top-level context fields
        if field_lower == "action_type":
            return context.action_type
        if field_lower == "resource_type":
            return context.resource_type
        if field_lower == "resource_id":
            return context.resource_id
        if field_lower == "data_mode":
            return context.data_mode.value
        if field_lower in ("actor_id", "user_id"):
            return context.actor.actor_id
        if field_lower == "roles":
            return context.actor.roles
        if field_lower == "tenant_id":
            return context.actor.tenant_id
        if field_lower == "unit_id":
            return context.actor.unit_id

        # Fallback to action parameters dictionary
        return context.parameters.get(condition_field)

    @classmethod
    def evaluate_condition(cls, condition: PolicyCondition, context: PolicyEvaluationContext) -> bool:
        actual = cls.extract_value(condition.field, context)
        expected = condition.value
        op = condition.operator

        if op == PolicyOperator.EXISTS:
            return actual is not None
        if op == PolicyOperator.NOT_EXISTS:
            return actual is None

        if actual is None:
            return False

        if op == PolicyOperator.EQUALS:
            return actual == expected
        elif op == PolicyOperator.NOT_EQUALS:
            return actual != expected
        elif op == PolicyOperator.IN:
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return str(actual) in str(expected)
        elif op == PolicyOperator.NOT_IN:
            if isinstance(expected, (list, tuple, set)):
                return actual not in expected
            return str(actual) not in str(expected)
        elif op == PolicyOperator.GREATER_THAN:
            try:
                return float(actual) > float(expected)
            except (ValueError, TypeError):
                return False
        elif op == PolicyOperator.GREATER_THAN_OR_EQUAL:
            try:
                return float(actual) >= float(expected)
            except (ValueError, TypeError):
                return False
        elif op == PolicyOperator.LESS_THAN:
            try:
                return float(actual) < float(expected)
            except (ValueError, TypeError):
                return False
        elif op == PolicyOperator.LESS_THAN_OR_EQUAL:
            try:
                return float(actual) <= float(expected)
            except (ValueError, TypeError):
                return False
        elif op == PolicyOperator.CONTAINS:
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            return str(expected) in str(actual)
        elif op == PolicyOperator.NOT_CONTAINS:
            if isinstance(actual, (list, tuple, set)):
                return expected not in actual
            return str(expected) not in str(actual)

        return False


class PolicyEngine:
    """
    Deterministic Policy Enforcement Engine.
    Enforces strict precedence: DENY > REQUIRE_APPROVAL > HOLD > ALLOW.
    Default outcome when no rules match is fail-closed: HOLD.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._policies: Dict[str, Policy] = {}

    def register_policy(self, policy: Policy) -> None:
        """Registers or replaces an active policy definition."""
        with self._lock:
            policy.policy_hash = policy.compute_hash()
            self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Retrieves a policy by ID."""
        with self._lock:
            return self._policies.get(policy_id)

    def remove_policy(self, policy_id: str) -> bool:
        """Removes a policy from the active registry."""
        with self._lock:
            return self._policies.pop(policy_id, None) is not None

    def list_policies(self, active_only: bool = True) -> List[Policy]:
        """Returns sorted list of policies (highest priority first)."""
        with self._lock:
            policies = list(self._policies.values())
            if active_only:
                policies = [p for p in policies if p.status == PolicyLifecycle.ACTIVE]
            policies.sort(key=lambda p: p.priority, reverse=True)
            return policies

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyDecision:
        """
        Authoritatively evaluates an action against active policies.
        Strict precedence: DENY > REQUIRE_APPROVAL > HOLD > ALLOW.
        Default outcome: HOLD (fail-closed).
        """
        blocking_rules: List[Dict[str, Any]] = []
        approval_rules: List[Dict[str, Any]] = []
        hold_rules: List[Dict[str, Any]] = []
        allow_rules: List[Dict[str, Any]] = []
        all_matched_rules: List[Dict[str, Any]] = []

        policies = self.list_policies(active_only=True)

        for policy in policies:
            # Check scope filtering if configured in policy
            if policy.scope:
                tenant_match = policy.scope.get("tenant_id")
                if tenant_match and tenant_match != context.actor.tenant_id:
                    continue
                unit_match = policy.scope.get("unit_id")
                if unit_match and unit_match != context.actor.unit_id:
                    continue

            for rule in policy.rules:
                # All conditions within a rule must match (AND logic)
                rule_matches = True
                for condition in rule.conditions:
                    if not PolicyConditionEvaluator.evaluate_condition(condition, context):
                        rule_matches = False
                        break

                if rule_matches:
                    rule_info = {
                        "policy_id": policy.policy_id,
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "effect": rule.effect.value,
                        "reason_code": rule.reason_code,
                        "explanation": rule.explanation,
                        "approval_requirement": rule.approval_requirement.model_dump()
                        if rule.approval_requirement
                        else None,
                    }
                    all_matched_rules.append(rule_info)

                    if rule.effect == PolicyEffect.DENY:
                        blocking_rules.append(rule_info)
                    elif rule.effect == PolicyEffect.REQUIRE_APPROVAL:
                        approval_rules.append(rule_info)
                    elif rule.effect == PolicyEffect.HOLD:
                        hold_rules.append(rule_info)
                    elif rule.effect == PolicyEffect.ALLOW:
                        allow_rules.append(rule_info)

        # Apply deterministic precedence hierarchy:
        # DENY > REQUIRE_APPROVAL > HOLD > ALLOW
        final_decision: PolicyEffect
        decisive_reason_codes: List[str] = []
        decisive_explanation: str
        effective_approval_req: Optional[ApprovalRequirement] = None
        decisive_policy_id: Optional[str] = None

        if blocking_rules:
            final_decision = PolicyEffect.DENY
            decisive_reason_codes = [r["reason_code"] for r in blocking_rules]
            decisive_explanation = f"Action DENIED by policy rule: {blocking_rules[0]['explanation']}"
            decisive_policy_id = blocking_rules[0]["policy_id"]

        elif approval_rules:
            final_decision = PolicyEffect.REQUIRE_APPROVAL
            decisive_reason_codes = [r["reason_code"] for r in approval_rules]
            decisive_explanation = (
                f"Action requires approval: {approval_rules[0]['explanation']}"
            )
            raw_req = approval_rules[0]["approval_requirement"]
            effective_approval_req = ApprovalRequirement(**raw_req) if raw_req else None
            decisive_policy_id = approval_rules[0]["policy_id"]

        elif hold_rules:
            final_decision = PolicyEffect.HOLD
            decisive_reason_codes = [r["reason_code"] for r in hold_rules]
            decisive_explanation = (
                f"Action placed on HOLD by policy: {hold_rules[0]['explanation']}"
            )
            decisive_policy_id = hold_rules[0]["policy_id"]

        elif allow_rules:
            final_decision = PolicyEffect.ALLOW
            decisive_reason_codes = [r["reason_code"] for r in allow_rules]
            decisive_explanation = (
                f"Action permitted by policy: {allow_rules[0]['explanation']}"
            )
            decisive_policy_id = allow_rules[0]["policy_id"]

        else:
            # Default fail-closed policy
            final_decision = PolicyEffect.HOLD
            decisive_reason_codes = ["NO_MATCHING_POLICY_FOUND"]
            decisive_explanation = (
                "No matching active policy permitted this action. System default: Fail-Closed HOLD."
            )

        decision = PolicyDecision(
            decision=final_decision,
            reason_codes=decisive_reason_codes,
            explanation=decisive_explanation,
            requires_approval=(final_decision == PolicyEffect.REQUIRE_APPROVAL),
            approval_requirement=effective_approval_req,
            matched_rules=all_matched_rules,
            decisive_policy_id=decisive_policy_id,
            evaluated_at=utc_now_iso(),
        )
        decision.decision_hash = decision.compute_hash()
        return decision


# Global default policy engine instance
default_policy_engine = PolicyEngine()
