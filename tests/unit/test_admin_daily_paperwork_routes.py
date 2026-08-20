from datetime import UTC, date, datetime
from uuid import uuid4

from backend.paperwork.daily_templates import load_daily_template
from backend.paperwork.models import PaperworkKind, PaperworkView
from backend.webapp.web_api.admin_daily_paperwork import daily_record_data


def _roster_payload():
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
                    {"post_code": post["code"], "initial_staff": None, "rotation_staff": None}
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


def test_daily_record_response_exposes_template_revision_and_safe_coverage_metadata():
    staff_id = uuid4()
    now = datetime(2026, 8, 20, 14, 0, tzinfo=UTC)
    view = PaperworkView(
        record_id=uuid4(),
        kind=PaperworkKind.ASSIGNMENT_ROSTER,
        work_date=date(2026, 8, 20),
        shift="D",
        current_revision_number=3,
        payload=_roster_payload(),
        created_by_staff_member_id=staff_id,
        last_editor_staff_member_id=staff_id,
        created_at=now,
        updated_at=now,
    )

    data = daily_record_data(view)

    assert data["kind"] == "assignment_roster"
    assert data["revision"] == 3
    assert data["state"] == "needs_attention"
    assert data["warning_count"] > 0
    assert data["validation"]["coverage_warnings"][0]["code"] == "p1_unfilled"
    assert data["template"]["title"] == "Shift Assignment Roster"
    assert data["template"]["print_orientation"] == "landscape"
    assert "payload" in data
    assert "display_name_snapshot" not in repr(data["validation"])


def test_daily_record_summary_omits_payload_and_template_definition():
    staff_id = uuid4()
    now = datetime(2026, 8, 20, 14, 0, tzinfo=UTC)
    view = PaperworkView(
        record_id=uuid4(),
        kind=PaperworkKind.ASSIGNMENT_ROSTER,
        work_date=date(2026, 8, 20),
        shift="D",
        current_revision_number=1,
        payload=_roster_payload(),
        created_by_staff_member_id=staff_id,
        last_editor_staff_member_id=staff_id,
        created_at=now,
        updated_at=now,
    )

    summary = daily_record_data(view, include_payload=False)

    assert "payload" not in summary
    assert "template" not in summary
    assert summary["warning_count"] == len(summary["validation"]["coverage_warnings"])

