"""Cookie-authenticated incident library routes for Guided Operations."""
from datetime import date, datetime

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.config import IdentitySettings
from backend.persistence.database import DatabaseUnavailable
from backend.reports.incident_library import (
    IncidentLibraryFilters,
    IncidentSummary,
    list_incident_summaries,
)
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_session,
)


incidents_bp = Blueprint("web_incidents", __name__)
_ALLOWED_QUERY_KEYS = {
    "q",
    "relationship",
    "category",
    "date_from",
    "date_to",
    "location",
    "limit",
    "cursor",
}
_RELATIONSHIPS = {"all", "reporting", "prepared"}


def _validation_error() -> ApiError:
    return ApiError(
        "validation_failed",
        "The incident library request is invalid.",
        status=400,
    )


def _single_query_value(name: str) -> str | None:
    values = request.args.getlist(name)
    if len(values) > 1:
        raise _validation_error()
    return values[0] if values else None


def _optional_text(name: str, *, maximum: int = 200) -> str | None:
    value = _single_query_value(name)
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if len(cleaned) > maximum:
        raise _validation_error()
    return cleaned


def _optional_date(name: str) -> date | None:
    value = _single_query_value(name)
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _validation_error() from None


def _limit() -> int:
    raw = _single_query_value("limit")
    if raw is None:
        return 25
    if not raw.isascii() or not raw.isdigit():
        raise _validation_error()
    value = int(raw)
    if not 1 <= value <= 50 or str(value) != raw:
        raise _validation_error()
    return value


def _settings() -> IdentitySettings:
    settings = current_app.config.get("IDENTITY_SETTINGS")
    if not isinstance(settings, IdentitySettings) or not settings.cursor_signing_key:
        raise ApiError(
            "dependency_unavailable",
            "The incident library is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return settings


def _cursor(settings: IdentitySettings) -> dict[str, str] | None:
    raw = _single_query_value("cursor")
    if raw is None or not raw:
        return None
    try:
        return decode_cursor(raw, settings.cursor_signing_key or "")
    except InvalidCursor:
        raise _validation_error() from None


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _summary(item: IncidentSummary) -> dict[str, object]:
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


@incidents_bp.get("")
@require_browser_session
def list_incidents_route():
    if set(request.args) - _ALLOWED_QUERY_KEYS:
        raise _validation_error()

    relationship = _single_query_value("relationship") or "all"
    if relationship not in _RELATIONSHIPS:
        raise _validation_error()

    settings = _settings()
    filters = IncidentLibraryFilters(
        q=_optional_text("q"),
        relationship=relationship,
        category=_optional_text("category", maximum=120),
        date_from=_optional_date("date_from"),
        date_to=_optional_date("date_to"),
        location=_optional_text("location", maximum=160),
    )

    try:
        page = list_incident_summaries(
            current_browser_session(),
            current_browser_actor(),
            filters=filters,
            limit=_limit(),
            cursor=_cursor(settings),
        )
    except ValueError:
        raise _validation_error() from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The incident library is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None

    next_cursor = (
        encode_cursor(page.next_cursor, settings.cursor_signing_key)
        if page.next_cursor is not None
        else None
    )
    return success({
        "items": [_summary(item) for item in page.items],
        "next_cursor": next_cursor,
    })
