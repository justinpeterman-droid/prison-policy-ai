"""PostgreSQL tests for the one-transaction revision services.

These exercise the property the whole feature exists for: two officers editing
the same report from the same base revision must produce exactly one new
revision and one conflict — never two revisions, never a half-written audit
trail.

Requires the RP-01 reporting models and a dedicated PostgreSQL database
(`TEST_DATABASE_URL`); the module skips cleanly without them rather than
pretending to have covered this ground.
"""
from uuid import uuid4

import pytest

reporting_models = pytest.importorskip(
    "backend.persistence.models.reporting",
    reason="RP-01 reporting models are not present on this branch",
)
revisions = pytest.importorskip(
    "backend.reports.revisions",
    reason="RP-01 reporting models are not present on this branch",
)

from backend.identity.audit import PostgresAuditWriter  # noqa: E402
from backend.webapp.api_v1.schemas.reporting import (  # noqa: E402
    IncidentSnapshotV1,
    ReportContentV1,
)

Report = reporting_models.Report
ReportRevision = reporting_models.ReportRevision
Incident = reporting_models.Incident
IncidentRevision = reporting_models.IncidentRevision

RevisionConflict = revisions.RevisionConflict
save_incident = revisions.save_incident
save_report = revisions.save_report
restore_report = revisions.restore_report
create_recovery_revision = revisions.create_recovery_revision


@pytest.fixture
def actor(seeded_account):
    return revisions.Actor(
        account_id=seeded_account.id,
        staff_member_id=seeded_account.staff_member_id,
        session_id=uuid4(),
        role="user",
        auth_version=1,
        must_change_pin=False,
    )


def _audit_rows(session, report_id):
    return session.execute(
        reporting_models.sa.text(
            "SELECT action FROM audit_events WHERE target_id = :target_id"
        ),
        {"target_id": report_id},
    ).scalars().all()


def test_two_saves_from_same_revision_yield_success_and_conflict(
    db_session_factory, fictional_report, actor
):
    first = save_report(
        db_session_factory(), actor, fictional_report.id,
        ReportContentV1(schema_version=1, narrative="First edit."),
        base_revision_number=1, reason="manual_save",
        request_id="req_revision_1", audit=PostgresAuditWriter(),
    )

    assert first.revision_number == 2

    with pytest.raises(RevisionConflict) as caught:
        save_report(
            db_session_factory(), actor, fictional_report.id,
            ReportContentV1(schema_version=1, narrative="Stale edit."),
            base_revision_number=1, reason="manual_save",
            request_id="req_revision_2", audit=PostgresAuditWriter(),
        )

    assert caught.value.current_revision_number == 2


def test_conflict_leaves_no_partial_revision_or_audit_row(
    db_session_factory, fictional_report, actor
):
    session = db_session_factory()
    before_revisions = session.query(ReportRevision).filter_by(
        report_id=fictional_report.id).count()
    before_audit = len(_audit_rows(session, fictional_report.id))

    with pytest.raises(RevisionConflict):
        save_report(
            db_session_factory(), actor, fictional_report.id,
            ReportContentV1(schema_version=1, narrative="Stale edit."),
            base_revision_number=0, reason="manual_save",
            request_id="req_revision_3", audit=PostgresAuditWriter(),
        )

    session.expire_all()
    assert session.query(ReportRevision).filter_by(
        report_id=fictional_report.id).count() == before_revisions
    assert len(_audit_rows(session, fictional_report.id)) == before_audit


def test_save_records_changed_field_names_without_values(
    db_session_factory, fictional_report, actor
):
    summary = save_report(
        db_session_factory(), actor, fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Fictional replacement."),
        base_revision_number=1, reason="manual_save",
        request_id="req_revision_4", audit=PostgresAuditWriter(),
    )

    assert summary.changed_fields == ["narrative"]
    session = db_session_factory()
    revision = session.query(ReportRevision).filter_by(
        report_id=fictional_report.id, revision_number=2).one()
    assert "Fictional replacement." not in str(revision.changed_fields)


def test_restore_copies_history_into_the_next_revision(
    db_session_factory, fictional_report, actor
):
    save_report(
        db_session_factory(), actor, fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Second."),
        base_revision_number=1, reason="manual_save",
        request_id="req_revision_5", audit=PostgresAuditWriter(),
    )

    restored = restore_report(
        db_session_factory(), actor, fictional_report.id,
        source_revision_number=1, base_revision_number=2,
        request_id="req_revision_6", audit=PostgresAuditWriter(),
    )

    assert restored.revision_number == 3
    assert restored.reason == "restored"
    session = db_session_factory()
    revision = session.query(ReportRevision).filter_by(
        report_id=fictional_report.id, revision_number=3).one()
    assert revision.source_revision_number == 1


def test_recovery_never_promotes_over_a_newer_current_revision(
    db_session_factory, fictional_report, actor
):
    save_report(
        db_session_factory(), actor, fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Newer current."),
        base_revision_number=1, reason="manual_save",
        request_id="req_revision_7", audit=PostgresAuditWriter(),
    )

    recovery = create_recovery_revision(
        db_session_factory(), actor, fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Recovered draft."),
        request_id="req_revision_8", audit=PostgresAuditWriter(),
    )

    assert recovery.reason == "recovery"
    assert recovery.revision_number == 3

    session = db_session_factory()
    report = session.get(Report, fictional_report.id)
    assert report.current_revision_number == 2
    assert report.content["narrative"] == "Newer current."


def test_incident_save_is_conflict_safe(
    db_session_factory, fictional_incident, actor
):
    first = save_incident(
        db_session_factory(), actor, fictional_incident.id,
        IncidentSnapshotV1(field_notes="First fictional notes."),
        base_revision_number=1, reason="manual_save",
        request_id="req_revision_9", audit=PostgresAuditWriter(),
    )

    assert first.revision_number == 2

    with pytest.raises(RevisionConflict):
        save_incident(
            db_session_factory(), actor, fictional_incident.id,
            IncidentSnapshotV1(field_notes="Stale fictional notes."),
            base_revision_number=1, reason="manual_save",
            request_id="req_revision_10", audit=PostgresAuditWriter(),
        )
