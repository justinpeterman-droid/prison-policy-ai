"""Pure helpers for folding reviewed gap answers into extracted slots."""
from copy import deepcopy


def merge_gap_answers(slots: dict, answers: dict) -> dict:
    """Return copied slots with non-empty, string-keyed answers applied."""
    merged = deepcopy(slots or {})
    for key, value in (answers or {}).items():
        if isinstance(key, str) and value not in (None, ""):
            merged[key] = value
    return merged
