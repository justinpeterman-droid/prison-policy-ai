from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import UniformInspectionV1


def _staff(name):
    return {"staff_id": str(uuid4()), "display_name_snapshot": name}


def _payload():
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "D",
        "roster_record_id": str(uuid4()),
        "roster_revision_number": 2,
        "inspector": _staff("Sgt. Riley Jordan"),
        "rows": [
            {
                "staff": _staff("Officer Morgan Lee"),
                "shirt": "S",
                "pants": "N/I",
                "shoes": "NONE",
                "cap": None,
                "coat": None,
                "id": "S",
                "hair": "S",
                "nails": "S",
                "comments": "",
            }
        ],
    }


def test_uniform_inspection_accepts_only_the_approved_values():
    model = UniformInspectionV1.model_validate(_payload())
    assert model.rows[0].pants == "N/I"

    payload = _payload()
    payload["rows"][0]["shirt"] = "PASS"
    with pytest.raises(ValidationError):
        UniformInspectionV1.model_validate(payload)


def test_uniform_inspection_rejects_duplicate_staff_and_requires_comment_for_u():
    payload = _payload()
    payload["rows"].append(deepcopy(payload["rows"][0]))
    with pytest.raises(ValidationError):
        UniformInspectionV1.model_validate(payload)

    payload = _payload()
    payload["rows"][0]["coat"] = "U"
    with pytest.raises(ValidationError):
        UniformInspectionV1.model_validate(payload)

    payload["rows"][0]["comments"] = "Missing required coat."
    assert UniformInspectionV1.model_validate(payload).rows[0].coat == "U"


def test_uniform_inspection_rejects_unknown_fields_invalid_uuid_and_long_comments():
    payload = _payload()
    payload["rows"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        UniformInspectionV1.model_validate(payload)

    payload = _payload()
    payload["rows"][0]["staff"]["staff_id"] = "bad"
    with pytest.raises(ValidationError):
        UniformInspectionV1.model_validate(payload)

    payload = _payload()
    payload["rows"][0]["comments"] = "x" * 501
    with pytest.raises(ValidationError):
        UniformInspectionV1.model_validate(payload)

