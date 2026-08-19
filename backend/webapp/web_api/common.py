"""Shared closed-input and response helpers for the browser workspace API."""
from datetime import UTC
from typing import Iterable

from flask import g, request

from backend.webapp.api_v1.errors import ApiError


LOCK_CONFLICT_STATES = frozenset({"40P01", "40001", "55P03"})


def timestamp(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def json_body(
    *,
    exact: Iterable[str] | None = None,
    allowed: Iterable[str] | None = None,
    required: Iterable[str] = (),
    message: str = "The request body is invalid.",
) -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ApiError("validation_failed", message, status=400)
    keys = set(value)
    exact_keys = set(exact) if exact is not None else None
    allowed_keys = set(allowed) if allowed is not None else None
    required_keys = set(required)
    if (
        (exact_keys is not None and keys != exact_keys)
        or (allowed_keys is not None and (not keys or not keys <= allowed_keys))
        or not required_keys <= keys
    ):
        raise ApiError("validation_failed", message, status=400)
    return value


def request_metadata() -> tuple[str, str]:
    version = getattr(g, "client_version", None)
    if version is None or version == "invalid":
        raise ApiError(
            "validation_failed",
            "X-Client-Version must be a valid semantic version.",
            status=400,
        )
    return str(g.request_id), str(version)


def validate_if_match(base_revision_number: int) -> None:
    value = request.headers.get("If-Match")
    if value is None:
        return
    if (
        len(value) < 3
        or value[0] != '"'
        or value[-1] != '"'
        or not value[1:-1].isdigit()
        or value[1:-1].startswith("0")
        or int(value[1:-1]) != base_revision_number
    ):
        raise ApiError(
            "validation_failed",
            "If-Match must agree with base_revision_number.",
            status=400,
        )


def require_idempotency_key() -> str:
    key = request.headers.get("Idempotency-Key", "")
    if not key:
        raise ApiError(
            "validation_failed", "Idempotency-Key is required.", status=400
        )
    return key


def positive_int(value: object, *, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ApiError(
            "validation_failed", f"{name} must be a positive integer.", status=400
        )
    return value


def bounded_text(
    value: object,
    *,
    name: str,
    minimum: int = 1,
    maximum: int = 500,
) -> str:
    if not isinstance(value, str):
        raise ApiError("validation_failed", f"{name} is invalid.", status=400)
    cleaned = " ".join(value.split())
    if not minimum <= len(cleaned) <= maximum:
        raise ApiError("validation_failed", f"{name} is invalid.", status=400)
    return cleaned
