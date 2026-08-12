import re


def normalize_employee_number(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise ValueError("employee number is required")
    if len(normalized) > 64 or not re.fullmatch(r"[A-Z0-9_-]+", normalized):
        raise ValueError("employee number is invalid")
    return normalized


def normalize_device_label(value: str) -> str:
    return " ".join(str(value or "").split())[:120]
