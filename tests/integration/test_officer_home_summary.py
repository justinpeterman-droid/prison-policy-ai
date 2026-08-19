from datetime import UTC, date, datetime

from backend.dashboard.home import get_officer_home_summary
from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.paperwork.count_sheet import (
    AREA_ROWS,
    HOUSING_COLUMNS,
    OPERATIONAL_FIELDS,
)
from backend.paperwork.models import PaperworkKind
from backend.paperwork.schemas import SavePaperworkRequest
from backend.paperwork.service import save_paperwork_record
from backend.webapp.api_v1.middleware import Actor


def _actor(account, session_id):
    return Actor(
        account.id,
        account.staff_member_id,
        session_id,
        account.role,
        account.auth_version,
        account.must_change_pin,
    )


def _blank_count_payload():
    return {
        "schema_version": 1,
        "count_started": None,
        "count_ended": None,
        "cells": {
            area: {column: None for column in HOUSING_COLUMNS}
            for area in AREA_ROWS
        },
        "in_housing": {column: None for column in HOUSING_COLUMNS},
        "operational": {field: None for field in OPERATIONAL_FIELDS},
    }


def test_home_summary_uses_authorized_records_and_no_fictional_dashboard_rows(
    db_session,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
    fictional_reporting_incident,
):
    del fictional_reporting_incident
    account = fictional_staff_and_accounts.user
    actor = _actor(account, fictional_owner_tokens.session_id)
    sync_form_catalog(
        db_session,
        load_form_catalog("templates/paperwork/catalog.json"),
        now=datetime(2026, 8, 19, 13, tzinfo=UTC),
    )
    count = save_paperwork_record(
        db_session,
        actor,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=SavePaperworkRequest(
            work_date=date(2026, 8, 19),
            shift="A",
            payload=_blank_count_payload(),
            reason="manual_save",
        ),
        idempotency_key="home-summary-count-create-001",
        request_id="request_home_summary_count_create",
        client_version="1.0.0",
        now=datetime(2026, 8, 19, 14, tzinfo=UTC),
    )
    db_session.flush()

    summary = get_officer_home_summary(
        db_session,
        actor,
        record_date=date(2026, 8, 19),
        shift="A",
    )

    assert summary.recent_incidents
    assert summary.continue_incident is not None
    assert summary.continue_incident.incident_id == summary.recent_incidents[0].incident_id
    assert summary.count_sheet is not None
    assert summary.count_sheet.record_id == count.record_id
    assert summary.count_sheet.current_revision_number == 1
    assert summary.quick_forms
    assert "field_notes" not in repr(summary)
    assert "narrative" not in repr(summary)


def test_home_summary_returns_clear_empty_states_without_sample_data(
    db_session,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
):
    account = fictional_staff_and_accounts.user
    actor = _actor(account, fictional_owner_tokens.session_id)

    summary = get_officer_home_summary(
        db_session,
        actor,
        record_date=date(2026, 8, 19),
        shift="A",
    )

    assert summary.recent_incidents == ()
    assert summary.continue_incident is None
    assert summary.count_sheet is None
    assert summary.quick_forms == ()
