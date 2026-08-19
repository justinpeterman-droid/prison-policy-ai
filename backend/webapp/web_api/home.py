"""Cookie-authenticated Home dashboard summary route."""
from datetime import date, datetime

from flask import Blueprint, request
from sqlalchemy.exc import SQLAlchemyError

from backend.dashboard.home import get_officer_home_summary
from backend.persistence.database import DatabaseUnavailable
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_session,
)


home_bp = Blueprint("web_home", __name__)


def _validation_error() -> ApiError:
    return ApiError(
        "validation_failed",
        "The Home summary request is invalid.",
        status=400,
    )


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _incident(item) -> dict[str, object]:
    return {
        "incident_id": str(item.incident_id),
        "incident_number": item.incident_number,
        "incident_name": item.incident_name,
        "incident_date": item.incident_date.isoformat() if item.incident_date else None,
        "category": item.category,
        "location": item.location,
        "reporting_officers": [
            {
                "staff_id": str(officer.staff_id),
                "display_name": officer.display_name,
            }
            for officer in item.reporting_officers
        ],
        "relationship": item.relationship,
        "progress": {
            "code": item.progress.code,
            "label": item.progress.label,
            "blocking_count": item.progress.blocking_count,
        },
        "officer_report_count": item.officer_report_count,
        "required_paperwork_count": item.required_paperwork_count,
        "updated_at": _timestamp(item.updated_at),
    }


@home_bp.get("/home", endpoint="summary")
@require_browser_session
def summary_route():
    if set(request.args) != {"date", "shift"}:
        raise _validation_error()
    raw_date = request.args.get("date", "")
    shift = request.args.get("shift", "")
    try:
        record_date = date.fromisoformat(raw_date)
        if record_date.isoformat() != raw_date:
            raise ValueError
        summary = get_officer_home_summary(
            current_browser_session(),
            current_browser_actor(),
            record_date=record_date,
            shift=shift,
        )
    except (TypeError, ValueError):
        raise _validation_error() from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The Home summary is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None

    return success({
        "continue_incident": (
            _incident(summary.continue_incident)
            if summary.continue_incident is not None
            else None
        ),
        "recent_incidents": [
            _incident(item) for item in summary.recent_incidents
        ],
        "quick_forms": [
            {
                "template_id": str(item.template_id),
                "code": item.code,
                "name": item.name,
                "output_kind": item.output_kind,
            }
            for item in summary.quick_forms
        ],
        "count_sheet": (
            {
                "record_id": str(summary.count_sheet.record_id),
                "current_revision_number": (
                    summary.count_sheet.current_revision_number
                ),
                "updated_at": _timestamp(summary.count_sheet.updated_at),
            }
            if summary.count_sheet is not None
            else None
        ),
    })
