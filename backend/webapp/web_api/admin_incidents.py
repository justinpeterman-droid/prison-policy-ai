"""Administrator incident-centered browser API."""
from datetime import UTC, date, datetime
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.browser_admin import require_browser_admin_elevation
from backend.identity.config import IdentitySettings
from backend.identity.elevation import AdminElevationRequired
from backend.persistence.database import DatabaseUnavailable
from backend.reports.admin_incidents import (
    AdminIncidentFilters,
    AdminIncidentSummary,
    list_admin_incident_summaries,
)
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_role,
    require_browser_session,
)


admin_incidents_bp = Blueprint("web_admin_incidents", __name__)
_ALLOWED_QUERY_KEYS = {
    "q",
    "incident_number",
    "reporting_staff_id",
    "prepared_by_staff_id",
    "incident_date_from",
    "incident_date_to",
    "created_at_from",
    "created_at_to",
    "category",
    "facility",
    "location",
    "shift",
    "records_status",
    "last_editor_staff_id",
    "updated_at_from",
    "updated_at_to",
    "limit",
    "cursor",
}


def _validation_error() -> ApiError:
    return ApiError(
        "validation_failed",
        "The administrator incident search is invalid.",
        status=400,
    )


def _single(name: str) -> str | None:
    values = request.args.getlist(name)
    if len(values) > 1:
        raise _validation_error()
    return values[0] if values else None


def _text(name: str, *, maximum: int = 200) -> str | None:
    raw = _single(name)
    if raw is None:
        return None
    value = " ".join(raw.split())
    if not value or len(value) > maximum:
        raise _validation_error()
    return value


def _uuid(name: str) -> UUID | None:
    raw = _single(name)
    if raw is None:
        return None
    try:
        return UUID(raw)
    except ValueError:
        raise _validation_error() from None


def _date(name: str) -> date | None:
    raw = _single(name)
    if raw is None:
        return None
    try:
        value = date.fromisoformat(raw)
    except ValueError:
        raise _validation_error() from None
    if value.isoformat() != raw:
        raise _validation_error()
    return value


def _datetime(name: str) -> datetime | None:
    raw = _single(name)
    if raw is None:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise _validation_error() from None
    if value.tzinfo is None:
        raise _validation_error()
    return value.astimezone(UTC)


def _limit() -> int:
    raw = _single("limit")
    if raw is None:
        return 25
    if not raw.isascii() or not raw.isdigit() or str(int(raw)) != raw:
        raise _validation_error()
    value = int(raw)
    if not 1 <= value <= 50:
        raise _validation_error()
    return value


def _settings() -> IdentitySettings:
    settings = current_app.config.get("IDENTITY_SETTINGS")
    if not isinstance(settings, IdentitySettings) or not settings.cursor_signing_key:
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident search is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return settings


def _cursor(settings: IdentitySettings) -> dict[str, str] | None:
    raw = _single("cursor")
    if raw is None:
        return None
    try:
        return decode_cursor(raw, settings.cursor_signing_key or "")
    except InvalidCursor:
        raise _validation_error() from None


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _staff(value) -> dict[str, str]:
    return {"staff_id": str(value.staff_id), "display_name": value.display_name}


def _summary(item: AdminIncidentSummary) -> dict[str, object]:
    return {
        "incident_id": str(item.incident_id),
        "incident_number": item.incident_number,
        "incident_name": item.incident_name,
        "incident_date": item.incident_date.isoformat() if item.incident_date else None,
        "category": item.category,
        "facility": item.facility,
        "location": item.location,
        "shift": item.shift,
        "records_status": item.records_status,
        "reporting_officers": [_staff(value) for value in item.reporting_officers],
        "preparers": [_staff(value) for value in item.preparers],
        "last_editor": _staff(item.last_editor) if item.last_editor else None,
        "progress": {
            "code": item.progress.code,
            "label": item.progress.label,
            "blocking_count": item.progress.blocking_count,
        },
        "officer_report_count": item.officer_report_count,
        "required_paperwork_count": item.required_paperwork_count,
        "created_at": _timestamp(item.created_at),
        "updated_at": _timestamp(item.updated_at),
    }


def _require_elevation() -> None:
    try:
        require_browser_admin_elevation(
            current_browser_session(),
            actor=current_browser_actor(),
            now=datetime.now(UTC),
        )
    except AdminElevationRequired:
        raise ApiError(
            "admin_elevation_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None


@admin_incidents_bp.get("/incidents", endpoint="list_incidents")
@require_browser_session
@require_browser_role("admin")
def list_incidents_route():
    if set(request.args) - _ALLOWED_QUERY_KEYS:
        raise _validation_error()
    _require_elevation()
    settings = _settings()
    try:
        filters = AdminIncidentFilters(
            q=_text("q"),
            incident_number=_text("incident_number", maximum=11),
            reporting_staff_id=_uuid("reporting_staff_id"),
            prepared_by_staff_id=_uuid("prepared_by_staff_id"),
            incident_date_from=_date("incident_date_from"),
            incident_date_to=_date("incident_date_to"),
            created_at_from=_datetime("created_at_from"),
            created_at_to=_datetime("created_at_to"),
            category=_text("category", maximum=120),
            facility=_text("facility", maximum=120),
            location=_text("location", maximum=200),
            shift=_text("shift", maximum=32),
            records_status=_text("records_status", maximum=16),
            last_editor_staff_id=_uuid("last_editor_staff_id"),
            updated_at_from=_datetime("updated_at_from"),
            updated_at_to=_datetime("updated_at_to"),
        )
        page = list_admin_incident_summaries(
            current_browser_session(),
            current_browser_actor(),
            filters=filters,
            limit=_limit(),
            cursor=_cursor(settings),
        )
    except ApiError:
        raise
    except ValueError:
        raise _validation_error() from None
    except PermissionError:
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident search is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None

    return success({
        "items": [_summary(item) for item in page.items],
        "next_cursor": (
            encode_cursor(page.next_cursor, settings.cursor_signing_key)
            if page.next_cursor else None
        ),
    })
