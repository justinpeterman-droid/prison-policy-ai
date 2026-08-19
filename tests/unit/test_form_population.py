"""Pure contracts for populating forms only from reviewed, saved information."""

import pytest

from backend.forms.population import (
    FormPopulationConfigurationError,
    calculate_form_completeness,
    resolve_form_fields,
)


def test_reviewed_gap_answers_override_extracted_suggestions():
    snapshot = {
        "incident_number": "2026-08-029",
        "incident_date": "2026-08-18",
        "location": "Barracks 4",
        "extracted_facts": {
            "medical_disposition": "AI suggestion that was not accepted",
            "inmate_injuries": "Possible redness",
        },
        "gap_answers": {
            "medical_disposition": "No medical treatment required",
            "inmate_injuries": "No injuries reported",
        },
    }

    fields = resolve_form_fields(
        snapshot,
        (
            "incident_number",
            "incident_date",
            "location",
            "medical_disposition",
            "injury_summary",
            "reporting_officer",
            "narrative",
        ),
        reporting_officer="Officer Alex Example",
        narrative="Saved reviewed narrative.",
    )

    assert fields == {
        "incident_number": "2026-08-029",
        "incident_date": "2026-08-18",
        "location": "Barracks 4",
        "medical_disposition": "No medical treatment required",
        "injury_summary": "Inmate injuries: No injuries reported",
        "reporting_officer": "Officer Alex Example",
        "narrative": "Saved reviewed narrative.",
    }


def test_unknown_catalog_field_fails_closed():
    with pytest.raises(
        FormPopulationConfigurationError,
        match="unsupported form field: unrestricted_free_text",
    ):
        resolve_form_fields(
            {"validation": {"facts_reviewed": True}},
            ("unrestricted_free_text",),
        )


def test_missing_required_fields_take_precedence_over_review():
    completeness = calculate_form_completeness(
        required_fields=("incident_number", "reporting_officer"),
        review_fields=("narrative",),
        populated_fields={
            "incident_number": "2026-08-029",
            "reporting_officer": None,
            "narrative": "Saved reviewed narrative.",
        },
    )

    assert completeness.state == "missing_information"
    assert completeness.missing_fields == ("reporting_officer",)
    assert completeness.review_fields == ("narrative",)


def test_populated_review_fields_require_review_before_ready():
    completeness = calculate_form_completeness(
        required_fields=("incident_number",),
        review_fields=("narrative",),
        populated_fields={
            "incident_number": "2026-08-029",
            "narrative": "Saved reviewed narrative.",
        },
    )

    assert completeness.state == "needs_review"
    assert completeness.missing_fields == ()
    assert completeness.review_fields == ("narrative",)


def test_manual_fields_override_automatic_values_for_completeness():
    completeness = calculate_form_completeness(
        required_fields=("incident_number", "reporting_officer"),
        review_fields=(),
        populated_fields={
            "incident_number": "2026-08-029",
            "reporting_officer": None,
        },
        manual_fields={"reporting_officer": "Officer Alex Example"},
    )

    assert completeness.state == "ready"
    assert completeness.missing_fields == ()
    assert completeness.review_fields == ()


@pytest.mark.parametrize("value", [None, "", "   ", [], {}, ()])
def test_blank_values_count_as_missing(value):
    completeness = calculate_form_completeness(
        required_fields=("value",),
        review_fields=(),
        populated_fields={"value": value},
    )

    assert completeness.state == "missing_information"
    assert completeness.missing_fields == ("value",)
