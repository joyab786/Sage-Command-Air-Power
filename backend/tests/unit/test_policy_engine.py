"""Unit tests for Aero deterministic Policy Engine and precedence hierarchy."""

import pytest
from app.contracts.common import ActorIdentity, ActorType, DataMode
from app.services.policy_engine import (
    PolicyEngine,
    Policy,
    PolicyRule,
    PolicyCondition,
    PolicyEffect,
    PolicyOperator,
    ApprovalRequirement,
    PolicyEvaluationContext,
)


@pytest.fixture
def policy_engine() -> PolicyEngine:
    return PolicyEngine()


@pytest.fixture
def base_context() -> PolicyEvaluationContext:
    actor = ActorIdentity(
        actor_id="operator_alpha",
        actor_type=ActorType.USER,
        roles=["operator"],
        tenant_id="wing_1",
        unit_id="sq_101",
    )
    return PolicyEvaluationContext(
        actor=actor,
        action_type="TEST_ACTION",
        resource_type="SYSTEM",
        resource_id="SYS_01",
        data_mode=DataMode.REAL,
        parameters={"impact_level": 5, "environment": "test"},
    )


def test_anti_code_injection_in_policy():
    """Policy conditions must strictly forbid executable Python injection."""
    with pytest.raises(ValueError, match="Prohibited code pattern"):
        PolicyCondition(
            field="action_type",
            operator=PolicyOperator.EQUALS,
            value="__import__('os').system('echo pwned')",
        )


def test_policy_precedence_hierarchy(policy_engine: PolicyEngine, base_context: PolicyEvaluationContext):
    """
    Validates strict deterministic precedence:
    DENY > REQUIRE_APPROVAL > HOLD > ALLOW
    """
    # 1. Register an ALLOW policy (Priority 40)
    policy_engine.register_policy(
        Policy(
            policy_id="POL-ALLOW",
            name="Allow Routine Test Actions",
            description="Allows test action",
            priority=40,
            rules=[
                PolicyRule(
                    name="Rule Allow",
                    conditions=[
                        PolicyCondition(
                            field="action_type",
                            operator=PolicyOperator.EQUALS,
                            value="TEST_ACTION",
                        )
                    ],
                    effect=PolicyEffect.ALLOW,
                    explanation="Action is routine.",
                )
            ],
        )
    )

    # With only ALLOW rule active -> outcome should be ALLOW
    decision = policy_engine.evaluate(base_context)
    assert decision.decision == PolicyEffect.ALLOW

    # 2. Register a HOLD policy (Priority 50)
    policy_engine.register_policy(
        Policy(
            policy_id="POL-HOLD",
            name="Hold Policy",
            description="Holds under test environment",
            priority=50,
            rules=[
                PolicyRule(
                    name="Rule Hold",
                    conditions=[
                        PolicyCondition(
                            field="environment",
                            operator=PolicyOperator.EQUALS,
                            value="test",
                        )
                    ],
                    effect=PolicyEffect.HOLD,
                    explanation="Action held during test environment check.",
                )
            ],
        )
    )

    # HOLD beats ALLOW
    decision = policy_engine.evaluate(base_context)
    assert decision.decision == PolicyEffect.HOLD

    # 3. Register a REQUIRE_APPROVAL policy (Priority 60)
    policy_engine.register_policy(
        Policy(
            policy_id="POL-APPROVAL",
            name="Approval Policy",
            description="Requires commander authorization",
            priority=60,
            rules=[
                PolicyRule(
                    name="Rule Approval",
                    conditions=[
                        PolicyCondition(
                            field="impact_level",
                            operator=PolicyOperator.GREATER_THAN_OR_EQUAL,
                            value=5,
                        )
                    ],
                    effect=PolicyEffect.REQUIRE_APPROVAL,
                    approval_requirement=ApprovalRequirement(
                        required=True,
                        required_role="commander",
                        reason="Impact level requires commander authorization",
                    ),
                    explanation="High impact requires human approval.",
                )
            ],
        )
    )

    # REQUIRE_APPROVAL beats HOLD and ALLOW
    decision = policy_engine.evaluate(base_context)
    assert decision.decision == PolicyEffect.REQUIRE_APPROVAL
    assert decision.requires_approval is True
    assert decision.approval_requirement is not None

    # 4. Register a DENY policy (Priority 70)
    policy_engine.register_policy(
        Policy(
            policy_id="POL-DENY",
            name="Denial Policy",
            description="Denies all actions on SYS_01",
            priority=70,
            rules=[
                PolicyRule(
                    name="Rule Deny",
                    conditions=[
                        PolicyCondition(
                            field="resource_id",
                            operator=PolicyOperator.EQUALS,
                            value="SYS_01",
                        )
                    ],
                    effect=PolicyEffect.DENY,
                    explanation="Target resource is frozen.",
                )
            ],
        )
    )

    # DENY beats REQUIRE_APPROVAL, HOLD, and ALLOW
    decision = policy_engine.evaluate(base_context)
    assert decision.decision == PolicyEffect.DENY
    assert "DENIED" in decision.explanation


def test_policy_default_fail_closed(policy_engine: PolicyEngine):
    """When no active policy rules match, system must default to fail-closed HOLD."""
    actor = ActorIdentity(actor_id="stranger", roles=["visitor"])
    unknown_context = PolicyEvaluationContext(
        actor=actor,
        action_type="UNCONFIGURED_ACTION",
        resource_type="UNKNOWN",
        resource_id="UNK_01",
    )

    decision = policy_engine.evaluate(unknown_context)
    assert decision.decision == PolicyEffect.HOLD
    assert "Fail-Closed" in decision.explanation
