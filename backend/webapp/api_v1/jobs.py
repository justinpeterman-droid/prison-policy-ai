"""Authenticated public submission and status routes for durable AI jobs."""

from datetime import UTC
from uuid import UUID

from flask import Blueprint, current_app, g, request
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.jobs.service import (
    JobNotFound,
    SubmitJobCommand,
    get_job,
    submit_job,
)
from backend.persistence.database import DatabaseUnavailable
from backend.reports.persistence import IncidentNotFound
from backend.reports.revisions import RevisionConflict
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import REQUEST_ID_PATTERN, request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
)
from backend.webapp.api_v1.responses import success


jobs_bp = Blueprint("jobs_api", __name__)


def _timestamp(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _job_data(job) -> dict[str, object]:
    return {
        "id": str(job.id),
        "incident_id": str(job.incident_id),
        "job_type": job.job_type,
        "state": job.state,
        "stage": job.stage,
        "created_at": _timestamp(job.created_at),
        "started_at": _timestamp(job.started_at),
        "completed_at": _timestamp(job.completed_at),
        "error_code": job.error_code,
        "result_reference": dict(job.result_reference or {}),
    }


def _closed_submission_body() -> int:
    supplied_request_id = request.headers.get("X-Request-ID", "")
    if not REQUEST_ID_PATTERN.fullmatch(supplied_request_id):
        raise ApiError("validation_failed", "X-Request-ID is required.", status=400)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"base_revision_number"}:
        raise ApiError("validation_failed", "The job request is invalid.", status=400)
    value = payload["base_revision_number"]
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ApiError("validation_failed", "The job request is invalid.", status=400)
    return value


def _submit(incident_id: UUID, job_type: str):
    base_revision_number = _closed_submission_body()
    db = current_request_session()
    try:
        job = submit_job(
            db,
            current_actor(),
            SubmitJobCommand(incident_id=incident_id, job_type=job_type),
            request.headers.get("Idempotency-Key", ""),
            base_revision_number,
            request_id=request_id(),
            client_version=str(g.client_version),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )
        db.commit()
        return success(_job_data(job), status=202)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError(
            "request_in_progress", str(error), status=409, retryable=True,
        ) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The incident changed; reload before submitting the job.",
            status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except (IncidentNotFound, JobNotFound):
        db.rollback()
        raise ApiError("not_found", "Job target not found.", status=404) from None
    except ValueError:
        db.rollback()
        raise ApiError("validation_failed", "The job request is invalid.", status=400) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "idempotency_conflict", "The job submission conflicts with an existing request.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "request_in_progress", "The job submission is still in progress.",
                status=409, retryable=True,
            ) from None
        raise ApiError(
            "dependency_unavailable", "Job storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable", "Job storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@jobs_bp.post(
    "/incidents/<uuid:incident_id>/jobs/classify", endpoint="submit_classify",
)
@require_access_token
@require_compatible_write
def submit_classify(incident_id: UUID):
    return _submit(incident_id, "classify")


@jobs_bp.post(
    "/incidents/<uuid:incident_id>/jobs/extract", endpoint="submit_extract",
)
@require_access_token
@require_compatible_write
def submit_extract(incident_id: UUID):
    return _submit(incident_id, "extract")


@jobs_bp.post(
    "/incidents/<uuid:incident_id>/jobs/generate", endpoint="submit_generate",
)
@require_access_token
@require_compatible_write
def submit_generate(incident_id: UUID):
    return _submit(incident_id, "generate")


@jobs_bp.post(
    "/incidents/<uuid:incident_id>/jobs/disciplinary", endpoint="submit_disciplinary",
)
@require_access_token
@require_compatible_write
def submit_disciplinary(incident_id: UUID):
    return _submit(incident_id, "disciplinary")


@jobs_bp.get("/jobs/<uuid:job_id>", endpoint="status")
@require_access_token
def status(job_id: UUID):
    supplied_request_id = request.headers.get("X-Request-ID", "")
    if not REQUEST_ID_PATTERN.fullmatch(supplied_request_id):
        raise ApiError("validation_failed", "X-Request-ID is required.", status=400)
    try:
        return success(_job_data(get_job(
            current_request_session(), current_actor(), job_id,
        )))
    except JobNotFound:
        raise ApiError("not_found", "Job not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Job storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
