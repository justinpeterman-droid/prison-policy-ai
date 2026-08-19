"""Service-level contracts for official incident identity revisions."""
from datetime import datetime, timedelta
from uuid import UUID

import pytest

from backend.reports.persistence import save_incident_record
from backend.webapp.api_v1.schemas.reporting import SaveIncidentRequest


@pytest.fixture(autouse=True)
def _fictional_access_api_environment(monkeypatch, identity_fixed_now):
    """Same bearer-token clock the other identity contracts run under.

    Without it the fixed token in `owner_bearer_headers` reads as expired and
    every request in this module comes back 401 instead of exercising the save.
    """
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


def _headers(base: dict[str, str], request_id: str, idempotency_key: str) -> dict[str, str]:
    return {
        **base,
        "X-Request-ID": request_id,
        "Idempotency-Key": idempotency_key,
    }


def test_save_service_normalizes_and_revisions_official_identity(
    db_session,
    db_session_factory,
    api_client,
    owner_bearer_headers,
    fictional_staff,
    user_actor,
):
    db_session.commit()
    created = api_client.post(
        "/api/v1/incidents",
        headers=_headers(
            owner_bearer_headers,
            "incident_identity_service_create",
            "incident-identity-service-create",
        ),
        json={
            "reporting_staff_ids": [
                str(fictional_staff.alex.id),
                str(fictional_staff.blair.id),
            ],
            "field_notes": "Fictional service identity field notes.",
            "incident_number": "2026-08-052",
            "incident_name": "Fictional Service Incident",
        },
    )
    assert created.status_code == 201
    incident_id = UUID(created.json["data"]["incident_id"])

    with db_session_factory() as service_session:
        view = save_incident_record(
            service_session,
            user_actor,
            incident_id,
            SaveIncidentRequest(
                field_notes="Fictional revised service identity notes.",
                incident_number="202608053",
                incident_name="  Fictional East   Hall Incident  ",
                base_revision_number=1,
            ),
            "incident-identity-service-save",
            request_id="incident_identity_service_save",
            client_version="1.0.0",
        )
        service_session.commit()

    assert view.incident.incident_number == "2026-08-053"
    assert view.incident.incident_name == "Fictional East Hall Incident"
    assert view.revision_number == 2
