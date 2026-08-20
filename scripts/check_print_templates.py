"""Validate the sanitized weekly and monthly print-template definitions.

The check intentionally operates on JSON only. It is safe to run in CI and
does not load, render, or copy any source workbook.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EMPLOYEE_NUMBER = re.compile(r"\b[A-Z]{2,10}-\d{3,}\b")
HTML = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
FILLED_ENTRY_KEYS = {"entries", "log_entries", "completed_entries", "records"}


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON ({exc})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path}: template must be a JSON object")
        return None
    return value


def _scan_values(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FILLED_ENTRY_KEYS and child not in (None, "", [], {}):
                errors.append(f"{child_path}: nonblank log entry data is not allowed")
            _scan_values(child, child_path, errors)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _scan_values(child, f"{path}[{index}]", errors)
        return
    if not isinstance(value, str):
        return
    if HTML.search(value):
        errors.append(f"{path}: HTML is not allowed in a print template")
    if "../" in value or "..\\" in value:
        errors.append(f"{path}: path traversal is not allowed")
    if EMPLOYEE_NUMBER.search(value):
        errors.append(f"{path}: employee-number-like values are not allowed")


def check_print_templates(paperwork_root: Path | None = None) -> list[str]:
    """Return all definition-safety failures for the release-one catalogs."""
    root = paperwork_root or ROOT / "templates" / "paperwork"
    errors: list[str] = []
    catalogs: dict[str, dict[str, Any]] = {}

    for period in ("weekly", "monthly"):
        catalog_path = root / period / "catalog.json"
        catalog = _read_json(catalog_path, errors)
        if catalog is None:
            continue
        catalogs[period] = catalog
        if catalog.get("period") != period:
            errors.append(f"{catalog_path}: catalog period must be {period!r}")
        if not isinstance(catalog.get("templates"), list):
            errors.append(f"{catalog_path}: templates must be an array")

    weekly = catalogs.get("weekly", {})
    if weekly.get("templates") not in ([], None):
        errors.append("weekly catalog: release one must not publish invented weekly forms")

    monthly = catalogs.get("monthly", {})
    catalog_codes = monthly.get("templates", [])
    if isinstance(catalog_codes, list) and len(catalog_codes) != len(set(catalog_codes)):
        errors.append("monthly catalog: duplicate template code")

    definition_codes: set[str] = set()
    monthly_dir = root / "monthly"
    for definition_path in sorted(monthly_dir.glob("*.json")) if monthly_dir.is_dir() else []:
        if definition_path.name == "catalog.json":
            continue
        definition = _read_json(definition_path, errors)
        if definition is None:
            continue
        code = definition.get("code")
        if not isinstance(code, str) or not code:
            errors.append(f"{definition_path}: code is required")
        elif code in definition_codes:
            errors.append(f"{definition_path}: duplicate template code {code!r}")
        else:
            definition_codes.add(code)
        if definition.get("period") != "monthly":
            errors.append(f"{definition_path}: only monthly definitions are supported")
        if definition.get("page_size") != "letter":
            errors.append(f"{definition_path}: page_size must be 'letter'")
        if definition.get("orientation") != "landscape":
            errors.append(f"{definition_path}: orientation must be 'landscape'")
        _scan_values(definition, definition_path.name, errors)

    if isinstance(catalog_codes, list) and set(catalog_codes) != definition_codes:
        errors.append("monthly catalog: codes must match the checked-in definitions")
    return errors


def main() -> int:
    errors = check_print_templates()
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
