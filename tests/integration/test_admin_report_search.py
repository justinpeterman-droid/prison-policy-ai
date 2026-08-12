"""Admin structured report search: filters, pagination, and bounded audit."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.persistence.models import AuditEvent
from tests.integration.identity_fixtures import bearer_headers, issue_fictional_tokens
from tests.support.reporting import make_incident, make_report


ADMIN_PIN = "Q7W9E2"


@pytest.fixture(autouse=True)
def _fictional_access_api_environment(monkeypatch, identity_fixed_now):
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.example.gov")
    import backend.webapp.api_v1.middleware as middleware
    import backend.webapp.api_v1.auth as auth_api
    import backend.webapp.api_v1.admin_reports as admin_reports_api

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)
    monkeypatch.setattr(auth_api, "datetime", _FixedDateTime)
    monkeypatch.setattr(admin_reports_api, "datetime", _FixedDateTime)


def _headers(headers, key):
    return headers | {"Idempotency-Key": key, "X-Request-ID": f"request_{key}"}


def _confirm_admin_pin(api_client, headers, purpose, key):
    response = api_client.post(
        "/api/v1/auth/admin-step-up",
        headers=_headers(headers, key),
        json={"pin": ADMIN_PIN, "purpose": purpose},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["data"]


@pytest.fixture
def elevated_admin_bearer_headers(api_client, admin_bearer_headers, db_session):
    db_session.commit()
    _confirm_admin_pin(api_client, admin_bearer_headers, "admin_center", "admin-elevate-search-0001")
    return admin_bearer_headers


def _headers_for_account(db_session, account, now, suffix):
    tokens = issue_fictional_tokens(
        db_session, account=account, device_id=f"device-fictional-{suffix}-0001", now=now)
    return bearer_headers(tokens)


def test_admin_search_filters_structured_inmate_adc_number(
    db_session, api_client, elevated_admin_bearer_headers, fictional_staff_and_accounts,
    identity_fixed_now,
):
    matching_incident = make_incident(
        db_session, fictional_staff_and_accounts.preparer, identity_fixed_now)
    matching_incident.extracted_facts = {"persons": [
        {"role": "inmate", "first": "Jordan", "last": "Rivera", "adc_number": "ADC900001"},
    ]}
    matching_report = make_report(
        db_session, incident=matching_incident,
        owner=fictional_staff_and_accounts.user, preparer=fictional_staff_and_accounts.preparer,
        now=identity_fixed_now,
    )
    other_incident = make_incident(
        db_session, fictional_staff_and_accounts.preparer,
        identity_fixed_now - timedelta(days=1))
    other_incident.extracted_facts = {"persons": [
        {"role": "inmate", "first": "Casey", "last": "Nguyen", "adc_number": "ADC900002"},
    ]}
    make_report(
        db_session, incident=other_incident,
        owner=fictional_staff_and_accounts.unrelated,
        preparer=fictional_staff_and_accounts.preparer,
        now=identity_fixed_now - timedelta(days=1),
    )
    db_session.commit()

    response = api_client.get(
        "/api/v1/admin/reports?inmate_adc_number=ADC900001",
        headers=elevated_admin_bearer_headers,
    )

    assert response.status_code == 200
    items = response.json["data"]["items"]
    assert [item["report_id"] for item in items] == [str(matching_report.id)]
    assert all(item["inmate_adc_numbers"] == ["ADC900001"] for item in items)


def test_admin_search_writes_one_bounded_audit_event_with_names_only(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers,
    fictional_staff_and_accounts, identity_fixed_now,
):
    incident = make_incident(db_session, fictional_staff_and_accounts.preparer, identity_fixed_now)
    incident.category = "fictional_use_of_force"
    make_report(
        db_session, incident=incident, owner=fictional_staff_and_accounts.user,
        preparer=fictional_staff_and_accounts.preparer, now=identity_fixed_now,
    )
    db_session.commit()

    response = api_client.get(
        "/api/v1/admin/reports?category=fictional_use_of_force&status=in_progress",
        headers=elevated_admin_bearer_headers,
    )

    assert response.status_code == 200
    with db_session_factory() as verification:
        events = verification.scalars(select(AuditEvent).where(
            AuditEvent.action == "admin.report_search",
        )).all()
        assert len(events) == 1
        details = events[0].details
        assert set(details) == {"filters", "result_count"}
        assert set(details["filters"]) == {"category", "status"}
        assert "fictional_use_of_force" not in details["filters"]
        assert details["result_count"] == len(response.json["data"]["items"])


def test_admin_search_pagination_default_and_max_page_size(
    db_session, api_client, elevated_admin_bearer_headers,
):
    response = api_client.get(
        "/api/v1/admin/reports?limit=101", headers=elevated_admin_bearer_headers)

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_admin_search_rejects_unknown_field(
    db_session, api_client, elevated_admin_bearer_headers,
):
    response = api_client.get(
        "/api/v1/admin/reports?not_a_real_filter=1", headers=elevated_admin_bearer_headers)

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_admin_search_rejects_empty_string_field(
    db_session, api_client, elevated_admin_bearer_headers,
):
    response = api_client.get(
        "/api/v1/admin/reports?category=", headers=elevated_admin_bearer_headers)

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_admin_search_cursor_pagination_walks_all_results(
    db_session, api_client, elevated_admin_bearer_headers, fictional_staff_and_accounts,
    identity_fixed_now,
):
    incident_a = make_incident(
        db_session, fictional_staff_and_accounts.preparer, identity_fixed_now)
    report_a = make_report(
        db_session, incident=incident_a, owner=fictional_staff_and_accounts.user,
        preparer=fictional_staff_and_accounts.preparer, now=identity_fixed_now,
    )
    incident_b = make_incident(
        db_session, fictional_staff_and_accounts.preparer,
        identity_fixed_now - timedelta(hours=1))
    report_b = make_report(
        db_session, incident=incident_b, owner=fictional_staff_and_accounts.unrelated,
        preparer=fictional_staff_and_accounts.preparer,
        now=identity_fixed_now - timedelta(hours=1),
    )
    db_session.commit()

    first = api_client.get(
        "/api/v1/admin/reports?limit=1", headers=elevated_admin_bearer_headers)
    second = api_client.get(
        "/api/v1/admin/reports?limit=1&cursor=" + first.json["data"]["next_cursor"],
        headers=elevated_admin_bearer_headers,
    )

    assert first.status_code == second.status_code == 200
    assert first.json["data"]["next_cursor"]
    assert {
        first.json["data"]["items"][0]["report_id"],
        second.json["data"]["items"][0]["report_id"],
    } == {str(report_a.id), str(report_b.id)}
