"""AI job submission and status routes (RP-06).

Submission always authorizes actor+incident+base revision, claims the ID-06
idempotency record, creates the queued job and its outbox row, and writes a
safe `ai.job_submitted` audit event in one transaction
(`backend.jobs.service.submit_job`). Nothing here calls the report engine,
Vertex AI, or Cloud Tasks -- RP-07 owns dispatch and result application.
"""
from datetime import UTC
from uuid import UUID

from flask import Blueprint, current_app, g, request
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.jobs import AiJob
from backend.reports.persistence import IncidentNotFound
from backend.reports.revisions import RevisionConflict
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
)
from backend.webapp.api_v1.responses import success


jobs_bp = Blueprint("jobs_api", __name__)
SUBMIT_FIELDS = {"base_revision_number"}


def _timestamp(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _body() -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) != SUBMIT_FIELDS:
        raise ApiError("validation_failed", "The job request is invalid.", status=400)
    base = value["base_revision_number"]
    if not isinstance(base, int) or isinstance(base, bool) or base < 0:
        raise ApiError("validation_failed", "The job request is invalid.", status=400)
    return value


def _metadata() -> tuple[str, str]:
    return request_id(), str(g.client_version)


def _job_data(job: AiJob) -> dict[str, object]:
    return {
        "id": str(job.id),
        "incident_id": str(job.incident_id),
        "job_type": job.job_type,
        "state": job.state,
        "stage": job.stage,
        "created_at": _timestamp(job.created_at),
        "started_at": _timestamp(job.started_at),
        "completed_at": _timestamp(job.completed_at),
    }


def _submit(incident_id: UUID, job_type: str):
    # Imported lazily: `backend.jobs.service` (via `reports.persistence`/
    # `reports.revisions`) sits on this package's own existing circular
    # import chain, so importing it at module scope here would fail whenever
    # `backend.jobs.service` is the first module to touch that chain -- as a
    # standalone unit test does. See `backend/jobs/service.py` for the
    # matching note.
    from backend.jobs.service import SubmitJobCommand, submit_job

    payload = _body()
    req_id, version = _metadata()
    db = current_request_session()
    try:
        job = submit_job(
            db, current_actor(), SubmitJobCommand(incident_id=incident_id, job_type=job_type),
            request.headers.get("Idempotency-Key", ""), payload["base_revision_number"],
            request_id=req_id, client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        )
        db.commit()
        return success(_job_data(job), status=202)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict", "The incident changed; reload before submitting.", status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except IncidentNotFound:
        db.rollback()
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (ValueError, TypeError):
        db.rollback()
        raise ApiError("validation_failed", "The job request is invalid.", status=400) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict", "The incident changed; reload before submitting.", status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "revision_conflict", "The incident changed; reload before submitting.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable", "Job submission is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable", "Job submission is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@jobs_bp.post("/incidents/<uuid:incident_id>/jobs/classify", endpoint="submit_classify")
@require_access_token
@require_compatible_write
def submit_classify_route(incident_id: UUID):
    return _submit(incident_id, "classify")


@jobs_bp.post("/incidents/<uuid:incident_id>/jobs/extract", endpoint="submit_extract")
@require_access_token
@require_compatible_write
def submit_extract_route(incident_id: UUID):
    return _submit(incident_id, "extract")


@jobs_bp.post("/incidents/<uuid:incident_id>/jobs/generate", endpoint="submit_generate")
@require_access_token
@require_compatible_write
def submit_generate_route(incident_id: UUID):
    return _submit(incident_id, "generate")


@jobs_bp.post("/incidents/<uuid:incident_id>/jobs/disciplinary", endpoint="submit_disciplinary")
@require_access_token
@require_compatible_write
def submit_disciplinary_route(incident_id: UUID):
    return _submit(incident_id, "disciplinary")


@jobs_bp.get("/jobs/<uuid:job_id>", endpoint="get")
@require_access_token
def get_route(job_id: UUID):
    # Imported lazily; see the matching note in `_submit` above.
    from backend.jobs.service import JobNotFound, get_job

    try:
        job = get_job(current_request_session(), current_actor(), job_id)
        return success(_job_data(job))
    except JobNotFound:
        raise ApiError("not_found", "Job not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Job status is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
