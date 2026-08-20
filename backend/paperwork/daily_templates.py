"""Sanitized definitions for administrator daily operational paperwork."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
from typing import Literal


ROOT = Path(__file__).resolve().parents[2]
DAILY_TEMPLATE_DIR = ROOT / "templates" / "paperwork" / "daily"

_ROOT_KEYS = {"kind", "title", "schema_version", "print_orientation", "definition"}
_ALLOWED_ORIENTATIONS = {"portrait", "landscape"}
_HTML_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_EMPLOYEE_NUMBER_RE = re.compile(r"\bADC#\s*[0-9]{4,}\b", re.IGNORECASE)
_PATH_TRAVERSAL_RE = re.compile(
    r"(?:^|[\\/])\.{1,2}(?:[\\/]|$)|^[A-Za-z]:[\\/]|^[/\\]|[/\\]$"
)


class DailyPaperworkKind(str, Enum):
    ASSIGNMENT_ROSTER = "assignment_roster"
    UNIFORM_INSPECTION = "uniform_inspection"
    METAL_DETECTOR_TEST = "metal_detector_test"
    PERIMETER_CHECK = "perimeter_check"
    RANDOM_SEARCH_LOG = "random_search_log"
    DETECTOR_SIGN_OUT = "detector_sign_out"


DAILY_TEMPLATE_FILES = {
    DailyPaperworkKind.ASSIGNMENT_ROSTER: "assignment_roster.json",
    DailyPaperworkKind.UNIFORM_INSPECTION: "uniform_inspection.json",
    DailyPaperworkKind.METAL_DETECTOR_TEST: "metal_detector_test.json",
    DailyPaperworkKind.PERIMETER_CHECK: "perimeter_check.json",
    DailyPaperworkKind.RANDOM_SEARCH_LOG: "random_search_log.json",
    DailyPaperworkKind.DETECTOR_SIGN_OUT: "detector_sign_out.json",
}


@dataclass(frozen=True)
class DailyTemplateDefinition:
    kind: DailyPaperworkKind
    title: str
    schema_version: int
    print_orientation: Literal["portrait", "landscape"]
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


def _validate_strings(value: object) -> None:
    for candidate in _walk(value):
        if not isinstance(candidate, str):
            continue
        if _HTML_RE.search(candidate):
            raise RuntimeError("daily paperwork template contains HTML")
        if _EMPLOYEE_NUMBER_RE.search(candidate):
            raise RuntimeError("daily paperwork template contains an employee number")
        if _PATH_TRAVERSAL_RE.search(candidate):
            raise RuntimeError("daily paperwork template contains a filesystem path")


def _collect_codes(value: object, *, codes: list[str]) -> None:
    if isinstance(value, dict):
        code = value.get("code")
        if code is not None:
            if not isinstance(code, str) or not code.strip():
                raise RuntimeError("daily paperwork template code is invalid")
            codes.append(code)
        for child in value.values():
            _collect_codes(child, codes=codes)
    elif isinstance(value, list):
        for child in value:
            _collect_codes(child, codes=codes)


def _validate_definition(raw: object, expected_kind: DailyPaperworkKind) -> DailyTemplateDefinition:
    if not isinstance(raw, dict) or set(raw) != _ROOT_KEYS:
        raise RuntimeError("daily paperwork template root is invalid")

    if raw["kind"] != expected_kind.value:
        raise RuntimeError("daily paperwork template kind does not match its file")
    if raw["schema_version"] != 1:
        raise RuntimeError("daily paperwork template version is unsupported")
    if raw["print_orientation"] not in _ALLOWED_ORIENTATIONS:
        raise RuntimeError("daily paperwork template print orientation is unsupported")
    if not isinstance(raw["title"], str) or not raw["title"].strip():
        raise RuntimeError("daily paperwork template title is invalid")
    if not isinstance(raw["definition"], dict):
        raise RuntimeError("daily paperwork template definition is invalid")

    _validate_strings(raw)

    codes: list[str] = []
    _collect_codes(raw["definition"], codes=codes)
    if len(codes) != len(set(codes)):
        raise RuntimeError("daily paperwork template contains duplicate codes")

    return DailyTemplateDefinition(
        kind=expected_kind,
        title=raw["title"],
        schema_version=1,
        print_orientation=raw["print_orientation"],
        definition=json.loads(json.dumps(raw["definition"])),
    )


def load_daily_template(
    kind: DailyPaperworkKind | str,
) -> DailyTemplateDefinition:
    """Load and validate one immutable, sanitized daily paperwork definition."""
    try:
        normalized_kind = kind if isinstance(kind, DailyPaperworkKind) else DailyPaperworkKind(kind)
    except ValueError as exc:
        raise KeyError(f"unknown daily paperwork kind: {kind}") from exc

    filename = DAILY_TEMPLATE_FILES[normalized_kind]
    raw = json.loads((DAILY_TEMPLATE_DIR / filename).read_text(encoding="utf-8"))
    return _validate_definition(raw, normalized_kind)


def load_all_daily_templates() -> tuple[DailyTemplateDefinition, ...]:
    """Return every approved daily template in stable product order."""
    return tuple(load_daily_template(kind) for kind in DailyPaperworkKind)
