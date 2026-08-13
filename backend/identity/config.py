from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit

from packaging.version import InvalidVersion, Version


def _enabled(value: str | None) -> bool:
    return (value or "false").strip().lower() in {"1", "true", "yes", "on"}


def _public_version(name: str, value: str) -> str:
    try:
        parsed = Version(value)
    except InvalidVersion as exc:
        raise RuntimeError(f"{name} must be a semantic version") from exc
    if parsed.local is not None or len(parsed.release) < 3:
        raise RuntimeError(f"{name} must be a public major.minor.patch version")
    return str(parsed)


def _https_origin(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlsplit(value)
    try:
        port = f":{parsed.port}" if parsed.port is not None else ""
    except ValueError as exc:
        raise RuntimeError("PUBLIC_BASE_URL must be an HTTPS origin") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("PUBLIC_BASE_URL must be an HTTPS origin")
    return f"https://{parsed.hostname}{port}"


@dataclass(frozen=True)
class IdentitySettings:
    enabled: bool
    database_url: str | None
    identity_hash_pepper: str | None
    cursor_signing_key: str | None
    release_version: str = "0.0.0-development"
    latest_client_version: str = "0.0.0-development"
    minimum_client_version: str = "0.0.0-development"
    minimum_server_version: str = "0.0.0-development"
    api_version: str = "v1"
    release_notes: str = "Development build; not approved for production."
    public_base_url: str | None = None
    review_lab_origin: str | None = None
    access_ttl_seconds: int = 15 * 60
    nonpersistent_renewal_ttl_seconds: int = 12 * 60 * 60
    persistent_renewal_ttl_seconds: int = 30 * 24 * 60 * 60
    step_up_ttl_seconds: int = 5 * 60
    admin_elevation_idle_seconds: int = 15 * 60
    browser_handoff_ttl_seconds: int = 60
    browser_session_idle_seconds: int = 30 * 60

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "IdentitySettings":
        enabled = _enabled(env.get("ACCESS_API_ENABLED"))
        database_url = env.get("DATABASE_URL") or None
        identity_hash_pepper = env.get("IDENTITY_HASH_PEPPER") or None
        cursor_signing_key = env.get("CURSOR_SIGNING_KEY") or None
        release_version = env.get("RELEASE_VERSION") or "0.0.0-development"
        latest_client_version = env.get("LATEST_CLIENT_VERSION") or "0.0.0-development"
        minimum_client_version = (
            env.get("MINIMUM_CLIENT_VERSION") or "0.0.0-development"
        )
        minimum_server_version = (
            env.get("MINIMUM_SERVER_VERSION") or "0.0.0-development"
        )
        api_version = env.get("API_VERSION") or "v1"
        release_notes = env.get(
            "RELEASE_NOTES", "Development build; not approved for production."
        ).strip()
        public_base_url = env.get("PUBLIC_BASE_URL") or None
        review_lab_origin = _https_origin(public_base_url)
        if enabled:
            missing = [
                name
                for name, value in (
                    ("DATABASE_URL", database_url),
                    ("IDENTITY_HASH_PEPPER", identity_hash_pepper),
                    ("CURSOR_SIGNING_KEY", cursor_signing_key),
                )
                if not value
            ]
            if missing:
                raise RuntimeError(
                    "Missing identity configuration: " + ", ".join(missing)
                )
            if (
                not release_notes
                or len(release_notes) > 500
                or any(ord(ch) < 32 for ch in release_notes)
            ):
                raise RuntimeError(
                    "RELEASE_NOTES must be one nonempty line of at most 500 characters"
                )
            if api_version != "v1":
                raise RuntimeError("API_VERSION must be v1")
            if review_lab_origin is None:
                raise RuntimeError("Missing identity configuration: PUBLIC_BASE_URL")
            if release_version != "0.0.0-development":
                release_version = _public_version("RELEASE_VERSION", release_version)
            if latest_client_version != "0.0.0-development":
                latest_client_version = _public_version(
                    "LATEST_CLIENT_VERSION", latest_client_version
                )
            if minimum_client_version != "0.0.0-development":
                minimum_client_version = _public_version(
                    "MINIMUM_CLIENT_VERSION", minimum_client_version
                )
            if minimum_server_version != "0.0.0-development":
                minimum_server_version = _public_version(
                    "MINIMUM_SERVER_VERSION", minimum_server_version
                )
            if (
                latest_client_version != "0.0.0-development"
                and minimum_client_version != "0.0.0-development"
                and Version(minimum_client_version) > Version(latest_client_version)
            ):
                raise RuntimeError(
                    "MINIMUM_CLIENT_VERSION cannot exceed LATEST_CLIENT_VERSION"
                )
        return cls(
            enabled=enabled,
            database_url=database_url,
            identity_hash_pepper=identity_hash_pepper,
            cursor_signing_key=cursor_signing_key,
            release_version=release_version,
            latest_client_version=latest_client_version,
            minimum_client_version=minimum_client_version,
            minimum_server_version=minimum_server_version,
            api_version=api_version,
            release_notes=release_notes,
            public_base_url=public_base_url,
            review_lab_origin=review_lab_origin,
        )
