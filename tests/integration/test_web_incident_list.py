"""PostgreSQL and cookie-API contracts for the incident-centered library."""
from contextlib import contextmanager
from datetime import date, timedelta
from uuid import UUID, uuid4

from backend.identity.browser_sessions import BrowserActor
from backend.persistence.models.forms import (
    DocumentActionEvent,
    FormTemplate,
    IncidentPacketItem,
)
from backend.persistence.models.reporting import Incident, IncidentRevision
from backend.webapp.web_api import middleware as web_middleware
from backend.webapp.web_api.middleware import ACCESS_COOKIE
from tests.support.reporting import make_report


SUMMARY_KEYS = {
    "incident_id",
    "incident_number",
    "incident_name",
    "incident_date",
    "category",
    "location",
    "reporting_officers",
    "relationship",
    "progress",
    "officer_report_count",
    "required_paperwork_count",
    "updated_at",
}


def _browser_actor(account) -> BrowserActor:
    return BrowserActor(
        account_id=account.id,
        staff_member_id=account.staff_member_id,
        session_id=uuid4(),
        role=account.role,
        auth_version=account.auth_version,
        must_change_pin=account.must_change_pin,
    )


def _authenticate_browser(
    monkeypatch,
    api_client,
    db_session_factory,
    account,
) -> None:
    @contextmanager
    def request_scope():
        session = db_session_factory()
        try:
            yield session
        finally:
            session.close()

    actor = _browser_actor(account)
    monkeypatch.setattr(web_middleware, "session_scope", request_scope)
    monkeypatch.setattr(
        web_middleware,
        "resolve_browser_actor",
        lambda _db, *, access_token, now: actor,
    )
    api_client.set_cookie(ACCESS_COOKIE, "fictional-browser-access")


def _incident(
    session,
    *,
    account,
    reporting_accounts,
    now,
    number,
    name,
    category,
    location,
    incident_date,
):
    """Insert revision one with its final snapshot; revisions are append-only."""
    field_notes = "Fictional field notes for incident library tests."
    incident = Incident(
        created_by_account_id=account.id,
        created_by_staff_member_id=account.staff_member_id,
        status="in_progress",
        current_revision_number=1,
        incident_number=number,
        incident_name=name,
        incident_date=incident_date,
        facility="Fictional Unit",
        shift="A",
        location=location,
        category=category,
        field_notes=field_notes,
        classification={},
        extracted_facts={},
        gap_answers={},
        charges=[],
        validation={},
        created_at=now,
        updated_at=now,
    )
    session.add(incident)
    session.flush()

    session.add(IncidentRevision(
        incident_id=incident.id,
        revision_number=1,
        editor_account_id=account.id,
        editor_staff_member_id=account.staff_member_id,
        snapshot={
            "schema_version": 1,
            "incident_number": number,
            "incident_name": name,
            "incident_date": incident_date.isoformat(),
            "field_notes": field_notes,
            "facility": incident.facility,
            "shift": incident.shift,
            "category": category,
            "location": location,
            "server_metadata": {
                "reporting_staff_ids": [
                    str(value.staff_member_id) for value in reporting_accounts
                ]
            },
        },
        changed_fields={
            "fields": [
                "category",
                "field_notes",
                "incident_date",
                "incident_name",
                "incident_number",
                "location",
            ]
        },
        reason="manual_save",
        client_version="1.0.0",
        request_id=f"request_fixture_incident_library_{number.replace('-', '_')}",
        created_at=now,
    ))
    session.flush()
    return incident


def _seed_library(db_session, fictional_staff_and_accounts, identity_fixed_now):
    accounts = fictional_staff_and_accounts
    base = identity_fixed_now

    reporting_only = _incident(
        db_session,
        account=accounts.user,
        reporting_accounts=[accounts.user],
        now=base + timedelta(minutes=1),
        number="2026-08-101",
        name="North Hall Contact",
        category="conduct",
        location="North Hall",
        incident_date=date(2026, 8, 10),
    )
    make_report(
        db_session,
        incident=reporting_only,
        owner=accounts.user,
        preparer=accounts.preparer,
        now=base + timedelta(minutes=1),
    )

    prepared_only = _incident(
        db_session,
        account=accounts.preparer,
        reporting_accounts=[accounts.preparer],
        now=base + timedelta(minutes=2),
        number="2026-08-102",
        name="South Hall Review",
        category="medical",
        location="South Hall",
        incident_date=date(2026, 8, 11),
    )
    make_report(
        db_session,
        incident=prepared_only,
        owner=accounts.preparer,
        preparer=accounts.user,
        now=base + timedelta(minutes=2),
    )

    both = _incident(
        db_session,
        account=accounts.user,
        reporting_accounts=[accounts.user],
        now=base + timedelta(minutes=3),
        number="2026-08-103",
        name="East Hall Review",
        category="use_of_force",
        location="East Hall",
        incident_date=date(2026, 8, 12),
    )
    first = make_report(
        db_session,
        incident=both,
        owner=accounts.preparer,
        preparer=accounts.user,
        now=base + timedelta(minutes=3),
    )
    make_report(
        db_session,
        incident=both,
        owner=accounts.user,
        preparer=accounts.user,
        now=base + timedelta(minutes=4),
    )

    hidden = _incident(
        db_session,
        account=accounts.unrelated,
        reporting_accounts=[accounts.unrelated],
        now=base + timedelta(minutes=4),
        number="2026-08-104",
        name="West Hall Restricted",
        category="evidence",
        location="West Hall",
        incident_date=date(2026, 8, 13),
    )
    make_report(
        db_session,
        incident=hidden,
        owner=accounts.unrelated,
        preparer=accounts.unrelated,
        now=base + timedelta(minutes=5),
    )

    template = FormTemplate(
        code="fictional_required_form",
        name="Fictional Required Form",
        category="incident",
        output_kind="digital_document",
        revision_label="fictional-v1",
        active=True,
        definition={},
        created_at=base,
        updated_at=base,
    )
    db_session.add(template)
    db_session.flush()
    db_session.add(IncidentPacketItem(
        incident_id=both.id,
        form_template_id=template.id,
        packet_group="required",
        packet_state="selected",
        source_incident_revision_number=both.current_revision_number,
        selection_reason="Fictional required-paperwork fixture.",
        added_by_account_id=accounts.user.id,
        created_at=base,
        updated_at=base,
    ))
    db_session.add(DocumentActionEvent(
        incident_id=both.id,
        report_id=first.id,
        actor_account_id=accounts.user.id,
        actor_staff_member_id=accounts.user.staff_member_id,
        action="print",
        incident_revision_number=both.current_revision_number,
        details={},
        request_id="request_fictional_incident_library_print",
        created_at=base + timedelta(minutes=5),
    ))
    db_session.commit()
    return reporting_only, prepared_only, both, hidden


def _items(response):
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()["data"]["items"]


def test_library_authorizes_once_per_incident_and_aggregates_summary(
    db_session,
    db_session_factory,
    api_client,
    monkeypatch,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    reporting_only, prepared_only, both, hidden = _seed_library(
        db_session, fictional_staff_and_accounts, identity_fixed_now)
    _authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.user,
    )

    response = api_client.get("/api/web/v1/incidents?limit=25")
    items = _items(response)
    by_id = {UUID(item["incident_id"]): item for item in items}

    assert set(by_id) == {reporting_only.id, prepared_only.id, both.id}
    assert hidden.id not in by_id
    assert all(set(item) == SUMMARY_KEYS for item in items)
    assert by_id[reporting_only.id]["relationship"] == "reporting_officer"
    assert by_id[prepared_only.id]["relationship"] == "preparer"
    assert by_id[both.id]["relationship"] == "both"
    assert by_id[both.id]["officer_report_count"] == 2
    assert by_id[both.id]["required_paperwork_count"] == 1
    assert by_id[both.id]["progress"] == {
        "code": "printed_or_exported",
        "label": "Printed or exported",
        "blocking_count": 0,
    }
    assert by_id[reporting_only.id]["reporting_officers"] == [{
        "staff_id": str(fictional_staff_and_accounts.user.staff_member_id),
        "display_name": "Officer Alex Example",
    }]


def test_library_search_filters_and_pagination_are_stable(
    db_session,
    db_session_factory,
    api_client,
    monkeypatch,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    reporting_only, prepared_only, both, _hidden = _seed_library(
        db_session, fictional_staff_and_accounts, identity_fixed_now)
    _authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.user,
    )

    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get("/api/web/v1/incidents?q=202608102")
    )} == {prepared_only.id}
    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get("/api/web/v1/incidents?q=East%20Hall%20Review")
    )} == {both.id}
    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get("/api/web/v1/incidents?q=Blair%20Example")
    )} == {prepared_only.id}
    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get(
            "/api/web/v1/incidents?category=use_of_force&location=East%20Hall"
            "&date_from=2026-08-12&date_to=2026-08-12"
        )
    )} == {both.id}
    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get("/api/web/v1/incidents?relationship=reporting")
    )} == {reporting_only.id, both.id}
    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get("/api/web/v1/incidents?relationship=prepared")
    )} == {prepared_only.id, both.id}

    first = api_client.get("/api/web/v1/incidents?limit=2")
    first_items = _items(first)
    cursor = first.get_json()["data"]["next_cursor"]
    assert len(first_items) == 2
    assert cursor
    second_items = _items(api_client.get(
        "/api/web/v1/incidents?limit=2&cursor=" + cursor))
    ids = [item["incident_id"] for item in first_items + second_items]
    assert len(ids) == 3
    assert len(set(ids)) == 3


def test_admin_sees_all_incidents_and_unknown_filters_are_rejected(
    db_session,
    db_session_factory,
    api_client,
    monkeypatch,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    seeded = _seed_library(db_session, fictional_staff_and_accounts, identity_fixed_now)
    _authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.admin,
    )

    assert {UUID(item["incident_id"]) for item in _items(
        api_client.get("/api/web/v1/incidents")
    )} == {incident.id for incident in seeded}

    invalid = api_client.get("/api/web/v1/incidents?status=completed")
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "validation_failed"
