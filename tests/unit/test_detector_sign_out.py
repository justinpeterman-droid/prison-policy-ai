from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import DetectorSignOutV1


def _payload():
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "D",
        "units": [
            {"unit_code": f"D{number}", "staff": None, "area_of_assignment": ""}
            for number in range(1, 10)
        ],
        "shift_supervisor": None,
        "sign_out_date": None,
    }


def test_detector_sign_out_requires_d1_through_d9_exactly_once():
    assert [row.unit_code for row in DetectorSignOutV1.model_validate(_payload()).units] == [
        f"D{number}" for number in range(1, 10)
    ]

    payload = _payload()
    payload["units"][1] = deepcopy(payload["units"][0])
    with pytest.raises(ValidationError):
        DetectorSignOutV1.model_validate(payload)

    payload = _payload()
    payload["units"][0]["unit_code"] = "D10"
    with pytest.raises(ValidationError):
        DetectorSignOutV1.model_validate(payload)


def test_detector_sign_out_allows_incomplete_rows_but_rejects_bad_identity_and_extra_fields():
    payload = _payload()
    payload["units"][0]["staff"] = {
        "staff_id": str(uuid4()),
        "display_name_snapshot": "Officer Avery Cole",
    }
    payload["units"][0]["area_of_assignment"] = "North Hall"
    assert DetectorSignOutV1.model_validate(payload).units[0].staff is not None

    payload = _payload()
    payload["units"][0]["staff"] = {
        "staff_id": "not-a-uuid",
        "display_name_snapshot": "Officer Avery Cole",
    }
    with pytest.raises(ValidationError):
        DetectorSignOutV1.model_validate(payload)

    payload = _payload()
    payload["units"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        DetectorSignOutV1.model_validate(payload)
