"""Employee report queues, detail, history, restore, recovery, and status API."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from tests.integration.identity_fixtures import bearer_headers, issue_fictional_tokens
from backend.persistence.models import AuditEvent
from backend.persistence.models.reporting import Report, ReportAccess, ReportRevision
from backend.persistence.models.security import IdempotencyRecord
from tests.support.reporting import fictional_report_content, make_incident, make_report


@pytest.fixture(autouse=True)
def _fictional_access_api_environment(monkeypatch, identity_fixed_now):
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.example.gov")
    import backend.webapp.api_v1.middleware as middleware

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)


def _headers(headers, key):
    return headers | {"Idempotency-Key": key, "X-Request-ID": f"request_{key}"}


def _save_body(narrative, base=1, **extra):
    return {
        "base_revision_number": base,
        "content": fictional_report_content(narrative),
        "reason": "manual_save",
        **extra,
    }


def _headers_for_account(db_session, account, now, suffix):
    tokens = issue_fictional_tokens(
        db_session, account=account,
        device_id=f"device-fictional-{suffix}-0001", now=now,
    )
    return bearer_headers(tokens)


@pytest.mark.parametrize(("method", "path_suffix", "body"), [
    ("get", "", None),
    ("patch", "", _save_body("Fictional unauthorized Admin content.")),
    ("get", "/revisions", None),
    ("get", "/revisions/1", None),
    ("post", "/restore", {"revision_number": 1}),
    ("post", "/recovery-revisions", {
        "base_revision_number": 1,
        "content": fictional_report_content("Fictional unauthorized recovery."),
    }),
    ("patch", "", {"base_revision_number": 1, "status": "archived"}),
])
def test_unrelated_admin_is_concealed_on_every_ordinary_report_operation(
    db_session, db_session_factory, api_client, fictional_staff_and_accounts,
    identity_fixed_now, shared_report, method, path_suffix, body,
):
    admin = fictional_staff_and_accounts.admin
    headers = _headers_for_account(db_session, admin, identity_fixed_now, "admin-unrelated")
    if method in {"patch", "post"}:
        headers = _headers(headers, f"admin-unrelated-{method}-{len(path_suffix)}-0001")
    report_id = shared_report.id
    db_session.commit()

    response = getattr(api_client, method)(
        f"/api/v1/reports/{report_id}{path_suffix}", headers=headers, json=body,
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
    with db_session_factory() as verification:
        assert verification.get(Report, report_id).current_revision_number == 1
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == report_id)) == 1
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.target_id == report_id)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == admin.id)) == 0


@pytest.mark.parametrize("relationship", ["owned", "prepared"])
def test_admin_with_live_employee_relationship_uses_ordinary_report_routes(
    db_session, api_client, fictional_staff_and_accounts, identity_fixed_now,
    relationship,
):
    admin = fictional_staff_and_accounts.admin
    user = fictional_staff_and_accounts.user
    incident = make_incident(db_session, admin, identity_fixed_now)
    report = make_report(
        db_session, incident=incident,
        owner=admin if relationship == "owned" else user,
        preparer=user if relationship == "owned" else admin,
        now=identity_fixed_now,
    )
    headers = _headers_for_account(db_session, admin, identity_fixed_now, relationship)
    db_session.commit()

    listed = api_client.get(
        f"/api/v1/reports?relationship={relationship}", headers=headers)
    detail = api_client.get(f"/api/v1/reports/{report.id}", headers=headers)

    assert listed.status_code == detail.status_code == 200
    assert [item["report_id"] for item in listed.json["data"]["items"]] == [
        str(report.id)]
    assert detail.json["data"]["report_id"] == str(report.id)


def test_owner_and_preparer_lists_reference_same_canonical_report(
    db_session, api_client, owner_bearer_headers, preparer_bearer_headers, shared_report,
):
    db_session.commit()

    owned = api_client.get(
        "/api/v1/reports?relationship=owned", headers=owner_bearer_headers)
    prepared = api_client.get(
        "/api/v1/reports?relationship=prepared", headers=preparer_bearer_headers)

    assert owned.status_code == prepared.status_code == 200
    assert [item["report_id"] for item in owned.json["data"]["items"]] == [
        str(shared_report.id)]
    assert [item["report_id"] for item in prepared.json["data"]["items"]] == [
        str(shared_report.id)]
    assert "content" not in owned.json["data"]["items"][0]
    assert "narrative" not in owned.json["data"]["items"][0]


def test_authorization_precedes_cursor_validation_and_conceals_report(
    db_session, api_client, unrelated_bearer_headers, shared_report,
):
    db_session.commit()

    detail = api_client.get(
        f"/api/v1/reports/{shared_report.id}", headers=unrelated_bearer_headers)
    history = api_client.get(
        f"/api/v1/reports/{shared_report.id}/revisions?cursor=not-a-cursor",
        headers=unrelated_bearer_headers,
    )

    assert detail.status_code == history.status_code == 404
    assert detail.json["error"]["code"] == history.json["error"]["code"] == "not_found"


def test_queue_filters_and_cursor_are_bounded_and_authorized_in_sql(
    db_session, api_client, owner_bearer_headers, fictional_staff_and_accounts,
    fictional_incident, shared_report,
):
    shared_report.status = "completed"
    shared_report.updated_at = datetime(2026, 8, 12, 17, 0, tzinfo=UTC)
    fictional_incident.incident_date = datetime(2026, 8, 11, tzinfo=UTC).date()
    fictional_incident.category = "fictional_use_of_force"
    second_incident = make_incident(db_session, fictional_staff_and_accounts.preparer)
    second_incident.incident_date = datetime(2026, 7, 1, tzinfo=UTC).date()
    second_incident.category = "fictional_property"
    second_report = make_report(
        db_session, incident=second_incident, owner=fictional_staff_and_accounts.user,
        preparer=fictional_staff_and_accounts.preparer,
    )
    unrelated_incident = make_incident(db_session, fictional_staff_and_accounts.unrelated)
    make_report(
        db_session, incident=unrelated_incident,
        owner=fictional_staff_and_accounts.unrelated,
        preparer=fictional_staff_and_accounts.unrelated,
    )
    db_session.commit()

    filtered = api_client.get(
        "/api/v1/reports?relationship=owned&status=completed"
        "&incident_date_from=2026-08-01&incident_date_to=2026-08-31"
        "&category=fictional_use_of_force"
        "&updated_at_from=2026-08-12T00:00:00Z&updated_at_to=2026-08-13T00:00:00Z",
        headers=owner_bearer_headers,
    )
    first = api_client.get(
        "/api/v1/reports?relationship=owned&limit=1", headers=owner_bearer_headers)
    second = api_client.get(
        "/api/v1/reports?relationship=owned&limit=1&cursor="
        + first.json["data"]["next_cursor"], headers=owner_bearer_headers)
    too_large = api_client.get(
        "/api/v1/reports?relationship=owned&limit=51", headers=owner_bearer_headers)

    assert filtered.status_code == 200
    assert [item["report_id"] for item in filtered.json["data"]["items"]] == [
        str(shared_report.id)]
    assert first.status_code == second.status_code == 200
    assert first.json["data"]["next_cursor"]
    assert {
        first.json["data"]["items"][0]["report_id"],
        second.json["data"]["items"][0]["report_id"],
    } == {str(shared_report.id), str(second_report.id)}
    assert too_large.status_code == 400


def test_detail_history_and_revision_detail_are_exact_and_authorized(
    db_session, api_client, owner_bearer_headers, preparer_bearer_headers, shared_report,
):
    db_session.commit()
    saved = api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(preparer_bearer_headers, "report-fictional-save-0001"),
        json=_save_body("Fictional second revision."),
    )
    detail = api_client.get(
        f"/api/v1/reports/{shared_report.id}", headers=owner_bearer_headers)
    history = api_client.get(
        f"/api/v1/reports/{shared_report.id}/revisions?limit=1",
        headers=owner_bearer_headers,
    )
    revision = api_client.get(
        f"/api/v1/reports/{shared_report.id}/revisions/2",
        headers=owner_bearer_headers,
    )

    assert saved.status_code == detail.status_code == history.status_code == revision.status_code == 200
    assert detail.json["data"]["report_id"] == str(shared_report.id)
    assert detail.json["data"]["content"]["narrative"] == "Fictional second revision."
    assert set(history.json["data"]["items"][0]) == {
        "revision_id", "revision_number", "reason", "changed_fields",
        "editor_staff_member_id", "editor_display_name", "client_version", "created_at",
        "source_revision_number", "is_current",
    }
    assert "content" not in history.json["data"]["items"][0]
    assert revision.json["data"]["content"]["narrative"] == "Fictional second revision."


@pytest.mark.parametrize("initial_status", ["completed", "archived"])
def test_completed_and_archived_reports_remain_editable(
    db_session, api_client, owner_bearer_headers, shared_report, initial_status,
):
    shared_report.status = initial_status
    db_session.commit()

    response = api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(owner_bearer_headers, f"report-{initial_status}-edit-0001"),
        json=_save_body(f"Fictional {initial_status} edit."),
    )

    assert response.status_code == 200
    assert response.json["data"]["status"] == initial_status
    assert response.json["data"]["current_revision_number"] == 2


def test_restore_copies_history_forward_without_mutating_source(
    db_session, db_session_factory, api_client, owner_bearer_headers, shared_report,
):
    source_id = db_session.scalar(select(ReportRevision.id).where(
        ReportRevision.report_id == shared_report.id,
        ReportRevision.revision_number == 1,
    ))
    db_session.commit()
    api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(owner_bearer_headers, "report-restore-prior-save-0001"),
        json=_save_body("Fictional content before restore."),
    )
    restored = api_client.post(
        f"/api/v1/reports/{shared_report.id}/restore",
        headers=_headers(owner_bearer_headers, "report-fictional-restore-0001"),
        json={"revision_number": 1},
    )

    assert restored.status_code == 200
    assert restored.json["data"]["current_revision_number"] == 3
    assert restored.json["data"]["content"]["narrative"] == "Fictional initial report narrative."
    with db_session_factory() as verification:
        source = verification.get(ReportRevision, source_id)
        assert source.revision_number == 1
        assert source.reason == "manual_save"
        assert source.snapshot["narrative"] == "Fictional initial report narrative."


def test_recovery_appends_without_promoting_over_newer_cloud_content(
    db_session, db_session_factory, api_client, owner_bearer_headers, shared_report,
):
    db_session.commit()
    api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(owner_bearer_headers, "report-cloud-save-0001"),
        json=_save_body("Fictional newer cloud content."),
    )
    recovered = api_client.post(
        f"/api/v1/reports/{shared_report.id}/recovery-revisions",
        headers=_headers(owner_bearer_headers, "report-recovery-save-0001"),
        json={
            "base_revision_number": 1,
            "content": fictional_report_content("Fictional preserved local content."),
        },
    )

    assert recovered.status_code == 201
    assert recovered.json["data"]["recovery_revision_number"] == 3
    assert recovered.json["data"]["current_revision_number"] == 2
    with db_session_factory() as verification:
        report = verification.get(Report, shared_report.id)
        recovery = verification.scalar(select(ReportRevision).where(
            ReportRevision.report_id == shared_report.id,
            ReportRevision.revision_number == 3,
        ))
        assert report.current_revision_number == 2
        assert report.current_content["narrative"] == "Fictional newer cloud content."
        assert recovery.reason == "recovery"
        assert recovery.snapshot["narrative"] == "Fictional preserved local content."


def test_status_changes_are_revisions_and_archiving_is_reversible(
    db_session, db_session_factory, api_client, owner_bearer_headers, shared_report,
):
    db_session.commit()
    archived = api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(owner_bearer_headers, "report-status-archive-0001"),
        json={"base_revision_number": 1, "status": "archived"},
    )
    reopened = api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(owner_bearer_headers, "report-status-reopen-0001"),
        json={"base_revision_number": 2, "status": "in_progress"},
    )

    assert archived.status_code == reopened.status_code == 200
    assert reopened.json["data"]["status"] == "in_progress"
    with db_session_factory() as verification:
        revisions = verification.scalars(select(ReportRevision).where(
            ReportRevision.report_id == shared_report.id,
        ).order_by(ReportRevision.revision_number)).all()
        assert [row.reason for row in revisions] == [
            "manual_save", "status_change", "status_change"]
        events = verification.scalars(select(AuditEvent).where(
            AuditEvent.target_id == shared_report.id,
            AuditEvent.action == "report.status_changed",
        )).all()
        assert [(row.details["old_status"], row.details["new_status"]) for row in events] == [
            ("in_progress", "archived"), ("archived", "in_progress")]


def test_idempotent_replay_remains_stable_after_later_changes(
    db_session, api_client, owner_bearer_headers, shared_report,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "report-stable-replay-0001")
    body = _save_body("Fictional replayed content.")
    first = api_client.patch(f"/api/v1/reports/{shared_report.id}", headers=headers, json=body)
    api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=_headers(owner_bearer_headers, "report-later-save-0001"),
        json=_save_body("Fictional later content.", base=2),
    )
    replay = api_client.patch(f"/api/v1/reports/{shared_report.id}", headers=headers, json=body)

    assert first.status_code == replay.status_code == 200
    assert replay.json["data"] == first.json["data"]
    assert replay.json["data"]["current_revision_number"] == 2
    assert replay.json["data"]["content"]["narrative"] == "Fictional replayed content."


def test_audit_failure_rolls_back_revision_current_row_and_idempotency(
    db_session, db_session_factory, api_client, owner_bearer_headers, shared_report,
):
    class FailingAuditWriter:
        def append(self, _session, _event):
            raise RuntimeError("fictional audit failure")

    report_id = shared_report.id
    db_session.commit()
    api_client.application.config["AUDIT_WRITER"] = FailingAuditWriter()
    response = api_client.patch(
        f"/api/v1/reports/{report_id}",
        headers=_headers(owner_bearer_headers, "report-audit-rollback-0001"),
        json=_save_body("Fictional content that must roll back."),
    )

    assert response.status_code == 503
    assert response.json["error"]["code"] == "dependency_unavailable"
    with db_session_factory() as verification:
        report = verification.get(Report, report_id)
        assert report.current_revision_number == 1
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == report_id)) == 1
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "report.save")) == 0


def test_database_failure_maps_to_safe_retryable_503(
    db_session, api_client, owner_bearer_headers, monkeypatch, shared_report,
):
    import backend.webapp.api_v1.reports as reports_api

    db_session.commit()
    monkeypatch.setattr(
        reports_api, "get_report", lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SQLAlchemyError("fictional database outage")))
    response = api_client.get(
        f"/api/v1/reports/{shared_report.id}", headers=owner_bearer_headers)

    assert response.status_code == 503
    assert response.json["error"] == {
        "code": "dependency_unavailable",
        "message": "Report storage is temporarily unavailable.",
        "retryable": True,
    }
