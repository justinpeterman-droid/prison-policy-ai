"""Deterministic official incident-number and descriptive-name rules.

**Who owns the number.** The `YYYY-MM-NNN` here is the *unit log* number an
officer reads off the log book and types in; `incidents.incident_number` is
unique across the table because `NNN` is the month's log sequence. That is a
different thing from `reports.gap_answers.build_incident_number()`, which
composes a number for the legacy 005 form out of the officer's last three badge
digits. The legacy value is a convenience for a paper form with no uniqueness
constraint, and it repeats for the same officer twice in a month — so it must
never be fed into this column, which would 409 on the officer's second incident.
The two paths are deliberately separate; don't wire them together.
"""
import re


INCIDENT_NUMBER_RE = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>0[1-9]|1[0-2])-(?P<sequence>[0-9]{3})$"
)
INCIDENT_NAME_MAX_LENGTH = 160

#: Officer-assigned identity that survives revisions which do not mention it.
IDENTITY_FIELDS = ("incident_number", "incident_name")


def normalize_incident_number(value: str | None) -> str | None:
    """Normalize digit-only input and validate the official YYYY-MM-NNN shape."""
    if value is None or not value.strip():
        return None
    compact = value.strip()
    if compact.isdigit() and len(compact) == 9:
        compact = f"{compact[:4]}-{compact[4:6]}-{compact[6:]}"
    if not INCIDENT_NUMBER_RE.fullmatch(compact):
        raise ValueError("incident number must use YYYY-MM-NNN")
    return compact


def _clean_label(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def normalize_incident_name(value: str | None) -> str | None:
    """Collapse whitespace runs and trim, so one incident has one label."""
    cleaned = _clean_label(value)
    if cleaned is None:
        return None
    return cleaned[:INCIDENT_NAME_MAX_LENGTH].rstrip() or None


def carry_forward_identity(incident, payload: dict) -> dict:
    """Fill omitted identity fields in `payload` from the incident row.

    Official identity is assigned once and belongs to the incident, not to any
    one revision. An AI result or a partial save that never mentions the number
    must leave it standing rather than blank it, and the revision it writes has
    to record the identity that was actually in effect — otherwise restoring
    that revision later would erase the number.

    A `None` therefore means "this revision does not speak to identity", never
    "clear it". Clearing is not expressible on purpose: an incident that has
    been given a log number does not lose it by autosave.
    """
    for field in IDENTITY_FIELDS:
        if payload.get(field) is None:
            existing = getattr(incident, field, None)
            if existing is not None:
                payload[field] = existing
    return payload


def suggest_incident_name(
    *,
    location: str | None,
    category_label: str | None,
) -> str | None:
    """Build a short recognition label without inventing missing facts."""
    parts = [
        value
        for value in (_clean_label(location), _clean_label(category_label))
        if value
    ]
    if not parts:
        return None
    return " ".join(parts)[:INCIDENT_NAME_MAX_LENGTH].rstrip()
