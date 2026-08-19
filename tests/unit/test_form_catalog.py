"""Contracts for the sanitized incident paperwork catalog."""
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from backend.forms.catalog import (
    ALLOWED_OUTPUT_KINDS,
    FormCatalogError,
    FormTemplateDefinition,
    load_form_catalog,
    sync_form_catalog,
)
from backend.persistence.models.forms import FormTemplate


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"
EXPECTED_CODES = {
    "form_005_409",
    "cover_letter",
    "chain_of_custody_physical",
    "medical_documentation_checklist",
    "additional_officer_statement",
}


def _write_catalog(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"schema_version": 1, "forms": entries}), encoding="utf-8")
    return path


def _entry(**overrides) -> dict:
    value = {
        "code": "fictional_form",
        "name": "Fictional Form",
        "category": "incident",
        "output_kind": "digital_document",
        "revision_label": "fictional-v1",
        "active": True,
        "definition": {"renderer": "web_print", "required_fields": []},
    }
    value.update(overrides)
    return value


def test_repository_catalog_is_sanitized_and_complete():
    definitions = load_form_catalog(CATALOG_PATH)

    assert {item.code for item in definitions} == EXPECTED_CODES
    assert len({item.code for item in definitions}) == len(definitions)
    assert {item.output_kind for item in definitions} <= ALLOWED_OUTPUT_KINDS
    assert all(item.name.strip() and item.category.strip() for item in definitions)

    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(raw, sort_keys=True).lower()
    for forbidden in (
        "employee_number",
        "staff_roster",
        "phone_number",
        "signature_value",
        "historical_entry",
    ):
        assert forbidden not in serialized

    chain = next(item for item in definitions if item.code == "chain_of_custody_physical")
    assert chain.output_kind == "physical_only"
    assert chain.definition["obtain_from"] == "approved paperwork location"
    assert "template_path" not in chain.definition


def test_loader_rejects_unknown_keys_duplicates_and_invalid_output_kind(tmp_path):
    with pytest.raises(FormCatalogError, match="unknown catalog key"):
        load_form_catalog(_write_catalog(tmp_path, [_entry(unexpected=True)]))

    with pytest.raises(FormCatalogError, match="duplicate form code"):
        load_form_catalog(_write_catalog(tmp_path, [_entry(), _entry()]))

    with pytest.raises(FormCatalogError, match="output kind"):
        load_form_catalog(_write_catalog(
            tmp_path,
            [_entry(output_kind="print_anything")],
        ))


def test_loader_rejects_missing_names_and_unsafe_paths(tmp_path):
    with pytest.raises(FormCatalogError, match="name"):
        load_form_catalog(_write_catalog(tmp_path, [_entry(name="  ")]))

    for unsafe in ("../private.docx", "/etc/passwd", r"C:\\private\\form.docx"):
        with pytest.raises(FormCatalogError, match="unsafe path"):
            load_form_catalog(_write_catalog(
                tmp_path,
                [_entry(definition={"template_path": unsafe})],
            ))


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, existing):
        self.existing = list(existing)
        self.added = []
        self.flushed = False

    def scalars(self, _statement):
        return _ScalarRows(self.existing)

    def add(self, row):
        self.added.append(row)
        self.existing.append(row)

    def flush(self):
        self.flushed = True


def test_sync_updates_adds_and_deactivates_without_deleting_history():
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    existing = FormTemplate(
        code="fictional_form",
        name="Old Name",
        category="old",
        output_kind="digital_document",
        revision_label="old-v1",
        active=True,
        definition={},
        created_at=now,
        updated_at=now,
    )
    historical = FormTemplate(
        code="retired_form",
        name="Retired Form",
        category="incident",
        output_kind="digital_document",
        revision_label="retired-v1",
        active=True,
        definition={},
        created_at=now,
        updated_at=now,
    )
    session = _FakeSession([existing, historical])
    definitions = (
        FormTemplateDefinition(
            code="fictional_form",
            name="Current Name",
            category="incident",
            output_kind="physical_only",
            revision_label="current-v2",
            active=True,
            definition={"obtain_from": "approved paperwork location"},
        ),
        FormTemplateDefinition(
            code="new_form",
            name="New Form",
            category="incident",
            output_kind="digital_document",
            revision_label="new-v1",
            active=True,
            definition={"renderer": "web_print"},
        ),
    )

    synchronized = sync_form_catalog(session, definitions=definitions, now=now)

    assert session.flushed is True
    assert len(session.added) == 1
    assert {row.code for row in synchronized} == {"fictional_form", "new_form"}
    assert existing.name == "Current Name"
    assert existing.output_kind == "physical_only"
    assert existing.definition == {"obtain_from": "approved paperwork location"}
    assert historical.active is False
    assert historical in session.existing
