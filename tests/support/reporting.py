from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from backend.identity.pins import hash_pin
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
    ReportRevision,
    ReportType,
)


@dataclass(frozen=True)
class FictionalStaffAndAccounts:
    user: Account
    preparer: Account
    unrelated: Account
    admin: Account


@dataclass(frozen=True)
class FictionalStaff:
    alex: StaffMember
    blair: StaffMember


def _account(
    session, *, employee_number: str, first_name: str, role: str, shift: str,
    now: datetime,
) -> Account:
    staff = StaffMember(
        employee_number=employee_number, rank="Officer", first_name=first_name,
        last_name="Example", shift=shift, is_active=True, created_at=now,
        updated_at=now,
    )
    session.add(staff)
    session.flush()
    account = Account(
        staff_member_id=staff.id, role=role, status="active",
        pin_hash=hash_pin("Q7W9E2"), must_change_pin=False,
        failed_attempts=0, lock_cycle=0, auth_version=1,
        created_at=now, updated_at=now,
    )
    account.staff_member = staff
    session.add(account)
    session.flush()
    return account


def seed_fictional_staff_and_accounts(
    session, now: datetime | None = None,
) -> FictionalStaffAndAccounts:
    fixed = now or datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    return FictionalStaffAndAccounts(
        user=_account(
            session, employee_number="TEST-2101", first_name="Alex",
            role="user", shift="A", now=fixed,
        ),
        preparer=_account(
            session, employee_number="TEST-2102", first_name="Blair",
            role="user", shift="B", now=fixed,
        ),
        unrelated=_account(
            session, employee_number="TEST-2103", first_name="Casey",
            role="user", shift="C", now=fixed,
        ),
        admin=_account(
            session, employee_number="TEST-9101", first_name="Drew",
            role="admin", shift="D", now=fixed,
        ),
    )


def fictional_report_content(narrative: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "narrative": narrative,
        "editable_fields": {},
        "validation": {},
        "warnings": [],
    }


def make_incident(
    session,
    account: Account,
    now: datetime | None = None,
    *,
    reporting_staff_ids: tuple[UUID, ...] | None = None,
    incident_id: UUID | None = None,
) -> Incident:
    fixed = now or datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    snapshot: dict[str, object] = {
        "schema_version": 1,
        "field_notes": "Fictional field notes for persistence tests.",
    }
    if reporting_staff_ids is not None:
        snapshot["server_metadata"] = {
            "reporting_staff_ids": [str(staff_id) for staff_id in reporting_staff_ids],
        }
    incident = Incident(
        **({"id": incident_id} if incident_id is not None else {}),
        created_by_account_id=account.id,
        created_by_staff_member_id=account.staff_member_id,
        status="in_progress", current_revision_number=1,
        facility="Fictional Unit", shift="A", location="Example Dayroom",
        category="fictional_incident",
        field_notes="Fictional field notes for persistence tests.",
        classification={}, extracted_facts={}, gap_answers={}, charges=[],
        validation={}, created_at=fixed, updated_at=fixed,
    )
    session.add(incident)
    session.flush()
    session.add(IncidentRevision(
        incident_id=incident.id, revision_number=1,
        editor_account_id=account.id,
        editor_staff_member_id=account.staff_member_id,
        snapshot=snapshot,
        changed_fields={"fields": ["field_notes"]}, reason="manual_save",
        client_version="1.0.0", request_id="request_fixture_incident_1",
        created_at=fixed,
    ))
    session.flush()
    return incident


def make_report(
    session, *, incident: Incident, owner: Account, preparer: Account,
    now: datetime | None = None, report_id: UUID | None = None,
) -> Report:
    fixed = now or datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    content = fictional_report_content("Fictional initial report narrative.")
    report = Report(
        **({"id": report_id} if report_id is not None else {}),
        incident_id=incident.id, report_type=ReportType.FIRST_PERSON,
        reporting_staff_member_id=owner.staff_member_id,
        prepared_by_staff_member_id=preparer.staff_member_id,
        created_by_account_id=preparer.id, status="in_progress",
        current_revision_number=1, current_content=content,
        created_at=fixed, updated_at=fixed,
    )
    session.add(report)
    session.flush()
    relationships = [(owner.staff_member_id, "owner")]
    if preparer.staff_member_id != owner.staff_member_id:
        relationships.append((preparer.staff_member_id, "preparer"))
    session.add_all([
        ReportAccess(
            report_id=report.id, staff_member_id=staff_id,
            relationship=relationship, granted_by_account_id=preparer.id,
            created_at=fixed,
        )
        for staff_id, relationship in relationships
    ])
    session.add(ReportRevision(
        report_id=report.id, revision_number=1,
        editor_account_id=preparer.id,
        editor_staff_member_id=preparer.staff_member_id,
        snapshot=content, changed_fields={"fields": ["narrative"]},
        reason="manual_save", provenance={}, client_version="1.0.0",
        request_id="request_fixture_report_1", created_at=fixed,
    ))
    session.flush()
    return report
