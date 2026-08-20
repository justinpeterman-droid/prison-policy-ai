from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import PerimeterCheckV1
from backend.paperwork.daily_templates import load_daily_template


def _payload():
    definition = load_daily_template("perimeter_check").definition
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "D",
        "checks": [
            {"check_code": item["code"], "result": None}
            for group in definition["groups"]
            for item in group["items"]
        ],
        "perimeter_inspector": None,
        "perimeter_signature_name": None,
        "perimeter_inspected_at": None,
        "senstar_inspector": None,
        "supervisor_signature_name": None,
        "supervisor_signed_at": None,
    }


def test_perimeter_requires_every_approved_check_exactly_once():
    assert len(PerimeterCheckV1.model_validate(_payload()).checks) == 65

    payload = _payload()
    payload["checks"].pop()
    with pytest.raises(ValidationError):
        PerimeterCheckV1.model_validate(payload)

    payload = _payload()
    payload["checks"][1] = deepcopy(payload["checks"][0])
    with pytest.raises(ValidationError):
        PerimeterCheckV1.model_validate(payload)


def test_perimeter_results_and_fields_are_closed_and_bounded():
    payload = _payload()
    payload["checks"][0]["result"] = "F"
    with pytest.raises(ValidationError):
        PerimeterCheckV1.model_validate(payload)

    payload = _payload()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        PerimeterCheckV1.model_validate(payload)

    payload = _payload()
    payload["perimeter_signature_name"] = "x" * 161
    with pytest.raises(ValidationError):
        PerimeterCheckV1.model_validate(payload)

    payload = _payload()
    payload["perimeter_inspector"] = {
        "staff_id": str(uuid4()),
        "display_name_snapshot": "Officer Avery Cole",
    }
    assert PerimeterCheckV1.model_validate(payload).perimeter_inspector is not None

