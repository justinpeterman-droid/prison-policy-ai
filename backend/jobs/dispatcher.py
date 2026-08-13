"""After-commit Cloud Tasks dispatcher for durable AI job outbox rows.

Only UUID control metadata crosses this boundary.  Submission transactions add
an outbox row; this independent dispatcher reads committed rows and creates a
deterministically named OIDC-authenticated task.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
import re
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

from google.api_core.exceptions import AlreadyExists
from sqlalchemy import select

from backend.persistence.database import session_scope
from backend.persistence.models.jobs import TaskOutbox
from backend.pipeline.retry import is_transient, with_retries


_RESOURCE_PART = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")


@dataclass(frozen=True)
class DispatchSettings:
    project: str
    location: str
    queue: str
    worker_url: str
    oidc_service_account: str

    def __post_init__(self) -> None:
        for value in (self.project, self.location, self.queue):
            if not _RESOURCE_PART.fullmatch(value):
                raise ValueError("Cloud Tasks resource configuration is invalid")
        parsed = urlsplit(self.worker_url)
        if (
            parsed.scheme != "https" or not parsed.netloc or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("AI_WORKER_URL must be an HTTPS origin")
        if "@" not in self.oidc_service_account or len(self.oidc_service_account) > 254:
            raise ValueError("Cloud Tasks OIDC service account is invalid")

    @classmethod
    def from_env(cls, environ=None) -> "DispatchSettings":
        source = os.environ if environ is None else environ
        required = {
            "project": "CLOUD_TASKS_PROJECT",
            "location": "CLOUD_TASKS_LOCATION",
            "queue": "CLOUD_TASKS_QUEUE",
            "worker_url": "AI_WORKER_URL",
            "oidc_service_account": "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT",
        }
        values = {field: str(source.get(name, "")).strip() for field, name in required.items()}
        if any(not value for value in values.values()):
            raise RuntimeError("Cloud Tasks dispatcher configuration is incomplete")
        return cls(**values)

    @property
    def parent(self) -> str:
        return (
            f"projects/{self.project}/locations/{self.location}/queues/{self.queue}"
        )

    @property
    def audience(self) -> str:
        parsed = urlsplit(self.worker_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@dataclass(frozen=True)
class DispatchSummary:
    dispatched: int = 0
    failed: int = 0
    pending: int = 0


@dataclass(frozen=True)
class PendingDispatch:
    id: UUID
    ai_job_id: UUID


class OutboxRepository(Protocol):
    def pending(self, *, limit: int, now: datetime) -> list[PendingDispatch]: ...
    def mark_dispatched(self, row_id: UUID, *, now: datetime) -> None: ...
    def mark_failure(
        self, row_id: UUID, *, code: str, retryable: bool, now: datetime,
    ) -> None: ...


class SqlOutboxRepository:
    """Short database transactions around already-committed outbox rows."""

    def __init__(self, session_factory=session_scope):
        self._session_factory = session_factory

    def _scope(self):
        begin = getattr(self._session_factory, "begin", None)
        return begin() if callable(begin) else self._session_factory()

    def pending(self, *, limit: int, now: datetime) -> list[PendingDispatch]:
        with self._scope() as session:
            rows = session.scalars(
                select(TaskOutbox)
                .where(
                    TaskOutbox.state == "pending",
                    TaskOutbox.available_at <= now,
                )
                .order_by(TaskOutbox.available_at, TaskOutbox.id)
                .limit(limit)
            ).all()
            return [PendingDispatch(row.id, row.ai_job_id) for row in rows]

    def mark_dispatched(self, row_id: UUID, *, now: datetime) -> None:
        with self._scope() as session:
            row = session.scalar(
                select(TaskOutbox).where(TaskOutbox.id == row_id).with_for_update()
            )
            if row is None or row.state != "pending":
                return
            row.state = "dispatched"
            row.attempts += 1
            row.dispatched_at = now
            row.last_error_code = None

    def mark_failure(
        self, row_id: UUID, *, code: str, retryable: bool, now: datetime,
    ) -> None:
        with self._scope() as session:
            row = session.scalar(
                select(TaskOutbox).where(TaskOutbox.id == row_id).with_for_update()
            )
            if row is None or row.state != "pending":
                return
            row.attempts += 1
            row.last_error_code = code
            if retryable:
                delay = min(300, 2 ** min(row.attempts, 8))
                row.available_at = now + timedelta(seconds=delay)
            else:
                row.state = "failed"


def _task(settings: DispatchSettings, job_id: UUID) -> dict[str, object]:
    body = json.dumps(
        {"job_id": str(job_id)}, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    return {
        "name": f"{settings.parent}/tasks/ai-job-{job_id}",
        "http_request": {
            # google.cloud.tasks_v2.HttpMethod.POST == 1.  Keeping the request
            # as the documented protobuf mapping means fake-only tests do not
            # need the optional Google client installed or initialized.
            "http_method": 1,
            "url": (
                f"{settings.worker_url.rstrip('/')}/internal/jobs/{job_id}/run"
            ),
            "headers": {"Content-Type": "application/json"},
            "body": body,
            "oidc_token": {
                "service_account_email": settings.oidc_service_account,
                "audience": settings.audience,
            },
        },
    }


def _default_client():
    try:
        from google.cloud import tasks_v2
    except ImportError as error:  # pragma: no cover - deployment installs requirements
        raise RuntimeError("google-cloud-tasks is not installed") from error
    return tasks_v2.CloudTasksClient()


def _error_code(error: BaseException) -> tuple[str, bool]:
    if is_transient(error):
        return "task_service_unavailable", True
    return "task_request_rejected", False


def dispatch_pending(
    limit: int = 100, *, client=None, repository: OutboxRepository | None = None,
    settings: DispatchSettings | None = None, now: datetime | None = None,
    sleep=None,
) -> DispatchSummary:
    """Send available committed intents and persist only bounded outcomes."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    fixed = now or datetime.now(UTC)
    config = settings or DispatchSettings.from_env()
    tasks_client = client or _default_client()
    outbox = repository or SqlOutboxRepository()
    dispatched = failed = pending = 0

    for row in outbox.pending(limit=limit, now=fixed):
        request = {"parent": config.parent, "task": _task(config, row.ai_job_id)}
        try:
            retry_options = {
                "attempts": 3,
                "base_delay": 0.25,
                "describe": "Cloud Tasks create",
            }
            if sleep is not None:
                retry_options["sleep"] = sleep
            with_retries(
                lambda: tasks_client.create_task(request=request), **retry_options,
            )
        except AlreadyExists:
            outbox.mark_dispatched(row.id, now=fixed)
            dispatched += 1
        except Exception as error:
            code, retryable = _error_code(error)
            outbox.mark_failure(
                row.id, code=code, retryable=retryable, now=fixed,
            )
            if retryable:
                pending += 1
            else:
                failed += 1
        else:
            outbox.mark_dispatched(row.id, now=fixed)
            dispatched += 1
    return DispatchSummary(dispatched=dispatched, failed=failed, pending=pending)


__all__ = ["DispatchSettings", "DispatchSummary", "dispatch_pending"]
