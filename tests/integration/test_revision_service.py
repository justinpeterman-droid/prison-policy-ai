"""PostgreSQL tests for caller-owned, conflict-safe revision transactions."""

from concurrent.futures import ThreadPoolExecutor
import inspect
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

reporting_models = pytest.importorskip(
    "backend.persistence.models.reporting",
    reason="RP-01 reporting models are not present on this branch",
)
revisions = pytest.importorskip(
    "backend.reports.revisions",
    reason="RP-02 revision services are not present on this branch",
)

from backend.identity.audit import PostgresAuditWriter  # noqa: E402
from backend.persistence.models import AuditEvent, StaffMember  # noqa: E402
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
def actor(fictional_staff_and_accounts):
    account = fictional_staff_and_accounts.user
    return revisions.Actor(
        account_id=account.id,
        staff_member_id=account.staff_member_id,
        session_id=uuid4(),
        role="user",
        auth_version=1,
        must_change_pin=False,
    )


def _audit_rows(session, report_id):
    return (
        session.execute(select(AuditEvent).where(AuditEvent.target_id == report_id))
        .scalars()
        .all()
    )


def test_public_report_service_interfaces_match_the_locked_roadmap():
    save_parameters = list(inspect.signature(save_report).parameters.values())
    restore_parameters = list(inspect.signature(restore_report).parameters.values())
    recovery_parameters = list(
        inspect.signature(create_recovery_revision).parameters.values()
    )

    assert [parameter.name for parameter in save_parameters[:6]] == [
        "session",
        "actor",
        "report_id",
        "content",
        "base_revision_number",
        "reason",
    ]
    assert [parameter.name for parameter in restore_parameters[:4]] == [
        "session",
        "actor",
        "report_id",
        "revision_number",
    ]
    assert [parameter.name for parameter in recovery_parameters[:5]] == [
        "session",
        "actor",
        "report_id",
        "content",
        "base_revision_number",
    ]
    assert inspect.signature(save_report).return_annotation is ReportRevision
    assert inspect.signature(restore_report).return_annotation is ReportRevision
    assert (
        inspect.signature(create_recovery_revision).return_annotation is ReportRevision
    )


def test_service_uses_caller_transaction_and_flushes_without_begin_or_commit(
    monkeypatch,
):
    class CallerOwnedSession:
        def __init__(self):
            self.added = []
            self.flush_count = 0
            self.begin_count = 0
            self.commit_count = 0

        def begin(self):
            self.begin_count += 1
            raise AssertionError("service must not open the caller transaction")

        def commit(self):
            self.commit_count += 1
            raise AssertionError("service must not commit the caller transaction")

        def add(self, value):
            self.added.append(value)

        def flush(self):
            self.flush_count += 1

    report = SimpleNamespace(
        id=uuid4(),
        current_revision_number=1,
        current_content={
            "schema_version": 1,
            "narrative": "Fictional initial report narrative.",
            "editable_fields": {},
            "validation": {},
            "warnings": [],
        },
        status="in_progress",
        updated_at=None,
    )
    actor = revisions.Actor(
        account_id=uuid4(),
        staff_member_id=uuid4(),
        session_id=uuid4(),
        role="user",
        auth_version=1,
        must_change_pin=False,
    )
    session = CallerOwnedSession()
    monkeypatch.setattr(revisions, "_lock_row", lambda *_args: report)
    monkeypatch.setattr(revisions, "_next_revision_number", lambda *_args: 2)
    monkeypatch.setattr(revisions, "_append_audit", lambda *_args, **_kwargs: None)

    revision = save_report(
        session,
        actor,
        report.id,
        ReportContentV1(schema_version=1, narrative="Fictional caller edit."),
        1,
        "manual_save",
    )

    assert isinstance(revision, ReportRevision)
    assert revision.provenance == {}
    assert revision.client_version == "0.0.0-development"
    UUID(revision.request_id)
    assert session.begin_count == 0
    assert session.commit_count == 0
    assert session.flush_count == 1


@pytest.mark.parametrize("target", ["report", "incident"])
def test_ai_result_stamps_centralized_provenance_and_fingerprint_columns(
    monkeypatch, target
):
    expected = {
        "fast_model": "fictional-fast-model",
        "pro_model": "fictional-pro-model",
        "model_location": "fictional-location",
        "classification_prompt_sha256": "a" * 64,
        "generation_prompt_sha256": "b" * 64,
        "checklist_sha256": "c" * 64,
        "template_sha256": "d" * 64,
        "cloud_run_revision": "fictional-cloud-revision",
        "source_commit": "e" * 40,
    }
    session = SimpleNamespace(added=[], flush_count=0)
    session.add = lambda value: session.added.append(value)
    session.flush = lambda: setattr(session, "flush_count", session.flush_count + 1)
    actor = revisions.Actor(uuid4(), uuid4(), uuid4(), "user", 1, False)
    monkeypatch.setattr(revisions, "collect_provenance", lambda: dict(expected))
    monkeypatch.setattr(revisions, "_next_revision_number", lambda *_args: 2)
    monkeypatch.setattr(revisions, "_append_audit", lambda *_args, **_kwargs: None)

    if target == "report":
        row = SimpleNamespace(
            current_revision_number=1,
            current_content={
                "schema_version": 1,
                "narrative": "Fictional initial narrative.",
                "editable_fields": {},
                "validation": {},
                "warnings": [],
            },
            status="in_progress",
            updated_at=None,
        )
        monkeypatch.setattr(revisions, "_lock_row", lambda *_args: row)
        revision = save_report(
            session,
            actor,
            uuid4(),
            ReportContentV1(narrative="Fictional AI narrative."),
            1,
            "ai_result",
        )
        assert revision.provenance == expected
        for key, value in expected.items():
            assert getattr(revision, key) == value
    else:
        row = SimpleNamespace(
            current_revision_number=1,
            incident_date=None,
            incident_time=None,
            facility="Fictional Unit",
            shift="A",
            location="Fictional Dayroom",
            category="inmate_fight",
            field_notes="Fictional notes.",
            classification={},
            extracted_facts={},
            gap_answers={},
            charges=[],
            validation={},
            status="in_progress",
            updated_at=None,
        )
        monkeypatch.setattr(revisions, "_lock_row", lambda *_args: row)
        revision = save_incident(
            session,
            actor,
            uuid4(),
            IncidentSnapshotV1(
                field_notes="Fictional notes.",
                classification={"persons_involved": [{"role": "inmate"}]},
            ),
            1,
            "ai_result",
        )
        assert revision.snapshot["provenance"] == expected

    assert session.flush_count == 1


@pytest.mark.parametrize("reason", ["manual_save", "autosave"])
def test_non_ai_report_save_does_not_claim_ai_provenance(monkeypatch, reason):
    session = SimpleNamespace(added=[], flush_count=0)
    session.add = lambda value: session.added.append(value)
    session.flush = lambda: setattr(session, "flush_count", session.flush_count + 1)
    row = SimpleNamespace(
        current_revision_number=1,
        current_content={
            "schema_version": 1,
            "narrative": "Fictional initial narrative.",
            "editable_fields": {},
            "validation": {},
            "warnings": [],
        },
        status="in_progress",
        updated_at=None,
    )
    actor = revisions.Actor(uuid4(), uuid4(), uuid4(), "user", 1, False)
    monkeypatch.setattr(revisions, "_lock_row", lambda *_args: row)
    monkeypatch.setattr(revisions, "_next_revision_number", lambda *_args: 2)
    monkeypatch.setattr(revisions, "_append_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        revisions,
        "collect_provenance",
        lambda: pytest.fail("manual/autosave must not collect AI provenance"),
    )

    revision = save_report(
        session,
        actor,
        uuid4(),
        ReportContentV1(narrative="Fictional officer edit."),
        1,
        reason,
    )

    assert revision.provenance == {}
    for key in revisions.PROVENANCE_COLUMN_NAMES:
        assert getattr(revision, key) is None


@pytest.mark.parametrize("reason", ["manual_save", "autosave"])
def test_non_ai_incident_save_does_not_inject_provenance(monkeypatch, reason):
    session = SimpleNamespace(added=[], flush_count=0)
    session.add = lambda value: session.added.append(value)
    session.flush = lambda: setattr(session, "flush_count", session.flush_count + 1)
    row = SimpleNamespace(
        current_revision_number=1,
        incident_date=None,
        incident_time=None,
        facility="Fictional Unit",
        shift="A",
        location="Fictional Dayroom",
        category="inmate_fight",
        field_notes="Fictional notes.",
        classification={},
        extracted_facts={},
        gap_answers={},
        charges=[],
        validation={},
        status="in_progress",
        updated_at=None,
    )
    actor = revisions.Actor(uuid4(), uuid4(), uuid4(), "user", 1, False)
    monkeypatch.setattr(revisions, "_lock_row", lambda *_args: row)
    monkeypatch.setattr(revisions, "_next_revision_number", lambda *_args: 2)
    monkeypatch.setattr(revisions, "_append_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        revisions,
        "collect_provenance",
        lambda: pytest.fail("manual/autosave must not collect AI provenance"),
    )

    revision = save_incident(
        session,
        actor,
        uuid4(),
        IncidentSnapshotV1(field_notes="Fictional notes."),
        1,
        reason,
    )

    assert "provenance" not in revision.snapshot
    assert not hasattr(row, "provenance")


def test_source_revision_metadata_composes_with_existing_provenance():
    source = {"fast_model": "fictional-fast-model", "source_commit": "a" * 40}

    assert revisions._source_revision_provenance(source, 3) == {
        **source,
        "source_revision_number": 3,
    }


@pytest.mark.parametrize("invalid_base", [-1, True, "1"])
def test_recovery_rejects_invalid_source_revision_before_database_work(invalid_base):
    actor = revisions.Actor(
        account_id=uuid4(),
        staff_member_id=uuid4(),
        session_id=uuid4(),
        role="user",
        auth_version=1,
        must_change_pin=False,
    )

    with pytest.raises(ValueError, match="base revision"):
        create_recovery_revision(
            SimpleNamespace(),
            actor,
            uuid4(),
            ReportContentV1(schema_version=1, narrative="Fictional recovery."),
            invalid_base,
        )


@pytest.mark.parametrize("invalid_revision", [-1, True, "1"])
def test_restore_rejects_invalid_source_revision_before_database_work(invalid_revision):
    actor = revisions.Actor(
        account_id=uuid4(),
        staff_member_id=uuid4(),
        session_id=uuid4(),
        role="user",
        auth_version=1,
        must_change_pin=False,
    )

    with pytest.raises(ValueError, match="revision number"):
        restore_report(SimpleNamespace(), actor, uuid4(), invalid_revision)


@pytest.mark.parametrize("invalid_base", [-1, True, "1"])
@pytest.mark.parametrize("service", ["report", "incident"])
def test_save_rejects_invalid_base_revision_before_database_work(invalid_base, service):
    actor = revisions.Actor(
        account_id=uuid4(),
        staff_member_id=uuid4(),
        session_id=uuid4(),
        role="user",
        auth_version=1,
        must_change_pin=False,
    )

    with pytest.raises(ValueError, match="base revision"):
        if service == "report":
            save_report(
                SimpleNamespace(),
                actor,
                uuid4(),
                ReportContentV1(schema_version=1, narrative="Fictional save."),
                invalid_base,
                "manual_save",
            )
        else:
            save_incident(
                SimpleNamespace(),
                actor,
                uuid4(),
                IncidentSnapshotV1(field_notes="Fictional notes."),
                invalid_base,
                "manual_save",
            )


def test_locked_base_call_returns_revision_with_non_null_safe_metadata(
    db_session, fictional_report, actor
):
    with db_session.begin_nested():
        revision = save_report(
            db_session,
            actor,
            fictional_report.id,
            ReportContentV1(schema_version=1, narrative="Fictional first edit."),
            1,
            "manual_save",
        )

        assert isinstance(revision, ReportRevision)
        assert revision.revision_number == 2
        assert revision.client_version == "0.0.0-development"
        UUID(revision.request_id)
        assert db_session.in_transaction()


def test_injected_request_metadata_is_persisted_without_service_commit(
    db_session, fictional_report, actor
):
    revision = save_report(
        db_session,
        actor,
        fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Fictional injected edit."),
        1,
        "manual_save",
        request_id="req_revision_injected",
        client_version="1.2.3",
        audit_writer=PostgresAuditWriter(),
    )

    assert revision.request_id == "req_revision_injected"
    assert revision.client_version == "1.2.3"
    assert db_session.in_transaction()


def test_two_real_connections_from_same_revision_yield_one_success_and_conflict(
    db_session_factory, db_session, fictional_report, actor
):
    report_id = fictional_report.id
    db_session.commit()
    barrier = Barrier(2)

    def save(narrative, request_id):
        session = db_session_factory()
        try:
            barrier.wait(timeout=10)
            with session.begin():
                revision = save_report(
                    session,
                    actor,
                    report_id,
                    ReportContentV1(schema_version=1, narrative=narrative),
                    1,
                    "manual_save",
                    request_id=request_id,
                    client_version="1.2.3",
                )
            return ("saved", revision.revision_number)
        except RevisionConflict as error:
            session.rollback()
            return ("conflict", error.current_revision_number)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda args: save(*args),
                [
                    ("Fictional concurrent edit A.", "req_concurrent_a"),
                    ("Fictional concurrent edit B.", "req_concurrent_b"),
                ],
            )
        )

    assert sorted(result[0] for result in results) == ["conflict", "saved"]
    assert {result[1] for result in results} == {2}

    with db_session_factory() as verification:
        assert (
            verification.scalar(
                select(Report.current_revision_number).where(Report.id == report_id)
            )
            == 2
        )
        assert (
            len(
                verification.scalars(
                    select(ReportRevision).where(ReportRevision.report_id == report_id)
                ).all()
            )
            == 2
        )
        assert len(_audit_rows(verification, report_id)) == 1


def test_committed_concurrency_rows_do_not_leak_into_the_next_test(db_session):
    leaked_employee_numbers = db_session.scalars(
        select(StaffMember.employee_number).where(
            StaffMember.employee_number.in_(
                {
                    "TEST-2101",
                    "TEST-2102",
                    "TEST-2103",
                    "TEST-9101",
                }
            )
        )
    ).all()

    assert leaked_employee_numbers == []


def test_caller_rollback_after_completed_work_removes_revision_current_and_audit(
    db_session_factory, db_session, fictional_report, actor
):
    report_id = fictional_report.id
    db_session.commit()
    session = db_session_factory()

    with pytest.raises(RuntimeError, match="force caller rollback"):
        with session.begin():
            revision = save_report(
                session,
                actor,
                report_id,
                ReportContentV1(
                    schema_version=1,
                    narrative="Fictional work that must roll back.",
                ),
                1,
                "manual_save",
                request_id="req_rollback_after_work",
                client_version="1.2.3",
            )
            assert revision.revision_number == 2
            assert len(_audit_rows(session, report_id)) == 1
            raise RuntimeError("force caller rollback")
    session.close()

    with db_session_factory() as verification:
        report = verification.get(Report, report_id)
        assert report.current_revision_number == 1
        assert report.current_content["narrative"] == (
            "Fictional initial report narrative."
        )
        assert (
            len(
                verification.scalars(
                    select(ReportRevision).where(ReportRevision.report_id == report_id)
                ).all()
            )
            == 1
        )
        assert _audit_rows(verification, report_id) == []


def test_save_records_changed_field_names_without_values(
    db_session, fictional_report, actor
):
    revision = save_report(
        db_session,
        actor,
        fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Fictional replacement."),
        1,
        "manual_save",
        request_id="req_revision_changed",
        client_version="1.2.3",
    )

    assert revision.changed_fields == {"fields": ["narrative"]}
    assert "Fictional replacement." not in str(revision.changed_fields)


def test_restore_copies_history_into_next_revision_and_current_content(
    db_session, fictional_report, actor
):
    save_report(
        db_session,
        actor,
        fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Fictional second revision."),
        1,
        "manual_save",
        request_id="req_revision_save_before_restore",
        client_version="1.2.3",
    )

    restored = restore_report(
        db_session,
        actor,
        fictional_report.id,
        1,
        request_id="req_revision_restore",
        client_version="1.2.3",
    )

    assert isinstance(restored, ReportRevision)
    assert restored.revision_number == 3
    assert restored.reason == "restored"
    assert restored.provenance["source_revision_number"] == 1
    assert fictional_report.current_revision_number == 3
    assert fictional_report.current_content == restored.snapshot


def test_recovery_preserves_supplied_stale_base_without_promoting(
    db_session, fictional_report, actor
):
    save_report(
        db_session,
        actor,
        fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Fictional newer current."),
        1,
        "manual_save",
        request_id="req_revision_current",
        client_version="1.2.3",
    )

    recovery = create_recovery_revision(
        db_session,
        actor,
        fictional_report.id,
        ReportContentV1(schema_version=1, narrative="Fictional recovered draft."),
        1,
        request_id="req_revision_recovery",
        client_version="1.2.3",
    )

    assert isinstance(recovery, ReportRevision)
    assert recovery.reason == "recovery"
    assert recovery.revision_number == 3
    assert recovery.provenance["source_revision_number"] == 1
    assert fictional_report.current_revision_number == 2
    assert fictional_report.current_content["narrative"] == ("Fictional newer current.")


def test_incident_save_updates_real_current_fields_and_is_conflict_safe(
    db_session, fictional_incident, actor
):
    snapshot = IncidentSnapshotV1.model_validate(
        {
            "field_notes": "Fictional replacement field notes.",
            "incident_date": fictional_incident.incident_date,
            "incident_time": fictional_incident.incident_time,
            "facility": "Fictional Updated Unit",
            "shift": "B",
            "location": "Fictional Updated Dayroom",
            "category": "fictional_updated_category",
            "classification": {"incident_type": "fictional_updated_category"},
            "extracted_facts": {"staff_count": 2},
            "gap_answers": {"camera_reviewed": "yes"},
            "charges": ["fictional charge"],
            "validation": {"complete": True},
        }
    )
    revision = save_incident(
        db_session,
        actor,
        fictional_incident.id,
        snapshot,
        1,
        "manual_save",
        request_id="req_incident_save",
        client_version="1.2.3",
    )

    assert isinstance(revision, IncidentRevision)
    assert revision.revision_number == 2
    assert fictional_incident.field_notes == snapshot.field_notes
    assert fictional_incident.facility == snapshot.facility
    assert fictional_incident.shift == snapshot.shift
    assert fictional_incident.location == snapshot.location
    assert fictional_incident.extracted_facts == snapshot.extracted_facts

    with pytest.raises(RevisionConflict):
        save_incident(
            db_session,
            actor,
            fictional_incident.id,
            IncidentSnapshotV1(field_notes="Fictional stale notes."),
            1,
            "manual_save",
            request_id="req_incident_stale",
            client_version="1.2.3",
        )
