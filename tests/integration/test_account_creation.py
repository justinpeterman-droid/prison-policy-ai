from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from backend.identity.accounts import (
    InitialAdminBootstrapRefused,
    bootstrap_first_admin,
    create_account,
)
from backend.persistence.models import Account, StaffMember


class RecordingAuditWriter:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)
        return uuid4()


class FailingAuditWriter:
    def append(self, _session, _event):
        raise RuntimeError("audit insert failed")


def test_bootstrap_creates_only_one_admin(db_session):
    db_session.execute(delete(Account))
    staff = StaffMember(
        employee_number="EMP-9901",
        rank="Officer",
        first_name="Avery",
        last_name="Morgan",
        shift="A",
        is_active=True,
    )
    db_session.add(staff)
    db_session.flush()
    audit = RecordingAuditWriter()
    result = bootstrap_first_admin(
        db_session,
        staff_member_id=staff.id,
        now=datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
        audit_writer=audit,
        operation_id=uuid4(),
        approval_reference_sha256="a" * 64,
    )
    stored = db_session.get(Account, result.account_id)
    assert stored.role == "admin" and stored.must_change_pin is True
    assert result.temporary_pin not in stored.pin_hash
    assert not hasattr(stored, "temporary_pin")
    assert audit.events[-1].action == "system.initial_admin_bootstrapped"
    with pytest.raises(InitialAdminBootstrapRefused):
        bootstrap_first_admin(
            db_session,
            staff_member_id=staff.id,
            now=datetime(2026, 8, 12, 15, 1, tzinfo=UTC),
            audit_writer=audit,
            operation_id=uuid4(),
            approval_reference_sha256="b" * 64,
        )


def test_account_creation_rolls_back_when_audit_fails(db_session_factory):
    with db_session_factory.begin() as session:
        staff = StaffMember(
            employee_number="EMP-9902",
            rank="Officer",
            first_name="Jordan",
            last_name="Lee",
            shift="B",
            is_active=True,
        )
        session.add(staff)
        session.flush()
        staff_id = staff.id
    try:
        with pytest.raises(RuntimeError, match="audit insert failed"):
            with db_session_factory.begin() as session:
                create_account(
                    session,
                    session.get(StaffMember, staff_id),
                    "user",
                    datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
                    FailingAuditWriter(),
                    "request-create-rollback",
                    uuid4(),
                    uuid4(),
                )
        with db_session_factory() as session:
            assert (
                session.scalar(
                    select(func.count(Account.id)).where(
                        Account.staff_member_id == staff_id
                    )
                )
                == 0
            )
    finally:
        with db_session_factory.begin() as session:
            session.execute(delete(StaffMember).where(StaffMember.id == staff_id))


def test_bootstrap_advisory_lock_allows_exactly_one_concurrent_success(
    db_session_factory,
):
    with db_session_factory.begin() as session:
        session.execute(delete(Account))
        staff_rows = [
            StaffMember(
                employee_number=f"EMP-991{index}",
                rank="Officer",
                first_name="Casey",
                last_name=f"Tester{index}",
                shift="A",
                is_active=True,
            )
            for index in (1, 2)
        ]
        session.add_all(staff_rows)
        session.flush()
        staff_ids = [row.id for row in staff_rows]

    barrier = Barrier(2)

    def attempt(staff_id, approval_character):
        try:
            with db_session_factory.begin() as session:
                barrier.wait(timeout=10)
                bootstrap_first_admin(
                    session,
                    staff_member_id=staff_id,
                    now=datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
                    audit_writer=RecordingAuditWriter(),
                    operation_id=uuid4(),
                    approval_reference_sha256=approval_character * 64,
                )
            return "success"
        except InitialAdminBootstrapRefused:
            return "refused"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, staff_ids, ("c", "d")))
        assert sorted(outcomes) == ["refused", "success"]
        with db_session_factory() as session:
            assert session.scalar(select(func.count(Account.id))) == 1
    finally:
        with db_session_factory.begin() as session:
            session.execute(delete(Account))
            session.execute(delete(StaffMember).where(StaffMember.id.in_(staff_ids)))
