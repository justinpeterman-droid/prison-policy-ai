import json

import pytest

from backend.paperwork.count_definition import (
    CountDefinitionUnavailable,
    build_count_paperwork_content,
    load_count_sheet_definition,
)


def _definition():
    return {
        "schema_version": 1,
        "title": "Fictional NCU Days Count Training Sheet",
        "rows": [
            {"id": "alpha", "label": "Housing Alpha", "section": "in_housing"},
            {"id": "infirmary", "label": "Infirmary", "section": "out_of_housing"},
        ],
        "columns": [
            {"id": "assigned", "label": "Assigned"},
            {"id": "present", "label": "Present"},
        ],
        "operational_total_column": "present",
    }


def test_loader_requires_exact_reviewed_json_definition(tmp_path):
    path = tmp_path / "count.json"
    path.write_text(json.dumps(_definition()), encoding="utf-8")

    loaded = load_count_sheet_definition(path)

    assert loaded.definition.title == "Fictional NCU Days Count Training Sheet"
    assert len(loaded.sha256) == 64
    assert loaded.source_path == path


def test_loader_fails_closed_when_definition_is_missing_or_invalid(tmp_path):
    with pytest.raises(CountDefinitionUnavailable):
        load_count_sheet_definition(tmp_path / "missing.json")

    path = tmp_path / "invalid.json"
    invalid = _definition()
    invalid["official_rows_not_reviewed"] = []
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(CountDefinitionUnavailable):
        load_count_sheet_definition(path)


def test_saved_content_contains_entered_values_and_server_calculated_totals(tmp_path):
    path = tmp_path / "count.json"
    path.write_text(json.dumps(_definition()), encoding="utf-8")
    loaded = load_count_sheet_definition(path)

    content = build_count_paperwork_content(
        loaded,
        values={
            "alpha": {"assigned": 10, "present": 9},
            "infirmary": {"assigned": 0, "present": 1},
        },
        expected_operational_total=11,
    )

    fields = content.fields
    assert fields["definition_sha256"] == loaded.sha256
    assert fields["values"]["alpha"]["present"] == 9
    assert fields["column_totals"] == {"assigned": 10, "present": 10}
    assert fields["operational_total"] == 10
    assert fields["expected_operational_total"] == 11
    assert fields["reconciliation_difference"] == -1
    assert fields["is_reconciled"] is False
