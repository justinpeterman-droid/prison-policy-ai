from datetime import UTC, date, datetime

from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.reporting import make_incident, make_report
from tests.support.web_browser import authenticate_browser, browser_headers


def _authenticate_and_elevate(
    monkeypatch,
    api_client,
    db_session,
    db_session_factory,
    account,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=account,
        device_id="device-fictional-admin-incidents",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-incidents",
    )
    response = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-incidents-elevation"),
    )
    assert response.status_code == 200, response.get_json()


def test_admin_incident_library_returns_one_incident_with_separate_records_status(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    incident = make_incident(
        db_session,
        accounts.preparer,
        reporting_staff_ids=(accounts.user.staff_member_id, accounts.unrelated.staff_member_id),
    )
    incident.incident_number = "2026-08-029"
    incident.incident_name = "Barracks 4 Fight"
    incident.incident_date = date(2026, 8, 19)
    incident.facility = "North Central Unit"
    incident.location = "Barracks 4"
    incident.category = "fight"
    incident.shift = "A"
    make_report(
        db_session,
        incident=incident,
        owner=accounts.user,
        preparer=accounts.preparer,
    )
    make_report(
        db_session,
        incident=incident,
        owner=accounts.unrelated,
        preparer=accounts.preparer,
    )
    db_session.commit()

    _authenticate_and_elevate(
        monkeypatch,
        api_client,
        db_session,
        db_session_factory,
        accounts.admin,
    )

    response = api_client.get(
        "/api/web/v1/admin/incidents"
        f"?incident_number=2026-08-029"
        f"&reporting_staff_id={accounts.user.staff_member_id}"
        f"&prepared_by_staff_id={accounts.preparer.staff_member_id}"
        "&records_status=in_progress",
        headers=browser_headers("request-admin-incidents-list"),
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["incident_id"] == str(incident.id)
    assert item["incident_number"] == "2026-08-029"
    assert item["incident_name"] == "Barracks 4 Fight"
    assert item["records_status"] == "in_progress"
    assert item["officer_report_count"] == 2
    assert len(item["reporting_officers"]) == 2
    assert len(item["preparers"]) == 1
    assert item["preparers"][0]["staff_id"] == str(accounts.preparer.staff_member_id)
    assert set(item["progress"]) == {"code", "label", "blocking_count"}
    assert data["next_cursor"] is None


def test_regular_user_cannot_list_all_incidents(
    api_client,
    db_session,
    db_session_factory,
    fictional_user_account,
    monkeypatch,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_user_account,
        device_id="device-fictional-user-admin-incidents",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_user_account,
        session_id=tokens.session_id,
        device_id="device-fictional-user-admin-incidents",
    )

    response = api_client.get(
        "/api/web/v1/admin/incidents",
        headers=browser_headers("request-user-admin-incidents-denied"),
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "permission_denied"
