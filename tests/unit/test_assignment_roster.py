from copy import deepcopy
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import (
    AssignmentRosterV1,
    calculate_roster_coverage,
    prepare_copied_roster_payload,
    validate_daily_payload,
)
from backend.paperwork.daily_templates import DailyPaperworkKind, load_daily_template
from backend.paperwork.models import PaperworkKind, PaperworkView
from backend.paperwork.service import (
    PaperworkAlreadyExists,
    copy_previous_daily_record,
)


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


def test_roster_coverage_warns_for_unfilled_p1_without_mutating_assignments():
    payload = _payload()
    original = deepcopy(payload)

    warnings = calculate_roster_coverage(payload)

    expected_p1 = sum(
        post["priority"] == "P1"
        for zone in load_daily_template("assignment_roster").definition["zones"]
        for post in zone["posts"]
    )
    assert len(warnings) == expected_p1
    assert {warning.code for warning in warnings} == {"p1_unfilled"}
    assert all(warning.post_code and warning.zone_code for warning in warnings)
    assert not any("P2" in warning.message for warning in warnings)
    assert payload == original


def test_roster_coverage_reports_initial_and_rotation_duplicates_separately():
    payload = _payload()
    shared = _staff("Officer Morgan Lee")
    payload["zones"][0]["posts"][0]["initial_staff"] = shared
    payload["zones"][0]["posts"][1]["initial_staff"] = shared
    payload["zones"][0]["posts"][0]["rotation_staff"] = shared
    payload["zones"][0]["posts"][1]["rotation_staff"] = shared

    warnings = calculate_roster_coverage(payload)

    duplicate_codes = [warning.code for warning in warnings if "duplicate" in warning.code]
    assert duplicate_codes == [
        "duplicate_initial_assignment",
        "duplicate_rotation_assignment",
    ]
    assert all(
        warning.staff_id == UUID(shared["staff_id"])
        for warning in warnings
        if "duplicate" in warning.code
    )
    assert "Officer Morgan Lee" not in repr(warnings)


def test_copy_previous_roster_resets_completion_and_personal_fields_but_keeps_assignments():
    payload = _payload()
    assigned = _staff("Officer Avery Cole")
    payload["captain"] = _staff("Captain Casey Quinn")
    payload["lieutenant"] = _staff("Lt. Taylor Reed")
    payload["duty_warden"] = "Warden Fictional"
    payload["alternate_shift_supervisor"] = _staff("Sgt. Riley Jordan")
    payload["leave_entries"] = [{"staff": assigned, "leave_time": "1400", "leave_type": "Annual"}]
    payload["extra_assignments"] = [{"label": "Transport", "staff": assigned}]
    payload["zones"][0]["posts"][0]["initial_staff"] = assigned
    payload["briefing_minutes"] = "Fictional briefing note"
    payload["roll_call_completed"] = True
    payload["uniform_inspection_completed"] = True
    payload["equipment"] = {key: "yes" for key in payload["equipment"]}
    payload["briefing_guests"] = ["Fictional Guest"]
    payload["assigned_and_dismissed"] = True
    payload["lieutenant_signature_name"] = "Lt. Taylor Reed"

    copied = prepare_copied_roster_payload(
        payload,
        target_work_date="2026-08-21",
        shift="N",
    )

    assert copied.work_date.isoformat() == "2026-08-21"
    assert copied.shift == "N"
    assert copied.zones[0].posts[0].initial_staff.staff_id == UUID(assigned["staff_id"])
    assert copied.extra_assignments[0].label == "Transport"
    assert copied.extra_assignments[0].staff is None
    assert copied.captain is None
    assert copied.lieutenant is None
    assert copied.duty_warden is None
    assert copied.alternate_shift_supervisor is None
    assert copied.leave_entries == []
    assert copied.briefing_minutes == ""
    assert copied.roll_call_completed is False
    assert copied.uniform_inspection_completed is False
    assert set(copied.equipment.values()) == {"not_checked"}
    assert copied.briefing_guests == []
    assert copied.assigned_and_dismissed is False
    assert copied.lieutenant_signature_name is None


class _CopySession:
    def __init__(self, *results):
        self.results = iter(results)

    def scalar(self, _statement):
        return next(self.results)


def test_copy_previous_service_creates_revision_one_with_a_new_idempotency_key(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        kind=PaperworkKind.ASSIGNMENT_ROSTER.value,
        work_date=date(2026, 8, 19),
        shift="D",
        current_revision_number=4,
        current_payload=_payload(),
        created_by_staff_member_id=uuid4(),
    )
    actor = SimpleNamespace(account_id=uuid4(), staff_member_id=uuid4(), role="admin")
    session = _CopySession(None, source)
    captured = {}

    def save(_session, _actor, **kwargs):
        captured.update(kwargs)
        request = kwargs["request_model"]
        return PaperworkView(
            record_id=uuid4(),
            kind=PaperworkKind.ASSIGNMENT_ROSTER,
            work_date=request.work_date,
            shift=request.shift,
            current_revision_number=1,
            payload=request.payload,
            created_by_staff_member_id=actor.staff_member_id,
            last_editor_staff_member_id=actor.staff_member_id,
            created_at=datetime(2026, 8, 20, tzinfo=UTC),
            updated_at=datetime(2026, 8, 20, tzinfo=UTC),
        )

    monkeypatch.setattr("backend.paperwork.service.save_paperwork_record", save)

    copied = copy_previous_daily_record(
        session,
        actor,
        kind=PaperworkKind.ASSIGNMENT_ROSTER,
        target_work_date=date(2026, 8, 20),
        shift="D",
        idempotency_key="copy-roster-fictional-0001",
        request_id="request-copy-roster-fictional-0001",
        client_version="1.0.0",
    )

    assert copied.current_revision_number == 1
    assert copied.work_date == date(2026, 8, 20)
    assert captured["record_id"] is None
    assert captured["idempotency_key"] == "copy-roster-fictional-0001"
    assert captured["request_model"].base_revision_number is None


def test_copy_previous_service_returns_existing_record_identity_in_conflict():
    existing = SimpleNamespace(id=uuid4())
    actor = SimpleNamespace(account_id=uuid4(), staff_member_id=uuid4(), role="admin")

    with pytest.raises(PaperworkAlreadyExists) as conflict:
        copy_previous_daily_record(
            _CopySession(existing),
            actor,
            kind=PaperworkKind.ASSIGNMENT_ROSTER,
            target_work_date=date(2026, 8, 20),
            shift="D",
            idempotency_key="copy-roster-fictional-0002",
            request_id="request-copy-roster-fictional-0002",
            client_version="1.0.0",
        )

    assert conflict.value.record_id == existing.id
