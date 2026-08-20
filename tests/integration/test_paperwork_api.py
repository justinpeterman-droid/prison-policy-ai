from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select

from backend.paperwork.count_sheet import AREA_ROWS, HOUSING_COLUMNS, OPERATIONAL_FIELDS
from backend.paperwork.daily_templates import load_daily_template
from backend.persistence.models.paperwork import PaperworkRecord, PaperworkRevision
from backend.persistence.models.security import AuditEvent
from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.web_browser import authenticate_browser, browser_headers


def _count_payload(value: int = 4):
    cells = {
        area: {column: None for column in HOUSING_COLUMNS}
        for area in AREA_ROWS
    }
    cells["A/W Office"]["1"] = value
    return {
        "schema_version": 1,
        "count_started": "14:00:00",
        "count_ended": "14:15:00",
        "cells": cells,
        "in_housing": {
            column: (6 if column == "1" else None)
            for column in HOUSING_COLUMNS
        },
        "operational": {
            field: (value + 6 if field == "on_site" else None)
            for field in OPERATIONAL_FIELDS
        },
    }


def _save_body(*, value: int = 4, base_revision_number=None, reason="manual_save"):
    return {
        "schema_version": 1,
        "work_date": "2026-08-19",
        "shift": "A",
        "payload": _count_payload(value),
        "base_revision_number": base_revision_number,
        "reason": reason,
    }


def _assert_status(response, expected: int):
    assert response.status_code == expected, response.get_json()


def _roster_body():
    definition = load_daily_template("assignment_roster").definition
    payload = {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "A",
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
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "A",
        "payload": payload,
        "base_revision_number": None,
        "reason": "manual_save",
    }


def _authenticate_admin(
    monkeypatch,
    api_client,
    db_session,
    db_session_factory,
    account,
    *,
    device_id: str,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=account,
        device_id=device_id,
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=tokens.session_id,
        device_id=device_id,
    )


def _elevate_admin(api_client):
    response = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-count-boundary-elevation"),
    )
    _assert_status(response, 200)


def test_count_sheet_api_create_replay_save_history_restore_and_list(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    db_session.commit()
    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.user)

    structure = api_client.get(
        "/api/web/v1/paperwork/count-sheets/structure",
        headers=browser_headers("request_count_structure"),
    )
    _assert_status(structure, 200)
    assert structure.get_json()["data"]["columns"] == list(HOUSING_COLUMNS)
    assert structure.get_json()["data"]["areas"] == list(AREA_ROWS)

    created = api_client.post(
        "/api/web/v1/paperwork/count-sheets",
        json=_save_body(),
        headers=browser_headers(
            "request_count_create_0001",
            idempotency_key="count-sheet-create-0001",
        ),
    )
    _assert_status(created, 201)
    replayed = api_client.post(
        "/api/web/v1/paperwork/count-sheets",
        json=_save_body(),
        headers=browser_headers(
            "request_count_create_replay",
            idempotency_key="count-sheet-create-0001",
        ),
    )
    _assert_status(replayed, 201)

    record = created.get_json()["data"]
    assert replayed.get_json()["data"]["record_id"] == record["record_id"]
    assert record["kind"] == "count_sheet"
    assert record["work_date"] == "2026-08-19"
    assert record["current_revision_number"] == 1
    assert record["validation"]["row_totals"]["A/W Office"] == 4
    assert record["validation"]["out_of_housing"]["1"] == 4
    assert record["validation"]["unit_totals"]["1"] == 10
    assert record["validation"]["housing_total"] == 10
    assert record["validation"]["operational_total"] == 10
    assert record["validation"]["difference"] == 0
    assert record["validation"]["reconciled"] is True

    record_id = record["record_id"]
    fetched = api_client.get(
        f"/api/web/v1/paperwork/count-sheets/{record_id}",
        headers=browser_headers("request_count_get"),
    )
    listed = api_client.get(
        "/api/web/v1/paperwork?kind=count_sheet",
        headers=browser_headers("request_count_list"),
    )
    _assert_status(fetched, 200)
    _assert_status(listed, 200)
    assert fetched.get_json()["data"]["payload"] == record["payload"]
    assert [item["record_id"] for item in listed.get_json()["data"]["items"]] == [record_id]

    updated = api_client.patch(
        f"/api/web/v1/paperwork/count-sheets/{record_id}",
        json=_save_body(value=7, base_revision_number=1, reason="autosave"),
        headers=browser_headers(
            "request_count_save_0002",
            idempotency_key="count-sheet-save-0002",
            if_match=1,
        ),
    )
    _assert_status(updated, 200)
    assert updated.get_json()["data"]["current_revision_number"] == 2
    assert updated.get_json()["data"]["validation"]["difference"] == 0

    stale = api_client.patch(
        f"/api/web/v1/paperwork/count-sheets/{record_id}",
        json=_save_body(value=9, base_revision_number=1),
        headers=browser_headers(
            "request_count_stale_0003",
            idempotency_key="count-sheet-stale-0003",
            if_match=1,
        ),
    )
    _assert_status(stale, 409)
    assert stale.get_json()["error"]["code"] == "revision_conflict"
    assert stale.get_json()["error"]["details"] == {"current_revision_number": 2}
    assert "local values" in stale.get_json()["error"]["message"].lower()

    revisions = api_client.get(
        f"/api/web/v1/paperwork/count-sheets/{record_id}/revisions",
        headers=browser_headers("request_count_revisions"),
    )
    _assert_status(revisions, 200)
    assert [item["revision_number"] for item in revisions.get_json()["data"]["items"]] == [1, 2]
    assert revisions.get_json()["data"]["items"][1]["changed_fields"] == [
        "payload.cells",
        "payload.operational",
    ]

    restored = api_client.post(
        f"/api/web/v1/paperwork/count-sheets/{record_id}/restore",
        json={"revision_number": 1},
        headers=browser_headers(
            "request_count_restore_0004",
            idempotency_key="count-sheet-restore-0004",
        ),
    )
    _assert_status(restored, 200)
    assert restored.get_json()["data"]["current_revision_number"] == 3
    assert restored.get_json()["data"]["payload"]["cells"]["A/W Office"]["1"] == 4

    with db_session_factory() as session:
        assert session.scalar(select(PaperworkRecord).where(
            PaperworkRecord.id == UUID(record_id)
        )).current_revision_number == 3
        assert len(list(session.scalars(select(PaperworkRevision).where(
            PaperworkRevision.record_id == UUID(record_id)
        )).all())) == 3


def test_count_sheet_api_requires_session_csrf_and_authorized_relationship(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    db_session.commit()

    unauthenticated = api_client.get(
        "/api/web/v1/paperwork?kind=count_sheet",
        headers=browser_headers("request_count_unauthenticated"),
    )
    _assert_status(unauthenticated, 401)

    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.user)
    headers = browser_headers(
        "request_count_csrf_missing",
        idempotency_key="count-sheet-csrf-0001",
    )
    headers.pop("X-CSRF-Token")
    csrf = api_client.post(
        "/api/web/v1/paperwork/count-sheets",
        json=_save_body(),
        headers=headers,
    )
    _assert_status(csrf, 403)
    assert csrf.get_json()["error"]["code"] == "csrf_validation_failed"

    created = api_client.post(
        "/api/web/v1/paperwork/count-sheets",
        json=_save_body(),
        headers=browser_headers(
            "request_count_access_create",
            idempotency_key="count-sheet-access-0002",
        ),
    )
    _assert_status(created, 201)
    record_id = created.get_json()["data"]["record_id"]

    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.unrelated)
    concealed = api_client.get(
        f"/api/web/v1/paperwork/count-sheets/{record_id}",
        headers=browser_headers("request_count_unrelated"),
    )
    _assert_status(concealed, 404)

    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.admin)
    admin = api_client.get(
        f"/api/web/v1/paperwork/count-sheets/{record_id}",
        headers=browser_headers("request_count_admin"),
    )
    _assert_status(admin, 200)
    assert admin.get_json()["data"]["record_id"] == record_id


def test_count_sheet_routes_conceal_daily_paperwork_from_unelevated_admin(
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
        device_id="device-count-boundary-creator",
    )
    _elevate_admin(api_client)
    created = api_client.post(
        "/api/web/v1/admin/paperwork/daily/assignment_roster",
        json=_roster_body(),
        headers=browser_headers(
            "request-count-boundary-create-daily",
            idempotency_key="count-boundary-create-daily",
        ),
    )
    _assert_status(created, 201)
    daily_record_id = created.get_json()["data"]["record_id"]

    _authenticate_admin(
        monkeypatch,
        api_client,
        db_session,
        db_session_factory,
        fictional_admin_account,
        device_id="device-count-boundary-attacker",
    )
    attempts = [
        api_client.get(
            f"/api/web/v1/paperwork/count-sheets/{daily_record_id}",
            headers=browser_headers("request-count-boundary-get"),
        ),
        api_client.patch(
            f"/api/web/v1/paperwork/count-sheets/{daily_record_id}",
            json=_save_body(base_revision_number=1),
            headers=browser_headers(
                "request-count-boundary-patch",
                idempotency_key="count-boundary-patch",
                if_match=1,
            ),
        ),
        api_client.get(
            f"/api/web/v1/paperwork/count-sheets/{daily_record_id}/revisions",
            headers=browser_headers("request-count-boundary-revisions"),
        ),
        api_client.post(
            f"/api/web/v1/paperwork/count-sheets/{daily_record_id}/restore",
            json={"revision_number": 1},
            headers=browser_headers(
                "request-count-boundary-restore",
                idempotency_key="count-boundary-restore",
            ),
        ),
        api_client.post(
            f"/api/web/v1/paperwork/count-sheets/{daily_record_id}/actions",
            json={"action": "print"},
            headers=browser_headers(
                "request-count-boundary-action",
                idempotency_key="count-boundary-action",
            ),
        ),
    ]

    for response in attempts:
        _assert_status(response, 404)
        assert response.get_json()["error"]["code"] == "not_found"

    with db_session_factory() as session:
        record = session.get(PaperworkRecord, UUID(daily_record_id))
        assert record is not None
        assert record.kind == "assignment_roster"
        assert record.current_revision_number == 1
        assert session.scalar(select(AuditEvent).where(
            AuditEvent.target_id == UUID(daily_record_id),
            AuditEvent.action == "paperwork.action_recorded",
        )) is None


def test_count_sheet_actions_are_closed_and_audited_without_payload_content(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    db_session.commit()
    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.user)
    created = api_client.post(
        "/api/web/v1/paperwork/count-sheets",
        json=_save_body(),
        headers=browser_headers(
            "request_count_action_create",
            idempotency_key="count-sheet-action-create",
        ),
    )
    _assert_status(created, 201)
    record_id = created.get_json()["data"]["record_id"]

    recorded = api_client.post(
        f"/api/web/v1/paperwork/count-sheets/{record_id}/actions",
        json={"action": "print"},
        headers=browser_headers(
            "request_count_action_print",
            idempotency_key="count-sheet-action-print",
        ),
    )
    replayed = api_client.post(
        f"/api/web/v1/paperwork/count-sheets/{record_id}/actions",
        json={"action": "print"},
        headers=browser_headers(
            "request_count_action_print_replay",
            idempotency_key="count-sheet-action-print",
        ),
    )
    rejected = api_client.post(
        f"/api/web/v1/paperwork/count-sheets/{record_id}/actions",
        json={"action": "delete"},
        headers=browser_headers(
            "request_count_action_invalid",
            idempotency_key="count-sheet-action-invalid",
        ),
    )

    _assert_status(recorded, 200)
    _assert_status(replayed, 200)
    _assert_status(rejected, 400)
    assert replayed.get_json()["data"] == recorded.get_json()["data"]
    assert recorded.get_json()["data"] == {
        "recorded": True,
        "record_id": record_id,
        "kind": "count_sheet",
        "revision_number": 1,
        "action": "print",
    }

    with db_session_factory() as session:
        events = list(session.scalars(
            select(AuditEvent).where(
                AuditEvent.target_id == UUID(record_id),
                AuditEvent.action == "paperwork.action_recorded",
            )
        ).all())
    assert len(events) == 1
    assert events[0].details == {
        "record_id": record_id,
        "kind": "count_sheet",
        "revision_number": 1,
        "paperwork_action": "print",
    }
    serialized = repr(events[0].details)
    assert "A/W Office" not in serialized
    assert "cells" not in serialized
