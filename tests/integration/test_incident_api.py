"""PostgreSQL/API and OpenAPI contracts for authorized incident creation."""
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
import yaml

from backend.persistence.models import AuditEvent
from backend.persistence.models.reporting import Incident, IncidentRevision, Report, ReportAccess
from backend.persistence.models.security import IdempotencyRecord


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


def _create_body(fictional_staff):
    return {
        "reporting_staff_ids": [
            str(fictional_staff.blair.id),
            str(fictional_staff.alex.id),
            str(fictional_staff.blair.id),
        ],
        "field_notes": "Fictional field notes for incident API testing.",
    }


def test_create_incident_is_idempotent_and_stores_only_server_owned_selection_metadata(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    fictional_staff_and_accounts, fictional_staff,
):
    actor = fictional_staff_and_accounts.user
    db_session.commit()
    headers = _headers(owner_bearer_headers, "incident-fictional-0001")
    body = _create_body(fictional_staff)

    first = api_client.post("/api/v1/incidents", headers=headers, json=body)
    replay = api_client.post("/api/v1/incidents", headers=headers, json=body)

    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json["data"]["incident_id"] == first.json["data"]["incident_id"]
    assert first.json["data"]["reporting_staff_ids"] == [
        str(fictional_staff.blair.id), str(fictional_staff.alex.id),
    ]
    with db_session_factory() as verification:
        incident_id = UUID(first.json["data"]["incident_id"])
        revision = verification.scalar(select(IncidentRevision).where(
            IncidentRevision.incident_id == incident_id,
            IncidentRevision.revision_number == 1,
        ))
        assert revision.snapshot["server_metadata"] == {
            "reporting_staff_ids": [
                str(fictional_staff.blair.id), str(fictional_staff.alex.id),
            ]
        }
        assert verification.scalar(select(func.count()).select_from(Report).where(
            Report.incident_id == incident_id)) == 0
        assert verification.scalar(select(func.count()).select_from(ReportAccess)) == 0
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "incident.created", AuditEvent.target_id == incident_id)) == 1
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == actor.id,
            IdempotencyRecord.action == "incident.create",
            IdempotencyRecord.status == "completed",
        )) == 1


def test_selected_staff_can_read_but_unrelated_user_receives_concealed_404(
    db_session, api_client, owner_bearer_headers, preparer_bearer_headers,
    unrelated_bearer_headers, fictional_staff,
):
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-fictional-auth-0001"),
        json=_create_body(fictional_staff),
    )
    incident_id = created.json["data"]["incident_id"]

    selected = api_client.get(
        f"/api/v1/incidents/{incident_id}", headers=preparer_bearer_headers)
    unrelated = api_client.get(
        f"/api/v1/incidents/{incident_id}", headers=unrelated_bearer_headers)

    assert selected.status_code == 200
    assert selected.json["data"]["incident_id"] == incident_id
    assert unrelated.status_code == 404
    assert unrelated.json["error"]["code"] == "not_found"


def test_staff_lookup_is_active_only_bounded_and_cursor_paginated(
    db_session, api_client, owner_bearer_headers, fictional_staff_and_accounts,
):
    inactive = fictional_staff_and_accounts.unrelated.staff_member
    inactive.is_active = False
    db_session.commit()

    first = api_client.get(
        "/api/v1/staff?query=Example&limit=2", headers=owner_bearer_headers)
    assert first.status_code == 200
    assert len(first.json["data"]["items"]) == 2
    assert first.json["data"]["next_cursor"]
    assert all(item["is_active"] is True for item in first.json["data"]["items"])

    second = api_client.get(
        "/api/v1/staff?query=Example&limit=2&cursor="
        + first.json["data"]["next_cursor"],
        headers=owner_bearer_headers,
    )
    assert second.status_code == 200
    all_ids = {
        item["staff_id"] for response in (first, second)
        for item in response.json["data"]["items"]
    }
    assert str(inactive.id) not in all_ids


def test_patch_and_restore_retain_server_metadata_and_revision_history(
    db_session, db_session_factory, api_client, owner_bearer_headers, fictional_staff,
):
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-fictional-history-0001"),
        json=_create_body(fictional_staff),
    )
    incident_id = created.json["data"]["incident_id"]
    patched = api_client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers=_headers(owner_bearer_headers, "incident-fictional-save-0001"),
        json={
            "field_notes": "Fictional revised field notes.",
            "base_revision_number": 1,
            "reason": "manual_save",
        },
    )
    restored = api_client.post(
        f"/api/v1/incidents/{incident_id}/restore",
        headers=_headers(owner_bearer_headers, "incident-fictional-restore-0001"),
        json={"revision_number": 1},
    )
    history = api_client.get(
        f"/api/v1/incidents/{incident_id}/revisions", headers=owner_bearer_headers)
    detail = api_client.get(
        f"/api/v1/incidents/{incident_id}/revisions/2", headers=owner_bearer_headers)

    assert patched.status_code == 200
    assert restored.status_code == 200
    assert restored.json["data"]["current_revision_number"] == 3
    assert restored.json["data"]["field_notes"] == _create_body(fictional_staff)["field_notes"]
    assert [item["revision_number"] for item in history.json["data"]["items"]] == [1, 2, 3]
    assert detail.json["data"]["field_notes"] == "Fictional revised field notes."
    with db_session_factory() as verification:
        revisions = verification.scalars(select(IncidentRevision).where(
            IncidentRevision.incident_id == UUID(incident_id)
        ).order_by(IncidentRevision.revision_number)).all()
        expected = _create_body(fictional_staff)["reporting_staff_ids"][:2]
        assert [row.snapshot["server_metadata"]["reporting_staff_ids"] for row in revisions] == [
            expected, expected, expected,
        ]


def test_patch_rejects_if_match_that_disagrees_with_body_without_writing(
    db_session, db_session_factory, api_client, owner_bearer_headers, fictional_staff,
):
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-fictional-etag-create-0001"),
        json=_create_body(fictional_staff),
    )
    incident_id = UUID(created.json["data"]["incident_id"])
    headers = _headers(owner_bearer_headers, "incident-fictional-etag-save-0001")
    headers["If-Match"] = '"2"'

    response = api_client.patch(
        f"/api/v1/incidents/{incident_id}", headers=headers,
        json={"field_notes": "Fictional conflicting edit.", "base_revision_number": 1},
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(IncidentRevision).where(
            IncidentRevision.incident_id == incident_id)) == 1


@pytest.mark.parametrize("injected_key", [
    "server_metadata", "actor", "role", "employee_number", "owner_staff_member_id",
    "model_name", "prompt_hash",
])
def test_create_rejects_client_identity_and_provenance_injection(
    db_session, api_client, owner_bearer_headers, fictional_staff, injected_key,
):
    db_session.commit()
    body = _create_body(fictional_staff)
    body[injected_key] = {"reporting_staff_ids": [str(fictional_staff.alex.id)]}

    response = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, f"incident-inject-{injected_key}"),
        json=body,
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_inactive_reporting_staff_is_rejected_before_any_incident_side_effect(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    fictional_staff_and_accounts,
):
    inactive = fictional_staff_and_accounts.unrelated.staff_member
    inactive.is_active = False
    actor_id = fictional_staff_and_accounts.user.id
    db_session.commit()

    response = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-fictional-inactive-0001"),
        json={
            "reporting_staff_ids": [str(inactive.id)],
            "field_notes": "Fictional field notes rejected for inactive staff.",
        },
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(Incident).where(
            Incident.created_by_account_id == actor_id)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == actor_id,
            IdempotencyRecord.action == "incident.create",
        )) == 0


def test_over_limit_unicode_is_rejected_atomically_before_idempotency_or_audit(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    fictional_staff_and_accounts, fictional_staff,
):
    actor_id = fictional_staff_and_accounts.user.id
    db_session.commit()
    response = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-fictional-limit-0001"),
        json={
            "reporting_staff_ids": [str(fictional_staff.alex.id)],
            "field_notes": "\U0001f6e1" * 30_001,
        },
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(Incident).where(
            Incident.created_by_account_id == actor_id)) == 0
        assert verification.scalar(select(func.count()).select_from(IncidentRevision).join(
            Incident, Incident.id == IncidentRevision.incident_id
        ).where(Incident.created_by_account_id == actor_id)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == actor_id,
            IdempotencyRecord.action == "incident.create",
        )) == 0
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.actor_account_id == actor_id,
            AuditEvent.action == "incident.created",
        )) == 0


def test_openapi_documents_exact_incident_boundary_headers_and_errors():
    document = yaml.safe_load(Path("openapi/access-v1.yaml").read_text(encoding="utf-8"))
    schemas = document["components"]["schemas"]
    create = schemas["IncidentCreateRequest"]
    save = schemas["IncidentSaveRequest"]
    assert create["properties"]["field_notes"]["type"] == "string"
    assert create["properties"]["field_notes"]["maxLength"] == 30000
    assert save["properties"]["field_notes"]["type"] == "string"
    assert save["properties"]["field_notes"]["maxLength"] == 30000
    assert "server_metadata" not in create["properties"]
    assert "actor" not in create["properties"]

    paths = document["paths"]
    required = {
        "/api/v1/staff",
        "/api/v1/incidents",
        "/api/v1/incidents/{incident_id}",
        "/api/v1/incidents/{incident_id}/revisions",
        "/api/v1/incidents/{incident_id}/revisions/{revision_number}",
        "/api/v1/incidents/{incident_id}/restore",
    }
    assert required <= set(paths)
    create_operation = paths["/api/v1/incidents"]["post"]
    parameter_refs = {item["$ref"] for item in create_operation["parameters"]}
    assert "#/components/parameters/XClientVersion" in parameter_refs
    assert "#/components/parameters/XRequestId" in parameter_refs
    assert "#/components/parameters/IdempotencyKey" in parameter_refs
    assert "400" in create_operation["responses"]
    assert "422" in create_operation["responses"]
