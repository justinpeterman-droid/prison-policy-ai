"""PostgreSQL/API contracts for durable idempotent AI-job submission."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from queue import Queue
import time
from uuid import UUID

from alembic import command as alembic_command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
import yaml

from backend.identity.audit import AuditEventInput
from backend.persistence.models import AuditEvent, IdempotencyRecord, ReportAccess
from backend.persistence.models.jobs import AiJob, Export, TaskOutbox
from backend.jobs.service import SubmitJobCommand, submit_job


ROOT = Path(__file__).resolve().parents[2]
JOB_TYPES = ("classify", "extract", "generate", "disciplinary")


@pytest.fixture(autouse=True)
def _fictional_job_api_clock(monkeypatch, identity_fixed_now):
    import backend.webapp.api_v1.middleware as middleware

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)


def _headers(base: dict[str, str], key: str) -> dict[str, str]:
    return base | {
        "Idempotency-Key": key,
        "X-Request-ID": f"request_{key}",
    }


def _read_headers(base: dict[str, str], label: str) -> dict[str, str]:
    return base | {"X-Request-ID": f"request_{label}"}


def _post(client, incident_id, job_type, headers, revision=1, **extra):
    return client.post(
        f"/api/v1/incidents/{incident_id}/jobs/{job_type}",
        headers=headers,
        json={"base_revision_number": revision, **extra},
    )


def test_same_key_returns_same_job_and_one_atomic_outbox_and_audit(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    fictional_incident, fictional_report, fictional_staff_and_accounts,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "job-fictional-0001")

    first = _post(api_client, fictional_incident.id, "classify", headers)
    replay = _post(api_client, fictional_incident.id, "classify", headers)

    assert first.status_code == replay.status_code == 202
    assert replay.json["data"]["id"] == first.json["data"]["id"]
    assert first.json["data"] == {
        "id": first.json["data"]["id"],
        "incident_id": str(fictional_incident.id),
        "job_type": "classify",
        "state": "queued",
        "stage": "queued",
        "created_at": first.json["data"]["created_at"],
        "started_at": None,
        "completed_at": None,
        "error_code": None,
        "result_reference": {},
    }
    with db_session_factory() as verification:
        job_id = UUID(first.json["data"]["id"])
        job = verification.get(AiJob, job_id)
        assert job is not None
        assert job.request_metadata == {"base_revision_number": 1}
        assert job.result_reference == {}
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 1
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 1
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == fictional_staff_and_accounts.user.id,
            IdempotencyRecord.action == "ai.job.submit",
            IdempotencyRecord.status == "completed",
        )) == 1
        record = verification.scalar(select(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == fictional_staff_and_accounts.user.id,
            IdempotencyRecord.action == "ai.job.submit",
        ))
        assert record.response_status == 202
        assert record.response_reference == {"job_id": str(job_id)}
        audit = verification.scalar(select(AuditEvent).where(
            AuditEvent.action == "ai.job_submitted", AuditEvent.target_id == job_id,
        ))
        assert audit.details == {
            "job_id": str(job_id),
            "job_type": "classify",
            "incident_id": str(fictional_incident.id),
        }


def test_same_key_changed_payload_or_job_type_conflicts_without_second_job(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    fictional_incident, fictional_report,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "job-fictional-0002")
    first = _post(api_client, fictional_incident.id, "extract", headers)
    changed_revision = _post(api_client, fictional_incident.id, "extract", headers, revision=2)
    changed_type = _post(api_client, fictional_incident.id, "generate", headers)

    assert first.status_code == 202
    assert changed_revision.status_code == changed_type.status_code == 409
    assert changed_revision.json["error"]["code"] == "idempotency_conflict"
    assert changed_type.json["error"]["code"] == "idempotency_conflict"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 1
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 1


def test_expired_shared_idempotency_key_creates_a_distinct_job_and_outbox(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    incident_id = fictional_incident.id
    account_id = user_actor.account_id
    first_now = datetime(2026, 8, 12, 15, 5, tzinfo=UTC)
    db_session.commit()

    with db_session_factory.begin() as first_session:
        first = submit_job(
            first_session,
            user_actor,
            SubmitJobCommand(incident_id, "classify"),
            "job-fictional-expired-key",
            1,
            now=first_now,
            request_id="request_job_fictional_expired_first",
            client_version="1.0.0",
        )
        first_id = first.id

    with db_session_factory.begin() as expire_session:
        record = expire_session.scalar(select(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == account_id,
            IdempotencyRecord.action == "ai.job.submit",
            IdempotencyRecord.idempotency_key == "job-fictional-expired-key",
        ))
        record.expires_at = first_now + timedelta(hours=24)

    try:
        with db_session_factory.begin() as reuse_session:
            second = submit_job(
                reuse_session,
                user_actor,
                SubmitJobCommand(incident_id, "extract"),
                "job-fictional-expired-key",
                1,
                now=first_now + timedelta(hours=24, seconds=1),
                request_id="request_job_fictional_expired_second",
                client_version="1.0.0",
            )
            second_id = second.id
    except IntegrityError:
        pytest.fail(
            "an expired ID-06 key was permanently blocked by AI-job uniqueness",
            pytrace=False,
        )

    assert second_id != first_id
    with db_session_factory() as verification:
        jobs = verification.scalars(select(AiJob).order_by(AiJob.created_at)).all()
        assert [job.id for job in jobs] == [first_id, second_id]
        assert [job.job_type for job in jobs] == ["classify", "extract"]
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 2
        record = verification.scalar(select(IdempotencyRecord).where(
            IdempotencyRecord.actor_account_id == account_id,
            IdempotencyRecord.action == "ai.job.submit",
            IdempotencyRecord.idempotency_key == "job-fictional-expired-key",
        ))
        assert record.response_reference == {"job_id": str(second_id)}


@pytest.mark.parametrize("job_type", JOB_TYPES)
def test_all_job_submission_routes_are_closed_and_start_queued(
    db_session, api_client, owner_bearer_headers, fictional_incident,
    fictional_report, job_type,
):
    db_session.commit()
    response = _post(
        api_client, fictional_incident.id, job_type,
        _headers(owner_bearer_headers, f"job-fictional-route-{job_type}"),
    )
    extra = _post(
        api_client, fictional_incident.id, job_type,
        _headers(owner_bearer_headers, f"job-fictional-extra-{job_type}"),
        unexpected="not accepted",
    )

    assert response.status_code == 202
    assert response.json["data"]["job_type"] == job_type
    assert response.json["data"]["state"] == "queued"
    assert response.json["data"]["stage"] == "queued"
    assert extra.status_code == 400
    assert extra.json["error"]["code"] == "validation_failed"


def test_authorization_and_stale_base_fail_without_durable_fragments(
    db_session, db_session_factory, api_client, unrelated_bearer_headers,
    owner_bearer_headers, fictional_incident, fictional_report,
):
    db_session.commit()
    denied = _post(
        api_client, fictional_incident.id, "classify",
        _headers(unrelated_bearer_headers, "job-fictional-denied"),
    )
    stale = _post(
        api_client, fictional_incident.id, "classify",
        _headers(owner_bearer_headers, "job-fictional-stale"), revision=2,
    )

    assert denied.status_code == 404
    assert denied.json["error"]["code"] == "not_found"
    assert stale.status_code == 409
    assert stale.json["error"]["code"] == "revision_conflict"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 0
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "ai.job.submit")) == 0
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "ai.job_submitted")) == 0


def test_unrelated_admin_cannot_submit_an_ordinary_incident_job(
    db_session, db_session_factory, api_client, admin_bearer_headers,
    fictional_incident, fictional_report,
):
    db_session.commit()
    with db_session_factory() as before:
        counts_before = (
            before.scalar(select(func.count()).select_from(AiJob)),
            before.scalar(select(func.count()).select_from(TaskOutbox)),
            before.scalar(select(func.count()).select_from(IdempotencyRecord)),
            before.scalar(select(func.count()).select_from(AuditEvent)),
        )

    response = _post(
        api_client,
        fictional_incident.id,
        "classify",
        _headers(admin_bearer_headers, "job-fictional-unrelated-admin"),
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
    with db_session_factory() as verification:
        counts_after = (
            verification.scalar(select(func.count()).select_from(AiJob)),
            verification.scalar(select(func.count()).select_from(TaskOutbox)),
            verification.scalar(select(func.count()).select_from(IdempotencyRecord)),
            verification.scalar(select(func.count()).select_from(AuditEvent)),
        )
        assert counts_after == counts_before


def test_access_revoked_before_live_relationship_lock_leaves_no_job_fragment(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    fictional_incident, fictional_report, monkeypatch,
):
    import backend.webapp.api_v1.jobs as jobs_api

    report_id = fictional_report.id
    owner_staff_id = fictional_report.reporting_staff_member_id
    db_session.commit()
    holder = db_session_factory()
    relationship = holder.scalar(select(ReportAccess).where(
        ReportAccess.report_id == report_id,
        ReportAccess.staff_member_id == owner_staff_id,
    ).with_for_update())

    submission_pid = Queue()
    original = jobs_api.submit_job

    def observed_submit(session, *args, **kwargs):
        submission_pid.put(session.scalar(text("SELECT pg_backend_pid()")))
        return original(session, *args, **kwargs)

    monkeypatch.setattr(jobs_api, "submit_job", observed_submit)

    def submit():
        with api_client.application.test_client() as client:
            return _post(
                client,
                fictional_incident.id,
                "classify",
                _headers(owner_bearer_headers, "job-fictional-revoked-race"),
            )

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(submit)
            pid = submission_pid.get(timeout=5)
            with db_session_factory() as observer:
                for _ in range(200):
                    wait_type = observer.scalar(text(
                        "SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"
                    ), {"pid": pid})
                    observer.rollback()
                    if wait_type == "Lock":
                        break
                    if future.done():
                        raise AssertionError(
                            "submission did not lock and revalidate live incident access")
                    time.sleep(0.01)
                else:
                    raise AssertionError(
                        "submission did not wait for the live relationship lock")
            relationship.revoked_at = datetime(2026, 8, 12, 15, 2, tzinfo=UTC)
            holder.commit()
            response = future.result(timeout=10)
    finally:
        holder.rollback()
        holder.close()

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 0
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "ai.job.submit")) == 0
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "ai.job_submitted")) == 0


class _FailingAuditWriter:
    def append(self, _session, _event: AuditEventInput):
        raise RuntimeError("fictional audit failure")


def test_audit_failure_rolls_back_job_outbox_idempotency_and_audit_together(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    work = db_session_factory()
    try:
        with pytest.raises(RuntimeError, match="fictional audit failure"):
            submit_job(
                work,
                user_actor,
                SubmitJobCommand(fictional_incident.id, "generate"),
                "job-fictional-rollback",
                1,
                now=datetime(2026, 8, 12, 15, 5, tzinfo=UTC),
                request_id="request_job_fictional_rollback",
                client_version="1.0.0",
                audit_writer=_FailingAuditWriter(),
            )
        work.rollback()
    finally:
        work.close()

    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 0
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "ai.job.submit")) == 0
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "ai.job_submitted")) == 0


def test_job_status_requires_requester_plus_current_access_or_admin(
    db_session, db_session_factory, api_client, owner_bearer_headers,
    preparer_bearer_headers, unrelated_bearer_headers, admin_bearer_headers,
    fictional_incident, fictional_report,
):
    db_session.commit()
    submitted = _post(
        api_client, fictional_incident.id, "disciplinary",
        _headers(owner_bearer_headers, "job-fictional-read-auth"),
    )
    job_id = submitted.json["data"]["id"]

    requester = api_client.get(
        f"/api/v1/jobs/{job_id}", headers=_read_headers(owner_bearer_headers, "job_owner"))
    other_authorized_user = api_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=_read_headers(preparer_bearer_headers, "job_preparer"))
    unrelated = api_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=_read_headers(unrelated_bearer_headers, "job_unrelated"))
    admin = api_client.get(
        f"/api/v1/jobs/{job_id}", headers=_read_headers(admin_bearer_headers, "job_admin"))

    assert requester.status_code == admin.status_code == 200
    assert requester.json["data"]["id"] == admin.json["data"]["id"] == job_id
    assert other_authorized_user.status_code == unrelated.status_code == 404

    with db_session_factory.begin() as revoke:
        from backend.persistence.models import ReportAccess
        relationship = revoke.scalar(select(ReportAccess).where(
            ReportAccess.report_id == fictional_report.id,
            ReportAccess.staff_member_id == fictional_report.reporting_staff_member_id,
        ))
        relationship.revoked_at = datetime(2026, 8, 12, 15, 10, tzinfo=UTC)

    revoked_requester = api_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=_read_headers(owner_bearer_headers, "job_owner_revoked"))
    admin_after_revoke = api_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=_read_headers(admin_bearer_headers, "job_admin_after_revoke"))
    assert revoked_requester.status_code == 404
    assert admin_after_revoke.status_code == 200


def test_jobs_migration_has_bounded_tables_constraints_and_lookup_indexes(db_engine):
    inspector = inspect(db_engine)
    assert {"ai_jobs", "task_outbox", "exports"} <= set(inspector.get_table_names())
    unique_names = {
        item["name"] for table in ("ai_jobs", "task_outbox")
        for item in inspector.get_unique_constraints(table)
    }
    assert "uq_task_outbox_ai_job_id" in unique_names
    assert "uq_ai_jobs_actor_idempotency_key" not in unique_names
    indexes = {
        item["name"] for table in ("ai_jobs", "task_outbox", "exports")
        for item in inspector.get_indexes(table)
    }
    assert {
        "ix_ai_jobs_queue", "ix_ai_jobs_requested_actor", "ix_ai_jobs_incident",
        "ix_task_outbox_available", "ix_exports_report_revision",
        "ix_exports_actor_created", "ix_ai_jobs_claim",
    } <= indexes
    assert {"lease_expires_at", "claim_token"} <= {
        column["name"] for column in inspector.get_columns("ai_jobs")
    }
    report_revision_foreign_keys = {
        item["name"]: item for item in inspector.get_foreign_keys("report_revisions")
    }
    source_job_fk = report_revision_foreign_keys[
        "fk_report_revisions_source_ai_job_id_ai_jobs"
    ]
    assert source_job_fk["constrained_columns"] == ["source_ai_job_id"]
    assert source_job_fk["referred_table"] == "ai_jobs"
    assert source_job_fk["referred_columns"] == ["id"]


def test_jobs_migration_downgrades_and_reupgrades_with_reverse_fk(db_engine):
    config = Config(str(ROOT / "alembic.ini"))

    alembic_command.downgrade(config, "20260812_0004")
    downgraded = inspect(db_engine)
    assert {"ai_jobs", "task_outbox", "exports"}.isdisjoint(
        downgraded.get_table_names()
    )
    assert "fk_report_revisions_source_ai_job_id_ai_jobs" not in {
        item["name"] for item in downgraded.get_foreign_keys("report_revisions")
    }

    alembic_command.upgrade(config, "20260812_0005")
    upgraded = inspect(db_engine)
    assert {"ai_jobs", "task_outbox", "exports"} <= set(upgraded.get_table_names())
    assert "fk_report_revisions_source_ai_job_id_ai_jobs" in {
        item["name"] for item in upgraded.get_foreign_keys("report_revisions")
    }


def test_openapi_declares_closed_job_routes_headers_stages_and_safe_conflicts():
    document = yaml.safe_load((ROOT / "openapi" / "access-v1.yaml").read_text("utf-8"))
    expected_paths = {
        f"/api/v1/incidents/{{incident_id}}/jobs/{job_type}" for job_type in JOB_TYPES
    } | {"/api/v1/jobs/{job_id}"}
    assert expected_paths <= set(document["paths"])
    schemas = document["components"]["schemas"]
    assert schemas["SubmitJobRequest"]["additionalProperties"] is False
    assert schemas["SubmitJobRequest"]["required"] == ["base_revision_number"]
    assert schemas["Job"]["additionalProperties"] is False
    result_reference = schemas["JobResultReference"]
    assert result_reference["additionalProperties"] is False
    assert set(result_reference["properties"]) == {
        "incident_revision_number", "reports",
    }
    assert schemas["JobResultReportReference"]["additionalProperties"] is False
    assert schemas["JobResultReportReference"]["required"] == [
        "report_id", "revision_number",
    ]
    assert set(schemas["JobStage"]["enum"]) == {
        "queued", "classifying", "extracting", "validating", "generating",
        "disciplinary", "completed", "failed",
    }
    for job_type in JOB_TYPES:
        operation = document["paths"][f"/api/v1/incidents/{{incident_id}}/jobs/{job_type}"]["post"]
        refs = {parameter.get("$ref") for parameter in operation["parameters"]}
        assert {
            "#/components/parameters/IncidentId",
            "#/components/parameters/XClientVersion",
            "#/components/parameters/RequiredXRequestId",
            "#/components/parameters/IdempotencyKey",
        } <= refs
        assert {"202", "400", "401", "403", "404", "409", "422", "503"} <= set(operation["responses"])
        response_ref = operation["responses"]["409"]["$ref"].rsplit("/", 1)[-1]
        examples = document["components"]["responses"][response_ref]["content"]["application/json"]["examples"]
        codes = {item["value"]["error"]["code"] for item in examples.values()}
        assert {
            "revision_conflict", "idempotency_conflict", "request_in_progress",
            "client_upgrade_required",
        } <= codes
    assert document["security"] == [{"AccessBearer": []}]
