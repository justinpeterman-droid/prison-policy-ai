from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from backend.paperwork.daily_templates import load_daily_template
from backend.persistence.models.paperwork import PaperworkRecord, PaperworkRevision
from backend.persistence.models.security import AuditEvent
from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.web_browser import authenticate_browser, browser_headers


def _roster_payload(work_date="2026-08-20", shift="D"):
    definition = load_daily_template("assignment_roster").definition
    return {
        "schema_version": 1,
        "work_date": work_date,
        "shift": shift,
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


def _save_body(*, work_date="2026-08-20", shift="D", base=None, reason="manual_save"):
    return {
        "schema_version": 1,
        "work_date": work_date,
        "shift": shift,
        "payload": _roster_payload(work_date, shift),
        "base_revision_number": base,
        "reason": reason,
    }


def _elevate(api_client):
    response = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-daily-elevation"),
    )
    assert response.status_code == 200, response.get_json()


def _authenticate_admin(
    monkeypatch,
    api_client,
    db_session,
    db_session_factory,
    account,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=account,
        device_id="device-fictional-daily-admin",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=tokens.session_id,
        device_id="device-fictional-daily-admin",
    )


def test_daily_paperwork_requires_admin_elevation(
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
    fictional_user_account,
    monkeypatch,
):
    db_session.commit()
    authenticate_browser(monkeypatch, api_client, db_session_factory, fictional_user_account)
    user = api_client.get(
        "/api/web/v1/admin/paperwork/daily?work_date=2026-08-20&shift=D",
        headers=browser_headers("request-daily-user-denied"),
    )
    assert user.status_code == 403

    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_admin_account,
        device_id="device-fictional-daily-admin",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_admin_account,
        session_id=tokens.session_id,
        device_id="device-fictional-daily-admin",
    )
    locked = api_client.get(
        "/api/web/v1/admin/paperwork/daily?work_date=2026-08-20&shift=D",
        headers=browser_headers("request-daily-admin-locked"),
    )
    assert locked.status_code == 403
    assert locked.get_json()["error"]["code"] == "admin_elevation_required"


def test_daily_roster_create_save_reopen_revision_copy_derive_and_print_audit(
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
    monkeypatch,
):
    _authenticate_admin(
        monkeypatch,
        api_client,
        db_session,
        db_session_factory,
        fictional_admin_account,
    )
    _elevate(api_client)

    created = api_client.post(
        "/api/web/v1/admin/paperwork/daily/assignment_roster",
        json=_save_body(),
        headers=browser_headers(
            "request-daily-create-roster",
            idempotency_key="daily-create-roster-0001",
        ),
    )
    assert created.status_code == 201, created.get_json()
    record = created.get_json()["data"]
    record_id = record["record_id"]
    assert record["revision"] == 1
    assert record["state"] == "needs_attention"
    assert record["warning_count"] > 0

    listed = api_client.get(
        "/api/web/v1/admin/paperwork/daily?work_date=2026-08-20&shift=D",
        headers=browser_headers("request-daily-list-roster"),
    )
    assert listed.status_code == 200, listed.get_json()
    assert [item["record_id"] for item in listed.get_json()["data"]["items"]] == [record_id]
    assert "payload" not in listed.get_json()["data"]["items"][0]

    changed = _save_body(base=1, reason="autosave")
    changed["payload"]["briefing_minutes"] = "Fictional roll-call note."
    updated = api_client.patch(
        f"/api/web/v1/admin/paperwork/daily/assignment_roster/{record_id}",
        json=changed,
        headers=browser_headers(
            "request-daily-save-roster",
            idempotency_key="daily-save-roster-0002",
            if_match=1,
        ),
    )
    assert updated.status_code == 200, updated.get_json()
    assert updated.get_json()["data"]["revision"] == 2

    stale = api_client.patch(
        f"/api/web/v1/admin/paperwork/daily/assignment_roster/{record_id}",
        json=_save_body(base=1),
        headers=browser_headers(
            "request-daily-stale-roster",
            idempotency_key="daily-stale-roster-0003",
            if_match=1,
        ),
    )
    assert stale.status_code == 409
    assert stale.get_json()["error"]["code"] == "revision_conflict"

    revisions = api_client.get(
        f"/api/web/v1/admin/paperwork/daily/assignment_roster/{record_id}/revisions",
        headers=browser_headers("request-daily-roster-revisions"),
    )
    assert revisions.status_code == 200, revisions.get_json()
    assert [item["revision_number"] for item in revisions.get_json()["data"]["items"]] == [1, 2]

    action = api_client.post(
        f"/api/web/v1/admin/paperwork/daily/assignment_roster/{record_id}/actions",
        json={"action": "print"},
        headers=browser_headers(
            "request-daily-roster-print",
            idempotency_key="daily-roster-print-0004",
        ),
    )
    assert action.status_code == 200, action.get_json()

    copied = api_client.post(
        "/api/web/v1/admin/paperwork/daily/assignment_roster/copy-previous",
        json={"target_work_date": "2026-08-21", "shift": "D"},
        headers=browser_headers(
            "request-daily-copy-roster",
            idempotency_key="daily-copy-roster-0005",
        ),
    )
    assert copied.status_code == 201, copied.get_json()
    assert copied.get_json()["data"]["work_date"] == "2026-08-21"
    assert copied.get_json()["data"]["revision"] == 1
    assert copied.get_json()["data"]["payload"]["briefing_minutes"] == ""

    uniform = api_client.post(
        f"/api/web/v1/admin/paperwork/daily/assignment-roster/{record_id}/uniform-inspection",
        json={"target_work_date": "2026-08-20", "shift": "D"},
        headers=browser_headers(
            "request-daily-derive-uniform",
            idempotency_key="daily-derive-uniform-0006",
        ),
    )
    assert uniform.status_code == 201, uniform.get_json()
    assert uniform.get_json()["data"]["kind"] == "uniform_inspection"
    assert uniform.get_json()["data"]["payload"]["roster_record_id"] == record_id

    with db_session_factory() as session:
        stored = session.scalar(select(PaperworkRecord).where(PaperworkRecord.id == UUID(record_id)))
        assert stored.current_revision_number == 2
        assert len(list(session.scalars(select(PaperworkRevision).where(
            PaperworkRevision.record_id == UUID(record_id)
        )).all())) == 2
        events = list(session.scalars(select(AuditEvent).where(
            AuditEvent.target_id == UUID(record_id)
        )).all())
    assert any(event.action == "paperwork.action_recorded" for event in events)
    assert all("Fictional roll-call note" not in repr(event.details) for event in events)


def test_daily_request_rejects_payload_scope_mismatch_and_unknown_fields(
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
    monkeypatch,
):
    _authenticate_admin(
        monkeypatch,
        api_client,
        db_session,
        db_session_factory,
        fictional_admin_account,
    )
    _elevate(api_client)

    mismatched = _save_body()
    mismatched["payload"]["shift"] = "N"
    response = api_client.post(
        "/api/web/v1/admin/paperwork/daily/assignment_roster",
        json=mismatched,
        headers=browser_headers(
            "request-daily-mismatched-scope",
            idempotency_key="daily-mismatched-scope-0001",
        ),
    )
    assert response.status_code == 400

    invalid_copy = api_client.post(
        "/api/web/v1/admin/paperwork/daily/assignment_roster/copy-previous",
        json={"target_work_date": "2026-08-21", "shift": "D", "unexpected": True},
        headers=browser_headers(
            "request-daily-invalid-copy",
            idempotency_key="daily-invalid-copy-0002",
        ),
    )
    assert invalid_copy.status_code == 400
