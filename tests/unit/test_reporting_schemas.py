"""Strict-contract tests for the versioned incident/report content schemas.

The field-notes limit is the contract release one promises the Access client, so
these tests pin both the exact boundary and *where the number comes from*: a
duplicate literal would drift silently the first time ID-02 changes the limit.
"""
import ast
import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.webapp.api_v1.client_policy import FIELD_NOTES_MAX_CHARACTERS
from backend.webapp.api_v1.schemas import reporting
from backend.webapp.api_v1.schemas.reporting import (
    IncidentSnapshotV1,
    ReportContentV1,
    RevisionSummary,
    SaveIncidentRequest,
    SaveReportRequest,
)


SOURCE = Path(reporting.__file__)
# Non-BMP: 4 UTF-8 bytes, 2 UTF-16 code units, 1 code point. Counting anything
# but code points makes the 30,000 boundary land in a different place.
NON_BMP = "\U0001d11e"


def _field_notes_max_length_node(class_name: str) -> ast.AST:
    """Return the AST node passed as ``max_length`` to ``field_notes``."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.target.id == "field_notes"
            ):
                call = statement.value
                assert isinstance(call, ast.Call), "field_notes must use Field(...)"
                for keyword in call.keywords:
                    if keyword.arg == "max_length":
                        return keyword.value
    raise AssertionError(f"{class_name}.field_notes max_length not found")


# --- the shared ID-02 field-notes contract -------------------------------


@pytest.mark.parametrize("model", [IncidentSnapshotV1, SaveIncidentRequest])
def test_field_notes_accepts_exactly_the_limit(model):
    instance = model.model_validate({"field_notes": "n" * FIELD_NOTES_MAX_CHARACTERS})

    assert len(instance.field_notes) == 30_000


@pytest.mark.parametrize("model", [IncidentSnapshotV1, SaveIncidentRequest])
def test_field_notes_rejects_one_character_over_the_limit(model):
    with pytest.raises(ValidationError):
        model.model_validate({"field_notes": "n" * (FIELD_NOTES_MAX_CHARACTERS + 1)})


@pytest.mark.parametrize("model", [IncidentSnapshotV1, SaveIncidentRequest])
def test_non_bmp_boundary_counts_code_points_not_bytes_or_units(model):
    accepted = model.model_validate(
        {"field_notes": NON_BMP * FIELD_NOTES_MAX_CHARACTERS})

    assert len(accepted.field_notes) == 30_000
    # 120,000 UTF-8 bytes and 60,000 UTF-16 units still fit: only code points count.
    assert len(accepted.field_notes.encode("utf-8")) == 4 * 30_000

    with pytest.raises(ValidationError):
        model.model_validate(
            {"field_notes": NON_BMP * (FIELD_NOTES_MAX_CHARACTERS + 1)})


@pytest.mark.parametrize(
    "class_name", ["IncidentSnapshotV1", "SaveIncidentRequest"])
def test_field_notes_limit_is_sourced_from_the_id_02_constant(class_name):
    node = _field_notes_max_length_node(class_name)

    assert isinstance(node, ast.Name), "max_length must reference the constant"
    assert node.id == "FIELD_NOTES_MAX_CHARACTERS"


def test_schema_module_reuses_the_single_constant_object():
    assert reporting.FIELD_NOTES_MAX_CHARACTERS is FIELD_NOTES_MAX_CHARACTERS
    for model in (IncidentSnapshotV1, SaveIncidentRequest):
        schema = model.model_json_schema()["properties"]["field_notes"]
        assert schema["maxLength"] == FIELD_NOTES_MAX_CHARACTERS


def test_field_notes_limit_is_not_read_from_environment_or_version_metadata():
    source = SOURCE.read_text(encoding="utf-8")

    assert "getenv" not in source
    assert "environ" not in source
    assert "release_version" not in source
    assert "from backend.webapp.api_v1.client_policy import" in source


# --- closed content contracts --------------------------------------------


def test_report_content_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({
            "schema_version": 1,
            "narrative": "Fictional narrative.",
            "unexpected": "not accepted",
        })


def test_incident_snapshot_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "field_notes": "Fictional field notes.",
            "unexpected": "not accepted",
        })


@pytest.mark.parametrize("model", [IncidentSnapshotV1, SaveIncidentRequest])
def test_incident_clients_cannot_supply_server_provenance(model):
    with pytest.raises(ValidationError):
        model.model_validate({
            "field_notes": "Fictional field notes.",
            "provenance": {"source_commit": "client-owned"},
        })


@pytest.mark.parametrize("forbidden", [
    "provenance",
    "prompt_fingerprints",
    "classification_prompt_sha256",
    "source_commit",
])
def test_client_supplied_fingerprints_are_rejected(forbidden):
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({
            "schema_version": 1,
            "narrative": "Fictional narrative.",
            forbidden: "client-owned value",
        })


@pytest.mark.parametrize("forbidden", [
    "actor_account_id",
    "owner_staff_member_id",
    "preparer_staff_member_id",
    "editor_account_id",
    "created_by_account_id",
])
def test_client_supplied_identity_fields_are_rejected(forbidden):
    with pytest.raises(ValidationError):
        SaveReportRequest.model_validate({
            "content": {"schema_version": 1, "narrative": "Fictional narrative."},
            "base_revision_number": 1,
            forbidden: str(uuid4()),
        })

    with pytest.raises(ValidationError):
        SaveIncidentRequest.model_validate({
            "field_notes": "Fictional field notes.",
            "base_revision_number": 1,
            forbidden: str(uuid4()),
        })


def test_schema_version_is_pinned_to_one():
    assert ReportContentV1(narrative="Fictional narrative.").schema_version == 1
    assert IncidentSnapshotV1().schema_version == 1

    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({"schema_version": 2, "narrative": "x"})
    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({"schema_version": 2})


def test_strict_mode_refuses_coercion():
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({"schema_version": 1, "narrative": 12345})
    with pytest.raises(ValidationError):
        SaveReportRequest.model_validate({
            "content": {"schema_version": 1, "narrative": "Fictional narrative."},
            "base_revision_number": "1",
        })


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numbers_are_rejected(bad):
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({
            "schema_version": 1,
            "narrative": "Fictional narrative.",
            "editable_fields": {"confidence": bad},
        })
    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "field_notes": "Fictional field notes.",
            "validation": {"score": bad},
        })


def test_oversized_json_is_rejected():
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({
            "schema_version": 1,
            "narrative": "Fictional narrative.",
            "validation": {"blob": "x" * (reporting.MAX_CONTENT_JSON_BYTES + 1)},
        })


def test_collections_are_bounded():
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({
            "schema_version": 1,
            "narrative": "Fictional narrative.",
            "warnings": ["w"] * (reporting.MAX_WARNINGS + 1),
        })
    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "field_notes": "Fictional field notes.",
            "charges": ["fictional charge"] * (reporting.MAX_CHARGES + 1),
        })


def test_incident_snapshot_carries_bounded_searchable_fields():
    # JSON is the wire format the routes parse; strict mode still refuses
    # coercion, it just knows JSON has no native date type.
    snapshot = IncidentSnapshotV1.model_validate_json(json.dumps({
        "field_notes": "Fictional field notes for contract testing.",
        "incident_date": "2026-08-12",
        "incident_time": "14:35:00",
        "facility": "Fictional Unit",
        "shift": "A",
        "location": "Fictional Dayroom B",
        "category": "inmate_fight",
        "classification": {"incident_type": "inmate_fight"},
        "extracted_facts": {"inmate_count": 2},
        "gap_answers": {"oc_lot_number": "fictional-lot-1"},
        "charges": ["fictional charge"],
    }))

    assert snapshot.incident_date.isoformat() == "2026-08-12"
    assert snapshot.incident_time.isoformat() == "14:35:00"
    assert snapshot.facility == "Fictional Unit"
    assert snapshot.shift == "A"
    assert snapshot.location == "Fictional Dayroom B"
    assert snapshot.extracted_facts == {"inmate_count": 2}
    assert snapshot.category == "inmate_fight"

    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "field_notes": "Fictional field notes.",
            "location": "x" * (reporting.MAX_SHORT_TEXT + 1),
        })


def test_incident_snapshot_accepts_realistic_nested_classifier_and_extractor_shapes():
    snapshot = IncidentSnapshotV1.model_validate({
        "field_notes": "Fictional Officer Example observed a staged incident.",
        "classification": {
            "incident_type": "inmate_fight",
            "label": "Inmate Fight",
            "persons_involved": [{
                "role": "inmate",
                "name": "Example, Jordan",
                "rank": None,
                "adc_number": "000000",
            }],
            "charges_applicable": [{
                "code": "12-1",
                "inmate": "Example",
                "description": "Fictional charge description.",
            }],
            "charge_descriptions": {
                "12-1": "Fictional charge description.",
            },
            "facility": "Fictional Unit",
            "shift": "A",
            "location": "Fictional Dayroom",
            "date": "2026-08-12",
            "time": "2:35pm",
        },
        "extracted_facts": {
            "persons": [{
                "role": "inmate",
                "last": "Example",
                "first": "Jordan",
                "adc_number": "000000",
                "actions": ["Raised hands in a staged confrontation."],
            }],
            "narrative_facts": [
                "Officer Example observed the fictional staged incident.",
                "Staff separated the fictional participants.",
            ],
            "quotes": [{
                "speaker": "Example, Jordan",
                "text": "Fictional quoted statement.",
            }],
            "investigation_findings": [
                "Reviewed fictional training footage.",
            ],
        },
    })

    assert snapshot.classification["persons_involved"][0]["role"] == "inmate"
    assert snapshot.classification["charges_applicable"][0]["code"] == "12-1"
    assert snapshot.extracted_facts["persons"][0]["actions"] == [
        "Raised hands in a staged confrontation."]


def test_recursive_incident_json_rejects_unbounded_or_unsafe_nested_values():
    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "classification": {
                "persons_involved": [
                    {"role": "inmate"}
                    for _ in range(reporting.MAX_JSON_COLLECTION_ITEMS + 1)
                ],
            },
        })

    nested = "fictional"
    for _ in range(reporting.MAX_JSON_DEPTH + 1):
        nested = {"nested": nested}
    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({"extracted_facts": {"nested": nested}})

    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "extracted_facts": {
                "persons": [{"actions": [float("nan")]}],
            },
        })

    with pytest.raises(ValidationError):
        IncidentSnapshotV1.model_validate({
            "classification": {"provenance": {"source_commit": "client-owned"}},
        })


def test_save_incident_has_one_authoritative_top_level_field_notes_source():
    request = SaveIncidentRequest.model_validate_json(json.dumps({
        "field_notes": "Fictional authoritative notes.",
        "base_revision_number": 1,
        "reason": "manual_save",
        "facility": "Fictional Unit",
        "shift": "A",
        "location": "Fictional Dayroom B",
        "extracted_facts": {"staff_count": 2},
    }))

    assert request.field_notes == "Fictional authoritative notes."
    assert request.extracted_facts == {"staff_count": 2}
    assert not hasattr(request, "snapshot")

    with pytest.raises(ValidationError):
        SaveIncidentRequest.model_validate({
            "field_notes": "Top-level notes.",
            "snapshot": {"field_notes": "Contradictory nested notes."},
            "base_revision_number": 1,
        })


def test_revision_summary_is_closed_and_carries_no_content():
    summary = RevisionSummary.model_validate_json(json.dumps({
        "revision_number": 2,
        "reason": "manual_save",
        "changed_fields": ["narrative"],
        "created_at": "2026-08-12T00:00:00Z",
        "editor_staff_member_id": None,
        "client_version": "1.0.0",
    }))

    assert summary.revision_number == 2
    assert "narrative" in summary.changed_fields

    with pytest.raises(ValidationError):
        RevisionSummary.model_validate_json(json.dumps({
            "revision_number": 2,
            "reason": "manual_save",
            "changed_fields": ["narrative"],
            "created_at": "2026-08-12T00:00:00Z",
            "narrative": "Fictional narrative.",
        }))


def test_save_requests_reject_negative_base_revisions():
    with pytest.raises(ValidationError):
        SaveReportRequest.model_validate({
            "content": {"schema_version": 1, "narrative": "Fictional narrative."},
            "base_revision_number": -1,
        })


def test_save_report_reason_is_bounded():
    request = SaveReportRequest.model_validate({
        "content": {"schema_version": 1, "narrative": "Fictional narrative."},
        "base_revision_number": 1,
        "reason": "autosave",
    })

    assert request.reason == "autosave"

    with pytest.raises(ValidationError):
        SaveReportRequest.model_validate({
            "content": {"schema_version": 1, "narrative": "Fictional narrative."},
            "base_revision_number": 1,
            "reason": "not_a_reason",
        })


@pytest.mark.parametrize("server_reason", ["ai_result", "admin_edit"])
def test_report_request_rejects_server_owned_reasons(server_reason):
    with pytest.raises(ValidationError):
        SaveReportRequest.model_validate({
            "content": {"schema_version": 1, "narrative": "Fictional narrative."},
            "base_revision_number": 1,
            "reason": server_reason,
        })


def test_incident_request_rejects_admin_edit_reason():
    with pytest.raises(ValidationError):
        SaveIncidentRequest.model_validate({
            "field_notes": "Fictional field notes.",
            "base_revision_number": 1,
            "reason": "admin_edit",
        })
