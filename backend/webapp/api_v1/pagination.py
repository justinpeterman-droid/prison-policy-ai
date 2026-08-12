import base64
from datetime import UTC, datetime
import hashlib
import hmac
import json
from uuid import UUID


class InvalidCursor(ValueError):
    pass


def encode_cursor(payload: dict[str, str], key: str) -> str:
    _validate_payload(payload)
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(key.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(body + signature).decode("ascii").rstrip("=")


def decode_cursor(value: str, key: str) -> dict[str, str]:
    padded = value + "=" * (-len(value) % 4)
    try:
        raw = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise InvalidCursor("cursor is invalid") from exc
    if len(raw) <= 32:
        raise InvalidCursor("cursor is invalid")
    body, supplied = raw[:-32], raw[-32:]
    expected = hmac.new(key.encode("utf-8"), body, hashlib.sha256).digest()
    if not hmac.compare_digest(supplied, expected):
        raise InvalidCursor("cursor is invalid")
    try:
        decoded = json.loads(body)
        _validate_payload(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidCursor("cursor is invalid") from exc
    return decoded


def parse_page_size(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("page size must be an integer from 1 through 100")
    try:
        size = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("page size must be an integer from 1 through 100") from exc
    if str(size) != str(value).strip() or not 1 <= size <= 100:
        raise ValueError("page size must be an integer from 1 through 100")
    return size


def _validate_payload(payload: object) -> None:
    if not isinstance(payload, dict) or set(payload) != {"created_at", "id"}:
        raise InvalidCursor("cursor is invalid")
    if not all(isinstance(value, str) for value in payload.values()):
        raise InvalidCursor("cursor is invalid")
    created_at = payload["created_at"]
    try:
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError
        UUID(payload["id"])
    except (AttributeError, TypeError, ValueError) as exc:
        raise InvalidCursor("cursor is invalid") from exc
