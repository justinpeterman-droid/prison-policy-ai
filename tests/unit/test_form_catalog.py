"""Contracts for the sanitized incident paperwork catalog."""
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from backend.forms.catalog import (
    CatalogConfigurationError,
    FormTemplateDefinition,
    load_form_catalog,
    sync_form_catalog,
)
from backend.persistence.models.forms import FormTemplate


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "templates" / "paperwork" / "catalog.json"
EXPECTED_CODES = {
    "form_005_409",
    "cover_letter",
    "chain_of_custody_physical",
    "medical_documentation_checklist",
    "additional_officer_statement",
}


def _write_catalog(tmp_path: Path, forms: list[dict], **extra_root) -> Path:
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps({"schema_version": 1, "forms": forms, **extra_root}),
        encoding="utf-8",
    )
    return path


def _digital(code: str = "fictional_form") -> dict:
    return {
        "code": code,
        "name": "Fictional Incident Form",
        "category": "incident",
        "output_kind": "digital_document",
        "revision_label": "fictional-v1",
        "active": True,
        "definition": {
            "description": "A fictional form used only by automated tests.",
            "render_kind": "browser_form",
            "download_formats": ["print", "pdf"],
            "required_fields": ["incident_number"],
            "review_fields": [],
            "optional_fields": [],
        },
    }


def test_repository_catalog_is_strict_sanitized_and_complete():
    definitions = load_form_catalog(CATALOG)
    by_code = {definition.code: definition for definition in definitions}

    assert EXPECTED_CODES <= set(by_code)
    assert len(by_code) == len(definitions)
    assert {definition.output_kind for definition in definitions} <= {
        "digital_document",
        "physical_only",
    }
    assert by_code["chain_of_custody_physical"].output_kind == "physical_only"
    assert by_code["chain_of_custody_physical"].definition == {
        "description": (
            "Official carbon-copy evidence form completed by hand; the web "
            "workspace supplies confirmed handwriting guidance only."
        ),
        "obtain_from": "approved paperwork location",
        "guidance_fields": [
            "incident_number",
            "incident_date",
            "reporting_officer",
            "evidence_description",
            "recovery_location",
        ],
    }

    serialized = CATALOG.read_text(encoding="utf-8")
    assert "Officer Peterman" not in serialized
    assert "Justin Peterman" not in serialized
    assert "employee_number\":" not in serialized
    assert "phone_number\":" not in serialized
    assert "signature\":" not in serialized

    for definition in definitions:
        path_value = definition.definition.get("template_path")
        if path_value is not None:
            path = Path(path_value)
            assert not path.is_absolute()
            assert ".." not in path.parts
            assert "\\" not in path_value


def test_loader_rejects_unknown_root_or_form_keys(tmp_path):
    with pytest.raises(CatalogConfigurationError, match="unknown root key"):
        load_form_catalog(_write_catalog(tmp_path, [_digital()], unexpected=True))

    form = _digital()
    form["unexpected"] = "not allowed"
    with pytest.raises(CatalogConfigurationError, match="unknown form key"):
        load_form_catalog(_write_catalog(tmp_path, [form]))


def test_loader_rejects_duplicate_codes_invalid_output_and_unsafe_paths(tmp_path):
    with pytest.raises(CatalogConfigurationError, match="duplicate form code"):
        load_form_catalog(_write_catalog(tmp_path, [_digital(), _digital()]))

    invalid_output = _digital()
    invalid_output["output_kind"] = "copy_text"
    with pytest.raises(CatalogConfigurationError, match="output_kind"):
        load_form_catalog(_write_catalog(tmp_path, [invalid_output]))

    unsafe = _digital()
    unsafe["definition"]["render_kind"] = "docx_template"
    unsafe["definition"]["template_path"] = "../../private/real-form.docx"
    with pytest.raises(CatalogConfigurationError, match="template_path"):
        load_form_catalog(_write_catalog(tmp_path, [unsafe]))


def test_loader_rejects_invalid_definition_shapes(tmp_path):
    physical = {
        "code": "physical_form",
        "name": "Fictional Physical Form",
        "category": "evidence",
        "output_kind": "physical_only",
        "revision_label": "official carbon-copy form",
        "active": True,
        "definition": {
            "description": "Fictional physical form.",
            "obtain_from": "approved paperwork location",
            "guidance_fields": ["incident_number"],
            "template_path": "templates/should-not-exist.docx",
        },
    }
    with pytest.raises(CatalogConfigurationError, match="physical definition key"):
        load_form_catalog(_write_catalog(tmp_path, [physical]))

    duplicated_fields = _digital()
    duplicated_fields["definition"]["required_fields"] = [
        "incident_number",
        "incident_number",
    ]
    with pytest.raises(CatalogConfigurationError, match="unique field names"):
        load_form_catalog(_write_catalog(tmp_path, [duplicated_fields]))


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self.rows = list(rows)
        self.added = []

    def scalars(self, _statement):
        return _ScalarRows(self.rows)

    def add(self, row):
        self.rows.append(row)
        self.added.append(row)


def test_sync_updates_creates_and_deactivates_without_deleting_history():
    now = datetime(2026, 8, 19, 12, tzinfo=UTC)
    existing = FormTemplate(
        code="form_005_409",
        name="Old Name",
        category="legacy",
        output_kind="digital_document",
        revision_label="old",
        active=False,
        definition={"description": "old"},
        created_at=now,
        updated_at=now,
    )
    historical = FormTemplate(
        code="retired_historical_form",
        name="Retired Historical Form",
        category="incident",
        output_kind="digital_document",
        revision_label="retired",
        active=True,
        definition={},
        created_at=now,
        updated_at=now,
    )
    session = _FakeSession([existing, historical])
    definitions = (
        FormTemplateDefinition(
            code="form_005_409",
            name="005/409 Incident Report",
            category="incident",
            output_kind="digital_document",
            revision_label="ADC 005/409",
            active=True,
            definition={
                "description": "Fictional-safe definition.",
                "render_kind": "docx_template",
                "template_path": "templates/005_template_v3.docx",
                "download_formats": ["print", "word", "pdf"],
                "required_fields": ["incident_number"],
                "review_fields": [],
                "optional_fields": [],
            },
        ),
        FormTemplateDefinition(
            code="new_fictional_form",
            name="New Fictional Form",
            category="incident",
            output_kind="digital_document",
            revision_label="fictional-v1",
            active=True,
            definition={
                "description": "Fictional-safe definition.",
                "render_kind": "browser_form",
                "download_formats": ["print"],
                "required_fields": [],
                "review_fields": [],
                "optional_fields": [],
            },
        ),
    )

    synced = sync_form_catalog(session, definitions, now=now)

    assert {row.code for row in synced} == {"form_005_409", "new_fictional_form"}
    assert existing.name == "005/409 Incident Report"
    assert existing.category == "incident"
    assert existing.active is True
    assert historical in session.rows
    assert historical.active is False
    assert len(session.added) == 1
    assert session.added[0].code == "new_fictional_form"
