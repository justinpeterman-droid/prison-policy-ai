from datetime import UTC, datetime
import re
from time import monotonic
from uuid import uuid4

from flask import g, request
from packaging.version import InvalidVersion, Version


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
STABLE_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def begin_request() -> None:
    supplied = request.headers.get("X-Request-ID", "")
    g.request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
    g.request_started_at = datetime.now(UTC)
    g.request_started_monotonic = monotonic()
    raw_version = request.headers.get("X-Client-Version", "")
    if request.endpoint == "api_v1.client_policy":
        g.client_version = None
        return
    try:
        parsed = Version(raw_version)
        g.client_version = parsed if parsed.local is None and len(parsed.release) >= 3 else None
    except InvalidVersion:
        g.client_version = None


def request_id() -> str:
    return g.request_id


def client_version() -> Version:
    version = getattr(g, "client_version", None)
    if version is None:
        raise RuntimeError("client version is unavailable")
    return version


def server_time() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _stable_code(value: str, fallback: str) -> str:
    return value if STABLE_CODE_PATTERN.fullmatch(value) else fallback


def _latency_bucket(latency_ms: int) -> str:
    if latency_ms < 100:
        return "under_100ms"
    if latency_ms < 500:
        return "100_to_499ms"
    if latency_ms < 2_000:
        return "500_to_1999ms"
    return "2000ms_or_more"


def request_event(
    *,
    action: str,
    result: str,
    status_code: int,
    error_code: str | None = None,
    dependency: str = "none",
) -> dict[str, object]:
    elapsed = max(0, int((monotonic() - g.request_started_monotonic) * 1000))
    latency_ms = min(elapsed, 300_000)
    parsed_version = getattr(g, "client_version", None)
    return {
        "request_id": request_id(),
        "action": _stable_code(action, "unknown"),
        "result": _stable_code(result, "error"),
        "latency_ms": latency_ms,
        "latency_bucket": _latency_bucket(latency_ms),
        "http_status_class": f"{min(max(status_code, 100), 599) // 100}xx",
        "error_code": (_stable_code(error_code, "internal_error") if error_code else None),
        "client_version": str(parsed_version) if parsed_version is not None else "missing",
        "dependency": _stable_code(dependency, "none"),
    }
