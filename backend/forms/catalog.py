"""Strict, repository-safe loader and database synchronizer for form templates."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models.forms import FormTemplate


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"
ALLOWED_OUTPUT_KINDS = frozenset({"digital_document", "physical_only"})
_CATALOG_KEYS = frozenset({"schema_version", "forms"})
_FORM_KEYS = frozenset({
    "code",
    "name",
    "category",
    "output_kind",
    "revision_label",
    "active",
    "definition",
})
_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]" )


class FormCatalogError(ValueError):
    """The committed form catalog is invalid or unsafe to load."""


@dataclass(frozen=True)
class FormTemplateDefinition:
    code: str
    name: str
    category: str
    output_kind: str
    revision_label: str
    active: bool
    definition: Mapping[str, object]


def _required_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise FormCatalogError(f"{field} must be text")
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > maximum:
        raise FormCatalogError(f"{field} is missing or too long")
    return cleaned


def _unsafe_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        PurePosixPath(normalized).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or bool(_WINDOWS_ABSOLUTE_RE.match(value))
        or ".." in PurePosixPath(normalized).parts
    )


def _validate_definition(value: object, *, trail: tuple[str, ...] = ()) -> object:
    """Copy JSON data while rejecting path traversal and non-JSON shapes."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if any("path" in part.lower() for part in trail) and _unsafe_path(value):
            raise FormCatalogError(f"unsafe path in definition: {value!r}")
        return value
    if isinstance(value, list):
        if len(value) > 200:
            raise FormCatalogError("definition list is too large")
        return [
            _validate_definition(item, trail=(*trail, str(index)))
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        if len(value) > 100:
            raise FormCatalogError("definition object is too large")
        copied: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                raise FormCatalogError("definition keys must be short text")
            copied[key] = _validate_definition(item, trail=(*trail, key))
        return copied
    raise FormCatalogError("definition contains a non-JSON value")


def _parse_form(raw: object, *, position: int) -> FormTemplateDefinition:
    if not isinstance(raw, dict):
        raise FormCatalogError(f"form entry {position} must be an object")
    unknown = set(raw) - _FORM_KEYS
    if unknown:
        raise FormCatalogError(
            f"unknown catalog key in form entry {position}: {sorted(unknown)[0]}"
        )
    missing = _FORM_KEYS - set(raw)
    if missing:
        raise FormCatalogError(
            f"form entry {position} is missing {sorted(missing)[0]}"
        )

    code = _required_text(raw["code"], field="code", maximum=80)
    if not _CODE_RE.fullmatch(code):
        raise FormCatalogError("form code must use lowercase snake_case")
    name = _required_text(raw["name"], field="name", maximum=160)
    category = _required_text(raw["category"], field="category", maximum=64)
    if not _CATEGORY_RE.fullmatch(category):
        raise FormCatalogError("category must use lowercase snake_case")
    output_kind = _required_text(
        raw["output_kind"], field="output kind", maximum=40)
    if output_kind not in ALLOWED_OUTPUT_KINDS:
        raise FormCatalogError(f"unsupported output kind: {output_kind}")
    revision_label = _required_text(
        raw["revision_label"], field="revision label", maximum=120)
    active = raw["active"]
    if not isinstance(active, bool):
        raise FormCatalogError("active must be true or false")
    definition = _validate_definition(raw["definition"], trail=("definition",))
    if not isinstance(definition, dict):
        raise FormCatalogError("definition must be an object")

    if output_kind == "physical_only" and "template_path" in definition:
        raise FormCatalogError("physical-only forms cannot define a template path")

    return FormTemplateDefinition(
        code=code,
        name=name,
        category=category,
        output_kind=output_kind,
        revision_label=revision_label,
        active=active,
        definition=definition,
    )


def load_form_catalog(
    path: str | Path = DEFAULT_CATALOG_PATH,
) -> tuple[FormTemplateDefinition, ...]:
    """Load a closed, sanitized form catalog from JSON."""
    catalog_path = Path(path)
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FormCatalogError("form catalog could not be read") from error
    if not isinstance(raw, dict):
        raise FormCatalogError("form catalog must be an object")
    unknown = set(raw) - _CATALOG_KEYS
    if unknown:
        raise FormCatalogError(f"unknown catalog key: {sorted(unknown)[0]}")
    if set(raw) != _CATALOG_KEYS or raw.get("schema_version") != 1:
        raise FormCatalogError("form catalog schema version is unsupported")
    forms = raw.get("forms")
    if not isinstance(forms, list) or not forms:
        raise FormCatalogError("form catalog must contain forms")
    if len(forms) > 500:
        raise FormCatalogError("form catalog is too large")

    definitions = tuple(
        _parse_form(item, position=index)
        for index, item in enumerate(forms, start=1)
    )
    seen: set[str] = set()
    for definition in definitions:
        if definition.code in seen:
            raise FormCatalogError(f"duplicate form code: {definition.code}")
        seen.add(definition.code)
    return definitions


def sync_form_catalog(
    session: Session,
    *,
    definitions: Iterable[FormTemplateDefinition] | None = None,
    path: str | Path = DEFAULT_CATALOG_PATH,
    now: datetime | None = None,
) -> tuple[FormTemplate, ...]:
    """Upsert catalog rows and deactivate removed definitions without deleting history."""
    resolved = tuple(definitions) if definitions is not None else load_form_catalog(path)
    duplicate_codes = [item.code for item in resolved]
    if len(set(duplicate_codes)) != len(duplicate_codes):
        raise FormCatalogError("duplicate form code in synchronized definitions")
    timestamp = now or datetime.now(UTC)
    existing = {
        row.code: row
        for row in session.scalars(select(FormTemplate)).all()
    }
    synchronized: list[FormTemplate] = []

    for item in resolved:
        row = existing.pop(item.code, None)
        if row is None:
            row = FormTemplate(
                code=item.code,
                name=item.name,
                category=item.category,
                output_kind=item.output_kind,
                revision_label=item.revision_label,
                active=item.active,
                definition=dict(item.definition),
                created_at=timestamp,
                updated_at=timestamp,
            )
            session.add(row)
        else:
            row.name = item.name
            row.category = item.category
            row.output_kind = item.output_kind
            row.revision_label = item.revision_label
            row.active = item.active
            row.definition = dict(item.definition)
            row.updated_at = timestamp
        synchronized.append(row)

    for retired in existing.values():
        if retired.active:
            retired.active = False
            retired.updated_at = timestamp

    session.flush()
    return tuple(synchronized)
