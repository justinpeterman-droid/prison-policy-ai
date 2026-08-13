from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

from google.api_core import exceptions as google_exceptions
from sqlalchemy import func, select

from backend.jobs.admin_bootstrap import (
    AdminBootstrapRequest,
    AdminBootstrapResult,
    execute_admin_bootstrap,
)
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.security import AuditEvent


NOW = datetime(2026, 8, 13, 15, 0, tzinfo=UTC)
SECRET = "projects/fixture/secrets/initial-admin-pin"


class SecretAdder:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def add_version(self, *, parent, payload):
        self.calls.append((parent, payload))
        if self.error is not None:
            raise self.error
        return f"{parent}/versions/7"


def _staff(factory, *, active=True):
    session = factory()
    row = StaffMember(
        employee_number=f"FX-{uuid4().hex[:8].upper()}",
        first_name="Avery",
        last_name="North",
        rank="Officer",
        shift="A",
        is_active=active,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(row)
    session.commit()
    staff_id = row.id
    session.close()
    return staff_id


def _request(staff_id):
    return AdminBootstrapRequest(uuid4(), staff_id, "fictional-approved-reference")


def _counts(factory):
    session = factory()
    try:
        return (
            session.scalar(select(func.count(Account.id))),
            session.scalar(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.action == "system.initial_admin_bootstrapped"
                )
            ),
        )
    finally:
        session.close()


def test_bootstrap_result_is_a_closed_safe_contract():
    assert set(AdminBootstrapResult.__annotations__) == {
        "operation_id",
        "status",
        "expires_at",
        "secret_version_reference",
    }


def test_active_staff_bootstraps_only_after_secret_version_returns(db_session_factory):
    staff_id = _staff(db_session_factory)
    secret = SecretAdder()
    result = execute_admin_bootstrap(
        db_session_factory,
        secret,
        request=_request(staff_id),
        initial_admin_pin_secret=SECRET,
        now=NOW,
    )
    assert result.status == "bootstrapped"
    assert result.secret_version_reference == "initial-admin-pin/versions/7"
    assert len(secret.calls) == 1
    assert _counts(db_session_factory) == (1, 1)


def test_missing_inactive_or_existing_account_refuses_without_secret_add(
    db_session_factory,
):
    for staff_id in (uuid4(), _staff(db_session_factory, active=False)):
        secret = SecretAdder()
        result = execute_admin_bootstrap(
            db_session_factory,
            secret,
            request=_request(staff_id),
            initial_admin_pin_secret=SECRET,
            now=NOW,
        )
        assert result.status == "bootstrap_refused"
        assert secret.calls == []

    active_id = _staff(db_session_factory)
    first = execute_admin_bootstrap(
        db_session_factory,
        SecretAdder(),
        request=_request(active_id),
        initial_admin_pin_secret=SECRET,
        now=NOW,
    )
    assert first.status == "bootstrapped"
    another_id = _staff(db_session_factory)
    secret = SecretAdder()
    refused = execute_admin_bootstrap(
        db_session_factory,
        secret,
        request=_request(another_id),
        initial_admin_pin_secret=SECRET,
        now=NOW,
    )
    assert refused.status == "bootstrap_refused"
    assert secret.calls == []


def test_secret_rejection_and_ambiguous_outcome_roll_back_account_and_audit(
    db_session_factory,
):
    for error, status in (
        (
            google_exceptions.InvalidArgument("definitive fixture rejection"),
            "pin_version_add_failed",
        ),
        (
            TimeoutError("ambiguous fixture timeout"),
            "pin_version_outcome_unknown_cleanup_required",
        ),
    ):
        staff_id = _staff(db_session_factory)
        secret = SecretAdder(error)
        result = execute_admin_bootstrap(
            db_session_factory,
            secret,
            request=_request(staff_id),
            initial_admin_pin_secret=SECRET,
            now=NOW,
        )
        assert result.status == status
        assert result.secret_version_reference is None
        assert len(secret.calls) == 1
        assert _counts(db_session_factory) == (0, 0)


def test_known_secret_version_and_commit_failure_returns_orphan_cleanup(
    db_session_factory,
):
    staff_id = _staff(db_session_factory)

    class CommitFailureSession:
        def __init__(self):
            self._session = db_session_factory()

        def __getattr__(self, name):
            return getattr(self._session, name)

        def commit(self):
            raise RuntimeError("fictional commit failure")

    result = execute_admin_bootstrap(
        CommitFailureSession,
        SecretAdder(),
        request=_request(staff_id),
        initial_admin_pin_secret=SECRET,
        now=NOW,
    )
    assert result.status == "orphan_pin_version_cleanup_required"
    assert result.secret_version_reference == "initial-admin-pin/versions/7"
    assert _counts(db_session_factory) == (0, 0)


def test_concurrent_attempts_create_exactly_one_admin(db_session_factory):
    staff_ids = (_staff(db_session_factory), _staff(db_session_factory))
    secrets = (SecretAdder(), SecretAdder())

    def attempt(index):
        return execute_admin_bootstrap(
            db_session_factory,
            secrets[index],
            request=_request(staff_ids[index]),
            initial_admin_pin_secret=SECRET,
            now=NOW,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, (0, 1)))
    assert sorted(result.status for result in results) == [
        "bootstrap_refused",
        "bootstrapped",
    ]
    assert sum(len(secret.calls) for secret in secrets) == 1
    assert _counts(db_session_factory) == (1, 1)
