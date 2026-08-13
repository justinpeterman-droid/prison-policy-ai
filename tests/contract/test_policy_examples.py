"""Executable, closed OpenAPI examples for the Policy Expert surface.

The Policy Expert contract has one unusual obligation the other surfaces do
not: it must promise, in the schema itself, that the response is *not* stored
for replay. So these tests check the ordinary things (closed schemas, required
headers, fictional examples that validate) and also that the documented 409
tells a client the honest reason a duplicate key cannot be answered.
"""

from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml


OPENAPI_PATH = Path("openapi/access-v1.yaml")
POLICY_PATH = "/api/v1/policy/questions"


def _document():
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def _validator(document, schema):
    return Draft202012Validator(
        {**schema, "components": document["components"]},
        format_checker=FormatChecker(),
    )


def _resolve(document, node):
    """Follow a local $ref so assertions read the real definition."""
    seen = 0
    while isinstance(node, dict) and "$ref" in node:
        seen += 1
        assert seen < 10, "runaway $ref chain"
        target = document
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def test_policy_question_operation_exists_with_required_headers():
    document = _document()
    assert POLICY_PATH in document["paths"]
    operation = document["paths"][POLICY_PATH]["post"]
    assert operation.get("security") != []
    refs = {item.get("$ref") for item in operation.get("parameters", [])}
    assert "#/components/parameters/XClientVersion" in refs
    assert "#/components/parameters/IdempotencyKey" in refs
    request_id = next(item for item in operation["parameters"] if item.get("name") == "X-Request-ID")
    assert request_id["required"] is True
    assert operation["requestBody"]["required"] is True


def test_policy_operation_documents_every_safe_outcome():
    document = _document()
    responses = document["paths"][POLICY_PATH]["post"]["responses"]
    for status in ("200", "400", "401", "403", "409", "500", "503", "504"):
        assert status in responses, f"missing documented {status}"


def test_policy_request_schema_is_closed_and_bounded():
    document = _document()
    schema = document["components"]["schemas"]["PolicyQuestionRequest"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"question", "history"}
    assert schema["required"] == ["question"]
    assert schema["properties"]["question"]["minLength"] >= 1
    assert schema["properties"]["question"]["maxLength"] <= 4000
    history = schema["properties"]["history"]
    # The shared cleaner trims rather than rejects older conversational turns.
    assert "maxItems" not in history
    turn = _resolve(document, history["items"])
    assert turn["additionalProperties"] is False
    assert set(turn["properties"]) == {"question", "answer"}
    for field in ("question", "answer"):
        assert turn["properties"][field]["maxLength"] == 2000


def test_policy_request_schema_rejects_client_owned_provider_controls():
    document = _document()
    schema = document["components"]["schemas"]["PolicyQuestionRequest"]
    forbidden = {
        "model",
        "temperature",
        "prompt",
        "system_prompt",
        "max_tokens",
        "actor",
        "account_id",
        "staff_id",
        "request_id",
        "idempotency_key",
    }
    assert forbidden.isdisjoint(schema["properties"])
    validator = _validator(document, schema)
    for name in sorted(forbidden):
        invalid = {"question": "Fictional question?", name: "fictional"}
        assert list(validator.iter_errors(invalid)), f"{name} should be rejected"


def test_policy_response_exposes_citations_without_storage_or_identity():
    document = _document()
    schemas = document["components"]["schemas"]
    data = schemas["PolicyAnswerData"]
    assert data["additionalProperties"] is False
    assert set(data["properties"]) == {
        "answer",
        "citations",
        "sources",
        "retrieved_sources",
    }
    citation = schemas["PolicyCitation"]
    assert citation["additionalProperties"] is False
    assert set(citation["properties"]) == {"n", "source", "text"}
    # Nothing in the answer envelope may carry an identity or a stored handle.
    forbidden = {
        "question",
        "account_id",
        "staff_id",
        "employee_number",
        "session_id",
        "idempotency_key",
        "response_id",
        "cached",
        "stored_response",
    }
    assert forbidden.isdisjoint(data["properties"])


def test_policy_duplicate_key_documents_no_replay():
    document = _document()
    responses = document["paths"][POLICY_PATH]["post"]["responses"]
    conflict = _resolve(document, responses["409"])
    described = str(conflict).lower()
    assert "request_in_progress" in described
    assert "idempotent_response_unavailable" in described
    assert "idempotency_conflict" in described
    assert "client_upgrade_required" in described
    # The contract must be explicit that a duplicate is not replayed.
    assert "not stored" in described or "never stored" in described or "no replay" in described


def test_every_policy_example_is_fictional_and_validates():
    document = _document()
    operation = document["paths"][POLICY_PATH]["post"]
    bodies = [operation["requestBody"]["content"]["application/json"]]
    bodies += [media for response in operation["responses"].values() for media in response.get("content", {}).values()]
    for media in bodies:
        if "schema" not in media:
            continue
        examples = media.get("examples", {})
        assert examples
        for example in examples.values():
            value = example["value"]
            assert "fictional" in str(value).lower() or "example" in str(value).lower()
            assert list(_validator(document, media["schema"]).iter_errors(value)) == []


def test_policy_examples_never_carry_real_looking_identifiers():
    document = _document()
    operation = document["paths"][POLICY_PATH]["post"]
    rendered = str(operation).lower()
    for leak in ("adc#", "employee_number", "@", "bearer ey"):
        assert leak not in rendered
