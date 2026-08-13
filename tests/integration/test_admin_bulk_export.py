"""Bounded, manifested Admin bulk Word export (RP-09).

Everything exported here is fictional test data created by the fixtures in
this module; no real report, officer, or inmate identifier is involved.
"""

from datetime import UTC, datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import tempfile
from uuid import uuid4
import zipfile

import pytest
from sqlalchemy import func, select

from backend.persistence.models import AuditEvent
from backend.persistence.models.jobs import Export
from backend.persistence.models.security import IdempotencyRecord
from backend.reports.deterministic_docx import ZIP_ENTRY_TIMESTAMP
from backend.reports.export_service import (
    BULK_EXPORT_MAX_DOCUMENTS,
    BULK_EXPORT_MIME_TYPE,
    EXPORT_TEMP_PREFIX,
    MANIFEST_NAME,
)
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
    _confirm_admin_pin(api_client, admin_bearer_headers, "admin_center", "admin-elevate-0001")
    return admin_bearer_headers


@pytest.fixture
def bulk_export_step_up_headers(api_client, elevated_admin_bearer_headers):
    data = _confirm_admin_pin(
        api_client,
        elevated_admin_bearer_headers,
        "bulk_export",
        "admin-stepup-bulk-0001",
    )
    return {"X-Admin-Step-Up": data["step_up_token"]}


@pytest.fixture
def second_bulk_export_step_up_headers(api_client, elevated_admin_bearer_headers):
    data = _confirm_admin_pin(
        api_client,
        elevated_admin_bearer_headers,
        "bulk_export",
        "admin-stepup-bulk-0002",
    )
    return {"X-Admin-Step-Up": data["step_up_token"]}


def _bulk_headers(elevated, step_up, key):
    return _headers(elevated | step_up, key)


def _ids_body(report_ids, reason="Fictional records request fixture."):
    return {
        "selection": {"mode": "report_ids", "report_ids": [str(x) for x in report_ids]},
        "revision_selection": "current_at_request",
        "reason": reason,
    }


def _filters_body(filters, reason="Fictional records request fixture."):
    return {
        "selection": {"mode": "filters", "filters": filters},
        "revision_selection": "current_at_request",
        "reason": reason,
    }


def _manifest(response):
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        return json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))


def _make_extra_report(db_session, accounts, now):
    """One report on its own incident.

    `uq_reports_incident_type_owner` allows one first-person report per
    (incident, owner), so each fixture report needs a fresh incident.
    """
    incident = make_incident(db_session, accounts.preparer, now)
    return make_report(
        db_session,
        incident=incident,
        owner=accounts.user,
        preparer=accounts.preparer,
        now=now,
    )


@pytest.fixture
def extra_reports(db_session, fictional_staff_and_accounts, identity_fixed_now):
    return [_make_extra_report(db_session, fictional_staff_and_accounts, identity_fixed_now) for _index in range(3)]


def _temp_export_directories() -> set[Path]:
    return set(Path(tempfile.gettempdir()).glob(f"{EXPORT_TEMP_PREFIX}*"))


# --- Selection branch validation -------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {},
        {
            "selection": {"mode": "report_ids", "report_ids": []},
            "revision_selection": "current_at_request",
            "reason": "Fictional.",
        },
        {
            "selection": {"mode": "filters", "filters": {}},
            "revision_selection": "latest",
            "reason": "Fictional.",
        },
        {
            "selection": {"mode": "filters", "filters": {}},
            "revision_selection": "current_at_request",
            "reason": "Fictional.",
            "limit": 10,
        },
        {
            "selection": {"mode": "filters", "filters": {"unknown_filter": "x"}},
            "revision_selection": "current_at_request",
            "reason": "Fictional.",
        },
        {
            "selection": {"mode": "everything"},
            "revision_selection": "current_at_request",
            "reason": "Fictional.",
        },
        {
            "selection": {"mode": "report_ids", "report_ids": ["not-a-uuid"]},
            "revision_selection": "current_at_request",
            "reason": "Fictional.",
        },
        {
            "selection": {"mode": "filters", "filters": {}},
            "revision_selection": "current_at_request",
        },
        {
            "selection": {"mode": "filters", "filters": {}},
            "revision_selection": "current_at_request",
            "reason": "   ",
        },
        {"revision_selection": "current_at_request", "reason": "Fictional."},
    ],
)
def test_bulk_export_rejects_an_unclosed_or_invalid_body(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    body,
):
    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-invalid-0001",
        ),
        json=body,
    )

    assert response.status_code == 400, response.get_data()[:300]
    assert response.json["error"]["code"] == "validation_failed"


def test_bulk_export_rejects_duplicate_report_ids(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
):
    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-duplicate-0001",
        ),
        json=_ids_body([report_id, report_id]),
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_bulk_export_requires_the_bulk_export_step_up(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    report_id,
):
    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_headers(elevated_admin_bearer_headers, "bulk-export-nostepup-0001"),
        json=_ids_body([report_id]),
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "step_up_required"


def test_bulk_export_rejects_a_step_up_issued_for_another_purpose(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    report_id,
):
    other = _confirm_admin_pin(
        api_client,
        elevated_admin_bearer_headers,
        "report_restore",
        "admin-stepup-other-0001",
    )

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_headers(
            elevated_admin_bearer_headers | {"X-Admin-Step-Up": other["step_up_token"]},
            "bulk-export-wrongpurpose-0001",
        ),
        json=_ids_body([report_id]),
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "step_up_required"


def test_bulk_export_is_concealed_from_a_regular_user(
    db_session,
    api_client,
    user_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_headers(user_bearer_headers | {"X-Admin-Step-Up": "x" * 48}, "bulk-export-user-0001"),
        json=_ids_body([report_id]),
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_bulk_export_requires_an_idempotency_key(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
):
    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=elevated_admin_bearer_headers | bulk_export_step_up_headers,
        json=_ids_body([report_id]),
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


# --- Bounds -----------------------------------------------------------------


def test_bulk_export_rejects_more_than_one_hundred_matches(
    db_session,
    api_client,
    monkeypatch,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    fictional_incident,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    import backend.reports.export_service as export_service

    for _index in range(BULK_EXPORT_MAX_DOCUMENTS + 1):
        _make_extra_report(db_session, fictional_staff_and_accounts, identity_fixed_now)
    db_session.commit()

    def _never(*args, **kwargs):
        raise AssertionError("no document may be generated before the selection is bounded")

    monkeypatch.setattr(export_service, "build_revision_docx", _never)

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0001",
        ),
        json=_filters_body({"status": "in_progress"}),
    )

    assert response.status_code == 409, response.get_data()[:300]
    assert response.json["error"]["code"] == "bulk_export_limit_exceeded"
    assert db_session.scalar(select(func.count()).select_from(Export)) == 0


def test_bulk_export_rejects_more_than_one_hundred_requested_ids(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0002",
        ),
        json=_ids_body([uuid4() for _index in range(BULK_EXPORT_MAX_DOCUMENTS + 1)]),
    )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "bulk_export_limit_exceeded"


def test_bulk_export_with_zero_matches_is_not_found(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0003",
        ),
        json=_filters_body({"status": "archived"}),
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
    assert db_session.scalar(select(func.count()).select_from(Export)) == 0


# --- Archive, manifest, ordering -------------------------------------------


def test_bulk_export_returns_a_deterministic_manifested_archive(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
    extra_reports,
):
    db_session.commit()
    expected = sorted([str(report_id)] + [str(row.id) for row in extra_reports])

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0004",
        ),
        json=_filters_body({"status": "in_progress"}),
    )

    assert response.status_code == 200, response.get_data()[:300]
    assert response.headers["Content-Type"] == BULK_EXPORT_MIME_TYPE
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.headers["Digest"].startswith("sha-256=")
    assert response.headers["X-Export-ID"]

    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert {item.date_time for item in archive.infolist()} == {ZIP_ENTRY_TIMESTAMP}
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        document_names = [name for name in names if name != MANIFEST_NAME]

    assert len(document_names) == 4
    assert [entry["report_id"] for entry in manifest["reports"]] == expected
    assert [entry["document_name"] for entry in manifest["reports"]] == document_names
    assert manifest["failures"] == []
    assert manifest["reason"] == "Fictional records request fixture."
    assert manifest["revision_selection"] == "current_at_request"
    assert db_session.scalar(select(func.count()).select_from(Export)) == 4


def test_bulk_manifest_records_filter_names_never_filter_values(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
    fictional_incident,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0005",
        ),
        json=_filters_body({"status": "in_progress", "facility": "Fictional Unit"}),
    )

    assert response.status_code == 200
    manifest = _manifest(response)
    assert manifest["filter_names"] == ["facility", "status"]
    assert "Fictional Unit" not in json.dumps(manifest)
    assert "in_progress" not in json.dumps(manifest)


def test_bulk_manifest_is_serialized_with_sorted_keys_and_stable_metadata(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
    fictional_admin_account,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0006",
        ),
        json=_ids_body([report_id]),
    )

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        raw = archive.read(MANIFEST_NAME).decode("utf-8")
    manifest = json.loads(raw)
    assert raw == json.dumps(manifest, indent=2, sort_keys=True)
    assert manifest["actor_account_id"] == str(fictional_admin_account.id)
    assert manifest["selection_mode"] == "report_ids"
    assert manifest["filter_names"] == []
    record = db_session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.action == "admin.bulk_export"))
    assert record is not None
    assert manifest["idempotency_recorded_at"] == (record.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"))

    entry = manifest["reports"][0]
    export_row = db_session.scalar(select(Export))
    assert entry["export_id"] == str(export_row.id)
    assert entry["sha256"] == export_row.output_sha256.hex()
    assert entry["byte_length"] == export_row.size_bytes


def test_bulk_export_documents_match_the_single_export_bytes(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
):
    db_session.commit()

    bulk = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0007",
        ),
        json=_ids_body([report_id]),
    )
    single = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=1",
        headers=_headers(elevated_admin_bearer_headers, "admin-export-bulkmatch-0001"),
    )

    assert bulk.status_code == single.status_code == 200
    manifest = _manifest(bulk)
    with zipfile.ZipFile(io.BytesIO(bulk.data)) as archive:
        document = archive.read(manifest["reports"][0]["document_name"])
    assert document == single.data


def test_bulk_export_unknown_report_ids_are_explicit_failures(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
):
    db_session.commit()
    missing = uuid4()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0008",
        ),
        json=_ids_body([report_id, missing]),
    )

    assert response.status_code == 200
    manifest = _manifest(response)
    assert [entry["report_id"] for entry in manifest["failures"]] == [str(missing)]
    assert manifest["failures"][0]["reason_code"] == "not_found"
    assert len(manifest["reports"]) == 1
    assert db_session.scalar(select(func.count()).select_from(Export)) == 1


def test_a_failure_after_selection_is_explicit_and_never_marked_exported(
    db_session,
    api_client,
    monkeypatch,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
    extra_reports,
):
    import backend.reports.export_service as export_service

    db_session.commit()
    doomed = str(sorted(str(row.id) for row in extra_reports)[0])
    original = export_service.build_revision_docx

    def _selective(report, revision):
        if str(report.id) == doomed:
            raise RuntimeError("fictional generation failure")
        return original(report, revision)

    monkeypatch.setattr(export_service, "build_revision_docx", _selective)

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0009",
        ),
        json=_filters_body({"status": "in_progress"}),
    )

    assert response.status_code == 200
    manifest = _manifest(response)
    assert [entry["report_id"] for entry in manifest["failures"]] == [doomed]
    assert manifest["failures"][0]["reason_code"] == "generation_failed"
    assert doomed not in [entry["report_id"] for entry in manifest["reports"]]
    assert db_session.scalar(select(func.count()).select_from(Export)) == 3
    assert db_session.scalar(select(func.count()).select_from(Export).where(Export.report_id == doomed)) == 0


# --- Idempotency, audit, cleanup -------------------------------------------


def test_the_same_bulk_key_regenerates_identical_bytes_and_no_new_rows(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    second_bulk_export_step_up_headers,
    report_id,
    extra_reports,
):
    db_session.commit()
    body = _filters_body({"status": "in_progress"})

    first = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0010",
        ),
        json=body,
    )
    second = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            second_bulk_export_step_up_headers,
            "bulk-export-fictional-0010",
        ),
        json=body,
    )

    assert first.status_code == second.status_code == 200, second.get_data()[:300]
    assert first.data == second.data
    assert hashlib.sha256(first.data).hexdigest() == hashlib.sha256(second.data).hexdigest()
    assert db_session.scalar(select(func.count()).select_from(Export)) == 4
    assert first.headers["X-Export-ID"] == second.headers["X-Export-ID"]


def test_bulk_export_writes_one_bounded_admin_audit_event(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
    extra_reports,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0011",
        ),
        json=_filters_body({"status": "in_progress"}),
    )

    events = db_session.scalars(select(AuditEvent).where(AuditEvent.action == "admin.bulk_exported")).all()
    assert len(events) == 1
    assert events[0].details == {
        "export_id": response.headers["X-Export-ID"],
        "report_count": 4,
    }
    assert db_session.scalars(select(AuditEvent).where(AuditEvent.action == "admin.report_search")).all() == []


def test_bulk_export_removes_its_temporary_workspace(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    bulk_export_step_up_headers,
    report_id,
    extra_reports,
):
    db_session.commit()
    before = _temp_export_directories()

    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=_bulk_headers(
            elevated_admin_bearer_headers,
            bulk_export_step_up_headers,
            "bulk-export-fictional-0012",
        ),
        json=_filters_body({"status": "in_progress"}),
    )
    response.close()

    assert response.status_code == 200
    assert _temp_export_directories() <= before
