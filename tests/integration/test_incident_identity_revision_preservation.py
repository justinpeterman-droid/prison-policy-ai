"""Cross-service contracts for official incident identity revision preservation."""

from backend.reports.revisions import save_incident
from backend.webapp.api_v1.schemas.reporting import IncidentSnapshotV1


def test_ai_revision_preserves_official_identity_in_snapshot(
    db_session,
    user_actor,
    fictional_incident,
):
    fictional_incident.incident_number = "2026-08-044"
    fictional_incident.incident_name = "Fictional East Hall Incident"
    db_session.commit()

    revision = save_incident(
        db_session,
        user_actor,
        fictional_incident.id,
        IncidentSnapshotV1(
            field_notes="Fictional AI-enriched notes that retain official identity."
        ),
        1,
        "ai_result",
        request_id="request_fictional_identity_ai_revision",
        client_version="1.0.0",
    )
    db_session.commit()
    db_session.refresh(fictional_incident)

    assert fictional_incident.incident_number == "2026-08-044"
    assert fictional_incident.incident_name == "Fictional East Hall Incident"
    assert revision.snapshot["incident_number"] == "2026-08-044"
    assert revision.snapshot["incident_name"] == "Fictional East Hall Incident"
