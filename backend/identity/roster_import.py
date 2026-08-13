from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.normalization import normalize_employee_number
from backend.persistence.models.identity import StaffMember


REQUIRED_FIELDS = {"rank", "first", "last", "employee_number", "shift"}


@dataclass(frozen=True)
class RosterImportSummary:
    source_count: int
    inserted_count: int
    existing_count: int
    checksum: str
    applied: bool


def roster_checksum(records: list[dict]) -> str:
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _required_text(record: dict, field: str, maximum: int) -> str:
    value = str(record.get(field) or "").strip()
    if (
        not value
        or len(value) > maximum
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(f"roster {field} is invalid")
    return value


def _bounded_text(record: dict, field: str, maximum: int) -> str:
    value = str(record.get(field) or "").strip()
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise ValueError(f"roster {field} is invalid")
    return value


def _validate(records: list[dict]) -> list[dict[str, str]]:
    if not isinstance(records, list):
        raise ValueError("roster records must be a list")
    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != REQUIRED_FIELDS:
            raise ValueError("roster record fields are invalid")
        employee_number = normalize_employee_number(record["employee_number"])
        if employee_number in seen:
            raise ValueError("duplicate employee number")
        seen.add(employee_number)
        validated.append(
            {
                "employee_number": employee_number,
                "rank": _bounded_text(record, "rank", 64),
                "first_name": _required_text(record, "first", 100),
                "last_name": _required_text(record, "last", 100),
                "shift": _required_text(record, "shift", 16),
            }
        )
    return validated


def import_roster(
    session: Session,
    records: list[dict],
    apply: bool,
) -> RosterImportSummary:
    checksum = roster_checksum(records)
    validated = _validate(records)
    employee_numbers = [record["employee_number"] for record in validated]
    existing_rows = (
        list(
            session.scalars(
                select(StaffMember).where(
                    StaffMember.employee_number.in_(employee_numbers)
                )
            ).all()
        )
        if employee_numbers
        else []
    )
    existing = {row.employee_number: row for row in existing_rows}

    for record in validated:
        current = existing.get(record["employee_number"])
        if current is None:
            continue
        expected = (
            record["rank"],
            record["first_name"],
            record["last_name"],
            record["shift"],
        )
        actual = (current.rank, current.first_name, current.last_name, current.shift)
        if actual != expected:
            raise ValueError("roster conflict with existing staff data")

    absent = [
        record for record in validated if record["employee_number"] not in existing
    ]
    if apply and absent:
        session.add_all([StaffMember(**record, is_active=True) for record in absent])
        session.flush()
    return RosterImportSummary(
        source_count=len(validated),
        inserted_count=len(absent),
        existing_count=len(existing),
        checksum=checksum,
        applied=bool(apply),
    )
