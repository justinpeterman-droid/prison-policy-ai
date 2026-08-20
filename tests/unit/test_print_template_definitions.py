import pytest

from backend.paperwork.templates import (
    PrintTemplatePeriod,
    list_print_templates,
    load_print_template,
    validate_print_prefill,
)


def test_weekly_catalog_is_intentionally_empty():
    assert list_print_templates(PrintTemplatePeriod.WEEKLY) == ()


def test_monthly_catalog_has_exactly_the_four_approved_landscape_templates():
    templates = list_print_templates(PrintTemplatePeriod.MONTHLY)

    assert [template.code for template in templates] == [
        "monthly_windows_bars_doors",
        "monthly_chemical_agents",
        "monthly_contraband_standard",
        "monthly_contraband_expanded",
    ]
    assert all(template.schema_version == 1 for template in templates)
    assert all(template.page_size == "letter" for template in templates)
    assert all(template.orientation == "landscape" for template in templates)


def test_monthly_prefill_is_normalized_and_rejects_unsupported_content():
    template = load_print_template("monthly_chemical_agents")

    assert validate_print_prefill(template, {
        "month": "2026-08",
        "shift_supervisor": "  Fictional Shift Supervisor  ",
    }) == {
        "month": "2026-08",
        "shift_supervisor": "Fictional Shift Supervisor",
    }

    with pytest.raises(ValueError, match="unsupported field"):
        validate_print_prefill(template, {"staff_name": "Not allowed"})
