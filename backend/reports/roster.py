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
        # First-name match
        if hint in first:
            return dict(person)
        # Partial employee number (e.g., "5123" matches "B5123")
        if hint in emp or emp.endswith(hint):
            return dict(person)

    return None


def _add_to_roster_file(rank: str, first: str, last: str,
                        employee_number: str, shift: str = "A") -> bool:
    """Persist a new staff member to the roster JSON file.

    Returns True if the entry was added, False if it already existed.
    """
    roster = _load()
    # Check for duplicate by employee number or last name
    for person in roster.get("staff", []):
        if (person.get("employee_number", "").lower() == employee_number.lower()
                or (person.get("last", "").lower() == last.lower()
                    and person.get("first", "").lower() == first.lower())):
            return False  # Already exists

    new_entry = {
        "rank": rank,
        "first": first,
        "last": last,
        "employee_number": employee_number,
        "shift": shift,
    }
    roster["staff"].append(new_entry)
    ROSTER_PATH.write_text(json.dumps(roster, indent=2) + "\n")
    # Bust cache so next lookup uses updated roster
    global _cache
    _cache = roster
    # Do not log names/employee numbers (PII / CodeQL clear-text-logging).
    logger.info("Added a new staff member to the roster (shift %s)", shift)
    return True


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
        r'\b(Sgt\.?|Sergeant)\b', r'\b(Cpl\.?|Corporal)\b',
        r'\b(Cpt\.?|Captain)\b', r'\b(Lt\.?|Lieutenant)\b',
        r'\b(Ofc\.?|Officer)\b', r'\b(Maj\.?|Major)\b',
        r'\b(Col\.?|Colonel)\b',
    ]
    for pat in RANK_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            rank_map = {
                "sergeant": "Sgt", "sgt": "Sgt", "sgt.": "Sgt",
                "corporal": "Cpl", "cpl": "Cpl", "cpl.": "Cpl",
                "captain": "Cpt", "cpt": "Cpt", "cpt.": "Cpt",
                "lieutenant": "Lt", "lt": "Lt", "lt.": "Lt",
                "officer": "Ofc", "ofc": "Ofc", "ofc.": "Ofc",
                "major": "Maj", "maj": "Maj", "maj.": "Maj",
                "colonel": "Col", "col": "Col", "col.": "Col",
            }
            rank = rank_map.get(m.group(1).lower().rstrip('.'), m.group(1))
            text = re.sub(pat, '', text, count=1, flags=re.I).strip()
            break

    # Try to extract employee number (digits at end or standalone digits)
    m = re.search(r'\b(\d{4,7})\b', text)
    if m:
        employee_number = m.group(1)
        text = re.sub(r'\b' + employee_number + r'\b', '', text).strip()

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
            gaps.append({
                "field": f"officer_identity_{name or last or 'unknown'}",
                "slot": f"officer_identity_{name or last or 'unknown'}",
                "label": f"Identify officer",
                "question": f"Could not find '{name or last or 'this officer'}' in staff roster. Enter their full name and employee number.",
                "required": True,
                "blocking": True,
                "type": "staff_identity",
                "answer_type": "text",
            })

    # Also flag any resolved staff missing required fields (after roster fill)
    required_staff_fields = ["rank", "first", "last"]
    for r in resolved:
        if r.get("role") == "security_staff" and not r.get("_roster_match"):
            missing = [f for f in required_staff_fields if not r.get(f)]
            if missing:
                name_key = r.get('last', r.get('name', 'unknown'))
                gaps.append({
                    "field": f"officer_fields_{name_key}",
                    "slot": f"officer_fields_{name_key}",
                    "label": f"Missing info for {r.get('last', r.get('name', '?'))}",
                    "question": f"Officer {r.get('last', r.get('name', '?'))} not found in roster and is missing: {', '.join(missing)}. Please provide.",
                    "required": True,
                    "blocking": True,
                    "type": "staff_missing_fields",
                    "answer_type": "text",
                })

    return resolved, gaps


def all_staff() -> list[dict]:
    """Return the full staff list."""
    return _load().get("staff", [])


def shifts() -> dict:
    """Return shift definitions."""
    return _load().get("shifts", {})
