"""PostgreSQL worker lifecycle tests with a fake report engine."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command as alembic_command
from alembic.config import Config
import pytest
from sqlalchemy import func, select

from backend.jobs.service import SubmitJobCommand, claim_job, submit_job
from backend.persistence.models import AuditEvent
from backend.persistence.models.jobs import AiJob
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
    ReportRevision,
    ReportType,
)
from backend.reports.revisions import save_report
from backend.webapp.api_v1.schemas.reporting import ReportContentV1
from backend.worker.app import create_worker_app
from backend.worker.routes import JobEngineResult, TerminalJobFailure


NOW = datetime(2026, 8, 12, 18, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def _restore_worker_schema_after_prior_migration_round_trips(db_engine):
    """Do not inherit a prior module's deliberately downgraded schema."""
    alembic_command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


class FakeReportEngine:
    def __init__(self, *, failure=None, before_result=None):
        self.failure = failure
        self.before_result = before_result
        self.calls = []

    def run(self, session, job):
        self.calls.append((job.id, job.job_type, job.stage, job.claim_token))
        if self.failure is not None:
            raise self.failure
        if self.before_result is not None:
            self.before_result()
        return JobEngineResult(
            report_content=ReportContentV1(
                narrative="Fictional generated report narrative.",
                validation={"result": "fictional_valid"},
            ),
        )


class FictionalLifecycleEngine:
    """Complete adapter-shaped fictional outputs for each public job type."""

    def __init__(
        self,
        *,
        before_result=None,
        generation_errors=None,
        report_key="supervisor_summary",
        include_form005=False,
    ):
        self.before_result = before_result
        self.generation_errors = list(generation_errors or [])
        self.report_key = report_key
        self.include_form005 = include_form005
        self.calls = []

    def run(self, session, job):
        self.calls.append((job.id, job.job_type, job.stage, job.claim_token))
        if self.before_result is not None:
            self.before_result()
        if job.job_type == "classify":
            return {
                "incident_type": "fictional_incident",
                "label": "Fictional incident",
                "charges": ["Fictional charge"],
                "charge_descriptions": {},
            }
        if job.job_type == "extract":
            return {
                "slots": {"location": "Fictional East Wing"},
                "gaps": [],
                "blocking_remaining": 0,
                "markers": [],
                "checklist": [],
                "auto_content": [],
                "officers": [],
                "provenance": {},
            }
        key = "disciplinary" if job.job_type == "disciplinary" else self.report_key
        narrative = (
            "Fictional disciplinary narrative."
            if key == "disciplinary"
            else ("Fictional supervisor summary narrative.")
        )
        return {
            "generation_errors": self.generation_errors,
            "reports": {key: narrative},
            "form005": {
                "narrative": "Fictional form 005 narrative.",
                "unit_division": "Fictional Unit",
            }
            if self.include_form005
            else {},
            "flags": [],
            "markers": [],
            "officers": [],
            "style": {"result": "fictional_valid"},
            "repaired": {},
        }


class InvalidContentEngine(FakeReportEngine):
    def run(self, session, job):
        self.calls.append((job.id, job.job_type, job.stage, job.claim_token))
        ReportContentV1(narrative="x" * 50_001)


class FakeMetricSink:
    def __init__(self):
        self.events = []

    def increment(self, name, *, labels):
        self.events.append((name, labels))


def _queue_job(
    db_session_factory,
    actor,
    incident_id,
    report_id,
    *,
    job_type="generate",
    idempotency_key="job-fictional-worker-0001",
):
    with db_session_factory.begin() as session:
        job = submit_job(
            session,
            actor,
            SubmitJobCommand(
                incident_id=incident_id,
                job_type=job_type,
                report_id=report_id,
            ),
            idempotency_key,
            1,
            now=NOW,
            request_id="request_fictional_worker_submit",
            client_version="1.0.0",
        )
        return job.id


def _queue_reportless_job(
    db_session_factory,
    actor,
    incident_id,
    *,
    job_type="generate",
    idempotency_key="job-fictional-worker-reportless",
    base_revision_number=1,
):
    with db_session_factory.begin() as session:
        job = submit_job(
            session,
            actor,
            SubmitJobCommand(incident_id=incident_id, job_type=job_type),
            idempotency_key,
            base_revision_number,
            now=NOW,
            request_id="request_fictional_worker_reportless",
            client_version="1.0.0",
        )
        return job.id


def _headers(job_id, retry_count="0"):
    return {
        "X-CloudTasks-TaskName": f"ai-job-{job_id}",
        "X-CloudTasks-QueueName": "fictional-report-jobs",
        "X-CloudTasks-TaskRetryCount": retry_count,
    }


def _post(client, job_id, retry_count="0"):
    return client.post(
        f"/internal/jobs/{job_id}/run",
        headers=_headers(job_id, retry_count),
        json={"job_id": str(job_id)},
    )


def _worker(db_session_factory, engine, metrics=None):
    app = create_worker_app(
        session_factory=db_session_factory,
        report_engine=engine,
        metric_sink=metrics,
        now=lambda: NOW,
        queue_name="fictional-report-jobs",
    )
    app.config["TESTING"] = True
    return app.test_client()


def _append_reporting_selection(
    db_session_factory,
    *,
    incident_id,
    actor,
    reporting_staff_ids,
):
    with db_session_factory.begin() as prepare:
        incident = prepare.get(Incident, incident_id)
        snapshot = {
            "schema_version": 1,
            "field_notes": incident.field_notes,
            "server_metadata": {
                "reporting_staff_ids": [str(value) for value in reporting_staff_ids],
            },
        }
        incident.current_revision_number = 2
        prepare.add(
            IncidentRevision(
                id=uuid4(),
                incident_id=incident.id,
                revision_number=2,
                editor_account_id=actor.account_id,
                editor_staff_member_id=actor.staff_member_id,
                snapshot=snapshot,
                changed_fields={"fields": []},
                reason="manual_save",
                client_version="1.0.0",
                request_id="request_fictional_reporting_selection",
                created_at=NOW,
            )
        )
    return 2


def test_worker_claims_runs_and_commits_one_fenced_revision_and_result(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    engine = FakeReportEngine()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )

    response = _post(_worker(db_session_factory, engine), job_id)

    if response.status_code != 204:
        with db_session_factory() as diagnosis:
            diagnostic_job = diagnosis.get(AiJob, job_id)
            pytest.fail(
                "worker did not commit the fictional result: "
                f"status={response.status_code}, state={diagnostic_job.state}, "
                f"stage={diagnostic_job.stage}, error={diagnostic_job.error_code}",
                pytrace=False,
            )
    assert len(engine.calls) == 1
    assert engine.calls[0][2] == "generating"
    assert isinstance(engine.calls[0][3], UUID)
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.stage, job.attempts, job.error_code) == (
            "succeeded",
            "completed",
            1,
            None,
        )
        assert job.claim_token is job.lease_expires_at is None
        assert job.result_reference == {
            "reports": [{"report_id": str(fictional_report.id), "revision_number": 2}],
        }
        revision = verification.scalar(
            select(ReportRevision).where(
                ReportRevision.report_id == fictional_report.id,
                ReportRevision.revision_number == 2,
            )
        )
        assert revision.reason == "ai_result"
        assert revision.source_ai_job_id == job_id
        assert revision.snapshot["narrative"] == "Fictional generated report narrative."


def test_redelivery_does_not_call_engine_or_apply_a_second_result(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    engine = FakeReportEngine()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    client = _worker(db_session_factory, engine)

    first = _post(client, job_id)
    redelivery = _post(client, job_id, "1")

    assert first.status_code == redelivery.status_code == 204
    assert len(engine.calls) == 1
    with db_session_factory() as verification:
        assert (
            verification.scalar(
                select(func.count())
                .select_from(ReportRevision)
                .where(
                    ReportRevision.report_id == fictional_report.id,
                )
            )
            == 2
        )


def test_expired_lease_recovery_emits_repeat_risk_without_identity_or_content(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    with db_session_factory.begin() as abandoned:
        claimed = claim_job(abandoned, job_id, now=NOW - timedelta(minutes=21))
        assert claimed is not None
        claimed.request_metadata = {
            **claimed.request_metadata,
            "provider_attempt_started": {
                "attempt": claimed.attempts,
                "claim_token": str(claimed.claim_token),
            },
        }
    engine = FakeReportEngine()
    metrics = FakeMetricSink()

    response = _post(_worker(db_session_factory, engine, metrics), job_id, "1")
    redelivery = _post(_worker(db_session_factory, engine, metrics), job_id, "2")

    assert response.status_code == redelivery.status_code == 204
    assert metrics.events == [
        (
            "ai_provider_repeat_risk_total",
            {"job_type": "generate"},
        )
    ]
    rendered = repr(metrics.events)
    assert str(user_actor.account_id) not in rendered
    assert fictional_incident.field_notes not in rendered
    assert len(engine.calls) == 1


def test_first_provider_attempt_emits_no_repeat_risk_metric(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    metrics = FakeMetricSink()

    response = _post(_worker(db_session_factory, FakeReportEngine(), metrics), job_id)

    assert response.status_code == 204
    assert metrics.events == []


def test_deterministic_failure_is_terminal_audited_and_not_retried(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    engine = FakeReportEngine(failure=TerminalJobFailure("job_output_invalid"))
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    client = _worker(db_session_factory, engine)

    first = _post(client, job_id)
    redelivery = _post(client, job_id, "1")

    assert first.status_code == redelivery.status_code == 204
    assert len(engine.calls) == 1
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.stage, job.error_code) == (
            "failed",
            "failed",
            "job_output_invalid",
        )
        audit = verification.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "ai.job_failed",
                AuditEvent.target_id == job_id,
            )
        )
        assert audit.details == {
            "job_id": str(job_id),
            "job_type": "generate",
            "result_code": "job_output_invalid",
        }


def test_revoked_live_report_access_fails_before_fake_engine_call(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    with db_session_factory.begin() as revoke:
        access = revoke.scalar(
            select(ReportAccess).where(
                ReportAccess.report_id == fictional_report.id,
                ReportAccess.staff_member_id == user_actor.staff_member_id,
            )
        )
        access.revoked_at = NOW
    engine = FakeReportEngine()

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    assert engine.calls == []
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == (
            "failed",
            "job_authorization_invalid",
        )


def test_revoked_incident_access_blocks_reportless_job_before_provider(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_reportless_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        job_type="classify",
        idempotency_key="job-fictional-revoked-classify",
    )
    with db_session_factory.begin() as revoke:
        access = revoke.scalar(
            select(ReportAccess).where(
                ReportAccess.report_id == fictional_report.id,
                ReportAccess.staff_member_id == user_actor.staff_member_id,
            )
        )
        access.revoked_at = NOW
    engine = FictionalLifecycleEngine()

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    assert engine.calls == []
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == (
            "failed",
            "job_authorization_invalid",
        )
        assert "provider_attempt_completed" not in job.request_metadata
        assert (
            verification.scalar(
                select(func.count())
                .select_from(IncidentRevision)
                .where(
                    IncidentRevision.incident_id == fictional_incident.id,
                )
            )
            == 1
        )


def test_transient_engine_failure_releases_claim_and_retry_commits_once(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    engine = FakeReportEngine(failure=TimeoutError("fictional timeout"))
    metrics = FakeMetricSink()
    client = _worker(db_session_factory, engine, metrics)

    transient = _post(client, job_id)
    with db_session_factory() as verification:
        released = verification.get(AiJob, job_id)
        assert (released.state, released.stage) == ("queued", "queued")
        assert released.claim_token is released.lease_expires_at is None
    engine.failure = None
    retry = _post(client, job_id, "1")

    assert transient.status_code == 503
    assert retry.status_code == 204
    assert len(engine.calls) == 2
    assert metrics.events == [
        (
            "ai_provider_repeat_risk_total",
            {"job_type": "generate"},
        )
    ]
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.attempts) == ("succeeded", 2)
        assert (
            verification.scalar(
                select(func.count())
                .select_from(ReportRevision)
                .where(
                    ReportRevision.report_id == fictional_report.id,
                )
            )
            == 2
        )


def test_reportless_generation_creates_revisioned_attributed_report_shell(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    base_revision = _append_reporting_selection(
        db_session_factory,
        incident_id=fictional_incident.id,
        actor=user_actor,
        reporting_staff_ids=[user_actor.staff_member_id],
    )
    job_id = _queue_reportless_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        base_revision_number=base_revision,
    )
    engine = FictionalLifecycleEngine()

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    assert len(engine.calls) == 1
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == ("succeeded", None)
        created = verification.scalar(
            select(Report).where(
                Report.incident_id == fictional_incident.id,
                Report.report_type == ReportType.SUPERVISOR_SUMMARY,
                Report.reporting_staff_member_id == user_actor.staff_member_id,
            )
        )
        revision = verification.scalar(
            select(ReportRevision).where(
                ReportRevision.report_id == created.id,
                ReportRevision.revision_number == 1,
            )
        )
        incident_revision = verification.scalar(
            select(IncidentRevision).where(
                IncidentRevision.incident_id == fictional_incident.id,
                IncidentRevision.revision_number == base_revision,
            )
        )
        assert revision.snapshot["narrative"] == "Fictional supervisor summary narrative."
        assert revision.source_incident_revision_id == incident_revision.id
        assert revision.source_ai_job_id == job_id
        assert job.result_reference == {
            "reports": [
                {
                    "report_id": str(created.id),
                    "revision_number": 1,
                }
            ]
        }


def test_generation_persists_form_005_as_an_attributed_report_revision(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    base_revision = _append_reporting_selection(
        db_session_factory,
        incident_id=fictional_incident.id,
        actor=user_actor,
        reporting_staff_ids=[user_actor.staff_member_id],
    )
    job_id = _queue_reportless_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        idempotency_key="job-fictional-form-005",
        base_revision_number=base_revision,
    )

    response = _post(
        _worker(
            db_session_factory,
            FictionalLifecycleEngine(include_form005=True),
        ),
        job_id,
    )

    assert response.status_code == 204
    with db_session_factory() as verification:
        report = verification.scalar(
            select(Report).where(
                Report.incident_id == fictional_incident.id,
                Report.report_type == ReportType.FORM_005,
                Report.reporting_staff_member_id == user_actor.staff_member_id,
            )
        )
        revision = verification.scalar(
            select(ReportRevision).where(
                ReportRevision.report_id == report.id,
            )
        )
        assert revision.snapshot == {
            "schema_version": 1,
            "narrative": "Fictional form 005 narrative.",
            "editable_fields": {
                "narrative": "Fictional form 005 narrative.",
                "unit_division": "Fictional Unit",
            },
            "validation": {
                "flags": [],
                "repaired": {},
                "style": {"result": "fictional_valid"},
            },
            "warnings": [],
        }
        assert revision.source_ai_job_id == job_id


def test_provider_result_is_rejected_when_claim_expires_during_call(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    clock_values = iter((NOW, NOW, NOW, NOW + timedelta(minutes=21)))
    app = create_worker_app(
        session_factory=db_session_factory,
        report_engine=FakeReportEngine(),
        metric_sink=FakeMetricSink(),
        now=lambda: next(clock_values),
        queue_name="fictional-report-jobs",
    )
    app.config["TESTING"] = True

    response = _post(app.test_client(), job_id)

    assert response.status_code == 503
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.attempts) == ("running", 1)
        assert job.result_reference == {}
        assert (
            verification.scalar(
                select(func.count())
                .select_from(ReportRevision)
                .where(
                    ReportRevision.report_id == fictional_report.id,
                )
            )
            == 1
        )


def test_incident_change_during_provider_call_commits_conflict_without_report_result(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )

    def advance_incident():
        from backend.persistence.models.reporting import Incident

        with db_session_factory.begin() as change:
            incident = change.get(Incident, fictional_incident.id)
            incident.current_revision_number = 2

    engine = FakeReportEngine(before_result=advance_incident)

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    assert len(engine.calls) == 1
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == ("failed", "job_result_conflict")
        assert job.result_reference == {}
        assert (
            verification.scalar(
                select(func.count())
                .select_from(ReportRevision)
                .where(
                    ReportRevision.report_id == fictional_report.id,
                )
            )
            == 1
        )


def test_report_edit_during_provider_call_is_terminal_conflict_without_ai_revision(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )

    def employee_edit():
        with db_session_factory.begin() as change:
            save_report(
                change,
                user_actor,
                fictional_report.id,
                ReportContentV1(
                    narrative="Fictional employee edit during provider work.",
                ),
                1,
                "manual_save",
                request_id="request_fictional_concurrent_edit",
                client_version="1.0.0",
            )

    engine = FictionalLifecycleEngine(
        before_result=employee_edit,
        report_key="first_person",
    )

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        report = verification.get(Report, fictional_report.id)
        assert (job.state, job.error_code) == ("failed", "job_result_conflict")
        assert report.current_revision_number == 2
        assert report.current_content["narrative"] == ("Fictional employee edit during provider work.")
        assert (
            verification.scalar(
                select(func.count())
                .select_from(ReportRevision)
                .where(
                    ReportRevision.report_id == fictional_report.id,
                    ReportRevision.reason == "ai_result",
                )
            )
            == 0
        )


@pytest.mark.parametrize("job_type", ["classify", "extract"])
def test_incident_jobs_append_immutable_ai_revision_and_result_reference(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
    job_type,
):
    db_session.commit()
    job_id = _queue_reportless_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        job_type=job_type,
        idempotency_key=f"job-fictional-{job_type}-0001",
    )

    response = _post(_worker(db_session_factory, FictionalLifecycleEngine()), job_id)

    assert response.status_code == 204
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        incident = verification.get(Incident, fictional_incident.id)
        revision = verification.scalar(
            select(IncidentRevision).where(
                IncidentRevision.incident_id == fictional_incident.id,
                IncidentRevision.revision_number == 2,
            )
        )
        assert (job.state, job.error_code) == ("succeeded", None)
        assert job.result_reference == {"incident_revision_number": 2}
        assert revision.reason == "ai_result"
        assert incident.current_revision_number == 2
        if job_type == "classify":
            assert incident.classification["label"] == "Fictional incident"
            assert incident.category == "fictional_incident"
        else:
            assert incident.extracted_facts["location"] == "Fictional East Wing"


def test_reportless_disciplinary_job_creates_durable_report_shell(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    base_revision = _append_reporting_selection(
        db_session_factory,
        incident_id=fictional_incident.id,
        actor=user_actor,
        reporting_staff_ids=[user_actor.staff_member_id],
    )
    job_id = _queue_reportless_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        job_type="disciplinary",
        idempotency_key="job-fictional-disciplinary-0001",
        base_revision_number=base_revision,
    )

    response = _post(_worker(db_session_factory, FictionalLifecycleEngine()), job_id)

    assert response.status_code == 204
    with db_session_factory() as verification:
        report = verification.scalar(
            select(Report).where(
                Report.incident_id == fictional_incident.id,
                Report.report_type == ReportType.DISCIPLINARY,
                Report.reporting_staff_member_id == user_actor.staff_member_id,
            )
        )
        revision = verification.scalar(
            select(ReportRevision).where(
                ReportRevision.report_id == report.id,
            )
        )
        assert revision.snapshot["narrative"] == "Fictional disciplinary narrative."
        assert revision.source_ai_job_id == job_id


def test_adapter_generation_errors_never_persist_placeholder_or_success(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    engine = FictionalLifecycleEngine(generation_errors=["first_person"])

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 503
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "queued"
        assert job.result_reference == {}
        assert (
            verification.scalar(
                select(func.count())
                .select_from(ReportRevision)
                .where(
                    ReportRevision.report_id == fictional_report.id,
                    ReportRevision.reason == "ai_result",
                )
            )
            == 0
        )
        assert "Error generating" not in repr(
            verification.scalars(
                select(ReportRevision.snapshot).where(
                    ReportRevision.report_id == fictional_report.id,
                )
            ).all()
        )


def test_unknown_worker_failure_stays_retryable_and_releases_claim(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )
    engine = FakeReportEngine(failure=RuntimeError("fictional unclassified failure"))

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 503
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.stage, job.error_code) == ("queued", "queued", None)
        assert job.claim_token is job.lease_expires_at is None


def test_pydantic_content_failure_is_durable_terminal_validation_result(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory,
        user_actor,
        fictional_incident.id,
        fictional_report.id,
    )

    response = _post(_worker(db_session_factory, InvalidContentEngine()), job_id)

    assert response.status_code == 204
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == ("failed", "job_output_invalid")
