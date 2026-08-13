"""Deterministic single Word export for employees and administrators (RP-09).

Every report, officer, and document in this module is fictional and created by
the fixtures below; nothing here reads a real ADC record.
"""

import base64
from datetime import datetime, timedelta
import hashlib
import io
from pathlib import Path
import tempfile
import zipfile

import pytest
from sqlalchemy import func, select

from backend.persistence.models import AuditEvent
from backend.persistence.models.jobs import Export
from backend.persistence.models.security import IdempotencyRecord
from backend.reports.deterministic_docx import CORE_PROPERTIES_NAME, ZIP_ENTRY_TIMESTAMP
from backend.reports.export_service import EXPORT_MIME_TYPE, EXPORT_TEMP_PREFIX


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


def _temp_export_directories() -> set[Path]:
    root = Path(tempfile.gettempdir())
    return {path for path in root.glob(f"{EXPORT_TEMP_PREFIX}*")}


# --- Deterministic bytes and single export metadata -------------------------


def test_same_export_key_returns_one_export_record(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "export-fictional-0001")

    first = api_client.post(f"/api/v1/reports/{report_id}/export-docx?revision=1", headers=headers)
    second = api_client.post(f"/api/v1/reports/{report_id}/export-docx?revision=1", headers=headers)

    assert first.status_code == second.status_code == 200, first.get_data()[:200]
    assert hashlib.sha256(first.data).digest() == hashlib.sha256(second.data).digest()
    assert first.data == second.data
    assert db_session.scalar(select(func.count()).select_from(Export)) == 1
    assert first.headers["X-Export-ID"] == second.headers["X-Export-ID"]


def test_export_response_carries_the_exact_locked_headers(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0002"),
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == EXPORT_MIME_TYPE
    row = db_session.scalar(select(Export))
    assert row is not None
    digest = hashlib.sha256(response.data).digest()
    assert response.headers["Digest"] == "sha-256=" + base64.b64encode(digest).decode("ascii")
    assert response.headers["X-Export-ID"] == str(row.id)
    assert response.headers["X-Report-Revision"] == "1"
    assert response.headers["X-Template-Version"] == row.template_version
    assert "attachment" in response.headers["Content-Disposition"]
    assert row.download_name in response.headers["Content-Disposition"]
    assert row.output_sha256 == digest
    assert row.size_bytes == len(response.data)
    assert row.mime_type == EXPORT_MIME_TYPE
    assert str(report_id) in row.download_name


def test_exported_document_is_a_deterministic_docx_archive(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0003"),
    )

    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert {item.date_time for item in archive.infolist()} == {ZIP_ENTRY_TIMESTAMP}
        core = archive.read(CORE_PROPERTIES_NAME).decode("utf-8")
    # The revision timestamp, not the generation time, drives core properties.
    assert "2026-08-12T15:00:00Z" in core


def test_export_persists_metadata_only_and_never_document_bytes(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0004"),
    )

    row = db_session.scalar(select(Export))
    assert row is not None
    assert len(row.output_sha256) == 32
    stored = {column.name: getattr(row, column.name) for column in Export.__table__.columns}
    assert not any(isinstance(value, (bytes, bytearray)) and len(value) > 32 for value in stored.values())
    record = db_session.scalar(select(IdempotencyRecord))
    assert record is not None
    assert "narrative" not in str(record.response_reference)


def test_export_writes_the_user_audit_action(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0005"),
    )

    events = db_session.scalars(select(AuditEvent).where(AuditEvent.action == "report.exported")).all()
    assert len(events) == 1
    assert events[0].details["export_id"] == response.headers["X-Export-ID"]
    assert events[0].details["export_format"] == "docx"


def test_temporary_export_files_are_removed_after_the_response_closes(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()
    before = _temp_export_directories()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0006"),
    )
    response.close()

    assert response.status_code == 200
    assert _temp_export_directories() <= before


# --- Explicit revision validation ------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?revision=",
        "?revision=0",
        "?revision=-1",
        "?revision=abc",
        "?revision=1.0",
        "?revision=01",
        "?revision=1&revision=2",
        "?revision=latest",
        "?revision=1&limit=5",
    ],
)
def test_export_requires_an_explicit_positive_revision_query(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
    query,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx{query}",
        headers=_headers(owner_bearer_headers, "export-fictional-0100"),
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    assert db_session.scalar(select(func.count()).select_from(Export)) == 0


def test_export_never_accepts_a_revision_supplied_in_the_body(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx",
        headers=_headers(owner_bearer_headers, "export-fictional-0101"),
        json={"revision": 1},
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    assert db_session.scalar(select(func.count()).select_from(Export)) == 0


def test_export_rejects_a_body_alongside_an_explicit_revision(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0102"),
        json={"revision": 2},
    )

    assert response.status_code == 400
    assert db_session.scalar(select(func.count()).select_from(Export)) == 0


def test_export_of_an_unknown_revision_is_not_found(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=99",
        headers=_headers(owner_bearer_headers, "export-fictional-0103"),
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_export_requires_an_idempotency_key(
    db_session,
    api_client,
    owner_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=owner_bearer_headers | {"X-Request-ID": "request_export_no_key"},
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


# --- Authorization ----------------------------------------------------------


def test_an_unrelated_employee_cannot_export_another_officers_report(
    db_session,
    api_client,
    unrelated_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(unrelated_bearer_headers, "export-fictional-0200"),
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
    assert db_session.scalar(select(func.count()).select_from(Export)) == 0


def test_export_requires_authentication(db_session, api_client, report_id):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers={
            "X-Client-Version": "1.0.0",
            "Idempotency-Key": "export-fictional-0201",
        },
    )

    assert response.status_code == 401


# --- Admin single export ----------------------------------------------------


def test_admin_single_export_uses_admin_route_and_explicit_revision(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=1",
        headers=_headers(elevated_admin_bearer_headers, "admin-export-fictional-0001"),
    )

    assert response.status_code == 200, response.get_data()[:200]
    assert response.headers["X-Report-Revision"] == "1"
    assert response.headers["Content-Type"] == EXPORT_MIME_TYPE


def test_admin_export_writes_a_distinct_admin_audit_action(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    report_id,
):
    db_session.commit()

    api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=1",
        headers=_headers(elevated_admin_bearer_headers, "admin-export-fictional-0002"),
    )

    actions = set(db_session.scalars(select(AuditEvent.action).where(AuditEvent.action.like("report.export%"))).all())
    assert actions == {"report.exported_by_admin"}


def test_admin_export_requires_active_elevation(
    db_session,
    api_client,
    admin_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=1",
        headers=_headers(admin_bearer_headers, "admin-export-fictional-0003"),
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "admin_elevation_required"


def test_admin_export_route_is_concealed_from_a_regular_user(
    db_session,
    api_client,
    user_bearer_headers,
    report_id,
):
    db_session.commit()

    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=1",
        headers=_headers(user_bearer_headers, "admin-export-fictional-0004"),
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_admin_export_requires_an_explicit_revision(
    db_session,
    api_client,
    elevated_admin_bearer_headers,
    report_id,
):
    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx",
        headers=_headers(elevated_admin_bearer_headers, "admin-export-fictional-0005"),
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_admin_and_user_exports_of_the_same_revision_agree_byte_for_byte(
    db_session,
    api_client,
    owner_bearer_headers,
    elevated_admin_bearer_headers,
    report_id,
):
    db_session.commit()

    admin_response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=1",
        headers=_headers(elevated_admin_bearer_headers, "admin-export-fictional-0006"),
    )
    user_response = api_client.post(
        f"/api/v1/reports/{report_id}/export-docx?revision=1",
        headers=_headers(owner_bearer_headers, "export-fictional-0300"),
    )

    assert admin_response.status_code == user_response.status_code == 200
    assert admin_response.data == user_response.data
    assert admin_response.headers["X-Export-ID"] != user_response.headers["X-Export-ID"]
