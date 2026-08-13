from collections.abc import Callable
from functools import wraps
from typing import Final, TypeVar

from flask import current_app, g
from packaging.version import Version

from backend.identity.config import IdentitySettings
from backend.webapp.api_v1.errors import ApiError


FIELD_NOTES_MAX_CHARACTERS: Final[int] = 30_000
MUST_CHANGE_PIN_ALLOWED_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/api/v1/me",
        "/api/v1/auth/change-pin",
        "/api/v1/auth/logout",
        "/api/v1/auth/logout-all",
        "/api/v1/auth/renew",
    }
)
F = TypeVar("F", bound=Callable)


def policy_data(settings: IdentitySettings) -> dict[str, object]:
    current = getattr(g, "client_version", None)
    minimum = settings.minimum_client_version
    read_only_required = bool(current is not None and minimum != "0.0.0-development" and current < Version(minimum))
    return {
        "release_version": settings.release_version,
        "latest_client_version": settings.latest_client_version,
        "minimum_client_version": settings.minimum_client_version,
        "minimum_server_version": settings.minimum_server_version,
        "api_version": settings.api_version,
        "release_notes": settings.release_notes,
        "read_only_required": read_only_required,
        "review_lab_origin": settings.review_lab_origin,
        "field_notes_max_characters": FIELD_NOTES_MAX_CHARACTERS,
    }


def require_compatible_write(view: F) -> F:
    @wraps(view)
    def wrapped(*args, **kwargs):
        settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
        version = getattr(g, "client_version", None)
        minimum = settings.minimum_client_version
        if version is None or (minimum != "0.0.0-development" and version < Version(minimum)):
            from backend.webapp.api_v1.admin_health import emit_client_upgrade_required

            parsed = "missing" if version is None else "_".join(map(str, version.release[:3]))
            emit_client_upgrade_required(parsed)
            raise ApiError(
                "client_upgrade_required",
                "A supported Access client version is required for this change.",
                status=409,
            )
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]
