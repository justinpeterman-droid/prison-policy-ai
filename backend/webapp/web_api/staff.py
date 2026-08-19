"""Active staff search for the Guided Operations officer-selection step."""
from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.persistence.database import DatabaseUnavailable
from backend.reports.roster import SqlStaffProvider
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_session,
    require_browser_session,
)


staff_bp = Blueprint("web_staff", __name__)


def _limit(raw: str | None) -> int:
    if raw is None:
        return 25
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError("staff limit is invalid") from None
    if str(value) != raw.strip() or not 1 <= value <= 50:
        raise ValueError("staff limit is invalid")
    return value


@staff_bp.get("/staff")
@require_browser_session
def search_staff():
    try:
        if not set(request.args) <= {"q", "limit", "cursor"}:
            raise ValueError("staff filters are invalid")
        query = request.args.get("q", "").strip()
        if not 1 <= len(query) <= 100:
            raise ValueError("staff query is invalid")
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("staff pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        page = SqlStaffProvider(current_browser_session()).search_page(
            query,
            limit=_limit(request.args.get("limit")),
            cursor=cursor,
        )
        return success({
            "items": page.items,
            "next_cursor": encode_cursor(page.next_cursor, key)
            if page.next_cursor
            else None,
        })
    except (InvalidCursor, ValueError):
        raise ApiError(
            "validation_failed", "Staff search is invalid.", status=400
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Staff search is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
