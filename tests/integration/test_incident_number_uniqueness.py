"""Official incident identity contracts across create, save, restore, and conflicts."""
from datetime import datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select

from backend.persistence.models.reporting import Incident, IncidentRevision


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
    return headers | {
        "Idempotency-Key": key,
        "X-Request-ID": f"request_{key}",
    }


def _create_body(fictional_staff, **overrides):
    body = {
        "reporting_staff_ids": [
            str(fictional_staff.blair.id),
            str(fictional_staff.alex.id),
        ],
        "field_notes": "Fictional field notes for official incident identity testing.",
    }
    body.update(overrides)
    return body


def test_create_normalizes_and_persists_official_incident_identity(
    db_session,
    db_session_factory,
    api_client,
    owner_bearer_headers,
    fictional_staff,
):
    db_session.commit()

    response = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-identity-create-0001"),
        json=_create_body(
            fictional_staff,
            incident_number="202608029",
            incident_name="  Barracks 4   Fight  ",
        ),
    )

    assert response.status_code == 201
    assert response.json["data"]["incident_number"] == "2026-08-029"
    assert response.json["data"]["incident_name"] == "Barracks 4 Fight"

    incident_id = UUID(response.json["data"]["incident_id"])
    with db_session_factory() as verification:
        incident = verification.get(Incident, incident_id)
        revision = verification.scalar(select(IncidentRevision).where(
            IncidentRevision.incident_id == incident_id,
            IncidentRevision.revision_number == 1,
        ))
        assert incident is not None
        assert incident.incident_number == "2026-08-029"
        assert incident.incident_name == "Barracks 4 Fight"
        assert revision is not None
        assert revision.snapshot["incident_number"] == "2026-08-029"
        assert revision.snapshot["incident_name"] == "Barracks 4 Fight"


def test_identity_changes_are_revisioned_and_restore_returns_the_original_values(
    db_session,
    api_client,
    owner_bearer_headers,
    fictional_staff,
):
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-identity-history-create"),
        json=_create_body(
            fictional_staff,
            incident_number="2026-08-029",
            incident_name="Barracks 4 Fight",
        ),
    )
    incident_id = created.json["data"]["incident_id"]

    saved = api_client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers=_headers(owner_bearer_headers, "incident-identity-history-save"),
        json={
            "field_notes": "Fictional revised incident identity notes.",
            "incident_number": "202608030",
            "incident_name": "  East Hall   Contraband  ",
            "base_revision_number": 1,
        },
    )
    revision_two = api_client.get(
        f"/api/v1/incidents/{incident_id}/revisions/2",
        headers=owner_bearer_headers,
    )
    restored = api_client.post(
        f"/api/v1/incidents/{incident_id}/restore",
        headers=_headers(owner_bearer_headers, "incident-identity-history-restore"),
        json={"revision_number": 1},
    )

    assert saved.status_code == 200
    assert saved.json["data"]["incident_number"] == "2026-08-030"
    assert saved.json["data"]["incident_name"] == "East Hall Contraband"
    assert revision_two.status_code == 200
    assert revision_two.json["data"]["incident_number"] == "2026-08-030"
    assert revision_two.json["data"]["incident_name"] == "East Hall Contraband"
    assert restored.status_code == 200
    assert restored.json["data"]["current_revision_number"] == 3
    assert restored.json["data"]["incident_number"] == "2026-08-029"
    assert restored.json["data"]["incident_name"] == "Barracks 4 Fight"


def test_duplicate_incident_number_returns_stable_conflict(
    db_session,
    api_client,
    owner_bearer_headers,
    fictional_staff,
):
    db_session.commit()
    first = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-identity-conflict-first"),
        json=_create_body(
            fictional_staff,
            incident_number="2026-08-031",
            incident_name="Fictional First Incident",
        ),
    )
    duplicate = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-identity-conflict-second"),
        json=_create_body(
            fictional_staff,
            incident_number="202608031",
            incident_name="Fictional Duplicate Incident",
        ),
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json["error"]["code"] == "incident_number_conflict"
    assert duplicate.json["error"]["message"] == (
        "This incident number is already in use."
    )


def test_invalid_incident_number_does_not_append_a_revision(
    db_session,
    db_session_factory,
    api_client,
    owner_bearer_headers,
    fictional_staff,
):
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-identity-invalid-create"),
        json=_create_body(fictional_staff),
    )
    incident_id = UUID(created.json["data"]["incident_id"])

    response = api_client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers=_headers(owner_bearer_headers, "incident-identity-invalid-save"),
        json={
            "field_notes": "Fictional invalid incident number attempt.",
            "incident_number": "2026-13-001",
            "base_revision_number": 1,
        },
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(
            IncidentRevision
        ).where(IncidentRevision.incident_id == incident_id)) == 1


def test_partial_save_keeps_the_assigned_incident_number(
    db_session,
    api_client,
    owner_bearer_headers,
    fictional_staff,
):
    """A save that never mentions identity must not clear it.

    The officer types the unit-log number once. An autosave of the notes, or any
    later partial save, does not speak to identity — so omitting the field means
    "unchanged", never "blank it". Losing the number would detach the record
    from the unit log it is filed under.
    """
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(owner_bearer_headers, "incident-identity-partial-create"),
        json=_create_body(
            fictional_staff,
            incident_number="2026-08-077",
            incident_name="Fictional Sticky Identity",
        ),
    )
    incident_id = created.json["data"]["incident_id"]

    saved = api_client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers=_headers(owner_bearer_headers, "incident-identity-partial-save"),
        json={
            "field_notes": "Fictional notes revised without touching identity.",
            "base_revision_number": 1,
        },
    )

    assert created.status_code == 201
    assert saved.status_code == 200
    assert saved.json["data"]["incident_number"] == "2026-08-077"
    assert saved.json["data"]["incident_name"] == "Fictional Sticky Identity"
