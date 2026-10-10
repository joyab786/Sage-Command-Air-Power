"""
SageCommand Air Power System (Aero) — Synthetic ATO Validation Engine.
Provides deterministic, fail-closed validation for structured synthetic Air Tasking Order (ATO) documents.
Protects against out-of-window sorties, duplicate identifiers, malformed temporal bounds, and unexpected keys.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from app.mission_manager.models import (
    ATODocument,
    ProposedSortie,
    ATOValidationStatus,
    ValidationFinding,
)

SUPPORTED_SCHEMA_VERSIONS = {"1.0.0", "1.0", "aero-ato-v1"}
FORBIDDEN_KEY_PATTERNS = {
    "weapon", "payload_release", "target", "kill_chain", "combat_radius",
    "strike", "engagement", "classified", "execute_script", "command_override",
    "tactical_route", "waypoint_combat", "roe_code", "warhead", "ballistic", "ordnance",
}


class ATOValidator:
    """
    Deterministic validator for synthetic non-operational ATO documents.
    """

    MAX_PLANNING_HORIZON_HOURS: float = 72.0

    @classmethod
    def validate_raw_dict(cls, data: Dict[str, Any]) -> Tuple[ATOValidationStatus, List[ValidationFinding]]:
        """
        Validates raw untrusted dictionary prior to or during Pydantic deserialization.
        Rejects forbidden operational or execution parameters.
        """
        findings: List[ValidationFinding] = []

        # 1. Structural checks
        if not isinstance(data, dict):
            findings.append(ValidationFinding(
                severity="ERROR",
                code="ATO_ROOT_NOT_OBJECT",
                message="ATO document payload must be a JSON object",
                field="root",
            ))
            return ATOValidationStatus.INVALID, findings

        # 2. Check forbidden keys (Safety Boundary)
        def scan_forbidden(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    k_lower = str(k).lower()
                    if any(pat in k_lower for pat in FORBIDDEN_KEY_PATTERNS):
                        findings.append(ValidationFinding(
                            severity="ERROR",
                            code="FORBIDDEN_OPERATIONAL_PARAMETER",
                            message=f"Forbidden weapon, targeting, or execution parameter '{k}' detected",
                            field=f"{path}.{k}" if path else str(k),
                        ))
                    scan_forbidden(v, f"{path}.{k}" if path else str(k))
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    scan_forbidden(item, f"{path}[{idx}]")

        scan_forbidden(data)

        # 3. Required top-level fields
        required_fields = ["ato_id", "planning_window_start", "planning_window_end", "sorties"]
        for rf in required_fields:
            if rf not in data or data[rf] is None:
                findings.append(ValidationFinding(
                    severity="ERROR",
                    code=f"MISSING_{rf.upper()}",
                    message=f"Required ATO field '{rf}' is missing or null",
                    field=rf,
                ))

        # 4. Schema version verification
        version = str(data.get("schema_version", "1.0.0"))
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            findings.append(ValidationFinding(
                severity="ERROR",
                code="UNSUPPORTED_SCHEMA_VERSION",
                message=f"Schema version '{version}' is not supported. Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
                field="schema_version",
            ))

        # 5. Planning window temporal order check
        pw_start_raw = data.get("planning_window_start")
        pw_end_raw = data.get("planning_window_end")
        if pw_start_raw and pw_end_raw:
            try:
                start_dt = datetime.fromisoformat(str(pw_start_raw).replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(str(pw_end_raw).replace("Z", "+00:00"))
                if end_dt <= start_dt:
                    findings.append(ValidationFinding(
                        severity="ERROR",
                        code="INVALID_PLANNING_WINDOW",
                        message=f"Planning window end ({pw_end_raw}) must be strictly after start ({pw_start_raw})",
                        field="planning_window_end",
                    ))
            except Exception:
                pass

        # 6. Check duplicate sortie IDs
        sorties_raw = data.get("sorties", [])
        if isinstance(sorties_raw, list):
            seen_ids = set()
            for idx, s in enumerate(sorties_raw):
                if isinstance(s, dict):
                    sid = s.get("sortie_id")
                    if sid:
                        if sid in seen_ids:
                            findings.append(ValidationFinding(
                                severity="ERROR",
                                code="DUPLICATE_SORTIE_ID",
                                message=f"Duplicate sortie identifier '{sid}' found in ATO document",
                                field=f"sorties[{idx}].sortie_id",
                                sortie_id=str(sid),
                            ))
                        seen_ids.add(sid)
                else:
                    findings.append(ValidationFinding(
                        severity="ERROR",
                        code="INVALID_SORTIE_ELEMENT",
                        message=f"Sortie at index {idx} must be a JSON object",
                        field=f"sorties[{idx}]",
                    ))

        status = ATOValidationStatus.INVALID if any(f.severity == "ERROR" for f in findings) else ATOValidationStatus.VALID
        return status, findings

    @classmethod
    def validate_document(cls, doc: ATODocument) -> Tuple[ATOValidationStatus, List[ValidationFinding]]:
        """
        Validates a deserialized ATODocument model for domain invariants and temporal boundaries.
        """
        findings: List[ValidationFinding] = []

        # 1. Planning window boundary check
        window_duration_hours = (doc.planning_window_end - doc.planning_window_start).total_seconds() / 3600.0
        if window_duration_hours <= 0:
            findings.append(ValidationFinding(
                severity="ERROR",
                code="INVALID_PLANNING_WINDOW",
                message=f"Planning window end ({doc.planning_window_end}) must be after start ({doc.planning_window_start})",
                field="planning_window_end",
            ))
        elif window_duration_hours > cls.MAX_PLANNING_HORIZON_HOURS:
            findings.append(ValidationFinding(
                severity="WARNING",
                code="EXCESSIVE_PLANNING_HORIZON",
                message=f"Planning window ({window_duration_hours:.1f} hrs) exceeds recommended horizon ({cls.MAX_PLANNING_HORIZON_HOURS} hrs)",
                field="planning_window_end",
            ))

        # 2. Sortie checks
        if not doc.sorties:
            findings.append(ValidationFinding(
                severity="WARNING",
                code="EMPTY_ATO_SORTIES",
                message="ATO document contains zero proposed sorties",
                field="sorties",
            ))

        for sortie in doc.sorties:
            # Check sortie inside planning window
            if sortie.start_time < doc.planning_window_start:
                findings.append(ValidationFinding(
                    severity="ERROR",
                    code="SORTIE_PRE_WINDOW",
                    message=f"Sortie launch ({sortie.start_time}) precedes ATO window start ({doc.planning_window_start})",
                    field="start_time",
                    sortie_id=sortie.sortie_id,
                ))
            if sortie.end_time > doc.planning_window_end:
                findings.append(ValidationFinding(
                    severity="ERROR",
                    code="SORTIE_POST_WINDOW",
                    message=f"Sortie recovery ({sortie.end_time}) exceeds ATO window end ({doc.planning_window_end})",
                    field="end_time",
                    sortie_id=sortie.sortie_id,
                ))

            # Duration check
            duration_hrs = (sortie.end_time - sortie.start_time).total_seconds() / 3600.0
            if duration_hrs > 12.0:
                findings.append(ValidationFinding(
                    severity="WARNING",
                    code="EXCESSIVE_SORTIE_DURATION",
                    message=f"Sortie duration ({duration_hrs:.1f} hrs) is unusually long for a single airframe sortie",
                    field="end_time",
                    sortie_id=sortie.sortie_id,
                ))

        # Determine aggregate status
        if any(f.severity == "ERROR" for f in findings):
            agg_status = ATOValidationStatus.INVALID
        elif any(f.severity == "WARNING" for f in findings):
            agg_status = ATOValidationStatus.WARNINGS
        else:
            agg_status = ATOValidationStatus.VALID

        return agg_status, findings
