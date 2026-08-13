"""Fail-closed first-Admin bootstrap job.

Only the closed result contract is written to stdout. Request contents, database
configuration, secret payloads, and provider exception details are never emitted.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
import re
from typing import Callable, Literal, Protocol
from urllib.parse import urlparse
from uuid import UUID

from google.api_core import exceptions as google_exceptions
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.identity.accounts import bootstrap_first_admin
from backend.identity.audit import PostgresAuditWriter
from backend.identity.errors import InitialAdminBootstrapRefused


class BootstrapRequestReader(Protocol):
    def read_exact(self, *, bucket: str, object_name: str, max_bytes: int) -> bytes: ...


class SecretVersionAdder(Protocol):
    def add_version(self, *, parent: str, payload: bytes) -> str: ...


class SecretVersionOutcomeUnknown(RuntimeError):
    """The non-idempotent add may have created a version."""


class GoogleBootstrapRequestReader:
    """Read one bounded object without authenticating until invoked by the job."""

    def __init__(self, client=None):
        if client is None:
            from google.cloud import storage

            client = storage.Client()
        self._client = client

    def read_exact(self, *, bucket: str, object_name: str, max_bytes: int) -> bytes:
        blob = self._client.bucket(bucket).blob(object_name)
        payload = blob.download_as_bytes(start=0, end=max_bytes)
        if len(payload) > max_bytes:
            raise ValueError("bootstrap request is invalid")
        return payload


class GoogleSecretVersionAdder:
    """Perform exactly one non-idempotent Secret Manager add-version RPC."""

    def __init__(self, client=None):
        if client is None:
            from google.cloud import secretmanager_v1

            client = secretmanager_v1.SecretManagerServiceClient()
        self._client = client

    def add_version(self, *, parent: str, payload: bytes) -> str:
        response = self._client.add_secret_version(
            request={"parent": parent, "payload": {"data": payload}},
            retry=None,
            timeout=10.0,
        )
        name = getattr(response, "name", None)
        if not isinstance(name, str) or not re.fullmatch(
            re.escape(parent.rstrip("/")) + r"/versions/[1-9][0-9]*", name
        ):
            raise SecretVersionOutcomeUnknown("secret version result is untrusted")
        return name


@dataclass(frozen=True)
class AdminBootstrapRequest:
    operation_id: UUID
    staff_member_id: UUID
    approval_reference: str


@dataclass(frozen=True)
class AdminBootstrapResult:
    operation_id: UUID
    status: Literal[
        "bootstrapped",
        "bootstrap_refused",
        "pin_version_add_failed",
        "pin_version_outcome_unknown_cleanup_required",
        "orphan_pin_version_cleanup_required",
    ]
    expires_at: datetime | None
    secret_version_reference: str | None


def _v4(value: object) -> UUID:
    parsed = UUID(str(value))
    if parsed.version != 4:
        raise ValueError("bootstrap request is invalid")
    return parsed


def load_bootstrap_request(
    storage_client: BootstrapRequestReader,
    *,
    request_uri: str,
    expected_sha256: str,
    expected_bucket: str,
    expected_prefix: str = "admin-bootstrap-requests/",
) -> AdminBootstrapRequest:
    parsed = urlparse(request_uri)
    if (
        parsed.scheme != "gs"
        or parsed.netloc != expected_bucket
        or parsed.params
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        or not re.fullmatch(r"[a-z0-9][a-z0-9._/-]{0,511}/", expected_prefix)
    ):
        raise ValueError("bootstrap request is invalid")
    object_name = parsed.path.lstrip("/")
    match = re.fullmatch(
        re.escape(expected_prefix)
        + r"([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\.json",
        object_name,
    )
    if not match:
        raise ValueError("bootstrap request is invalid")
    body = storage_client.read_exact(
        bucket=expected_bucket, object_name=object_name, max_bytes=4096
    )
    if (
        not isinstance(body, bytes)
        or len(body) > 4096
        or hashlib.sha256(body).hexdigest() != expected_sha256
    ):
        raise ValueError("bootstrap request is invalid")
    try:
        data = json.loads(body)
        if (
            not isinstance(data, dict)
            or set(data)
            != {
                "schema_version",
                "operation_id",
                "staff_member_id",
                "approval_reference",
            }
            or data["schema_version"] != 1
        ):
            raise ValueError
        operation_id = _v4(data["operation_id"])
        staff_member_id = _v4(data["staff_member_id"])
        reference = data["approval_reference"]
        if (
            not isinstance(reference, str)
            or not re.fullmatch(r"[\x20-\x7e]{1,200}", reference)
            or str(operation_id) != match.group(1)
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("bootstrap request is invalid") from None
    return AdminBootstrapRequest(operation_id, staff_member_id, reference)


def execute_admin_bootstrap(
    session_factory: Callable[[], Session],
    secret_client: SecretVersionAdder,
    *,
    request: AdminBootstrapRequest,
    initial_admin_pin_secret: str,
    now: datetime,
) -> AdminBootstrapResult:
    session = session_factory()
    pending = None
    payload = None
    try:
        pending = bootstrap_first_admin(
            session,
            staff_member_id=request.staff_member_id,
            now=now,
            audit_writer=PostgresAuditWriter(),
            operation_id=request.operation_id,
            approval_reference_sha256=hashlib.sha256(
                request.approval_reference.encode("utf-8")
            ).hexdigest(),
        )
    except InitialAdminBootstrapRefused:
        session.rollback()
        session.close()
        return AdminBootstrapResult(
            request.operation_id, "bootstrap_refused", None, None
        )
    except Exception:
        session.rollback()
        session.close()
        raise

    expires_at = pending.expires_at
    payload = bytearray(pending.temporary_pin.encode("utf-8"))
    try:
        name = secret_client.add_version(
            parent=initial_admin_pin_secret,
            payload=bytes(payload),
        )
    except google_exceptions.ClientError as error:
        session.rollback()
        session.close()
        if isinstance(
            error,
            (
                google_exceptions.Aborted,
                google_exceptions.BadGateway,
                google_exceptions.Cancelled,
                google_exceptions.GatewayTimeout,
                google_exceptions.Unknown,
            ),
        ):
            return AdminBootstrapResult(
                request.operation_id,
                "pin_version_outcome_unknown_cleanup_required",
                None,
                None,
            )
        return AdminBootstrapResult(
            request.operation_id, "pin_version_add_failed", None, None
        )
    except Exception:
        session.rollback()
        session.close()
        return AdminBootstrapResult(
            request.operation_id,
            "pin_version_outcome_unknown_cleanup_required",
            None,
            None,
        )
    finally:
        if payload is not None:
            payload[:] = b"\x00" * len(payload)
        pending = None
        payload = None

    prefix = initial_admin_pin_secret.rstrip("/") + "/versions/"
    if not isinstance(name, str) or not re.fullmatch(
        re.escape(prefix) + r"[1-9][0-9]*", name
    ):
        session.rollback()
        session.close()
        return AdminBootstrapResult(
            request.operation_id,
            "pin_version_outcome_unknown_cleanup_required",
            None,
            None,
        )
    reference = "initial-admin-pin/versions/" + name.rsplit("/", 1)[1]
    try:
        session.commit()
    except Exception:
        session.rollback()
        session.close()
        return AdminBootstrapResult(
            request.operation_id,
            "orphan_pin_version_cleanup_required",
            expires_at,
            reference,
        )
    session.close()
    return AdminBootstrapResult(
        request.operation_id, "bootstrapped", expires_at, reference
    )


def _safe_result(result: AdminBootstrapResult) -> dict[str, object]:
    values = asdict(result)
    values["operation_id"] = str(result.operation_id)
    values["expires_at"] = (
        result.expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if result.expires_at is not None
        else None
    )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controlled initial Admin bootstrap")
    parser.add_argument("--request-uri", required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    expected_bucket = os.environ.get("ADMIN_BOOTSTRAP_REQUEST_BUCKET")
    expected_prefix = os.environ.get(
        "ADMIN_BOOTSTRAP_REQUEST_PREFIX", "admin-bootstrap-requests/"
    )
    secret_parent = os.environ.get("INITIAL_ADMIN_PIN_SECRET")
    if not all((database_url, expected_bucket, expected_prefix, secret_parent)):
        return 1

    try:
        request = load_bootstrap_request(
            GoogleBootstrapRequestReader(),
            request_uri=args.request_uri,
            expected_sha256=args.expected_sha256,
            expected_bucket=expected_bucket,
            expected_prefix=expected_prefix,
        )
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"options": "-c timezone=utc"},
        )
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        try:
            result = execute_admin_bootstrap(
                factory,
                GoogleSecretVersionAdder(),
                request=request,
                initial_admin_pin_secret=secret_parent,
                now=datetime.now(UTC),
            )
        finally:
            engine.dispose()
    except Exception:
        return 1
    print(json.dumps(_safe_result(result), sort_keys=True, separators=(",", ":")))
    return 0 if result.status == "bootstrapped" else 1


if __name__ == "__main__":
    raise SystemExit(main())
