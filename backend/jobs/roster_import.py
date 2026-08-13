"""Validation-first, hash-bound roster import job."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
import re
from typing import Any, Callable, Iterable, Protocol
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.identity.normalization import normalize_employee_number
from backend.identity.roster_import import import_roster
from backend.persistence.models.identity import StaffMember

_SHIFTS = frozenset({"A", "B", "C", "D", "U", "F"})
_ROW_KEYS = frozenset({"employee_number", "first_name", "last_name", "rank", "shift"})


class PrivateObjectStore(Protocol):
    def read(self, uri: str, *, max_bytes: int) -> bytes: ...

    def write(self, uri: str, payload: bytes) -> None: ...


class GooglePrivateObjectStore:
    """Bounded GCS adapter constructed only by an invoked operational CLI."""

    def __init__(self, client=None):
        if client is None:
            from google.cloud.storage import Client

            client = Client()
        self._client = client

    @staticmethod
    def _location(uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        object_name = parsed.path.lstrip("/")
        if parsed.scheme != "gs" or not parsed.netloc or not object_name or parsed.query or parsed.fragment:
            raise ValueError("private object URI is invalid")
        return parsed.netloc, object_name

    def read(self, uri: str, *, max_bytes: int) -> bytes:
        bucket, object_name = self._location(uri)
        payload = self._client.bucket(bucket).blob(object_name).download_as_bytes(start=0, end=max_bytes)
        if len(payload) > max_bytes:
            raise ValueError("private object exceeds maximum size")
        return payload

    def write(self, uri: str, payload: bytes) -> None:
        bucket, object_name = self._location(uri)
        self._client.bucket(bucket).blob(object_name).upload_from_string(
            payload, content_type="application/json", if_generation_match=0
        )


@dataclass(frozen=True)
class RosterFinding:
    code: str
    row_number: int | None = None


@dataclass(frozen=True)
class RosterImportPlan:
    source_sha256: str
    findings: tuple[RosterFinding, ...]
    inserts: tuple[dict[str, str], ...]
    updates: tuple[dict[str, str], ...]

    @property
    def ready(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class RosterImportResult:
    import_run_id: str
    inserted_count: int
    updated_count: int
    source_sha256: str


def _canonical_bytes(rows: list[dict[str, Any]]) -> bytes:
    return json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _text(row: dict[str, Any], key: str, maximum: int) -> str | None:
    value = row.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > maximum or any(ord(character) < 32 for character in value):
        return None
    return value


def _existing_values(staff: object) -> dict[str, str]:
    return {
        "staff_member_id": str(getattr(staff, "id")),
        "employee_number": normalize_employee_number(getattr(staff, "employee_number")),
        "first_name": str(getattr(staff, "first_name")),
        "last_name": str(getattr(staff, "last_name")),
        "rank": str(getattr(staff, "rank")),
        "shift": str(getattr(staff, "shift")),
    }


def _approved_target(corrections: dict[str, Any], employee_number: str) -> UUID | None:
    correction = corrections.get(employee_number)
    if correction is None:
        return None
    if (
        not isinstance(correction, dict)
        or set(correction) != {"staff_member_id", "approved"}
        or correction.get("approved") is not True
    ):
        raise ValueError("correction is not approved")
    target = UUID(str(correction["staff_member_id"]))
    if target.version != 4:
        raise ValueError("correction is not approved")
    return target


def build_roster_plan(
    rows: list[dict[str, Any]],
    *,
    corrections: dict[str, Any],
    expected_sha256: str | None = None,
    source_bytes: bytes | None = None,
    existing_staff: Iterable[object] = (),
) -> RosterImportPlan:
    exact_bytes = source_bytes if source_bytes is not None else _canonical_bytes(rows)
    source_sha256 = hashlib.sha256(exact_bytes).hexdigest()
    findings: list[RosterFinding] = []
    if expected_sha256 is not None and (
        not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or expected_sha256 != source_sha256
    ):
        findings.append(RosterFinding("source_hash_mismatch"))
    if not isinstance(rows, list) or not isinstance(corrections, dict):
        return RosterImportPlan(source_sha256, (RosterFinding("invalid_source_schema"),), (), ())

    existing = [_existing_values(row) for row in existing_staff]
    by_employee = {row["employee_number"]: row for row in existing}
    by_id = {UUID(row["staff_member_id"]): row for row in existing}
    by_name: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in existing:
        key = (row["first_name"].casefold(), row["last_name"].casefold())
        by_name.setdefault(key, []).append(row)

    seen: set[str] = set()
    normalized_rows: list[tuple[int, dict[str, str]]] = []
    used_corrections: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != _ROW_KEYS:
            findings.append(RosterFinding("invalid_source_schema", row_number))
            continue
        try:
            employee_number = normalize_employee_number(row["employee_number"])
        except (TypeError, ValueError):
            findings.append(RosterFinding("missing_employee_number", row_number))
            continue
        if employee_number in seen:
            findings.append(RosterFinding("duplicate_employee_number", row_number))
        seen.add(employee_number)
        first_name = _text(row, "first_name", 100)
        last_name = _text(row, "last_name", 100)
        rank = _text(row, "rank", 64)
        shift = _text(row, "shift", 1)
        if shift is None:
            findings.append(RosterFinding("invalid_shift", row_number))
            if first_name is None or last_name is None or rank is None:
                findings.append(RosterFinding("missing_required_field", row_number))
            continue
        if shift not in _SHIFTS:
            findings.append(RosterFinding("invalid_shift", row_number))
        if first_name is None or last_name is None or rank is None:
            findings.append(RosterFinding("missing_required_field", row_number))
            continue
        values: dict[str, str] = {
            "employee_number": employee_number,
            "first_name": first_name,
            "last_name": last_name,
            "rank": rank,
            "shift": shift,
        }
        normalized_rows.append((row_number, values))

    inserts: list[dict[str, str]] = []
    updates: list[dict[str, str]] = []
    for row_number, row in normalized_rows:
        current = by_employee.get(row["employee_number"])
        name_matches = by_name.get((row["first_name"].casefold(), row["last_name"].casefold()), [])
        try:
            approved_id = _approved_target(corrections, row["employee_number"])
        except (KeyError, TypeError, ValueError):
            findings.append(RosterFinding("unapproved_correction", row_number))
            continue
        if approved_id is not None:
            used_corrections.add(row["employee_number"])
            target = by_id.get(approved_id)
            if target is None or (current is not None and current is not target):
                findings.append(RosterFinding("ambiguous_mapping", row_number))
                continue
            current = target
        elif current is None and len(name_matches) > 1:
            findings.append(RosterFinding("ambiguous_mapping", row_number))
            continue
        elif current is None and len(name_matches) == 1:
            findings.append(RosterFinding("unapproved_correction", row_number))
            continue

        if current is None:
            inserts.append(row)
            continue
        comparable = {key: current[key] for key in _ROW_KEYS}
        if comparable != row:
            if approved_id is None:
                findings.append(RosterFinding("unapproved_correction", row_number))
            else:
                updates.append({"staff_member_id": current["staff_member_id"], **row})

    if set(corrections) != used_corrections:
        findings.append(RosterFinding("unapproved_correction"))
    unique_findings = tuple(dict.fromkeys((finding.code, finding.row_number) for finding in findings))
    closed_findings = tuple(RosterFinding(*finding) for finding in unique_findings)
    if closed_findings:
        inserts = []
        updates = []
    return RosterImportPlan(source_sha256, closed_findings, tuple(inserts), tuple(updates))


def apply_roster_plan(
    plan: RosterImportPlan,
    *,
    session_factory: Callable[[], Session],
    import_run_id: str,
    source_bytes: bytes | None = None,
) -> RosterImportResult:
    if not plan.ready:
        raise ValueError("roster plan is not approved for apply")
    if source_bytes is not None and hashlib.sha256(source_bytes).hexdigest() != plan.source_sha256:
        raise ValueError("approved source hash changed before apply")
    UUID(import_run_id)
    session = session_factory()
    try:
        with session.begin():
            if plan.inserts:
                service_rows = [
                    {
                        "employee_number": row["employee_number"],
                        "first": row["first_name"],
                        "last": row["last_name"],
                        "rank": row["rank"],
                        "shift": row["shift"],
                    }
                    for row in plan.inserts
                ]
                import_roster(session, service_rows, apply=True)
            for update in plan.updates:
                staff_id = UUID(update["staff_member_id"])
                staff = session.scalar(select(StaffMember).where(StaffMember.id == staff_id).with_for_update())
                if staff is None:
                    raise ValueError("approved roster mapping changed before apply")
                for key in _ROW_KEYS:
                    setattr(staff, key, update[key])
                staff.updated_at = datetime.now(UTC)
            session.flush()
        return RosterImportResult(
            import_run_id,
            len(plan.inserts),
            len(plan.updates),
            plan.source_sha256,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _decode_source(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload)
    rows = data.get("staff") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("roster source schema is invalid")
    return rows


def _current_migration_revision(session: Session) -> str:
    revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-z_]{1,64}", revision):
        raise RuntimeError("migration revision is invalid")
    return revision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validation-first controlled roster import")
    parser.add_argument("--source-uri", required=True)
    parser.add_argument("--corrections-uri", required=True)
    parser.add_argument("--report-uri", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return 1

    store = GooglePrivateObjectStore()
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=utc"},
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    import_run_id = str(uuid4())
    try:
        source_bytes = store.read(args.source_uri, max_bytes=5 * 1024 * 1024)
        corrections_bytes = store.read(args.corrections_uri, max_bytes=1024 * 1024)
        corrections = json.loads(corrections_bytes)
        rows = _decode_source(source_bytes)
        session = factory()
        try:
            existing = list(session.scalars(select(StaffMember)).all())
            migration_revision = _current_migration_revision(session)
        finally:
            session.close()
        plan = build_roster_plan(
            rows,
            corrections=corrections,
            expected_sha256=args.expected_sha256,
            source_bytes=source_bytes,
            existing_staff=existing,
        )
        report = {
            "import_run_id": import_run_id,
            "source_sha256": plan.source_sha256,
            "findings": [asdict(finding) for finding in plan.findings],
            "migration_revision": migration_revision,
        }
        store.write(
            args.report_uri,
            json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        result = None
        if args.apply and plan.ready:
            result = apply_roster_plan(
                plan,
                session_factory=factory,
                import_run_id=import_run_id,
                source_bytes=source_bytes,
            )
        safe = {
            "status": "applied" if result else "validated" if plan.ready else "refused",
            "source_sha256": plan.source_sha256,
            "import_run_id": import_run_id,
            "migration_revision": migration_revision,
            "finding_codes": sorted({finding.code for finding in plan.findings}),
            "inserted_count": result.inserted_count if result else 0,
            "updated_count": result.updated_count if result else 0,
        }
        print(json.dumps(safe, sort_keys=True, separators=(",", ":")))
        return 0 if plan.ready else 1
    except Exception:
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
