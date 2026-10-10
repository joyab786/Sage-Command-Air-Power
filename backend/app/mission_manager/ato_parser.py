"""
SageCommand Air Power System (Aero) — Synthetic ATO Document Parser.
Safely deserializes structured JSON payloads into validated ATODocument instances.
Enforces schema validation and rejects malformed or unvetted inputs without executing arbitrary content.
"""

import json
from typing import Dict, Any, Optional, Tuple
from pydantic import ValidationError

from app.core.exceptions import ValidationError as AeroValidationError
from app.core.logging import get_logger
from app.mission_manager.models import (
    ATODocument,
    ATOValidationStatus,
    ATOValidationResponse,
    ValidationFinding,
)
from app.mission_manager.validation import ATOValidator

logger = get_logger(__name__)


class ATOParser:
    """
    Parser for synthetic, non-operational Air Tasking Order (ATO) documents.
    """

    @classmethod
    def parse_dict(cls, payload: Dict[str, Any]) -> Tuple[Optional[ATODocument], ATOValidationResponse]:
        """
        Parses and validates an ATO dictionary representation.
        Returns the parsed ATODocument (if valid) and the structured ATOValidationResponse.
        """
        ato_id = str(payload.get("ato_id", "UNKNOWN_ATO")) if isinstance(payload, dict) else "UNKNOWN_ATO"

        # 1. Pre-validation on raw dictionary
        raw_status, raw_findings = ATOValidator.validate_raw_dict(payload)
        if raw_status == ATOValidationStatus.INVALID:
            return None, ATOValidationResponse(
                ato_id=ato_id,
                is_valid=False,
                validation_status=ATOValidationStatus.INVALID,
                findings=raw_findings,
                sortie_count=len(payload.get("sorties", [])) if isinstance(payload, dict) and isinstance(payload.get("sorties"), list) else 0,
            )

        # 2. Pydantic schema validation
        try:
            document = ATODocument.model_validate(payload)
        except ValidationError as val_err:
            schema_findings: list[ValidationFinding] = list(raw_findings)
            for err in val_err.errors():
                loc = " -> ".join(str(p) for p in err.get("loc", []))
                schema_findings.append(ValidationFinding(
                    severity="ERROR",
                    code="SCHEMA_VALIDATION_ERROR",
                    message=err.get("msg", "Invalid schema type"),
                    field=loc,
                ))
            return None, ATOValidationResponse(
                ato_id=ato_id,
                is_valid=False,
                validation_status=ATOValidationStatus.INVALID,
                findings=schema_findings,
                sortie_count=len(payload.get("sorties", [])) if isinstance(payload.get("sorties"), list) else 0,
            )

        # 3. Post-validation on deserialized domain document
        domain_status, domain_findings = ATOValidator.validate_document(document)
        all_findings = raw_findings + domain_findings
        is_valid = not any(f.severity == "ERROR" for f in all_findings)

        if not is_valid:
            final_status = ATOValidationStatus.INVALID
        elif any(f.severity == "WARNING" for f in all_findings):
            final_status = ATOValidationStatus.WARNINGS
        else:
            final_status = ATOValidationStatus.VALID

        document.validation_status = final_status
        document.validation_findings = all_findings

        val_resp = ATOValidationResponse(
            ato_id=document.ato_id,
            is_valid=is_valid,
            validation_status=final_status,
            findings=all_findings,
            sortie_count=len(document.sorties),
        )

        return (document if is_valid else None), val_resp

    @classmethod
    def parse_json_string(cls, json_str: str) -> Tuple[Optional[ATODocument], ATOValidationResponse]:
        """Safely parses JSON string with syntax error protection."""
        try:
            payload = json.loads(json_str)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            findings = [ValidationFinding(
                severity="ERROR",
                code="MALFORMED_JSON_SYNTAX",
                message=f"JSON decoding failed: {exc}",
                field="root",
            )]
            return None, ATOValidationResponse(
                ato_id="INVALID_JSON",
                is_valid=False,
                validation_status=ATOValidationStatus.INVALID,
                findings=findings,
                sortie_count=0,
            )

        return cls.parse_dict(payload)
