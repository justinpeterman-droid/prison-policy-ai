"""Durable classify, extract, generate, and disciplinary browser jobs."""
from uuid import UUID

from flask import Blueprint, current_app, g
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.jobs.service import JobNotFound, SubmitJobCommand, get_job, submit_job
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.jobs import (
    InvalidJobResultReference,
    normalize_job_result_reference,
)
from backend.reports.persistence import IncidentNotFound
from backend.reports.revisions import RevisionConflict
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.common import (
    LOCK_CONFLICT_STATES,
    json_body,
    request_metadata,
    require_idempotency_key,
    timestamp,
)
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


jobs_bp = Blueprint("web_jobs", __name__)
_JOB_TYPES = frozenset({"classify", "extract", "generate", "disciplinary"})


def _job_data(job) -> dict[str, object]:
    return {
        "job_id": str(job.id),
        "incident_id": str(job.incident_id),
        "job_type": job.job_type,
        "state": job.state,
        "stage": job.stage,
        "base_incident_revision": job.base_incident_revision,
        "created_at": timestamp(job.created_at),
        "started_at": timestamp(job.started_at),
        "completed_at": timestamp(job.completed_at),
        "error_code": job.error_code,
        "result_reference": normalize_job_result_reference(job.result_reference or {}),
    }


@jobs_bp.post("/incidents/<uuid:incident_id>/jobs/<job_type>")
@require_browser_session
@require_browser_csrf
def submit_browser_job(incident_id: UUID, job_type: str):
    if job_type not in _JOB_TYPES:
        raise ApiError("not_found", "Job target not found.", status=404)
    payload = json_body(
        exact={"base_revision_number"}, message="The job request is invalid."
    )
    base_revision = payload["base_revision_number"]
    if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 1:
        raise ApiError(
            "validation_failed", "The job request is invalid.", status=400
        )
    db = current_browser_session()
    try:
        req_id, version = request_metadata()
        job = submit_job(
            db,
            current_browser_actor(),
            SubmitJobCommand(incident_id=incident_id, job_type=job_type),
            require_idempotency_key(),
            base_revision,
            request_id=req_id,
            client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        )
        db.commit()
        return success(_job_data(job), status=202)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError(
            "request_in_progress", str(error), status=409, retryable=True
        ) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The incident changed; reload before starting this step.",
            status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except (IncidentNotFound, JobNotFound):
        db.rollback()
        raise ApiError("not_found", "Job target not found.", status=404) from None
    except (ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The job request is invalid.", status=400
        ) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "idempotency_conflict",
            "The job conflicts with an existing request.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in LOCK_CONFLICT_STATES:
            raise ApiError(
                "request_in_progress",
                "The job submission is still in progress.",
                status=409,
                retryable=True,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Job storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Job storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@jobs_bp.get("/jobs/<uuid:job_id>")
@require_browser_session
def browser_job_status(job_id: UUID):
    try:
        return success(_job_data(get_job(
            current_browser_session(), current_browser_actor(), job_id
        )))
    except JobNotFound:
        raise ApiError("not_found", "Job not found.", status=404) from None
    except (
        DatabaseUnavailable,
        InvalidJobResultReference,
        SQLAlchemyError,
        RuntimeError,
    ):
        raise ApiError(
            "dependency_unavailable",
            "Job storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
