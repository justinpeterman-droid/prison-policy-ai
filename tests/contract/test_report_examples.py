"""Executable, closed OpenAPI examples for the employee report surface."""

from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml


OPENAPI_PATH = Path("openapi/access-v1.yaml")
REPORT_PATHS = {
    "/api/v1/reports": {"get"},
    "/api/v1/reports/{report_id}": {"get", "patch"},
    "/api/v1/reports/{report_id}/revisions": {"get"},
    "/api/v1/reports/{report_id}/revisions/{revision_number}": {"get"},
    "/api/v1/reports/{report_id}/restore": {"post"},
    "/api/v1/reports/{report_id}/recovery-revisions": {"post"},
}


def _document():
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def _validator(document, schema):
    return Draft202012Validator(
        {**schema, "components": document["components"]},
        format_checker=FormatChecker(),
    )


def test_every_employee_report_operation_has_closed_fictional_examples_and_errors():
    document = _document()
    for path, methods in REPORT_PATHS.items():
        assert path in document["paths"]
        assert methods <= set(document["paths"][path])
        for method in methods:
            operation = document["paths"][path][method]
            assert operation.get("security") != []
            if "{report_id}" in path:
                assert "404" in operation["responses"]
            if method in {"patch", "post"}:
                refs = {item.get("$ref") for item in operation.get("parameters", [])}
                assert "#/components/parameters/IdempotencyKey" in refs
                assert "400" in operation["responses"]
            for response in operation["responses"].values():
                for media in response.get("content", {}).values():
                    if "schema" not in media:
                        continue
                    examples = media.get("examples", {})
                    assert examples
                    for example in examples.values():
                        value = example["value"]
                        assert "fictional" in str(value).lower() or "example" in str(value).lower()
                        assert list(_validator(document, media["schema"]).iter_errors(value)) == []


def test_report_request_schemas_are_closed_and_reject_client_owned_identity():
    document = _document()
    schemas = document["components"]["schemas"]
    for name in (
        "ReportSaveRequest",
        "ReportStatusSaveRequest",
        "ReportRestoreRequest",
        "ReportRecoveryRequest",
    ):
        schema = schemas[name]
        assert schema["additionalProperties"] is False
        properties = schema["properties"]
        assert not (
            {
                "actor",
                "actor_account_id",
                "owner_staff_member_id",
                "preparer_staff_member_id",
                "model",
                "audit_identity",
            }
            & set(properties)
        )
        example = schema["example"]
        assert list(_validator(document, {"$ref": f"#/components/schemas/{name}"}).iter_errors(example)) == []
        assert list(
            _validator(document, {"$ref": f"#/components/schemas/{name}"}).iter_errors(
                example | {"actor_account_id": "00000000-0000-4000-8000-000000000099"}
            )
        )


def test_report_summaries_and_conflicts_exclude_sensitive_content():
    document = _document()
    schemas = document["components"]["schemas"]
    summary_properties = schemas["ReportSummary"]["properties"]
    conflict_properties = schemas["RevisionConflictDetails"]["properties"]
    assert "narrative" not in summary_properties
    assert "content" not in summary_properties
    assert "field_notes" not in summary_properties
    assert "narrative" not in conflict_properties
    assert "content" not in conflict_properties
    assert "field_notes" not in conflict_properties


def test_report_patch_409_oneof_executes_every_actual_safe_conflict_envelope():
    document = _document()
    response = document["paths"]["/api/v1/reports/{report_id}"]["patch"]["responses"]["409"]
    media = response["content"]["application/json"]
    assert {branch["$ref"] for branch in media["schema"]["oneOf"]} == {
        "#/components/schemas/ReportRevisionConflictEnvelope",
        "#/components/schemas/ReportIdempotencyConflictEnvelope",
        "#/components/schemas/ReportRequestInProgressEnvelope",
        "#/components/schemas/ClientUpgradeRequiredEnvelope",
    }
    assert set(media["examples"]) == {
        "revision_conflict",
        "idempotency_conflict",
        "request_in_progress",
        "client_upgrade_required",
    }
    validator = _validator(document, media["schema"])
    for example in media["examples"].values():
        assert list(validator.iter_errors(example["value"])) == []
