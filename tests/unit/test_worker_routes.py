"""Private worker HTTP defense-in-depth contract tests."""

from uuid import UUID

from backend.worker.app import create_worker_app
from backend.worker.routes import TerminalJobFailure, TransientJobFailure


JOB_ID = UUID("00000000-0000-4000-8000-000000000071")


class FakeProcessor:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []

    def run(self, job_id, *, retry_count):
        self.calls.append((job_id, retry_count))
        if self.failure is not None:
            raise self.failure


def _client(processor):
    app = create_worker_app(
        processor=processor,
        queue_name="fictional-report-jobs",
    )
    app.config["TESTING"] = True
    return app.test_client()


def _headers(job_id=JOB_ID, *, retry_count="0"):
    return {
        "X-CloudTasks-TaskName": f"ai-job-{job_id}",
        "X-CloudTasks-QueueName": "fictional-report-jobs",
        "X-CloudTasks-TaskRetryCount": retry_count,
    }


def test_worker_rejects_request_without_cloud_tasks_metadata():
    processor = FakeProcessor()
    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 401
    assert response.json == {"error": "cloud_tasks_metadata_required"}
    assert processor.calls == []


def test_worker_requires_closed_json_and_exact_route_body_uuid_match():
    processor = FakeProcessor()
    client = _client(processor)

    mismatch = client.post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=_headers(),
        json={"job_id": "00000000-0000-4000-8000-000000000099"},
    )
    extra = client.post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=_headers(),
        json={"job_id": str(JOB_ID), "unexpected": True},
    )

    assert mismatch.status_code == extra.status_code == 400
    assert mismatch.json == extra.json == {"error": "task_request_invalid"}
    assert processor.calls == []


def test_worker_requires_task_name_to_bind_same_job_uuid():
    processor = FakeProcessor()
    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=_headers(UUID("00000000-0000-4000-8000-000000000099")),
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 400
    assert response.json == {"error": "task_request_invalid"}
    assert processor.calls == []


def test_worker_requires_queue_metadata_to_match_configured_queue():
    processor = FakeProcessor()
    headers = _headers()
    headers["X-CloudTasks-QueueName"] = "different-fictional-queue"

    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=headers,
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 400
    assert response.json == {"error": "task_request_invalid"}
    assert processor.calls == []


def test_worker_rejects_full_task_resource_in_delivery_header():
    processor = FakeProcessor()
    headers = _headers()
    headers["X-CloudTasks-TaskName"] = (
        f"projects/fictional-project/locations/us-central1/queues/fictional-report-jobs/tasks/ai-job-{JOB_ID}"
    )

    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=headers,
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 400
    assert response.json == {"error": "task_request_invalid"}
    assert processor.calls == []


def test_worker_runs_valid_delivery_and_parses_bounded_retry_count():
    processor = FakeProcessor()
    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=_headers(retry_count="2"),
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 204
    assert response.data == b""
    assert processor.calls == [(JOB_ID, 2)]


def test_terminal_failure_returns_2xx_to_stop_cloud_tasks_retry():
    processor = FakeProcessor(TerminalJobFailure("job_output_invalid"))
    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=_headers(),
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 204
    assert response.data == b""


def test_transient_failure_returns_503_without_exposing_exception():
    processor = FakeProcessor(
        TransientJobFailure("private provider response must not escape"),
    )
    response = _client(processor).post(
        f"/internal/jobs/{JOB_ID}/run",
        headers=_headers(),
        json={"job_id": str(JOB_ID)},
    )

    assert response.status_code == 503
    assert response.json == {"error": "worker_temporarily_unavailable"}
    assert b"provider" not in response.data
