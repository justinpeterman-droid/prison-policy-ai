"""Cloud Tasks dispatch contract tests; no credentials or network are used."""

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from uuid import UUID

from google.api_core.exceptions import (
    AlreadyExists,
    InvalidArgument,
    ServiceUnavailable,
)

from backend.jobs.dispatcher import DispatchSettings, dispatch_pending


JOB_ID = UUID("00000000-0000-4000-8000-000000000071")
OUTBOX_ID = UUID("00000000-0000-4000-8000-000000000072")
NOW = datetime(2026, 8, 12, 18, 0, tzinfo=UTC)


@dataclass
class FakeOutbox:
    id: UUID = OUTBOX_ID
    ai_job_id: UUID = JOB_ID


class FakeOutboxRepository:
    def __init__(self, rows=None):
        self.rows = list(rows if rows is not None else [FakeOutbox()])
        self.dispatched = []
        self.failures = []

    def pending(self, *, limit, now):
        assert limit == 10
        assert now == NOW
        return self.rows

    def mark_dispatched(self, row_id, *, now):
        self.dispatched.append((row_id, now))

    def mark_failure(self, row_id, *, code, retryable, now):
        self.failures.append((row_id, code, retryable, now))


class FakeTasksClient:
    def __init__(self, failures=()):
        self.failures = list(failures)
        self.created = []

    def create_task(self, request):
        self.created.append(request)
        if self.failures:
            raise self.failures.pop(0)
        return request["task"]


def _settings():
    return DispatchSettings(
        project="fictional-project",
        location="us-central1",
        queue="fictional-report-jobs",
        worker_url="https://worker.example.invalid",
        oidc_service_account="task-invoker@example.invalid",
    )


def test_dispatcher_uses_exact_oidc_body_url_and_stable_task_name():
    client = FakeTasksClient()
    repository = FakeOutboxRepository()

    summary = dispatch_pending(
        limit=10,
        client=client,
        repository=repository,
        settings=_settings(),
        now=NOW,
        sleep=lambda _delay: None,
    )

    assert summary.dispatched == 1
    assert summary.failed == 0
    assert summary.pending == 0
    request = client.created[0]
    assert request["parent"] == (
        "projects/fictional-project/locations/us-central1/queues/fictional-report-jobs"
    )
    task = request["task"]
    assert task["name"] == f"{request['parent']}/tasks/ai-job-{JOB_ID}"
    http_request = task["http_request"]
    assert http_request["http_method"] == 1
    assert http_request["url"] == (
        f"https://worker.example.invalid/internal/jobs/{JOB_ID}/run"
    )
    assert json.loads(http_request["body"]) == {"job_id": str(JOB_ID)}
    assert http_request["headers"] == {"Content-Type": "application/json"}
    assert http_request["oidc_token"]["service_account_email"] == (
        "task-invoker@example.invalid"
    )
    assert http_request["oidc_token"]["audience"] == "https://worker.example.invalid"
    assert repository.dispatched == [(OUTBOX_ID, NOW)]
    assert repository.failures == []


def test_already_exists_is_idempotent_dispatch_success():
    client = FakeTasksClient([AlreadyExists("fictional duplicate")])
    repository = FakeOutboxRepository()

    summary = dispatch_pending(
        limit=10,
        client=client,
        repository=repository,
        settings=_settings(),
        now=NOW,
        sleep=lambda _delay: None,
    )

    assert summary.dispatched == 1
    assert summary.failed == summary.pending == 0
    assert repository.dispatched == [(OUTBOX_ID, NOW)]


def test_transient_task_failure_retries_then_records_only_bounded_code():
    client = FakeTasksClient(
        [
            ServiceUnavailable("provider body must not persist"),
            ServiceUnavailable("provider body must not persist"),
            ServiceUnavailable("provider body must not persist"),
        ]
    )
    repository = FakeOutboxRepository()

    summary = dispatch_pending(
        limit=10,
        client=client,
        repository=repository,
        settings=_settings(),
        now=NOW,
        sleep=lambda _delay: None,
    )

    assert len(client.created) == 3
    assert summary.dispatched == summary.failed == 0
    assert summary.pending == 1
    assert repository.failures == [
        (OUTBOX_ID, "task_service_unavailable", True, NOW),
    ]
    assert "provider" not in repr(repository.failures)


def test_permanent_task_failure_is_not_retried_and_is_bounded():
    client = FakeTasksClient([InvalidArgument("sensitive upstream body")])
    repository = FakeOutboxRepository()

    summary = dispatch_pending(
        limit=10,
        client=client,
        repository=repository,
        settings=_settings(),
        now=NOW,
        sleep=lambda _delay: None,
    )

    assert len(client.created) == 1
    assert summary.dispatched == summary.pending == 0
    assert summary.failed == 1
    assert repository.failures == [
        (OUTBOX_ID, "task_request_rejected", False, NOW),
    ]
