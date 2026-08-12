from pathlib import Path

from openapi_spec_validator import validate_spec
import yaml


def test_access_openapi_is_valid_and_client_policy_is_closed():
    path = Path("openapi/access-v1.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_spec(document)
    assert document["openapi"] == "3.1.0"
    assert document["info"]["version"] == "1.0.0"
    operation = document["paths"]["/api/v1/client-policy"]["get"]
    assert operation["security"] == []
    schema = document["components"]["schemas"]["ClientPolicy"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    limit = schema["properties"]["field_notes_max_characters"]
    assert limit == {"type": "integer", "const": 30000, "example": 30000}
