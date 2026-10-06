"""Unit tests for Aero Cryptographic Audit Ledger and hash chain integrity."""

import pytest
from app.contracts.common import ActorIdentity, ActorType
from app.services.audit_ledger import AuditLedgerService


@pytest.fixture
def audit_ledger() -> AuditLedgerService:
    return AuditLedgerService()


@pytest.fixture
def sample_actor() -> ActorIdentity:
    return ActorIdentity(
        actor_id="officer_bravo",
        actor_type=ActorType.USER,
        roles=["flight_lead"],
        tenant_id="wing_7",
    )


def test_audit_ledger_append_and_hash_chaining(audit_ledger: AuditLedgerService, sample_actor: ActorIdentity):
    """Events must be monotonically sequenced and linked via SHA-256 hashes."""
    e1 = audit_ledger.append_event(
        event_type="SYSTEM_BOOT",
        actor=sample_actor,
        action="BOOT",
        result="SUCCESS",
        payload={"subsystem": "avionics_gateway"},
    )
    assert e1.sequence_number == 1
    assert e1.previous_event_hash == AuditLedgerService.GENESIS_HASH
    assert len(e1.event_hash) == 64

    e2 = audit_ledger.append_event(
        event_type="CALIBRATION_PERFORMED",
        actor=sample_actor,
        action="CALIBRATE",
        result="SUCCESS",
        payload={"sensor": "pitot_tube_01"},
    )
    assert e2.sequence_number == 2
    assert e2.previous_event_id == e1.event_id
    assert e2.previous_event_hash == e1.event_hash
    assert len(e2.event_hash) == 64

    e3 = audit_ledger.append_event(
        event_type="READINESS_VERIFIED",
        actor=sample_actor,
        action="VERIFY",
        result="SUCCESS",
        payload={"status": "GO"},
    )
    assert e3.sequence_number == 3
    assert e3.previous_event_hash == e2.event_hash

    # Verify pristine chain
    report = audit_ledger.verify_integrity()
    assert report.is_valid is True
    assert report.total_events == 3
    assert report.verified_events == 3
    assert report.broken_sequence is None


def test_audit_ledger_tamper_detection(audit_ledger: AuditLedgerService, sample_actor: ActorIdentity):
    """Modifying any historical event payload must invalidate the cryptographic chain."""
    audit_ledger.append_event(
        event_type="EVENT_ONE",
        actor=sample_actor,
        action="ACT_1",
        result="SUCCESS",
        payload={"param": "original_val"},
    )
    audit_ledger.append_event(
        event_type="EVENT_TWO",
        actor=sample_actor,
        action="ACT_2",
        result="SUCCESS",
        payload={"param": "val_2"},
    )
    audit_ledger.append_event(
        event_type="EVENT_THREE",
        actor=sample_actor,
        action="ACT_3",
        result="SUCCESS",
        payload={"param": "val_3"},
    )

    # Initial chain is valid
    assert audit_ledger.verify_integrity().is_valid is True

    # Deliberately tamper with internal payload of event 2
    audit_ledger._events[1].payload["param"] = "tampered_compromised_val"

    # Verification must catch the tampering immediately
    tamper_report = audit_ledger.verify_integrity()
    assert tamper_report.is_valid is False
    assert tamper_report.broken_sequence == 2
    assert "tampering detected" in tamper_report.error_message


def test_audit_ledger_query_filtering(audit_ledger: AuditLedgerService, sample_actor: ActorIdentity):
    """Ledger must support filtering by event type and correlation ID."""
    audit_ledger.append_event(
        event_type="SORTIE_DISPATCH",
        actor=sample_actor,
        action="DISPATCH",
        result="SUCCESS",
        correlation_id="corr_mission_alpha",
    )
    audit_ledger.append_event(
        event_type="MAINTENANCE_LOG",
        actor=sample_actor,
        action="INSPECT",
        result="SUCCESS",
        correlation_id="corr_maintenance_beta",
    )

    events, total = audit_ledger.query_events(correlation_id="corr_mission_alpha")
    assert total == 1
    assert events[0].event_type == "SORTIE_DISPATCH"
