"""Admin report detail, history, edit, restore, and transfer API."""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
import yaml
from sqlalchemy import func, select

from backend.persistence.models import AuditEvent
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.reporting import Report, ReportAccess, ReportRevision
from backend.persistence.models.security import IdempotencyRecord
from backend.persistence.models.sessions import AdminElevation
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


def test_admin_with_expired_elevation_is_rejected(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
    identity_fixed_now,
):
    elevation = db_session.scalar(select(AdminElevation))
    assert elevation is not None
    elevation.issued_at = identity_fixed_now - timedelta(minutes=30)
    elevation.last_used_at = identity_fixed_now - timedelta(minutes=20)
    elevation.idle_expires_at = identity_fixed_now - timedelta(minutes=5)
    db_session.commit()

    response = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}",
        headers=elevated_admin_bearer_headers,
    )

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


def test_admin_historical_revision_detail_writes_viewed_by_admin_audit_event(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers,
    shared_report,
):
    db_session.commit()

    response = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}/revisions/1",
        headers=elevated_admin_bearer_headers,
    )

    assert response.status_code == 200
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


def test_admin_revision_attribution_is_an_immutable_roster_snapshot(
    db_session, api_client, elevated_admin_bearer_headers,
    fictional_admin_account, shared_report,
):
    db_session.commit()
    saved = api_client.patch(
        f"/api/v1/admin/reports/{shared_report.id}",
        headers=_headers(elevated_admin_bearer_headers, "admin-snapshot-edit-0001"),
        json=_save_body("Fictional immutable-attribution edit."),
    )
    assert saved.status_code == 200

    editor = db_session.get(StaffMember, fictional_admin_account.staff_member_id)
    editor.rank = "Captain"
    editor.first_name = "Renamed"
    editor.last_name = "Officer"
    db_session.commit()

    detail = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}/revisions/2",
        headers=elevated_admin_bearer_headers,
    )

    assert detail.status_code == 200
    assert detail.json["data"]["editor_display_name"] == "Officer Jordan Taylor"
    assert detail.json["data"]["editor_rank"] == "Officer"


def test_pre_snapshot_revision_attribution_uses_safe_nullable_fallback(
    db_session, api_client, elevated_admin_bearer_headers, shared_report,
):
    db_session.commit()

    detail = api_client.get(
        f"/api/v1/admin/reports/{shared_report.id}/revisions/1",
        headers=elevated_admin_bearer_headers,
    )

    assert detail.status_code == 200
    assert detail.json["data"]["editor_display_name"] is None
    assert detail.json["data"]["editor_rank"] is None


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


def test_admin_transfer_replay_preserves_original_ownership_after_later_transfer(
    db_session, api_client, elevated_admin_bearer_headers,
    fictional_staff_and_accounts, shared_report,
):
    transfer_a_step_up = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_transfer",
        "admin-transfer-a-step-up-0001",
    )
    db_session.commit()
    transfer_a_key = "admin-transfer-a-0001"
    transfer_a_body = {
        "new_owner_staff_id": str(fictional_staff_and_accounts.unrelated.staff_member_id),
        "new_preparer_staff_id": str(fictional_staff_and_accounts.preparer.staff_member_id),
        "reason": "Fictional first ownership transfer.",
    }
    first = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, transfer_a_key) | {
            "X-Admin-Step-Up": transfer_a_step_up["step_up_token"],
        },
        json=transfer_a_body,
    )
    assert first.status_code == 200

    transfer_b_step_up = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_transfer",
        "admin-transfer-b-step-up-0001",
    )
    second = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, "admin-transfer-b-0001") | {
            "X-Admin-Step-Up": transfer_b_step_up["step_up_token"],
        },
        json={
            "new_owner_staff_id": str(fictional_staff_and_accounts.user.staff_member_id),
            "new_preparer_staff_id": str(fictional_staff_and_accounts.preparer.staff_member_id),
            "reason": "Fictional second ownership transfer.",
        },
    )
    assert second.status_code == 200
    assert second.json["data"]["reporting_staff_member_id"] != (
        first.json["data"]["reporting_staff_member_id"]
    )

    replay_step_up = _confirm_admin_pin(
        api_client, elevated_admin_bearer_headers, "report_transfer",
        "admin-transfer-a-replay-step-up-0001",
    )
    replay = api_client.post(
        f"/api/v1/admin/reports/{shared_report.id}/transfer",
        headers=_headers(elevated_admin_bearer_headers, transfer_a_key) | {
            "X-Admin-Step-Up": replay_step_up["step_up_token"],
        },
        json=transfer_a_body,
    )

    assert replay.status_code == 200
    assert replay.json["data"] == first.json["data"]


def test_simultaneous_admin_transfers_serialize_to_consistent_access_and_revisions(
    db_session, db_session_factory, api_client, elevated_admin_bearer_headers,
    fictional_staff_and_accounts, shared_report,
):
    target_accounts = (
        fictional_staff_and_accounts.unrelated,
        fictional_staff_and_accounts.user,
    )
    step_ups = [
        _confirm_admin_pin(
            api_client, elevated_admin_bearer_headers, "report_transfer",
            f"admin-transfer-race-step-up-{index:04d}",
        )["step_up_token"]
        for index in (1, 2)
    ]
    report_id = shared_report.id
    preparer_id = fictional_staff_and_accounts.preparer.staff_member_id
    db_session.commit()
    barrier = Barrier(2)
    app = api_client.application

    def transfer(index: int):
        target = target_accounts[index - 1]
        barrier.wait()
        with app.test_client() as client:
            return client.post(
                f"/api/v1/admin/reports/{report_id}/transfer",
                headers=_headers(
                    elevated_admin_bearer_headers,
                    f"admin-transfer-race-{index:04d}",
                ) | {"X-Admin-Step-Up": step_ups[index - 1]},
                json={
                    "new_owner_staff_id": str(target.staff_member_id),
                    "new_preparer_staff_id": str(preparer_id),
                    "reason": f"Fictional serialized transfer {index}.",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(transfer, (1, 2)))

    assert [response.status_code for response in responses] == [200, 200]
    with db_session_factory() as verification:
        report = verification.get(Report, report_id)
        live_access = verification.scalars(select(ReportAccess).where(
            ReportAccess.report_id == report_id,
            ReportAccess.revoked_at.is_(None),
        )).all()
        assert {row.staff_member_id for row in live_access} == {
            report.reporting_staff_member_id,
            report.prepared_by_staff_member_id,
        }
        revisions = verification.scalars(select(ReportRevision).where(
            ReportRevision.report_id == report_id,
        ).order_by(ReportRevision.revision_number)).all()
        assert [row.revision_number for row in revisions] == [1, 2, 3]
        assert [row.reason for row in revisions[1:]] == [
            "ownership_change", "ownership_change",
        ]
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.target_id == report_id,
            AuditEvent.action == "report.ownership_transferred",
        )) == 2
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "report.transfer",
        )) == 2


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


def test_admin_report_openapi_rejects_empty_filters_and_matches_runtime_contracts():
    document = yaml.safe_load(
        Path("openapi/access-v1.yaml").read_text(encoding="utf-8")
    )
    paths = document["paths"]
    search_parameters = {
        item["name"]: item["schema"]
        for item in paths["/api/v1/admin/reports"]["get"]["parameters"]
        if "name" in item
    }
    for name in {
        "sort", "incident_date_from", "incident_date_to",
        "inmate_first_name", "inmate_middle_name", "inmate_last_name",
        "inmate_adc_number", "category", "facility", "location", "shift",
    }:
        assert search_parameters[name]["minLength"] == 1
    schemas = document["components"]["schemas"]
    assert schemas["Uuid"]["minLength"] == 1
    assert schemas["UtcTimestamp"]["minLength"] == 1

    transfer = schemas["AdminReportTransferRequest"]
    preparer_options = transfer["properties"]["new_preparer_staff_id"]["oneOf"]
    assert {option.get("type") for option in preparer_options} == {None, "null"}
    assert any(option.get("$ref") == "#/components/schemas/Uuid" for option in preparer_options)

    expected_conflicts = {
        "#/components/schemas/ReportRevisionConflictEnvelope",
        "#/components/schemas/ReportIdempotencyConflictEnvelope",
        "#/components/schemas/ReportRequestInProgressEnvelope",
        "#/components/schemas/ClientUpgradeRequiredEnvelope",
    }
    for suffix in ("restore", "transfer"):
        response = paths[f"/api/v1/admin/reports/{{report_id}}/{suffix}"]["post"][
            "responses"
        ]["409"]
        options = response["content"]["application/json"]["schema"]["oneOf"]
        assert {option["$ref"] for option in options} == expected_conflicts
