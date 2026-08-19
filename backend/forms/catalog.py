"""Strict, sanitized catalog of forms available to incident paperwork packets."""
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models.forms import FormTemplate


CATALOG_SCHEMA_VERSION = 1
OUTPUT_KINDS = frozenset({"digital_document", "physical_only"})
RENDER_KINDS = frozenset({
    "docx_template",
    "generated_document",
    "report_document",
    "browser_form",
})
DOWNLOAD_FORMATS = frozenset({"print", "word", "pdf"})
SOURCE_REPORT_TYPES = frozenset({"cover_letter", "first_person"})
_ROOT_KEYS = frozenset({"schema_version", "forms"})
_FORM_KEYS = frozenset({
    "code",
    "name",
    "category",
    "output_kind",
    "revision_label",
    "active",
    "definition",
})
_DIGITAL_DEFINITION_KEYS = frozenset({
    "description",
    "render_kind",
    "template_path",
    "source_report_type",
    "download_formats",
    "required_fields",
    "review_fields",
    "optional_fields",
})
_PHYSICAL_DEFINITION_KEYS = frozenset({
    "description",
    "obtain_from",
    "guidance_fields",
})
_CODE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
_FIELD = re.compile(r"^[a-z][a-z0-9_]{1,79}$")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")


class CatalogConfigurationError(ValueError):
    """Raised when form catalog source data is unsafe or structurally invalid."""


@dataclass(frozen=True)
class FormTemplateDefinition:
    code: str
    name: str
    category: str
    output_kind: str
    revision_label: str | None
    active: bool
    definition: dict[str, object]


def _error(message: str) -> CatalogConfigurationError:
    return CatalogConfigurationError(message)


def _exact_keys(value: object, expected: frozenset[str], *, context: str) -> dict:
    if not isinstance(value, dict):
        raise _error(f"{context} must be an object")
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise _error(f"unknown {context} key: {sorted(unknown)[0]}")
    if missing:
        raise _error(f"missing {context} key: {sorted(missing)[0]}")
    return value


def _bounded_string(
    value: object,
    *,
    name: str,
    maximum: int,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise _error(f"{name} must be text")
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > maximum:
        raise _error(f"{name} must be 1 through {maximum} characters")
    if "@" in cleaned or _PHONE.search(cleaned):
        raise _error(f"{name} contains sensitive-looking literal data")
    return cleaned


def _identifier(value: object, *, name: str, pattern: re.Pattern[str]) -> str:
    cleaned = _bounded_string(value, name=name, maximum=80)
    assert isinstance(cleaned, str)
    if not pattern.fullmatch(cleaned):
        raise _error(f"{name} is invalid")
    return cleaned


def _field_list(value: object, *, name: str, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise _error(f"{name} must be a list")
    if len(value) > 100 or (not allow_empty and not value):
        raise _error(f"{name} has an invalid number of field names")
    fields: list[str] = []
    for item in value:
        fields.append(_identifier(item, name=name, pattern=_FIELD))
    if len(fields) != len(set(fields)):
        raise _error(f"{name} must contain unique field names")
    return fields


def _safe_template_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise _error("template_path must be a safe repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.parts[0] != "templates":
        raise _error("template_path must be a safe repository-relative path")
    if path.suffix.lower() not in {".docx", ".html"}:
        raise _error("template_path must point to a supported document template")
    return path.as_posix()


def _download_formats(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise _error("download_formats must be a nonempty list")
    if not all(isinstance(item, str) and item in DOWNLOAD_FORMATS for item in value):
        raise _error("download_formats contains an unsupported value")
    if len(value) != len(set(value)):
        raise _error("download_formats must contain unique values")
    return list(value)


def _digital_definition(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _error("digital definition must be an object")
    unknown = set(value) - _DIGITAL_DEFINITION_KEYS
    if unknown:
        raise _error(f"unknown digital definition key: {sorted(unknown)[0]}")
    required = {
        "description",
        "render_kind",
        "download_formats",
        "required_fields",
        "review_fields",
        "optional_fields",
    }
    missing = required - set(value)
    if missing:
        raise _error(f"missing digital definition key: {sorted(missing)[0]}")

    description = _bounded_string(
        value["description"], name="definition description", maximum=500)
    render_kind = _bounded_string(
        value["render_kind"], name="render_kind", maximum=40)
    if render_kind not in RENDER_KINDS:
        raise _error("render_kind is unsupported")

    definition: dict[str, object] = {
        "description": description,
        "render_kind": render_kind,
        "download_formats": _download_formats(value["download_formats"]),
        "required_fields": _field_list(
            value["required_fields"], name="required_fields"),
        "review_fields": _field_list(
            value["review_fields"], name="review_fields"),
        "optional_fields": _field_list(
            value["optional_fields"], name="optional_fields"),
    }
    field_memberships = [
        *definition["required_fields"],
        *definition["review_fields"],
        *definition["optional_fields"],
    ]
    if len(field_memberships) != len(set(field_memberships)):
        raise _error("form fields must belong to only one field group")

    template_path = value.get("template_path")
    if render_kind == "docx_template":
        if template_path is None:
            raise _error("docx_template requires template_path")
        definition["template_path"] = _safe_template_path(template_path)
    elif template_path is not None:
        definition["template_path"] = _safe_template_path(template_path)

    source_report_type = value.get("source_report_type")
    if render_kind == "report_document" and source_report_type is None:
        raise _error("report_document requires source_report_type")
    if source_report_type is not None:
        if source_report_type not in SOURCE_REPORT_TYPES:
            raise _error("source_report_type is unsupported")
        definition["source_report_type"] = source_report_type
    return definition


def _physical_definition(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _error("physical definition must be an object")
    unknown = set(value) - _PHYSICAL_DEFINITION_KEYS
    if unknown:
        raise _error(f"unknown physical definition key: {sorted(unknown)[0]}")
    missing = _PHYSICAL_DEFINITION_KEYS - set(value)
    if missing:
        raise _error(f"missing physical definition key: {sorted(missing)[0]}")
    return {
        "description": _bounded_string(
            value["description"], name="definition description", maximum=500),
        "obtain_from": _bounded_string(
            value["obtain_from"], name="obtain_from", maximum=200),
        "guidance_fields": _field_list(
            value["guidance_fields"],
            name="guidance_fields",
            allow_empty=False,
        ),
    }


def _definition(value: object, output_kind: str) -> dict[str, object]:
    if output_kind == "digital_document":
        return _digital_definition(value)
    return _physical_definition(value)


def _form_definition(value: object) -> FormTemplateDefinition:
    row = _exact_keys(value, _FORM_KEYS, context="form")
    code = _identifier(row["code"], name="form code", pattern=_CODE)
    category = _identifier(row["category"], name="form category", pattern=_CODE)
    output_kind = _bounded_string(
        row["output_kind"], name="output_kind", maximum=32)
    if output_kind not in OUTPUT_KINDS:
        raise _error("output_kind is unsupported")
    if not isinstance(row["active"], bool):
        raise _error("active must be a boolean")
    return FormTemplateDefinition(
        code=code,
        name=_bounded_string(row["name"], name="form name", maximum=200),
        category=category,
        output_kind=output_kind,
        revision_label=_bounded_string(
            row["revision_label"],
            name="revision_label",
            maximum=120,
            allow_none=True,
        ),
        active=row["active"],
        definition=_definition(row["definition"], output_kind),
    )


def load_form_catalog(path: str | Path) -> tuple[FormTemplateDefinition, ...]:
    """Load and fully validate a catalog before any row is synchronized."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _error("form catalog could not be read as UTF-8 JSON") from exc
    root = _exact_keys(payload, _ROOT_KEYS, context="root")
    if root["schema_version"] != CATALOG_SCHEMA_VERSION:
        raise _error("form catalog schema_version is unsupported")
    if not isinstance(root["forms"], list) or not root["forms"]:
        raise _error("form catalog forms must be a nonempty list")
    definitions = tuple(_form_definition(value) for value in root["forms"])
    codes = [definition.code for definition in definitions]
    if len(codes) != len(set(codes)):
        raise _error("duplicate form code in catalog")
    return definitions


def sync_form_catalog(
    session: Session,
    definitions: Iterable[FormTemplateDefinition],
    *,
    now: datetime | None = None,
) -> tuple[FormTemplate, ...]:
    """Create/update catalog rows and retire missing rows without deleting history."""
    timestamp = now or datetime.now(UTC)
    ordered = tuple(definitions)
    codes = [definition.code for definition in ordered]
    if len(codes) != len(set(codes)):
        raise _error("duplicate form code in synchronization input")

    existing = {
        row.code: row
        for row in session.scalars(select(FormTemplate)).all()
    }
    synced: list[FormTemplate] = []
    for definition in ordered:
        row = existing.get(definition.code)
        if row is None:
            row = FormTemplate(
                code=definition.code,
                name=definition.name,
                category=definition.category,
                output_kind=definition.output_kind,
                revision_label=definition.revision_label,
                active=definition.active,
                definition=dict(definition.definition),
                created_at=timestamp,
                updated_at=timestamp,
            )
            session.add(row)
        else:
            row.name = definition.name
            row.category = definition.category
            row.output_kind = definition.output_kind
            row.revision_label = definition.revision_label
            row.active = definition.active
            row.definition = dict(definition.definition)
            row.updated_at = timestamp
        synced.append(row)

    active_codes = set(codes)
    for code, row in existing.items():
        if code not in active_codes and row.active:
            row.active = False
            row.updated_at = timestamp
    return tuple(synced)
