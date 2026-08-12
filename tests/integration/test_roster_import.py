from sqlalchemy import select

from backend.identity.roster_import import import_roster
from backend.persistence.models import StaffMember


FICTIONAL_RECORDS = [
    {
        "rank": "Officer",
        "first": "Avery",
        "last": "Morgan",
        "employee_number": "EMP-9001",
        "shift": "A",
    }
]


def test_roster_import_is_idempotent_and_preserves_uuid(db_session):
    first = import_roster(db_session, FICTIONAL_RECORDS, apply=True)
    db_session.commit()
    original_id = db_session.scalar(select(StaffMember.id).where(
        StaffMember.employee_number == "EMP-9001"
    ))
    second = import_roster(db_session, FICTIONAL_RECORDS, apply=True)
    db_session.commit()
    current_id = db_session.scalar(select(StaffMember.id).where(
        StaffMember.employee_number == "EMP-9001"
    ))
    assert (first.inserted_count, first.existing_count) == (1, 0)
    assert (second.inserted_count, second.existing_count) == (0, 1)
    assert original_id == current_id
