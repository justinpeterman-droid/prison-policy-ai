"""Deterministic official incident-number and descriptive-name rules."""
import re


INCIDENT_NUMBER_RE = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>0[1-9]|1[0-2])-(?P<sequence>[0-9]{3})$"
)
INCIDENT_NAME_MAX_LENGTH = 160


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
