"""
SageCommand Air Power System (Aero) — Cryptographic Audit Ledger.
Provides append-only, immutable event records with SHA-256 hash chaining
for tamper-evident historical auditability across human, system, and AI decisions.
"""

import uuid
import json
import hashlib
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from pydantic import Field, field_validator
from app.contracts.base import AeroBaseModel, utc_now_iso
from app.contracts.common import ActorIdentity, ActorType


class LedgerEvent(AeroBaseModel):
    """Immutable, cryptographically chained audit ledger event record."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    sequence_number: int = Field(..., ge=1, description="Monotonically increasing sequence within ledger")
    event_type: str = Field(..., description="Canonical event classification code")
    occurred_at: str = Field(default_factory=utc_now_iso)
    recorded_at: str = Field(default_factory=utc_now_iso)

    # Actor identity
    actor: ActorIdentity = Field(..., description="Initiator of action or decision")

    # Operational context
    action: str = Field(..., description="Operational action name or command")
    result: str = Field(..., description="Outcome: SUCCESS | FAILED | DENIED | PENDING")
    resource_type: Optional[str] = Field(default=None)
    resource_id: Optional[str] = Field(default=None)
    correlation_id: Optional[str] = Field(default=None)

    # Structured details
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Cryptographic Chain Linkage
    previous_event_id: Optional[str] = Field(default=None)
    previous_event_hash: Optional[str] = Field(default=None)
    event_hash: str = Field(default="", description="Deterministic SHA-256 tamper-evident fingerprint")

    def compute_hash(self) -> str:
        """
        Computes deterministic SHA-256 hash over event fields including previous_event_hash.
        Guarantees that altering any historical record invalidates the subsequent chain.
        """
        canonical_dict = {
            "event_id": self.event_id,
            "sequence_number": self.sequence_number,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "actor": self.actor.model_dump(),
            "action": self.action,
            "result": self.result,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "correlation_id": self.correlation_id,
            "previous_event_id": self.previous_event_id,
            "previous_event_hash": self.previous_event_hash,
            "payload": self.payload,
        }
        encoded = json.dumps(canonical_dict, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class AuditIntegrityReport(AeroBaseModel):
    """Result of full cryptographic audit chain verification."""

    is_valid: bool = Field(..., description="True if all hashes and sequence links are unbroken")
    total_events: int = Field(..., ge=0)
    verified_events: int = Field(..., ge=0)
    broken_sequence: Optional[int] = Field(default=None, description="First sequence number where link failed")
    error_message: Optional[str] = Field(default=None)
    verified_at: str = Field(default_factory=utc_now_iso)


class AuditLedgerService:
    """
    Authoritative Audit Ledger Service.
    Enforces append-only semantics and maintains unbroken SHA-256 cryptographic chain.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self._lock = threading.RLock()
        self._events: List[LedgerEvent] = []
        self._event_index: Dict[str, LedgerEvent] = {}

    def append_event(
        self,
        event_type: str,
        actor: ActorIdentity,
        action: str,
        result: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LedgerEvent:
        """
        Appends an event to the ledger with deterministic hash chaining.
        Thread-safe and strictly monotonically sequenced.
        """
        with self._lock:
            sequence_number = len(self._events) + 1

            if sequence_number == 1:
                prev_id = None
                prev_hash = self.GENESIS_HASH
            else:
                prev_event = self._events[-1]
                prev_id = prev_event.event_id
                prev_hash = prev_event.event_hash

            event = LedgerEvent(
                sequence_number=sequence_number,
                event_type=event_type,
                occurred_at=utc_now_iso(),
                recorded_at=utc_now_iso(),
                actor=actor,
                action=action,
                result=result,
                resource_type=resource_type,
                resource_id=resource_id,
                correlation_id=correlation_id,
                payload=payload or {},
                metadata=metadata or {},
                previous_event_id=prev_id,
                previous_event_hash=prev_hash,
            )
            event.event_hash = event.compute_hash()

            self._events.append(event)
            self._event_index[event.event_id] = event
            return event

    def get_event(self, event_id: str) -> Optional[LedgerEvent]:
        """Retrieves single audit event by ID."""
        with self._lock:
            return self._event_index.get(event_id)

    def get_latest_event(self) -> Optional[LedgerEvent]:
        """Returns most recently committed ledger event."""
        with self._lock:
            return self._events[-1] if self._events else None

    def query_events(
        self,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[LedgerEvent], int]:
        """Queries events with optional filtering and pagination."""
        with self._lock:
            filtered = self._events

            if event_type:
                filtered = [e for e in filtered if e.event_type == event_type]
            if actor_id:
                filtered = [e for e in filtered if e.actor.actor_id == actor_id]
            if correlation_id:
                filtered = [e for e in filtered if e.correlation_id == correlation_id]
            if resource_id:
                filtered = [e for e in filtered if e.resource_id == resource_id]

            total = len(filtered)
            paged = filtered[offset : offset + limit]
            return paged, total

    def verify_integrity(self) -> AuditIntegrityReport:
        """
        Cryptographically verifies the unbroken chain of the entire audit ledger.
        Recalculates every SHA-256 hash and verifies pointer to previous event hash.
        """
        with self._lock:
            total = len(self._events)
            if total == 0:
                return AuditIntegrityReport(
                    is_valid=True,
                    total_events=0,
                    verified_events=0,
                )

            expected_prev_hash = self.GENESIS_HASH

            for idx, event in enumerate(self._events):
                seq = idx + 1

                # 1. Verify sequence monotonicity
                if event.sequence_number != seq:
                    return AuditIntegrityReport(
                        is_valid=False,
                        total_events=total,
                        verified_events=idx,
                        broken_sequence=seq,
                        error_message=f"Sequence gap detected: expected {seq}, found {event.sequence_number}",
                    )

                # 2. Verify previous event hash link
                if event.previous_event_hash != expected_prev_hash:
                    return AuditIntegrityReport(
                        is_valid=False,
                        total_events=total,
                        verified_events=idx,
                        broken_sequence=seq,
                        error_message=f"Chain linkage broken at sequence {seq}: previous hash mismatch",
                    )

                # 3. Recalculate and verify event hash
                computed = event.compute_hash()
                if event.event_hash != computed:
                    return AuditIntegrityReport(
                        is_valid=False,
                        total_events=total,
                        verified_events=idx,
                        broken_sequence=seq,
                        error_message=f"Event content tampering detected at sequence {seq}: hash mismatch",
                    )

                expected_prev_hash = event.event_hash

            return AuditIntegrityReport(
                is_valid=True,
                total_events=total,
                verified_events=total,
            )


# Global default audit ledger instance
default_audit_ledger = AuditLedgerService()
