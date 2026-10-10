"""
Unit tests for SageCommand Aero Mission Manager — ATO Parser & Validator.
Tests schema validation, safety boundary rejection (forbidden operational keys),
temporal boundary enforcement, malformed JSON handling, and duplicate sortie rejection.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest

from app.mission_manager.ato_parser import ATOParser
from app.mission_manager.models import ATOValidationStatus
from app.mission_manager.service import create_demo_ato_dict


def test_parse_valid_demo_dict():
    data = create_demo_ato_dict("ATO-TEST-VALID-01")
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is not None
    assert val_resp.is_valid is True
    assert val_resp.validation_status == ATOValidationStatus.VALID
    assert len(val_resp.findings) == 0
    assert len(doc.sorties) == 4
    assert doc.ato_id == "ATO-TEST-VALID-01"


def test_parse_valid_json_string():
    data = create_demo_ato_dict("ATO-JSON-01")
    json_str = json.dumps(data)
    doc, val_resp = ATOParser.parse_json_string(json_str)

    assert doc is not None
    assert val_resp.is_valid is True
    assert doc.ato_id == "ATO-JSON-01"


def test_reject_malformed_json_syntax():
    bad_json = '{"ato_id": "ATO-BAD", "sorties": [}'
    doc, val_resp = ATOParser.parse_json_string(bad_json)

    assert doc is None
    assert val_resp.is_valid is False
    assert val_resp.validation_status == ATOValidationStatus.INVALID
    assert any("JSON decoding failed" in f.message for f in val_resp.findings)


def test_reject_unsupported_schema_version():
    data = create_demo_ato_dict("ATO-VERSION-BAD")
    data["schema_version"] = "99.0.0"
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is None
    assert val_resp.is_valid is False
    assert any("UNSUPPORTED_SCHEMA_VERSION" in f.code for f in val_resp.findings)


def test_safety_boundary_rejects_forbidden_operational_keys():
    """Safety boundary: Weapons, targeting, kill chains, or combat radius parameters are strictly rejected."""
    data = create_demo_ato_dict("ATO-WEAPONS-FORBIDDEN")
    data["sorties"][0]["weapon_payload"] = "AIM-120"
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is None
    assert val_resp.is_valid is False
    assert any("FORBIDDEN_OPERATIONAL_PARAMETER" in f.code for f in val_resp.findings)


def test_safety_boundary_rejects_target_coordinates():
    data = create_demo_ato_dict("ATO-TARGET-FORBIDDEN")
    data["sorties"][0]["target_coordinates"] = {"lat": 34.0, "lon": 74.0}
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is None
    assert val_resp.is_valid is False
    assert any("FORBIDDEN_OPERATIONAL_PARAMETER" in f.code for f in val_resp.findings)


def test_reject_out_of_window_sorties():
    data = create_demo_ato_dict("ATO-WINDOW-BAD")
    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    # Launch before window start
    data["sorties"][0]["start_time"] = (t0 - timedelta(hours=2)).isoformat()
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is None
    assert val_resp.is_valid is False
    assert any("SORTIE_PRE_WINDOW" in f.code for f in val_resp.findings)


def test_reject_duplicate_sortie_ids():
    data = create_demo_ato_dict("ATO-DUP-SORTIES")
    dup_id = data["sorties"][0]["sortie_id"]
    data["sorties"][1]["sortie_id"] = dup_id
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is None
    assert val_resp.is_valid is False
    assert any("DUPLICATE_SORTIE_ID" in f.code for f in val_resp.findings)


def test_reject_missing_required_fields():
    data = {"source": "SYNTHETIC_SIH_DEMO"}
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is None
    assert val_resp.is_valid is False
    assert any("MISSING_ATO_ID" in f.code for f in val_resp.findings)


def test_warns_excessive_planning_horizon():
    data = create_demo_ato_dict("ATO-LONG-HORIZON")
    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    # 96 hours window (> 72 max recommended)
    data["planning_window_end"] = (t0 + timedelta(hours=96)).isoformat()
    data["sorties"][0]["end_time"] = (t0 + timedelta(hours=90)).isoformat()
    doc, val_resp = ATOParser.parse_dict(data)

    assert doc is not None
    assert val_resp.is_valid is True
    assert val_resp.validation_status == ATOValidationStatus.WARNINGS
    assert any("EXCESSIVE_PLANNING_HORIZON" in f.code for f in val_resp.findings)
