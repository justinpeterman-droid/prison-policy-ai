"""PostgreSQL browser contracts for guided incident creation and revisions."""
from datetime import date, time

from tests.support.web_browser import authenticate_browser, browser_headers


def test_browser_incident_crud_history_restore_and_staff_search(
    db_session,
    db_session_factory,
    api_client,
    fictional_staff_and_accounts,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    authenticate_browser(
        monkeypatch, api_client, db_session_factory, account
    )

    created = api_client.post(
        "/api/web/v1/incidents",
        json={
            "reporting_staff_ids": [str(account.staff_member_id)],
            "incident_number": "202608029",
            "incident_name": "  Barracks   4 Fight  ",
            "field_notes": "Fictional officer notes for the guided workflow.",
            "incident_date": "2026-08-20",
            "incident_time": "11:30",
            "facility": "Fictional Unit",
            "shift": "A",
            "location": "Barracks 4",
            "category": "inmate_fight",
        },
        headers=browser_headers(
            "request_web_incident_create",
            idempotency_key="web-incident-create-0001",
        ),
    )

    assert created.status_code == 201
    incident = created.get_json()["data"]
    assert incident["incident_number"] == "2026-08-029"
    assert incident["incident_name"] == "Barracks 4 Fight"
    assert incident["incident_date"] == date(2026, 8, 20).isoformat()
    assert incident["incident_time"] == time(11, 30).isoformat()
    assert incident["current_revision_number"] == 1
    assert incident["reporting_officers"][0]["staff_id"] == str(
        account.staff_member_id
    )

    incident_id = incident["incident_id"]
    detail = api_client.get(
        f"/api/web/v1/incidents/{incident_id}",
        headers=browser_headers("request_web_incident_detail"),
    )
    assert detail.status_code == 200
    assert detail.get_json()["data"]["field_notes"].startswith("Fictional")

    saved = api_client.patch(
        f"/api/web/v1/incidents/{incident_id}",
        json={
            "incident_number": incident["incident_number"],
            "incident_name": incident["incident_name"],
            "field_notes": "Fictional notes updated after reviewing the scene.",
            "facility": incident["facility"],
            "shift": incident["shift"],
            "location": incident["location"],
            "category": incident["category"],
            "classification": {},
            "extracted_facts": {},
            "gap_answers": {},
            "charges": [],
            "validation": {"facts_reviewed": True},
            "warnings": [],
            "base_revision_number": 1,
            "reason": "manual_save",
        },
        headers=browser_headers(
            "request_web_incident_save",
            idempotency_key="web-incident-save-0001",
            if_match=1,
        ),
    )
    assert saved.status_code == 200
    assert saved.get_json()["data"]["current_revision_number"] == 2

    revisions = api_client.get(
        f"/api/web/v1/incidents/{incident_id}/revisions",
        headers=browser_headers("request_web_incident_revisions"),
    )
    assert revisions.status_code == 200
    assert [
        item["revision_number"]
        for item in revisions.get_json()["data"]["items"]
    ] == [1, 2]

    restored = api_client.post(
        f"/api/web/v1/incidents/{incident_id}/restore",
        json={"revision_number": 1},
        headers=browser_headers(
            "request_web_incident_restore",
            idempotency_key="web-incident-restore-0001",
        ),
    )
    assert restored.status_code == 200
    assert restored.get_json()["data"]["current_revision_number"] == 3
    assert restored.get_json()["data"]["field_notes"].startswith(
        "Fictional officer"
    )

    staff = api_client.get(
        "/api/web/v1/staff?q=Alex",
        headers=browser_headers("request_web_staff_search"),
    )
    assert staff.status_code == 200
    assert any(
        item["staff_id"] == str(account.staff_member_id)
        for item in staff.get_json()["data"]["items"]
    )


def test_duplicate_incident_number_returns_stable_conflict(
    db_session,
    db_session_factory,
    api_client,
    fictional_staff_and_accounts,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    authenticate_browser(monkeypatch, api_client, db_session_factory, account)
    payload = {
        "reporting_staff_ids": [str(account.staff_member_id)],
        "incident_number": "2026-08-030",
        "incident_name": "Fictional Duplicate Check",
        "field_notes": "Fictional notes.",
    }
    first = api_client.post(
        "/api/web/v1/incidents",
        json=payload,
        headers=browser_headers(
            "request_web_incident_duplicate_first",
            idempotency_key="web-incident-duplicate-first",
        ),
    )
    second = api_client.post(
        "/api/web/v1/incidents",
        json=payload,
        headers=browser_headers(
            "request_web_incident_duplicate_second",
            idempotency_key="web-incident-duplicate-second",
        ),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "incident_number_conflict"


def test_browser_incident_write_requires_same_origin_csrf(
    db_session,
    db_session_factory,
    api_client,
    fictional_staff_and_accounts,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    authenticate_browser(monkeypatch, api_client, db_session_factory, account)

    response = api_client.post(
        "/api/web/v1/incidents",
        json={
            "reporting_staff_ids": [str(account.staff_member_id)],
            "field_notes": "Fictional notes.",
        },
        headers={
            "X-Client-Version": "1.0.0",
            "X-Request-ID": "request_web_incident_missing_csrf",
            "Idempotency-Key": "web-incident-missing-csrf",
        },
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_validation_failed"
