"""Unit tests for the incident-classifier response schema (RG-4).

The schema is what makes an invalid incident category unrepresentable. A wrong
category cascades: wrong checklist -> wrong gap questions -> wrong report, so
these guard the contract rather than the model.

No AI, no GCP — but importing classifier.py pulls google.genai, so these run in
CI where requirements are installed and skip cleanly if the SDK isn't importable
locally.
"""

import json
from pathlib import Path

import pytest

try:
    from backend.reports import classifier
except ImportError as exc:  # pragma: no cover - environment-dependent
    classifier = None
    _import_error = str(exc)

pytestmark = pytest.mark.skipif(
    classifier is None,
    reason=f"google-genai not importable: {globals().get('_import_error', '')}",
)

CHECKLIST_PATH = (
    Path(__file__).parent.parent.parent / "templates" / "incident_checklist_v2.json"
)


class TestCategoryEnum:
    def test_enum_matches_valid_categories(self):
        enum = classifier.CLASSIFIER_RESPONSE_SCHEMA["properties"]["incident_type"][
            "enum"
        ]
        assert set(enum) == classifier.VALID_CATEGORIES
        assert len(enum) == 9

    def test_enum_matches_the_checklist_file(self):
        """The real invariant: the schema, the validator, and the checklist data
        must agree. If someone adds a category to the JSON without updating the
        classifier, extraction would be asked for a category the model can never
        return."""
        checklist = json.loads(CHECKLIST_PATH.read_text())
        names = {c["name"] for c in checklist["categories"]}
        assert names == classifier.VALID_CATEGORIES

    def test_enum_is_sorted_and_deduped(self):
        enum = classifier.CLASSIFIER_RESPONSE_SCHEMA["properties"]["incident_type"][
            "enum"
        ]
        assert enum == sorted(set(enum))


class TestSchemaShape:
    def test_top_level_required_fields(self):
        schema = classifier.CLASSIFIER_RESPONSE_SCHEMA
        assert schema["type"] == "OBJECT"
        assert set(schema["required"]) == {
            "incident_type",
            "persons_involved",
            "charges_applicable",
        }

    def test_person_items_constrain_role(self):
        person = classifier.CLASSIFIER_RESPONSE_SCHEMA["properties"][
            "persons_involved"
        ]["items"]
        assert person["required"] == ["role"]
        assert set(person["properties"]["role"]["enum"]) == {
            "reporting_officer",
            "inmate",
            "security_staff",
            "witness",
        }

    def test_person_identity_fields_are_nullable(self):
        # Null means "the notes didn't say" — it must never be forced to a guess.
        props = classifier.CLASSIFIER_RESPONSE_SCHEMA["properties"]["persons_involved"][
            "items"
        ]["properties"]
        for field in ("name", "rank", "adc_number"):
            assert props[field]["nullable"] is True

    def test_charge_items_require_a_code(self):
        charge = classifier.CLASSIFIER_RESPONSE_SCHEMA["properties"][
            "charges_applicable"
        ]["items"]
        assert charge["required"] == ["code"]
        assert charge["properties"]["inmate"]["nullable"] is True

    def test_incident_context_fields_are_nullable(self):
        props = classifier.CLASSIFIER_RESPONSE_SCHEMA["properties"]
        for field in ("facility", "shift", "location", "date", "time"):
            assert props[field]["nullable"] is True

    def test_schema_is_json_serializable(self):
        # It's sent over the wire to Vertex — anything non-serializable would
        # fail only at request time, in production.
        json.dumps(classifier.CLASSIFIER_RESPONSE_SCHEMA)
