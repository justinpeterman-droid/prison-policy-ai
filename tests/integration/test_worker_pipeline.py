"""PostgreSQL worker lifecycle tests with a fake report engine."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from alembic import command as alembic_command
from alembic.config import Config
import pytest
from sqlalchemy import func, select

from backend.jobs.service import SubmitJobCommand, claim_job, submit_job
from backend.persistence.models import AuditEvent
from backend.persistence.models.jobs import AiJob
from backend.persistence.models.reporting import ReportAccess, ReportRevision
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


class InvalidContentEngine(FakeReportEngine):
    def run(self, session, job):
        self.calls.append((job.id, job.job_type, job.stage, job.claim_token))
        ReportContentV1(narrative="x" * 50_001)


class FakeMetricSink:
    def __init__(self):
        self.events = []

    def increment(self, name, *, labels):
        self.events.append((name, labels))


def _queue_job(db_session_factory, actor, incident_id, report_id):
    with db_session_factory.begin() as session:
        job = submit_job(
            session, actor,
            SubmitJobCommand(
                incident_id=incident_id, job_type="generate", report_id=report_id,
            ),
            "job-fictional-worker-0001", 1, now=NOW,
            request_id="request_fictional_worker_submit",
            client_version="1.0.0",
        )
        return job.id


def _queue_reportless_job(db_session_factory, actor, incident_id):
    with db_session_factory.begin() as session:
        job = submit_job(
            session, actor,
            SubmitJobCommand(incident_id=incident_id, job_type="generate"),
            "job-fictional-worker-reportless", 1, now=NOW,
            request_id="request_fictional_worker_reportless",
            client_version="1.0.0",
        )
        return job.id


def _headers(job_id, retry_count="0"):
    return {
        "X-CloudTasks-TaskName": (
            "projects/fictional-project/locations/us-central1/queues/"
            f"fictional-report-jobs/tasks/ai-job-{job_id}"
        ),
        "X-CloudTasks-QueueName": "fictional-report-jobs",
        "X-CloudTasks-TaskRetryCount": retry_count,
    }


def _post(client, job_id, retry_count="0"):
    return client.post(
        f"/internal/jobs/{job_id}/run",
        headers=_headers(job_id, retry_count), json={"job_id": str(job_id)},
    )


def _worker(db_session_factory, engine, metrics=None):
    app = create_worker_app(
        session_factory=db_session_factory, report_engine=engine,
        metric_sink=metrics, now=lambda: NOW,
    )
    app.config["TESTING"] = True
    return app.test_client()


def test_worker_claims_runs_and_commits_one_fenced_revision_and_result(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    engine = FakeReportEngine()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
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
            "succeeded", "completed", 1, None,
        )
        assert job.claim_token is job.lease_expires_at is None
        assert job.result_reference == {
            "reports": [{"report_id": str(fictional_report.id), "revision_number": 2}],
        }
        revision = verification.scalar(select(ReportRevision).where(
            ReportRevision.report_id == fictional_report.id,
            ReportRevision.revision_number == 2,
        ))
        assert revision.reason == "ai_result"
        assert revision.source_ai_job_id == job_id
        assert revision.snapshot["narrative"] == "Fictional generated report narrative."


def test_redelivery_does_not_call_engine_or_apply_a_second_result(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    engine = FakeReportEngine()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )
    client = _worker(db_session_factory, engine)

    first = _post(client, job_id)
    redelivery = _post(client, job_id, "1")

    assert first.status_code == redelivery.status_code == 204
    assert len(engine.calls) == 1
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == fictional_report.id,
        )) == 2


def test_expired_lease_recovery_emits_repeat_risk_without_identity_or_content(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )
    with db_session_factory.begin() as abandoned:
        claimed = claim_job(abandoned, job_id, now=NOW - timedelta(minutes=21))
        assert claimed is not None
    engine = FakeReportEngine()
    metrics = FakeMetricSink()

    response = _post(_worker(db_session_factory, engine, metrics), job_id, "1")

    assert response.status_code == 204
    # RP-06 exposes no durable provider-started/possible-acceptance marker, so
    # RP-07 must not infer this metric from attempts or an expired lease.
    assert metrics.events == []
    rendered = repr(metrics.events)
    assert str(user_actor.account_id) not in rendered
    assert fictional_incident.field_notes not in rendered


def test_deterministic_failure_is_terminal_audited_and_not_retried(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    engine = FakeReportEngine(failure=TerminalJobFailure("job_output_invalid"))
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )
    client = _worker(db_session_factory, engine)

    first = _post(client, job_id)
    redelivery = _post(client, job_id, "1")

    assert first.status_code == redelivery.status_code == 204
    assert len(engine.calls) == 1
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.stage, job.error_code) == (
            "failed", "failed", "job_output_invalid",
        )
        audit = verification.scalar(select(AuditEvent).where(
            AuditEvent.action == "ai.job_failed", AuditEvent.target_id == job_id,
        ))
        assert audit.details == {
            "job_id": str(job_id), "job_type": "generate",
            "result_code": "job_output_invalid",
        }


def test_revoked_live_report_access_fails_before_fake_engine_call(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )
    with db_session_factory.begin() as revoke:
        access = revoke.scalar(select(ReportAccess).where(
            ReportAccess.report_id == fictional_report.id,
            ReportAccess.staff_member_id == user_actor.staff_member_id,
        ))
        access.revoked_at = NOW
    engine = FakeReportEngine()

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    assert engine.calls == []
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == (
            "failed", "job_authorization_invalid",
        )


def test_transient_engine_failure_releases_claim_and_retry_commits_once(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
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
    assert metrics.events == []
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.attempts) == ("succeeded", 2)
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == fictional_report.id,
        )) == 2


def test_reportless_generation_fails_closed_before_provider_or_revision(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_reportless_job(
        db_session_factory, user_actor, fictional_incident.id,
    )
    engine = FakeReportEngine()

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 204
    assert engine.calls == []
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == ("failed", "job_target_invalid")
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == fictional_report.id,
        )) == 1


def test_provider_result_is_rejected_when_claim_expires_during_call(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )
    clock_values = iter((NOW, NOW, NOW, NOW + timedelta(minutes=21)))
    app = create_worker_app(
        session_factory=db_session_factory, report_engine=FakeReportEngine(),
        metric_sink=FakeMetricSink(), now=lambda: next(clock_values),
    )
    app.config["TESTING"] = True

    response = _post(app.test_client(), job_id)

    assert response.status_code == 503
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.attempts) == ("running", 1)
        assert job.result_reference == {}
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == fictional_report.id,
        )) == 1


def test_incident_change_during_provider_call_commits_conflict_without_report_result(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
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
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == fictional_report.id,
        )) == 1


def test_unknown_worker_failure_stays_retryable_and_releases_claim(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )
    engine = FakeReportEngine(failure=RuntimeError("fictional unclassified failure"))

    response = _post(_worker(db_session_factory, engine), job_id)

    assert response.status_code == 503
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.stage, job.error_code) == ("queued", "queued", None)
        assert job.claim_token is job.lease_expires_at is None


def test_pydantic_content_failure_is_durable_terminal_validation_result(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    job_id = _queue_job(
        db_session_factory, user_actor, fictional_incident.id, fictional_report.id,
    )

    response = _post(_worker(db_session_factory, InvalidContentEngine()), job_id)

    assert response.status_code == 204
    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert (job.state, job.error_code) == ("failed", "job_output_invalid")
