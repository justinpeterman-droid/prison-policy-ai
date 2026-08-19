from datetime import UTC, date, datetime

from backend.dashboard.home import get_officer_home_summary
from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.paperwork.contracts import (
    OperationalPaperworkContentV1,
    PaperworkIdentity,
)
from backend.paperwork.service import create_operational_paperwork
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
    count = create_operational_paperwork(
        db_session,
        actor,
        identity=PaperworkIdentity(
            paperwork_type="ncu_days_count",
            record_date=date(2026, 8, 19),
            shift="A",
            record_key="primary",
        ),
        content=OperationalPaperworkContentV1(fields={
            "expected_operational_total": 40,
            "reconciliation_difference": -1,
        }),
        idempotency_key="home-summary-count-create-001",
        request_id="request_home_summary_count_create",
        client_version="1.0.0",
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
    assert summary.count_sheet.record_id == count.record.id
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
