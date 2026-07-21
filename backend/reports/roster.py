"""Staff roster lookup — resolves partial officer names against the roster,
generating gaps for unidentifiable staff and filling in known details."""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROSTER_PATH = Path(__file__).parent.parent.parent / "templates" / "staff_roster.json"

_cache = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if not ROSTER_PATH.exists():
        logger.warning("Staff roster not found at %s — lookups will fail", ROSTER_PATH)
        _cache = {"shifts": {}, "staff": []}
        return _cache
    _cache = json.loads(ROSTER_PATH.read_text())
    return _cache


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

    return None


def resolve_staff_from_persons(persons: list[dict]) -> tuple[list[dict], list[dict]]:
    """Given a list of person dicts from extraction, resolve each against
    the roster. Returns (resolved_persons, gaps).

    A gap is generated for any security_staff person whose last name can't
    be matched in the roster, or who is missing required fields.
    """
    resolved = []
    gaps = []

    for p in persons:
        if p.get("role") != "security_staff":
            resolved.append(p)
            continue

        name = p.get("name", "") or ""
        last = p.get("last", "") or ""

        # Try last name first, then full name from the person dict
        match = lookup(last) or lookup(name)

        if match:
            # Fill in missing fields from roster
            merged = dict(p)
            merged.setdefault("rank", match.get("rank", ""))
            merged.setdefault("first", match.get("first", ""))
            merged.setdefault("last", match.get("last", ""))
            merged.setdefault("employee_number", match.get("employee_number", ""))
            merged.setdefault("shift", match.get("shift", ""))
            merged["_roster_match"] = True
            resolved.append(merged)
        else:
            # Could not identify — generate a gap
            resolved.append(p)
            gaps.append({
                "field": f"officer_{name or last or 'unknown'}",
                "label": f"Identify officer",
                "question": f"Could not find '{name or last or 'this officer'}' in staff roster. Enter their full name and employee number.",
                "required": True,
                "blocking": True,
                "type": "staff_identity",
            })

    # Also flag any resolved staff missing required fields
    required_staff_fields = ["rank", "first", "last"]
    for r in resolved:
        if r.get("role") == "security_staff":
            missing = [f for f in required_staff_fields if not r.get(f)]
            if missing:
                gaps.append({
                    "field": f"officer_{r.get('last', r.get('name', 'unknown'))}",
                    "label": f"Missing info for {r.get('last', r.get('name', '?'))}",
                    "question": f"Officer {r.get('last', r.get('name', '?'))} is missing: {', '.join(missing)}. Please provide.",
                    "required": True,
                    "blocking": True,
                    "type": "staff_missing_fields",
                })

    return resolved, gaps


def all_staff() -> list[dict]:
    """Return the full staff list."""
    return _load().get("staff", [])


def shifts() -> dict:
    """Return shift definitions."""
    return _load().get("shifts", {})
