from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import UniformInspectionV1, build_uniform_rows_from_roster
from backend.paperwork.daily_templates import load_daily_template


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


def test_uniform_rows_are_unique_blank_and_preserve_roster_print_order():
    definition = load_daily_template("assignment_roster").definition
    supervisor = _staff("Sgt. Riley Jordan")
    first = _staff("Officer Avery Cole")
    second = _staff("Officer Morgan Lee")
    roster = {
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
                "supervisor": supervisor if index == 0 else None,
                "posts": [
                    {
                        "post_code": post["code"],
                        "initial_staff": first if index == 0 and post_index == 0 else None,
                        "rotation_staff": second if index == 0 and post_index == 0 else (
                            first if index == 0 and post_index == 1 else None
                        ),
                    }
                    for post_index, post in enumerate(zone["posts"])
                ],
            }
            for index, zone in enumerate(definition["zones"])
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
    record_id = uuid4()

    inspection = build_uniform_rows_from_roster(
        roster,
        roster_record_id=record_id,
        roster_revision_number=3,
    )

    assert inspection.roster_record_id == record_id
    assert inspection.roster_revision_number == 3
    assert [row.staff.display_name_snapshot for row in inspection.rows] == [
        "Sgt. Riley Jordan",
        "Officer Avery Cole",
        "Officer Morgan Lee",
    ]
    assert all(row.comments == "" for row in inspection.rows)
    assert all(
        value is None
        for row in inspection.rows
        for value in (row.shirt, row.pants, row.shoes, row.cap, row.coat, row.id, row.hair, row.nails)
    )
