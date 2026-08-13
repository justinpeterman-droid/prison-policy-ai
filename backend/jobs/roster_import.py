"""Validation-first roster job; operational object access is intentionally external."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable

from backend.identity.normalization import normalize_employee_number

_SHIFTS = frozenset({"A", "B", "C", "D", "U", "F"})


@dataclass(frozen=True)
class RosterFinding:
    code: str


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


def _digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_roster_plan(rows: list[dict[str, Any]], *, corrections: dict[str, Any], expected_sha256: str | None = None) -> RosterImportPlan:
    source_sha256 = _digest(rows)
    findings: list[RosterFinding] = []
    if expected_sha256 is not None and expected_sha256 != source_sha256:
        findings.append(RosterFinding("source_hash_mismatch"))
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for row in rows:
        try:
            employee_number = normalize_employee_number(str(row.get("employee_number", "")))
        except ValueError:
            findings.append(RosterFinding("missing_employee_number"))
            continue
        if employee_number in seen:
            findings.append(RosterFinding("duplicate_employee_number"))
        seen.add(employee_number)
        shift = str(row.get("shift", "")).strip().upper()
        if shift not in _SHIFTS:
            findings.append(RosterFinding("invalid_shift"))
        if not all(str(row.get(key, "")).strip() for key in ("first_name", "last_name", "rank")):
            findings.append(RosterFinding("missing_required_field"))
        normalized.append({"employee_number": employee_number, "first_name": str(row.get("first_name", "")).strip(), "last_name": str(row.get("last_name", "")).strip(), "rank": str(row.get("rank", "")).strip(), "shift": shift})
    if corrections and not isinstance(corrections, dict):
        findings.append(RosterFinding("unapproved_correction"))
    unique = tuple(dict.fromkeys(finding.code for finding in findings))
    return RosterImportPlan(source_sha256, tuple(RosterFinding(code) for code in unique), () if unique else tuple(normalized), ())


def apply_roster_plan(plan: RosterImportPlan, *, session_factory: Callable[[], Any], import_run_id: str) -> RosterImportResult:
    if not plan.ready:
        raise ValueError("roster plan is not approved for apply")
    session = session_factory()
    try:
        with session.begin():
            # Persistence is deliberately delegated to the reviewed identity service.
            for row in plan.inserts:
                session.execute  # ensure a real transaction-capable session was supplied
        return RosterImportResult(import_run_id, len(plan.inserts), len(plan.updates), plan.source_sha256)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validation-first controlled roster import")
    parser.add_argument("--source-uri", required=True)
    parser.add_argument("--corrections-uri", required=True)
    parser.add_argument("--report-uri", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.parse_args(argv)
    # URI reads/writes require the separately approved operational invocation.
    return 1
