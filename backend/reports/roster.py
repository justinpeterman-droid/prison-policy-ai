"""Staff roster lookup — resolves partial officer names against the roster,
generating gaps for unidentifiable staff and filling in known details."""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.reports import roster_store
from backend.persistence.models.identity import StaffMember

logger = logging.getLogger(__name__)

ROSTER_PATH = roster_store.SEED_PATH


class StaffProvider(Protocol):
    """Minimal route-neutral staff lookup used by report orchestration."""

    def lookup(self, name_hint: str) -> dict | None: ...

    def search(self, query: str, *, limit: int = 25) -> list[dict]: ...


@dataclass(frozen=True)
class StaffPage:
    items: list[dict]
    next_cursor: dict[str, str] | None


class FileStaffProvider:
    """Legacy roster adapter retained for the browser report routes."""

    def lookup(self, name_hint: str) -> dict | None:
        return lookup(name_hint)

    def search(self, query: str, *, limit: int = 25) -> list[dict]:
        hint = query.strip().lower()
        if not hint:
            return []
        matches = []
        for person in all_staff():
            values = (
                person.get("first", ""),
                person.get("last", ""),
                person.get("employee_number", ""),
            )
            if any(hint in str(value).lower() for value in values):
                matches.append(dict(person))
            if len(matches) >= limit:
                break
        return matches

    def add_from_gap_answer(self, name_hint: str, answer_text: str) -> bool:
        return add_staff_from_gap_answer(name_hint, answer_text)


class SqlStaffProvider:
    """Active-only Cloud SQL staff provider for Access/API report work."""

    def __init__(self, session: Session):
        self._session = session

    @staticmethod
    def _record(row: StaffMember) -> dict[str, object]:
        display_name = " ".join(value for value in (row.rank, row.first_name, row.last_name) if value)
        return {
            "staff_id": str(row.id),
            "employee_number": row.employee_number,
            "display_name": display_name,
            "rank": row.rank,
            "first": row.first_name,
            "last": row.last_name,
            "shift": row.shift,
            "is_active": row.is_active,
        }

    def search_page(
        self,
        query: str,
        *,
        limit: int = 25,
        cursor: dict[str, str] | None = None,
    ) -> StaffPage:
        hint = query.strip()
        if not hint or not 1 <= limit <= 50:
            return StaffPage([], None)
        escaped = hint.replace("%", "\\%").replace("_", "\\_")[:100]
        pattern = f"%{escaped}%"
        statement = select(StaffMember).where(
            StaffMember.is_active.is_(True),
            or_(
                StaffMember.employee_number.ilike(pattern, escape="\\"),
                StaffMember.first_name.ilike(pattern, escape="\\"),
                StaffMember.last_name.ilike(pattern, escape="\\"),
            ),
        )
        if cursor:
            created_at = datetime.fromisoformat(cursor["created_at"].replace("Z", "+00:00"))
            staff_id = UUID(cursor["id"])
            statement = statement.where(
                or_(
                    StaffMember.created_at > created_at,
                    and_(StaffMember.created_at == created_at, StaffMember.id > staff_id),
                )
            )
        rows = list(
            self._session.scalars(statement.order_by(StaffMember.created_at, StaffMember.id).limit(limit + 1)).all()
        )
        page_rows = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page_rows:
            last = page_rows[-1]
            next_cursor = {
                "created_at": last.created_at.isoformat(),
                "id": str(last.id),
            }
        return StaffPage([self._record(row) for row in page_rows], next_cursor)

    def search(self, query: str, *, limit: int = 25) -> list[dict]:
        return self.search_page(query, limit=limit).items

    def lookup(self, name_hint: str) -> dict | None:
        hint = name_hint.strip().lower()
        if not hint:
            return None
        for record in self.search(name_hint, limit=25):
            first = str(record.get("first", "")).lower()
            last = str(record.get("last", "")).lower()
            employee_number = str(record.get("employee_number", "")).lower()
            if (
                hint == last
                or hint == employee_number
                or hint == f"{first} {last}"
                or hint in last
                or hint in first
                or hint in employee_number
                or employee_number.endswith(hint)
            ):
                return record
        return None


def _load() -> dict:
    """The current roster. Backed by GCS when ROSTER_BUCKET is set, otherwise
    the packaged file — see backend/reports/roster_store.py."""
    return roster_store.read()


def lookup(name_hint: str) -> dict | None:
    """Try to match a name fragment against the staff roster.

    Matches by: last name (case-insensitive), employee number, or full name.
    Returns the full staff record or None if no match.
    """
    roster = _load()
    hint = name_hint.strip().lower()
    if not hint:
        return None

    for person in roster.get("staff", []):
        last = person.get("last", "").lower()
        first = person.get("first", "").lower()
        emp = person.get("employee_number", "").lower()
        full = f"{first} {last}"

        if hint == last or hint == emp.lower() or hint == full:
            return dict(person)
        # Partial: hint appears in last name or full name
        if hint in last or hint in full:
            return dict(person)
        # First-name match
        if hint in first:
            return dict(person)
        # Partial employee number (e.g., "5123" matches "B5123")
        if hint in emp or emp.endswith(hint):
            return dict(person)

    return None


def _add_to_roster_file(rank: str, first: str, last: str, employee_number: str, shift: str = "A") -> bool:
    """Persist a new staff member to the roster.

    Returns True if the entry was added, False if it already existed.
    """

    def mutate(roster: dict):
        # Re-checked on every attempt, not once up front: update() re-runs this
        # against a fresh copy after a write conflict, and by then the officer
        # we're adding may already be there because another request added them.
        for person in roster.get("staff", []):
            if person.get("employee_number", "").lower() == employee_number.lower() or (
                person.get("last", "").lower() == last.lower() and person.get("first", "").lower() == first.lower()
            ):
                return None  # Already exists — nothing to write

        roster.setdefault("staff", []).append(
            {
                "rank": rank,
                "first": first,
                "last": last,
                "employee_number": employee_number,
                "shift": shift,
            }
        )
        return True

    added = roster_store.update(mutate)
    if added:
        # Do not log names/employee numbers (PII / CodeQL clear-text-logging).
        logger.info("Added a new staff member to the roster (shift %s)", shift)
    return bool(added)


def add_staff_from_gap_answer(name_hint: str, answer_text: str) -> bool:
    """Parse a staff identity gap answer and persist to roster.

    Accepts answers like 'Sgt. Dana Halvorsen 100411' or 'Dana Halvorsen'.
    Returns True if successfully parsed and persisted.
    """
    text = answer_text.strip()
    if not text:
        return False

    # Try to parse: [Rank] First Last [EmployeeNumber]
    import re

    rank = ""
    employee_number = ""
    first = ""
    last = ""

    # Known rank patterns
    RANK_PATTERNS = [
        r"\b(Sgt\.?|Sergeant)\b",
        r"\b(Cpl\.?|Corporal)\b",
        r"\b(Cpt\.?|Captain)\b",
        r"\b(Lt\.?|Lieutenant)\b",
        r"\b(Ofc\.?|Officer)\b",
        r"\b(Maj\.?|Major)\b",
        r"\b(Col\.?|Colonel)\b",
    ]
    for pat in RANK_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            rank_map = {
                "sergeant": "Sgt",
                "sgt": "Sgt",
                "sgt.": "Sgt",
                "corporal": "Cpl",
                "cpl": "Cpl",
                "cpl.": "Cpl",
                "captain": "Cpt",
                "cpt": "Cpt",
                "cpt.": "Cpt",
                "lieutenant": "Lt",
                "lt": "Lt",
                "lt.": "Lt",
                "officer": "Ofc",
                "ofc": "Ofc",
                "ofc.": "Ofc",
                "major": "Maj",
                "maj": "Maj",
                "maj.": "Maj",
                "colonel": "Col",
                "col": "Col",
                "col.": "Col",
            }
            rank = rank_map.get(m.group(1).lower().rstrip("."), m.group(1))
            # The `\.?` in each pattern can never match: `\b` after a period
            # fails, since '.' and ' ' are both non-word characters. So "Sgt."
            # matches as "Sgt" and leaves the period behind, where it used to
            # be parsed as the officer's first name — every rank written the
            # normal way ("Sgt. Dana Halvorsen") produced first=".".
            text = re.sub(pat, "", text, count=1, flags=re.I).lstrip(". ").strip()
            break

    # Try to extract employee number (digits at end or standalone digits)
    m = re.search(r"\b(\d{4,7})\b", text)
    if m:
        employee_number = m.group(1)
        text = re.sub(r"\b" + employee_number + r"\b", "", text).strip()

    # Remaining text should be first [middle] last
    parts = text.split()
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
    elif len(parts) == 1:
        # Just a last name or first name — try lookup
        match = lookup(parts[0])
        if match:
            return False  # Already in roster
        # Can't determine — need at least first + last
        logger.warning("Could not parse a staff name from a gap answer")
        return False
    else:
        return False

    if not first or not last:
        return False

    # Title-case names
    first = first[0].upper() + first[1:].lower() if len(first) > 1 else first.upper()
    last = last[0].upper() + last[1:].lower() if len(last) > 1 else last.upper()

    if not rank:
        rank = "Ofc"  # Default rank

    return _add_to_roster_file(rank, first, last, employee_number)


def resolve_staff_from_persons(
    persons: list[dict],
    staff_provider: StaffProvider | None = None,
) -> tuple[list[dict], list[dict]]:
    """Given a list of person dicts from extraction, resolve each against
    the roster. Returns (resolved_persons, gaps).

    A gap is generated for any security_staff person whose last name can't
    be matched in the roster, or who is missing required fields.
    """
    provider = staff_provider or FileStaffProvider()
    resolved = []
    gaps = []

    for p in persons:
        if p.get("role") != "security_staff":
            resolved.append(p)
            continue

        name = p.get("name", "") or ""
        last = p.get("last", "") or ""

        # Try last name first, then full name from the person dict
        match = provider.lookup(last) or provider.lookup(name)

        if match:
            # Fill in missing fields from roster — override None values
            merged = dict(p)
            for key in ("rank", "first", "last", "employee_number", "shift"):
                if not merged.get(key):  # None, empty, or missing
                    merged[key] = match.get(key, "")
            merged["_roster_match"] = True
            resolved.append(merged)
        else:
            # Could not identify — generate a gap
            resolved.append(p)
            gaps.append(
                {
                    "field": f"officer_identity_{name or last or 'unknown'}",
                    "slot": f"officer_identity_{name or last or 'unknown'}",
                    "label": "Identify officer",
                    "question": f"Could not find '{name or last or 'this officer'}' in staff roster. Enter their full name and employee number.",
                    "required": True,
                    "blocking": True,
                    "type": "staff_identity",
                    "answer_type": "text",
                }
            )

    # Also flag any resolved staff missing required fields (after roster fill)
    required_staff_fields = ["rank", "first", "last"]
    for r in resolved:
        if r.get("role") == "security_staff" and not r.get("_roster_match"):
            missing = [f for f in required_staff_fields if not r.get(f)]
            if missing:
                name_key = r.get("last", r.get("name", "unknown"))
                gaps.append(
                    {
                        "field": f"officer_fields_{name_key}",
                        "slot": f"officer_fields_{name_key}",
                        "label": f"Missing info for {r.get('last', r.get('name', '?'))}",
                        "question": f"Officer {r.get('last', r.get('name', '?'))} not found in roster and is missing: {', '.join(missing)}. Please provide.",
                        "required": True,
                        "blocking": True,
                        "type": "staff_missing_fields",
                        "answer_type": "text",
                    }
                )

    return resolved, gaps


def all_staff() -> list[dict]:
    """Return the full staff list."""
    return _load().get("staff", [])


def shifts() -> dict:
    """Return shift definitions."""
    return _load().get("shifts", {})
