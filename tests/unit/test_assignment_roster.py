from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import AssignmentRosterV1, validate_daily_payload
from backend.paperwork.daily_templates import DailyPaperworkKind, load_daily_template


def _staff(name="Officer Avery Cole"):
    return {"staff_id": str(uuid4()), "display_name_snapshot": name}


def _payload():
    definition = load_daily_template("assignment_roster").definition
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "D",
        "captain": None,
        "lieutenant": None,
        "duty_warden": None,
        "alternate_shift_supervisor": None,
        "leave_entries": [],
        "extra_assignments": [],
        "zones": [
            {
                "zone_code": zone["code"],
                "supervisor": None,
                "posts": [
                    {
                        "post_code": post["code"],
                        "initial_staff": None,
                        "rotation_staff": None,
                    }
                    for post in zone["posts"]
                ],
            }
            for zone in definition["zones"]
        ],
        "briefing_minutes": "",
        "roll_call_completed": False,
        "uniform_inspection_completed": False,
        "equipment": {
            "digital_camera": "not_checked",
            "video_camera_go_pro": "not_checked",
            "metal_detector_wands": "not_checked",
        },
        "briefing_guests": [],
        "assigned_and_dismissed": False,
        "lieutenant_signature_name": None,
    }


def test_assignment_roster_accepts_each_approved_zone_and_post_exactly_once():
    model = validate_daily_payload(DailyPaperworkKind.ASSIGNMENT_ROSTER, _payload())

    assert isinstance(model, AssignmentRosterV1)
    assert model.work_date.isoformat() == "2026-08-20"
    assert [zone.zone_code for zone in model.zones] == [
        "zone_1", "zone_2", "zone_3", "zone_4", "zone_5"
    ]


@pytest.mark.parametrize("mutation", ["unknown_zone", "unknown_post", "missing_post", "duplicate_post"])
def test_assignment_roster_rejects_codes_that_do_not_match_the_template(mutation):
    payload = _payload()
    if mutation == "unknown_zone":
        payload["zones"][0]["zone_code"] = "invented_zone"
    elif mutation == "unknown_post":
        payload["zones"][0]["posts"][0]["post_code"] = "invented_post"
    elif mutation == "missing_post":
        payload["zones"][0]["posts"].pop()
    else:
        payload["zones"][0]["posts"][1] = deepcopy(payload["zones"][0]["posts"][0])

    with pytest.raises(ValidationError):
        AssignmentRosterV1.model_validate(payload)


def test_assignment_roster_is_closed_and_bounds_identity_and_operational_fields():
    payload = _payload()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        AssignmentRosterV1.model_validate(payload)

    payload = _payload()
    payload["captain"] = {"staff_id": "not-a-uuid", "display_name_snapshot": "Officer Cole"}
    with pytest.raises(ValidationError):
        AssignmentRosterV1.model_validate(payload)

    payload = _payload()
    payload["duty_warden"] = "x" * 161
    with pytest.raises(ValidationError):
        AssignmentRosterV1.model_validate(payload)

    payload = _payload()
    payload["equipment"]["digital_camera"] = "invented"
    with pytest.raises(ValidationError):
        AssignmentRosterV1.model_validate(payload)

    payload = _payload()
    payload["zones"][0]["supervisor"] = _staff()
    assert AssignmentRosterV1.model_validate(payload).zones[0].supervisor is not None

