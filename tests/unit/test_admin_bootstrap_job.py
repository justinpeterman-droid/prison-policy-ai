import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from google.api_core import exceptions as google_exceptions

from backend.jobs.admin_bootstrap import (
    AdminBootstrapRequest,
    AdminBootstrapResult,
    GoogleSecretVersionAdder,
    execute_admin_bootstrap,
    load_bootstrap_request,
    main,
)


class Reader:
    def __init__(self, payload):
        self.payload = payload

    def read_exact(self, *, bucket, object_name, max_bytes):
        return self.payload


def test_bootstrap_request_requires_hash_schema_and_matching_opaque_path():
    operation = "00000000-0000-4000-8000-000000000001"
    body = json.dumps(
        {
            "schema_version": 1,
            "operation_id": operation,
            "staff_member_id": "00000000-0000-4000-8000-000000000002",
            "approval_reference": "fictional-approval-reference",
        }
    ).encode()
    request = load_bootstrap_request(
        Reader(body),
        request_uri=f"gs://fixture-config/admin-bootstrap-requests/{operation}.json",
        expected_sha256=hashlib.sha256(body).hexdigest(),
        expected_bucket="fixture-config",
    )
    assert request.operation_id == UUID(operation)
    with pytest.raises(ValueError):
        load_bootstrap_request(
            Reader(body),
            request_uri="gs://fixture-config/other.json",
            expected_sha256=hashlib.sha256(body).hexdigest(),
            expected_bucket="fixture-config",
        )


@pytest.mark.parametrize(
    "change",
    [
        {"extra": "rejected"},
        {"schema_version": 2},
        {"approval_reference": "line\nbreak"},
    ],
)
def test_bootstrap_request_rejects_non_closed_schema(change):
    operation = str(uuid4())
    values = {
        "schema_version": 1,
        "operation_id": operation,
        "staff_member_id": str(uuid4()),
        "approval_reference": "fictional-approval",
    }
    values.update(change)
    body = json.dumps(values).encode()
    with pytest.raises(ValueError, match="bootstrap request is invalid"):
        load_bootstrap_request(
            Reader(body),
            request_uri=f"gs://fixture-config/admin-bootstrap-requests/{operation}.json",
            expected_sha256=hashlib.sha256(body).hexdigest(),
            expected_bucket="fixture-config",
        )


def test_secret_adapter_makes_one_non_idempotent_call_and_validates_name():
    calls = []

    class Client:
        def add_secret_version(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                name="projects/fixture/secrets/initial-admin-pin/versions/7"
            )

    parent = "projects/fixture/secrets/initial-admin-pin"
    result = GoogleSecretVersionAdder(Client()).add_version(
        parent=parent, payload=b"fictional-pin"
    )
    assert result == f"{parent}/versions/7"
    assert calls == [
        {
            "request": {"parent": parent, "payload": {"data": b"fictional-pin"}},
            "retry": None,
            "timeout": 10.0,
        }
    ]


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError(),
        ConnectionError(),
        google_exceptions.DeadlineExceeded("uncertain"),
        google_exceptions.ServiceUnavailable("uncertain"),
        google_exceptions.Unknown("uncertain"),
        RuntimeError("unclassified add outcome"),
    ],
)
def test_transport_uncertainty_never_becomes_safe_to_retry(monkeypatch, error):
    request = AdminBootstrapRequest(uuid4(), uuid4(), "fictional-approval")
    session = SimpleNamespace(rollback=lambda: None, close=lambda: None)
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.bootstrap_first_admin",
        lambda *args, **kwargs: SimpleNamespace(
            temporary_pin="fictional-pin", expires_at=datetime(2026, 8, 13, tzinfo=UTC)
        ),
    )

    class Client:
        def add_version(self, **kwargs):
            raise error

    result = execute_admin_bootstrap(
        lambda: session,
        Client(),
        request=request,
        initial_admin_pin_secret="projects/fixture/secrets/initial-admin-pin",
        now=datetime(2026, 8, 13, tzinfo=UTC),
    )
    assert result.status == "pin_version_outcome_unknown_cleanup_required"
    assert result.secret_version_reference is None


def test_cli_emits_only_the_closed_four_field_result(monkeypatch, capsys):
    operation_id = uuid4()
    staff_id = uuid4()
    approval = "fictional-approval"
    request = AdminBootstrapRequest(operation_id, staff_id, approval)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture.invalid/test")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_REQUEST_BUCKET", "fixture-config")
    monkeypatch.setenv(
        "INITIAL_ADMIN_PIN_SECRET", "projects/fixture/secrets/initial-admin-pin"
    )
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.GoogleBootstrapRequestReader", lambda: object()
    )
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.GoogleSecretVersionAdder", lambda: object()
    )
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.load_bootstrap_request",
        lambda *args, **kwargs: request,
    )
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.create_engine",
        lambda *args, **kwargs: SimpleNamespace(dispose=lambda: None),
    )
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.sessionmaker", lambda **kwargs: object()
    )
    monkeypatch.setattr(
        "backend.jobs.admin_bootstrap.execute_admin_bootstrap",
        lambda *args, **kwargs: AdminBootstrapResult(
            operation_id,
            "bootstrapped",
            datetime(2026, 8, 14, tzinfo=UTC),
            "initial-admin-pin/versions/7",
        ),
    )
    assert (
        main(
            [
                "--request-uri",
                f"gs://fixture-config/admin-bootstrap-requests/{operation_id}.json",
                "--expected-sha256",
                "0" * 64,
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert set(json.loads(output)) == {
        "operation_id",
        "status",
        "expires_at",
        "secret_version_reference",
    }
    assert str(staff_id) not in output
    assert approval not in output
