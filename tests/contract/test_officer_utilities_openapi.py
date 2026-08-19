from pathlib import Path

from openapi_spec_validator import validate_spec
import yaml


SPEC = Path("openapi/officer-utilities-v1.yaml")


def test_officer_utilities_openapi_is_valid_and_contains_closed_surface():
    document = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    validate_spec(document)

    assert set(document["paths"]) == {
        "/home",
        "/forms-library",
        "/count-sheet/definition",
        "/count-sheet",
        "/count-sheet/{record_id}",
        "/paperwork",
        "/paperwork/{record_id}",
        "/paperwork/{record_id}/revisions",
        "/paperwork/{record_id}/restore",
    }
    assert document["components"]["securitySchemes"]["BrowserSession"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "slut_web_access",
    }


def test_officer_utilities_contract_never_defines_credentials_or_raw_reports():
    text = SPEC.read_text(encoding="utf-8").lower()

    for forbidden in (
        "access_token",
        "renewal_token",
        "pin_hash",
        "field_notes",
        "narrative",
        "template_path",
    ):
        assert forbidden not in text
