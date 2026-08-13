"""Pure helpers for folding reviewed gap answers into extracted slots."""

from copy import deepcopy
from datetime import datetime
import re


def build_incident_number(last3, incident_date=None) -> str:
    """Compose YYYY-MM-### from a three-digit log suffix and incident date."""
    digits = "".join(ch for ch in str(last3 or "") if ch.isdigit())[-3:]
    if not digits:
        return ""
    year, month = None, None
    if incident_date:
        match = re.match(r"(\d{4})[-/](\d{2})", str(incident_date))
        if match:
            year, month = match.group(1), match.group(2)
        else:
            match = re.match(r"(\d{2})[-/](\d{2})[-/](\d{4})", str(incident_date))
            if match:
                year, month = match.group(3), match.group(1)
    if year and month:
        return f"{year}-{month}-{digits.zfill(3)}"
    return f"{datetime.now():%Y-%m}-{digits.zfill(3)}"


def merge_gap_answers(slots: dict, answers: dict) -> dict:
    """Return copied slots with non-empty, string-keyed answers applied."""
    merged = deepcopy(slots or {})
    for key, value in (answers or {}).items():
        if isinstance(key, str) and value not in (None, ""):
            merged[key] = value
    return merged
