"""Cookie-authenticated searchable Forms Library routes."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.library import (
    FormLibraryItem,
    FormLibraryNotFound,
    FormLibrarySelectionInvalid,
    get_form_library_item,
    get_form_selection,
    search_form_library,
)
from backend.persistence.database import DatabaseUnavailable
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.common import json_body
from backend.webapp.web_api.middleware import (
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


forms_library_bp = Blueprint("web_forms_library", __name__)
ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"
_ALLOWED_QUERY_KEYS = frozenset({"q", "category", "limit", "cursor"})
_MAX_QUERY = 200
_MAX_CATEGORY = 80


def _sync_catalog():
    db = current_browser_session()
    sync_form_catalog(db, load_form_catalog(CATALOG_PATH))
    db.flush()
    return db


def _cursor_key() -> str:
    settings = current_app.config.get("IDENTITY_SETTINGS")
    key = getattr(settings, "cursor_signing_key", None)
    if not isinstance(key, str) or not key:
        raise ApiError(
            "dependency_unavailable",
            "The Forms Library is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return key


def _query_fingerprint(q: str | None, category: str | None) -> str:
    canonical = json.dumps(
        {"q": q or "", "category": category or ""},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _encode_cursor(offset: int, q: str | None, category: str | None) -> str:
    body = json.dumps(
        {
            "offset": offset,
            "query_sha256": _query_fingerprint(q, category),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(_cursor_key().encode("utf-8"), body, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(body + signature).decode("ascii").rstrip("=")


def _decode_cursor(
    value: str | None,
    q: str | None,
    category: str | None,
) -> int:
    if value is None:
        return 0
    if not isinstance(value, str) or not 1 <= len(value) <= 512:
        raise ValueError("forms cursor is invalid")
    padded = value + "=" * (-len(value) % 4)
    try:
        raw = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("forms cursor is invalid") from None
    if len(raw) <= 32:
        raise ValueError("forms cursor is invalid")
    canonical = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if not hmac.compare_digest(value, canonical):
        raise ValueError("forms cursor is invalid")
    body, supplied = raw[:-32], raw[-32:]
    expected = hmac.new(_cursor_key().encode("utf-8"), body, hashlib.sha256).digest()
    if not hmac.compare_digest(supplied, expected):
        raise ValueError("forms cursor is invalid")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("forms cursor is invalid") from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"offset", "query_sha256"}
        or not isinstance(payload["offset"], int)
        or isinstance(payload["offset"], bool)
        or payload["offset"] < 1
        or payload["offset"] > 1_000_000
        or payload["query_sha256"] != _query_fingerprint(q, category)
    ):
        raise ValueError("forms cursor is invalid")
    return payload["offset"]


def _single_query(name: str) -> str | None:
    values = request.args.getlist(name)
    if len(values) > 1:
        raise ValueError("forms query is invalid")
    return values[0] if values else None


def _bounded_query(name: str, maximum: int) -> str | None:
    value = _single_query(name)
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if len(cleaned) > maximum:
        raise ValueError("forms query is invalid")
    return cleaned


def _limit() -> int:
    raw = _single_query("limit")
    if raw is None:
        return 25
    if not raw.isascii() or not raw.isdigit():
        raise ValueError("forms page size is invalid")
    value = int(raw)
    if str(value) != raw or not 1 <= value <= 50:
        raise ValueError("forms page size is invalid")
    return value


def _item_data(item: FormLibraryItem, *, detail: bool = False) -> dict[str, object]:
    result: dict[str, object] = {
        "template_id": str(item.template_id),
        "code": item.code,
        "name": item.name,
        "category": item.category,
        "purpose": item.purpose,
        "when_used": item.when_used,
        "output_kind": item.output_kind,
        "revision_label": item.revision_label,
        "capabilities": sorted(item.capabilities),
        "frequent": item.frequent,
        "obtain_from": item.obtain_from,
    }
    if detail:
        result["definition"] = item.definition
    return result


def _selection_ids() -> list[UUID]:
    payload = json_body(
        exact={"template_ids"},
        message="The form selection is invalid.",
    )
    values = payload["template_ids"]
    if not isinstance(values, list) or not 1 <= len(values) <= 50:
        raise ApiError("validation_failed", "The form selection is invalid.", status=400)
    result: list[UUID] = []
    try:
        for value in values:
            if not isinstance(value, str) or str(UUID(value)) != value.lower():
                raise ValueError
            result.append(UUID(value))
    except ValueError:
        raise ApiError("validation_failed", "The form selection is invalid.", status=400) from None
    if len(result) != len(set(result)):
        raise ApiError("validation_failed", "The form selection is invalid.", status=400)
    return result


def _selection_data(template_ids: list[UUID]) -> dict[str, object]:
    db = _sync_catalog()
    plan = get_form_selection(db, template_ids)
    return {
        "items": [_item_data(item, detail=True) for item in plan.items],
        "digital_items": [
            _item_data(item, detail=True) for item in plan.digital_items
        ],
        "physical_items": [
            _item_data(item, detail=True) for item in plan.physical_items
        ],
    }


@forms_library_bp.get("/forms")
@require_browser_session
def list_forms_route():
    if set(request.args) - _ALLOWED_QUERY_KEYS:
        raise ApiError("validation_failed", "The Forms Library request is invalid.", status=400)
    try:
        q = _bounded_query("q", _MAX_QUERY)
        category = _bounded_query("category", _MAX_CATEGORY)
        limit = _limit()
        offset = _decode_cursor(_single_query("cursor"), q, category)
        db = _sync_catalog()
        page = search_form_library(
            db,
            q=q,
            category=category,
            limit=limit,
            offset=offset,
        )
        categories = sorted({
            item.category
            for item in search_form_library(
                db,
                limit=50,
                offset=0,
            ).items
        })
        return success({
            "items": [_item_data(item) for item in page.items],
            "categories": categories,
            "next_cursor": (
                _encode_cursor(page.next_offset, q, category)
                if page.next_offset is not None
                else None
            ),
        })
    except (ValueError, FormLibrarySelectionInvalid):
        raise ApiError("validation_failed", "The Forms Library request is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The Forms Library is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@forms_library_bp.get("/forms/<uuid:template_id>")
@require_browser_session
def get_form_route(template_id: UUID):
    try:
        return success(_item_data(
            get_form_library_item(_sync_catalog(), template_id),
            detail=True,
        ))
    except FormLibraryNotFound:
        raise ApiError("not_found", "Form not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The Forms Library is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@forms_library_bp.post("/forms/selection/preview")
@require_browser_session
@require_browser_csrf
def preview_selection_route():
    try:
        return success(_selection_data(_selection_ids()))
    except FormLibrarySelectionInvalid:
        raise ApiError("validation_failed", "The form selection is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The selected forms are temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@forms_library_bp.post("/forms/selection/download")
@require_browser_session
@require_browser_csrf
def download_selection_route():
    try:
        data = _selection_data(_selection_ids())
        return success({
            "downloadable_items": data["digital_items"],
            "skipped_physical_items": data["physical_items"],
        })
    except FormLibrarySelectionInvalid:
        raise ApiError("validation_failed", "The form selection is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The selected forms are temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
