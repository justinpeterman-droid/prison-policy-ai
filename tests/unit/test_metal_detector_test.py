from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import MetalDetectorTestV1


POSITION_CODES = [f"position_{number}" for number in range(1, 8)]


def _payload():
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "D",
        "detectors": [
            {
                "detector_code": str(number),
                "location": "",
                "equipment_identifier": "",
                "tests": [
                    {"position_code": position, "result": None}
                    for position in POSITION_CODES
                ],
                "corrective_action": "",
            }
            for number in range(1, 12)
        ],
        "tested_by": None,
        "reviewed_by": None,
        "comments": "",
    }


def test_metal_detector_requires_each_detector_and_position_exactly_once():
    assert len(MetalDetectorTestV1.model_validate(_payload()).detectors) == 11

    for mutation in ("unknown_detector", "duplicate_detector", "missing_position", "unknown_position"):
        payload = _payload()
        if mutation == "unknown_detector":
            payload["detectors"][0]["detector_code"] = "12"
        elif mutation == "duplicate_detector":
            payload["detectors"][1] = deepcopy(payload["detectors"][0])
        elif mutation == "missing_position":
            payload["detectors"][0]["tests"].pop()
        else:
            payload["detectors"][0]["tests"][0]["position_code"] = "invented"
        with pytest.raises(ValidationError):
            MetalDetectorTestV1.model_validate(payload)


def test_metal_detector_failure_requires_corrective_action_and_enum_is_closed():
    payload = _payload()
    payload["detectors"][0]["tests"][0]["result"] = "F"
    with pytest.raises(ValidationError):
        MetalDetectorTestV1.model_validate(payload)

    payload["detectors"][0]["corrective_action"] = "Detector removed from service."
    assert MetalDetectorTestV1.model_validate(payload).detectors[0].tests[0].result == "F"

    payload = _payload()
    payload["detectors"][0]["tests"][0]["result"] = "S"
    with pytest.raises(ValidationError):
        MetalDetectorTestV1.model_validate(payload)


def test_metal_detector_rejects_unknown_fields_and_unbounded_identifiers():
    payload = _payload()
    payload["detectors"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        MetalDetectorTestV1.model_validate(payload)

    payload = _payload()
    payload["detectors"][0]["equipment_identifier"] = "x" * 161
    with pytest.raises(ValidationError):
        MetalDetectorTestV1.model_validate(payload)

