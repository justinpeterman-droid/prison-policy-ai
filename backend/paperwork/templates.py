"""Sanitized, read-only definitions for weekly and monthly print paperwork."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Literal


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = ROOT / "templates" / "paperwork"
_ROOT_KEYS = {"code", "title", "period", "category", "schema_version", "page_size", "orientation", "definition"}
_CATALOG_KEYS = {"schema_version", "period", "templates"}
_HTML_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_EMPLOYEE_NUMBER_RE = re.compile(r"\b(?:ADC#\s*)?[0-9]{6,}\b", re.IGNORECASE)
_PATH_RE = re.compile(r"(?:^|[\\/])\.{1,2}(?:[\\/]|$)|^[A-Za-z]:[\\/]|^[/\\]")
_MONTH_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


class PrintTemplatePeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True)
class PrintTemplateDefinition:
    code: str
    title: str
    period: PrintTemplatePeriod
    category: str
    schema_version: int
    page_size: Literal["letter"]
    orientation: Literal["portrait", "landscape"]
    definition: dict[str, object]


def _walk(value: object):
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _validate_sanitized(value: object) -> None:
    for candidate in _walk(value):
        if not isinstance(candidate, str):
            continue
        if _HTML_RE.search(candidate):
            raise RuntimeError("print template contains HTML")
        if _EMPLOYEE_NUMBER_RE.search(candidate):
            raise RuntimeError("print template contains an employee number")
        if _PATH_RE.search(candidate):
            raise RuntimeError("print template contains a filesystem path")


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("print template definition is unreadable") from error


def _validate_catalog(raw: object, period: PrintTemplatePeriod) -> tuple[str, ...]:
    if not isinstance(raw, dict) or set(raw) != _CATALOG_KEYS:
        raise RuntimeError("print template catalog is invalid")
    if raw["schema_version"] != 1 or raw["period"] != period.value:
        raise RuntimeError("print template catalog is invalid")
    codes = raw["templates"]
    if not isinstance(codes, list) or any(not isinstance(code, str) for code in codes):
        raise RuntimeError("print template catalog is invalid")
    if len(codes) != len(set(codes)):
        raise RuntimeError("print template catalog contains duplicate codes")
    return tuple(codes)


def _definition_path(period: PrintTemplatePeriod, code: str) -> Path:
    filenames = {
        "monthly_windows_bars_doors": "windows_bars_doors",
        "monthly_chemical_agents": "chemical_agents",
        "monthly_contraband_standard": "contraband_search_standard",
        "monthly_contraband_expanded": "contraband_search_expanded",
    }
    filename = filenames.get(code, code.removeprefix(f"{period.value}_"))
    return TEMPLATE_ROOT / period.value / f"{filename}.json"


def _validate_definition(raw: object, period: PrintTemplatePeriod, code: str) -> PrintTemplateDefinition:
    if not isinstance(raw, dict) or set(raw) != _ROOT_KEYS:
        raise RuntimeError("print template root is invalid")
    if raw["code"] != code or raw["period"] != period.value:
        raise RuntimeError("print template does not match its catalog")
    if raw["schema_version"] != 1 or raw["page_size"] != "letter":
        raise RuntimeError("print template version or page size is unsupported")
    if raw["orientation"] not in {"portrait", "landscape"}:
        raise RuntimeError("print template orientation is unsupported")
    if not all(isinstance(raw[field], str) and raw[field].strip() for field in ("code", "title", "category")):
        raise RuntimeError("print template metadata is invalid")
    if not isinstance(raw["definition"], dict):
        raise RuntimeError("print template definition is invalid")
    fields = raw["definition"].get("prefill_fields", [])
    if not isinstance(fields, list) or not set(fields) <= ALLOWED_PREFILL_FIELDS or len(fields) != len(set(fields)):
        raise RuntimeError("print template prefill fields are invalid")
    _validate_sanitized(raw)
    return PrintTemplateDefinition(
        code=code,
        title=raw["title"],
        period=period,
        category=raw["category"],
        schema_version=1,
        page_size="letter",
        orientation=raw["orientation"],
        definition=deepcopy(raw["definition"]),
    )


ALLOWED_PREFILL_FIELDS = frozenset({"month", "shift", "shift_supervisor"})


@lru_cache(maxsize=1)
def _templates() -> tuple[PrintTemplateDefinition, ...]:
    definitions: list[PrintTemplateDefinition] = []
    seen: set[str] = set()
    for period in PrintTemplatePeriod:
        catalog = _validate_catalog(_read_json(TEMPLATE_ROOT / period.value / "catalog.json"), period)
        for code in catalog:
            if code in seen:
                raise RuntimeError("print template code is duplicated")
            seen.add(code)
            definitions.append(_validate_definition(_read_json(_definition_path(period, code)), period, code))
    return tuple(definitions)


def _copy(template: PrintTemplateDefinition) -> PrintTemplateDefinition:
    return PrintTemplateDefinition(
        code=template.code, title=template.title, period=template.period,
        category=template.category, schema_version=template.schema_version,
        page_size=template.page_size, orientation=template.orientation,
        definition=deepcopy(template.definition),
    )


def list_print_templates(period: PrintTemplatePeriod | str) -> tuple[PrintTemplateDefinition, ...]:
    """Return approved templates for one period in stable catalog order."""
    try:
        selected = period if isinstance(period, PrintTemplatePeriod) else PrintTemplatePeriod(period)
    except ValueError as error:
        raise KeyError(f"unknown print template period: {period}") from error
    return tuple(_copy(item) for item in _templates() if item.period is selected)


def load_print_template(code: str) -> PrintTemplateDefinition:
    """Return one approved template without exposing the cached definition."""
    for template in _templates():
        if template.code == code:
            return _copy(template)
    raise KeyError(f"unknown print template: {code}")


def validate_print_prefill(
    template: PrintTemplateDefinition,
    payload: dict[str, object],
) -> dict[str, object]:
    """Validate browser-local print prefill; no completed form content is accepted."""
    if not isinstance(payload, dict):
        raise ValueError("print prefill is invalid")
    allowed = set(template.definition.get("prefill_fields", []))
    if set(payload) - allowed:
        raise ValueError("print prefill contains an unsupported field")
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        if not isinstance(value, str):
            raise ValueError("print prefill is invalid")
        cleaned = " ".join(value.split())
        if key == "month":
            if not _MONTH_RE.fullmatch(cleaned):
                raise ValueError("print prefill month is invalid")
        elif key == "shift":
            if not 1 <= len(cleaned) <= 32:
                raise ValueError("print prefill shift is invalid")
        elif key == "shift_supervisor":
            if not 1 <= len(cleaned) <= 160:
                raise ValueError("print prefill supervisor is invalid")
        else:
            raise ValueError("print prefill contains an unsupported field")
        normalized[key] = cleaned
    return normalized
