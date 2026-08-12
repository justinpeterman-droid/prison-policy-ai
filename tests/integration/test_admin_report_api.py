"""Admin report detail, history, edit, restore, and transfer API."""
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from backend.persistence.models import AuditEvent
from backend.persistence.models.reporting import Report, ReportAccess, ReportRevision
from backend.persistence.models.security import IdempotencyRecord
from tests.integration.identity_fixtures import bearer_headers, issue_fictional_tokens
from tests.support.reporting import fictional_report_content, make_incident, make_report


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


def _save_body(narrative, base=1):
    return {
        "base_revision_number": base,
        "content": fictional_report_content(narrative),
    }


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
    _confirm_admin_pin(api_client, admin_bearer_headers, "admin_center", "admin-elevate-0001")
    return admin_bearer_headers


@pytest.fixture
def report_restore_step_up_headers(api_client, elevated_admin_bearer_headers):
    data = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_restore", "admin-stepup-restore-0001")
    return {"X-Admin-Step-Up": data["step_up_token"]}


@pytest.fixture
def report_transfer_step_up_headers(api_client, elevated_admin_bearer_headers):
    data = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_transfer", "admin-stepup-transfer-0001")
    return {"X-Admin-Step-Up": data["step_up_token"]}


def _headers_for_account(db_session, account, now, suffix):
    tokens = issue_fictional_tokens(
        db_session, account=account, device_id=f"device-fictional-{suffix}-0001", now=now)
    return bearer_headers(tokens)


# --- User discovery (must be concealed as 404, never 403) -----------------

@pytest.mark.parametrize(("method", "path_suffix", "body"), [
    ("get", "", None),
    ("get", "/{report_id}", None),
    ("patch", "/{report_id}", _save_body("Fictional unauthorized admin edit.")),
    ("get", "/{report_id}/revisions", None),
    ("get", "/{report_id}/revisions/1", None),
    ("post", "/{report_id}/restore", {"revision_number": 1}),
    ("post", "/{report_id}/transfer", {"new_owner_staff_id": str(uuid4()), "reason": "Fictional."}),
])
def test_regular_user_is_concealed_with_404_on_every_admin_report_route(
    db_session, api_client, user_bearer_headers, shared_report, method, path_suffix, body,
):
    db_session.commit()
    path = "/api/v1/admin/reports" + path_suffix.format(report_id=shared_report.id)
    headers = user_bearer_headers
    if method in {"patch", "post"}:
        headers = _headers(headers, f"user-hidden-{method}-{len(path_suffix)}-0001")

    response = getattr(api_client, method)(path, headers=headers, json=body)

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


# --- Admin elevation / step-up gates ----------------------------------------

def test_admin_without_elevation_is_rejected(
    db_session, api_client, admin_bearer_headers, shared_report,
):
    db_session.commit()

    response = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}", headers=admin_bearer_headers)

    assert response.status_code == 403
    assert response.json["error"]["code"] == "admin_elevation_required"


def test_restore_requires_purpose_scoped_step_up(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
):
    db_session.commit()

    missing = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/restore",
        headers=_headers(elevated_admin_bearer_headers, "admin-restore-missing-step-up-0001"),
        json={"revision_number": 1},
    )

    assert missing.status_code == 403
    assert missing.json["error"]["code"] == "step_up_required"


def test_restore_rejects_wrong_purpose_step_up_token(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
):
    wrong_purpose = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_transfer", "admin-wrong-purpose-0001")
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/restore",
        headers=_headers(elevated_admin_bearer_headers, "admin-restore-wrong-purpose-0001")
        | {"X-Admin-Step-Up": wrong_purpose["step_up_token"]},
        json={"revision_number": 1},
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "step_up_required"


def test_restore_rejects_replayed_step_up_token(
    db_session, api_client, elevated_admin_bearer_headers, report_restore_step_up_headers,
    shared_report,
):
    db_session.commit()
    first = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/restore",
        headers=_headers(elevated_admin_bearer_headers, "admin-restore-first-use-0001")
        | report_restore_step_up_headers,
        json={"revision_number": 1},
    )

    replay = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/restore",
        headers=_headers(elevated_admin_bearer_headers, "admin-restore-replay-token-0002")
        | report_restore_step_up_headers,
        json={"revision_number": 1},
    )

    assert first.status_code == 200
    assert replay.status_code == 403
    assert replay.json["error"]["code"] == "step_up_required"


def test_transfer_requires_purpose_scoped_step_up(
    api_client, elevated_admin_bearer_headers, shared_report,
):
    headers = _headers(elevated_admin_bearer_headers, "transfer-fictional-0001")
    response = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=headers,
        json={"new_owner_staff_id": str(uuid4()), "reason": "Correct fictional owner."},
    )
    assert response.status_code == 403
    assert response.json["error"]["code"] == "step_up_required"


# --- Admin view audit --------------------------------------------------------

def test_admin_detail_view_writes_viewed_by_admin_audit_event(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers, shared_report,
):
    db_session.commit()

    response = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}", headers=elevated_admin_bearer_headers)

    assert response.status_code == 200
    assert response.json["data"]["report_id"] == str(shared_report.id)
    with db_session_factory() as verification:
        events = verification.scalars(select(AuditEvent).where(
            AuditEvent.target_id == shared_report.id,
            AuditEvent.action == "report.viewed_by_admin",
        )).all()
        assert len(events) == 1
        assert events[0].details == {"report_id": str(shared_report.id)}


# --- Edit: attributed, idempotent, no step-up required -----------------------

def test_admin_edit_reuses_shared_save_service_with_admin_edit_reason(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers,
    fictional_admin_account, shared_report,
):
    db_session.commit()

    response = api_client.patch(
        f"/api/v1/admin/reports/{shared_report.id}",
        headers=_headers(elevated_admin_bearer_headers, "admin-edit-0001"),
        json=_save_body("Fictional admin-authored correction."),
    )

    assert response.status_code == 200
    assert response.json["data"]["current_revision_number"] == 2
    assert response.json["data"]["content"]["narrative"] == "Fictional admin-authored correction."
    with db_session_factory() as verification:
        revision = verification.scalar(select(ReportRevision).where(
            ReportRevision.report_id == shared_report.id,
            ReportRevision.revision_number == 2,
        ))
        assert revision.reason == "admin_edit"
        assert revision.editor_staff_member_id == fictional_admin_account.staff_member_id


def test_admin_edit_optimistic_concurrency_conflict(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
):
    db_session.commit()

    response = api_client.patch(
        f"/api/v1/admin/reports/{shared_report.id}",
        headers=_headers(elevated_admin_bearer_headers, "admin-edit-conflict-0001"),
        json=_save_body("Fictional stale admin edit.", base=99),
    )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "revision_conflict"
    assert "current_revision_number" in response.json["error"]["details"]


def test_admin_edit_idempotent_replay_is_stable(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
):
    db_session.commit()
    headers = _headers(elevated_admin_bearer_headers, "admin-edit-replay-0001")
    body = _save_body("Fictional replayed admin edit.")

    first = api_client.patch(f"/api/v1/admin/reports/{shared_report.id}", headers=headers, json=body)
    replay = api_client.patch(f"/api/v1/admin/reports/{shared_report.id}", headers=headers, json=body)

    assert first.status_code == replay.status_code == 200
    assert first.json["data"] == replay.json["data"]


# --- Restore: exact request/response shape -----------------------------------

def test_admin_restore_uses_closed_source_revision_body(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers,
    report_restore_step_up_headers, shared_report,
):
    db_session.commit()
    api_client.patch(
        f"/api/v1/admin/reports/{shared_report.id}",
        headers=_headers(elevated_admin_bearer_headers, "admin-restore-prior-save-0001"),
        json=_save_body("Fictional content before admin restore."),
    )

    response = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/restore",
        headers=_headers(elevated_admin_bearer_headers, "admin-restore-0001")
        | report_restore_step_up_headers,
        json={"revision_number": 1},
    )

    assert response.status_code == 200
    assert response.json["data"]["current_revision_number"] == 3
    assert response.json["data"]["content"]["narrative"] == "Fictional initial report narrative."
    with db_session_factory() as verification:
        source = verification.scalar(select(ReportRevision).where(
            ReportRevision.report_id == shared_report.id,
            ReportRevision.revision_number == 1,
        ))
        restored = verification.scalar(select(ReportRevision).where(
            ReportRevision.report_id == shared_report.id,
            ReportRevision.revision_number == 3,
        ))
        assert source.snapshot["narrative"] == "Fictional initial report narrative."
        assert restored.reason == "restored"
        assert restored.provenance["source_revision_number"] == 1


def test_admin_restore_rejects_obsolete_revision_scoped_path(api_client):
    response = api_client.post(
        "/api/v1/admin/reports/00000000-0000-4000-8000-000000000041/"
        "revisions/1/restore",
        json={},
    )
    assert response.status_code == 404


# --- Transfer: purpose, atomicity, attribution --------------------------------

def test_admin_transfer_replaces_access_and_creates_ownership_revision(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers,
    report_transfer_step_up_headers, fictional_staff_and_accounts, shared_report,
):
    new_owner = fictional_staff_and_accounts.unrelated
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, "admin-transfer-0001")
        | report_transfer_step_up_headers,
        json={
            "new_owner_staff_id": str(new_owner.staff_member_id),
            "reason": "Fictional reassignment for coverage.",
        },
    )

    assert response.status_code == 200
    assert response.json["data"]["reporting_staff_member_id"] == str(new_owner.staff_member_id)
    with db_session_factory() as verification:
        report = verification.get(Report, shared_report.id)
        assert report.reporting_staff_member_id == new_owner.staff_member_id
        live_access = verification.scalars(select(ReportAccess).where(
            ReportAccess.report_id == shared_report.id,
            ReportAccess.revoked_at.is_(None),
        )).all()
        assert {row.staff_member_id for row in live_access} >= {new_owner.staff_member_id}
        events = verification.scalars(select(AuditEvent).where(
            AuditEvent.target_id == shared_report.id,
            AuditEvent.action == "report.ownership_transferred",
        )).all()
        assert len(events) == 1
        assert events[0].details["new_owner_staff_id"] == str(new_owner.staff_member_id)
        revision = verification.scalar(select(ReportRevision).where(
            ReportRevision.report_id == shared_report.id,
            ReportRevision.revision_number == report.current_revision_number,
        ))
        assert revision.reason == "ownership_change"


def test_admin_transfer_rejects_inactive_target(
    db_session, api_client, elevated_admin_bearer_headers, report_transfer_step_up_headers,
    shared_report,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, "admin-transfer-inactive-0001")
        | report_transfer_step_up_headers,
        json={"new_owner_staff_id": str(uuid4()), "reason": "Fictional invalid target."},
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_admin_transfer_rejects_blank_reason(
    db_session, api_client, elevated_admin_bearer_headers, report_transfer_step_up_headers,
    fictional_staff_and_accounts, shared_report,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, "admin-transfer-blank-reason-0001")
        | report_transfer_step_up_headers,
        json={
            "new_owner_staff_id": str(fictional_staff_and_accounts.unrelated.staff_member_id),
            "reason": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_admin_transfer_idempotent_replay_is_stable(
    db_session, api_client, elevated_admin_bearer_headers, report_transfer_step_up_headers,
    fictional_staff_and_accounts, shared_report,
):
    new_owner = fictional_staff_and_accounts.unrelated
    db_session.commit()
    idem_key = "admin-transfer-replay-0001"
    body = {
        "new_owner_staff_id": str(new_owner.staff_member_id),
        "reason": "Fictional replay-stable reassignment.",
    }

    first = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, idem_key) | report_transfer_step_up_headers,
        json=body,
    )
    # A step-up token is single-use even on an idempotent replay -- the
    # replayed *response* is stable, but a fresh token is still required to
    # reach that replay branch (mirrors the existing Admin mutation pattern).
    fresh_step_up = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_transfer",
        "admin-transfer-replay-fresh-step-up-0001")
    replay = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=(
            _headers(elevated_admin_bearer_headers, idem_key)
            | {"X-Admin-Step-Up": fresh_step_up["step_up_token"]}
        ),
        json=body,
    )

    assert first.status_code == replay.status_code == 200
    assert first.json["data"] == replay.json["data"]


# --- Revision list / detail: attribution fields -------------------------------

def test_admin_revision_history_exposes_full_attribution(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
):
    db_session.commit()

    history = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}/revisions",
        headers=elevated_admin_bearer_headers,
    )
    detail = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}/revisions/1",
        headers=elevated_admin_bearer_headers,
    )

    assert history.status_code == detail.status_code == 200
    item = history.json["data"]["items"][0]
    assert set(item) == {
        "revision_id", "revision_number", "reason", "source_revision_number",
        "editor_account_id", "editor_staff_member_id", "editor_display_name",
        "editor_rank", "content_hash", "client_version", "created_at", "is_current",
    }
    assert "content" not in item
    assert detail.json["data"]["content"]["narrative"] == "Fictional initial report narrative."
    assert UUID(item["editor_account_id"])
