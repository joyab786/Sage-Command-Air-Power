"""Unit tests for Aero Deterministic Execution Gateway and governance gates."""

import pytest
from app.contracts.common import ActorIdentity, ActorType, RiskLevel, DataMode
from app.services.execution_gateway import (
    ExecutionGateway,
    ActionProposal,
    ActionStatus,
    ExecutionRequest,
    RollbackRequest,
)
from app.services.policy_engine import PolicyEngine, Policy, PolicyRule, PolicyEffect
from app.services.audit_ledger import AuditLedgerService
from app.core.exceptions import ExecutionGatewayError


@pytest.fixture
def gateway() -> ExecutionGateway:
    pol_engine = PolicyEngine()
    audit_ledger = AuditLedgerService()
    # Permit test actions by default in policy engine
    pol_engine.register_policy(
        Policy(
            policy_id="POL-TEST-ALLOW",
            name="Allow Test Execution",
            description="Default test allow",
            priority=10,
            rules=[
                PolicyRule(
                    name="Rule Test Allow",
                    effect=PolicyEffect.ALLOW,
                    explanation="Permit test execution",
                )
            ],
        )
    )
    return ExecutionGateway(policy_engine=pol_engine, audit_ledger=audit_ledger)


@pytest.fixture
def proposer() -> ActorIdentity:
    return ActorIdentity(
        actor_id="officer_alice",
        actor_type=ActorType.USER,
        roles=["flight_lead"],
    )


@pytest.fixture
def commander() -> ActorIdentity:
    return ActorIdentity(
        actor_id="commander_bob",
        actor_type=ActorType.USER,
        roles=["commander"],
    )


def test_execution_low_risk_action(gateway: ExecutionGateway, proposer: ActorIdentity):
    """Low-risk action proceeds through gateway without approval requirement."""
    proposal = ActionProposal(
        action_type="ROUTINE_DIAGNOSTIC",
        proposer=proposer,
        resource_type="RADAR",
        resource_id="AN_APG_81",
        risk_level=RiskLevel.LOW,
        requires_approval=False,
    )
    gateway.submit_proposal(proposal)

    req = ExecutionRequest(action_id=proposal.action_id, caller=proposer)
    result = gateway.execute_action(req)

    assert result.status == ActionStatus.SUCCEEDED
    assert result.affected_records == 1
    assert result.audit_event_id is not None

    # Verify action state transitioned to SUCCEEDED
    updated = gateway.get_action(proposal.action_id)
    assert updated.status == ActionStatus.SUCCEEDED


def test_two_person_rule_enforcement(gateway: ExecutionGateway, proposer: ActorIdentity, commander: ActorIdentity):
    """Proposer cannot approve their own high-risk action (Two-Person Rule)."""
    high_risk_proposal = ActionProposal(
        action_type="HIGH_RISK_COMMAND",
        proposer=proposer,
        resource_type="AVIONICS",
        resource_id="MISSION_COMPUTER",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )
    gateway.submit_proposal(high_risk_proposal)

    # 1. Proposer attempts to approve own action -> must raise TWO_PERSON_RULE_VIOLATION
    with pytest.raises(ExecutionGatewayError) as exc_info:
        gateway.approve_action(high_risk_proposal.action_id, approver=proposer)
    assert exc_info.value.error_code == "TWO_PERSON_RULE_VIOLATION"

    # 2. Execution attempted before approval -> must raise APPROVAL_REQUIRED
    req = ExecutionRequest(action_id=high_risk_proposal.action_id, caller=proposer)
    with pytest.raises(ExecutionGatewayError) as exc_info:
        gateway.execute_action(req)
    assert exc_info.value.error_code == "APPROVAL_REQUIRED"

    # 3. Second independent actor (Commander) approves action -> succeeds
    approved = gateway.approve_action(high_risk_proposal.action_id, approver=commander)
    assert approved.status == ActionStatus.APPROVED
    assert approved.approver.actor_id == commander.actor_id

    # 4. Now execution proceeds successfully
    result = gateway.execute_action(req)
    assert result.status == ActionStatus.SUCCEEDED


def test_execution_idempotency_caching(gateway: ExecutionGateway, proposer: ActorIdentity):
    """Re-submitting with identical idempotency token returns cached result without re-executing."""
    execution_counter = 0

    def mock_counter_handler(action, _):
        nonlocal execution_counter
        execution_counter += 1
        return 1, {"count": execution_counter}

    gateway.register_handler("INCREMENT_COUNTER", mock_counter_handler)

    proposal = ActionProposal(
        action_type="INCREMENT_COUNTER",
        proposer=proposer,
        resource_type="COUNTER",
        resource_id="CNT_01",
    )
    gateway.submit_proposal(proposal)

    req1 = ExecutionRequest(
        action_id=proposal.action_id,
        caller=proposer,
        idempotency_key="idempotency_token_abc",
    )
    res1 = gateway.execute_action(req1)
    assert res1.output["count"] == 1
    assert execution_counter == 1

    # Second call with same idempotency token
    req2 = ExecutionRequest(
        action_id=proposal.action_id,
        caller=proposer,
        idempotency_key="idempotency_token_abc",
    )
    res2 = gateway.execute_action(req2)
    assert res2.output["count"] == 1
    assert execution_counter == 1  # Handler was not executed second time
    assert res1.execution_id == res2.execution_id


def test_action_rollback(gateway: ExecutionGateway, proposer: ActorIdentity):
    """Succeeded action can be cleanly rolled back with audit trail."""
    proposal = ActionProposal(
        action_type="CONFIGURATION_UPDATE",
        proposer=proposer,
        resource_type="RADAR_MODE",
        resource_id="RADAR_01",
        can_rollback=True,
    )
    gateway.submit_proposal(proposal)

    exec_req = ExecutionRequest(action_id=proposal.action_id, caller=proposer)
    gateway.execute_action(exec_req)

    rb_req = RollbackRequest(
        action_id=proposal.action_id,
        caller=proposer,
        reason="Sensor drift detected post-update",
    )
    rb_res = gateway.rollback_action(rb_req)
    assert rb_res.status == ActionStatus.ROLLED_BACK
    assert rb_res.audit_event_id is not None

    updated = gateway.get_action(proposal.action_id)
    assert updated.status == ActionStatus.ROLLED_BACK
