"""Active staff lookup for report selection."""
from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.persistence.database import DatabaseUnavailable
from backend.reports.roster import SqlStaffProvider
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import current_request_session, require_access_token
from backend.webapp.api_v1.pagination import decode_cursor, encode_cursor, InvalidCursor
from backend.webapp.api_v1.responses import success


staff_bp = Blueprint("staff_api", __name__)


@staff_bp.get("", endpoint="staff_list")
@require_access_token
def staff_list():
    query = request.args.get("query", "").strip()
    try:
        limit = int(request.args.get("limit", "25"))
    except ValueError:
        raise ApiError("validation_failed", "Staff search input is invalid.", status=400) from None
    if not 2 <= len(query) <= 100 or not 1 <= limit <= 50:
        raise ApiError("validation_failed", "Staff search input is invalid.", status=400)
    try:
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("staff pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        page = SqlStaffProvider(current_request_session()).search_page(
            query, limit=limit, cursor=cursor)
        return success({
            "items": page.items,
            "next_cursor": encode_cursor(page.next_cursor, key) if page.next_cursor else None,
        })
    except InvalidCursor:
        raise ApiError("validation_failed", "Staff search input is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Staff lookup is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
