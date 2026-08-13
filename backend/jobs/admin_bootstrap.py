"""Fail-closed first-Admin bootstrap contract."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Callable, Literal, Protocol
from urllib.parse import urlparse
from uuid import UUID

from backend.identity.accounts import bootstrap_first_admin
from backend.identity.audit import PostgresAuditWriter
from backend.identity.errors import InitialAdminBootstrapRefused


class BootstrapRequestReader(Protocol):
    def read_exact(self, *, bucket: str, object_name: str, max_bytes: int) -> bytes: ...


class SecretVersionAdder(Protocol):
    def add_version(self, *, parent: str, payload: bytes) -> str: ...


@dataclass(frozen=True)
class AdminBootstrapRequest:
    operation_id: UUID
    staff_member_id: UUID
    approval_reference: str


@dataclass(frozen=True)
class AdminBootstrapResult:
    operation_id: UUID
    status: Literal["bootstrapped", "bootstrap_refused", "pin_version_add_failed", "pin_version_outcome_unknown_cleanup_required", "orphan_pin_version_cleanup_required"]
    expires_at: datetime | None
    secret_version_reference: str | None


def _v4(value: object) -> UUID:
    parsed = UUID(str(value))
    if parsed.version != 4:
        raise ValueError("bootstrap request is invalid")
    return parsed


def load_bootstrap_request(storage_client: BootstrapRequestReader, *, request_uri: str, expected_sha256: str, expected_bucket: str, expected_prefix: str = "admin-bootstrap-requests/") -> AdminBootstrapRequest:
    parsed = urlparse(request_uri)
    if parsed.scheme != "gs" or parsed.netloc != expected_bucket or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("bootstrap request is invalid")
    object_name = parsed.path.lstrip("/")
    match = re.fullmatch(re.escape(expected_prefix) + r"([0-9a-f-]{36})\.json", object_name)
    if not match:
        raise ValueError("bootstrap request is invalid")
    body = storage_client.read_exact(bucket=expected_bucket, object_name=object_name, max_bytes=4096)
    if not isinstance(body, bytes) or len(body) > 4096 or hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError("bootstrap request is invalid")
    try:
        data = json.loads(body)
        if set(data) != {"schema_version", "operation_id", "staff_member_id", "approval_reference"} or data["schema_version"] != 1:
            raise ValueError
        operation_id, staff_member_id = _v4(data["operation_id"]), _v4(data["staff_member_id"])
        reference = data["approval_reference"]
        if not isinstance(reference, str) or not re.fullmatch(r"[\x20-\x7e]{1,200}", reference) or str(operation_id) != match.group(1):
            raise ValueError
    except Exception as exc:
        raise ValueError("bootstrap request is invalid") from None
    return AdminBootstrapRequest(operation_id, staff_member_id, reference)


def execute_admin_bootstrap(session_factory: Callable[[], object], secret_client: SecretVersionAdder, *, request: AdminBootstrapRequest, initial_admin_pin_secret: str, now: datetime) -> AdminBootstrapResult:
    session = session_factory()
    try:
        pending = bootstrap_first_admin(session, staff_member_id=request.staff_member_id, now=now, audit_writer=PostgresAuditWriter(), operation_id=request.operation_id, approval_reference_sha256=hashlib.sha256(request.approval_reference.encode()).hexdigest())
    except InitialAdminBootstrapRefused:
        session.rollback(); session.close()
        return AdminBootstrapResult(request.operation_id, "bootstrap_refused", None, None)
    except Exception:
        session.rollback(); session.close()
        return AdminBootstrapResult(request.operation_id, "bootstrap_refused", None, None)
    try:
        name = secret_client.add_version(parent=initial_admin_pin_secret, payload=pending.temporary_pin.encode())
    except TimeoutError:
        session.rollback(); session.close()
        return AdminBootstrapResult(request.operation_id, "pin_version_outcome_unknown_cleanup_required", None, None)
    except Exception:
        session.rollback(); session.close()
        return AdminBootstrapResult(request.operation_id, "pin_version_add_failed", None, None)
    prefix = initial_admin_pin_secret.rstrip("/") + "/versions/"
    if not isinstance(name, str) or not re.fullmatch(re.escape(prefix) + r"[1-9][0-9]*", name):
        session.rollback(); session.close()
        return AdminBootstrapResult(request.operation_id, "pin_version_outcome_unknown_cleanup_required", None, None)
    reference = "initial-admin-pin/versions/" + name.rsplit("/", 1)[1]
    try:
        session.commit()
    except Exception:
        session.rollback(); session.close()
        return AdminBootstrapResult(request.operation_id, "orphan_pin_version_cleanup_required", pending.expires_at, reference)
    session.close()
    return AdminBootstrapResult(request.operation_id, "bootstrapped", pending.expires_at, reference)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controlled initial Admin bootstrap")
    parser.add_argument("--request-uri", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.parse_args(argv)
    return 1
