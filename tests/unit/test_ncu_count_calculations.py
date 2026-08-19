import pytest

from backend.paperwork.counts import (
    CountSheetValidationError,
    calculate_count_sheet,
    count_sheet_content,
    parse_count_sheet_template,
)


FICTIONAL_TEMPLATE = {
    "schema_version": 1,
    "template_code": "fictional_ncu_count",
    "title": "Fictional NCU Days Count",
    "sections": [
        {
            "section_id": "in_housing",
            "label": "In Housing",
            "reconciliation_side": "left",
            "rows": [
                {"row_id": "housing_a", "label": "Fictional Housing A", "help_text": None},
                {"row_id": "housing_b", "label": "Fictional Housing B", "help_text": None},
            ],
        },
        {
            "section_id": "out_of_housing",
            "label": "Out of Housing",
            "reconciliation_side": "left",
            "rows": [
                {"row_id": "medical", "label": "Fictional Medical", "help_text": None},
            ],
        },
        {
            "section_id": "operational",
            "label": "Operational Total",
            "reconciliation_side": "right",
            "rows": [
                {"row_id": "official_total", "label": "Fictional Official Total", "help_text": None},
            ],
        },
    ],
}


def template():
    return parse_count_sheet_template(FICTIONAL_TEMPLATE)


def test_calculates_section_totals_and_signed_difference():
    calculation = calculate_count_sheet(template(), {
        "housing_a": 10,
        "housing_b": 8,
        "medical": 2,
        "official_total": 19,
    })

    assert calculation.section_totals == {
        "in_housing": 18,
        "out_of_housing": 2,
        "operational": 19,
    }
    assert calculation.left_total == 20
    assert calculation.right_total == 19
    assert calculation.difference == 1
    assert calculation.balanced is False


def test_balanced_requires_every_row_to_be_entered():
    complete = calculate_count_sheet(template(), {
        "housing_a": 10,
        "housing_b": 8,
        "medical": 2,
        "official_total": 20,
    })
    incomplete = calculate_count_sheet(template(), {
        "housing_a": 10,
        "housing_b": 8,
        "medical": None,
        "official_total": 18,
    })

    assert complete.balanced is True
    assert complete.difference == 0
    assert incomplete.difference == 0
    assert incomplete.balanced is False
    assert incomplete.missing_row_ids == ("medical",)


def test_engine_never_silently_balances_a_mismatch():
    content = count_sheet_content(template(), {
        "housing_a": 7,
        "housing_b": 5,
        "medical": 1,
        "official_total": 10,
    })

    assert content["left_total"] == 13
    assert content["right_total"] == 10
    assert content["difference"] == 3
    assert content["balanced"] is False
    assert content["values"]["official_total"] == 10


@pytest.mark.parametrize("value", [-1, 1.5, True, 100_000, "12"])
def test_counts_must_be_bounded_whole_numbers(value):
    with pytest.raises(CountSheetValidationError, match="whole number"):
        calculate_count_sheet(template(), {
            "housing_a": value,
            "housing_b": 0,
            "medical": 0,
            "official_total": 0,
        })


def test_unknown_rows_are_rejected_instead_of_ignored():
    with pytest.raises(CountSheetValidationError, match="unknown row"):
        calculate_count_sheet(template(), {
            "housing_a": 1,
            "housing_b": 1,
            "medical": 0,
            "official_total": 2,
            "invented_row": 99,
        })


def test_template_requires_unique_rows_and_both_reconciliation_sides():
    duplicate = {
        **FICTIONAL_TEMPLATE,
        "sections": [
            FICTIONAL_TEMPLATE["sections"][0],
            {
                **FICTIONAL_TEMPLATE["sections"][2],
                "rows": [
                    {"row_id": "housing_a", "label": "Duplicate", "help_text": None},
                ],
            },
        ],
    }
    with pytest.raises(CountSheetValidationError, match="unique"):
        parse_count_sheet_template(duplicate)

    no_right = {
        **FICTIONAL_TEMPLATE,
        "sections": [
            FICTIONAL_TEMPLATE["sections"][0],
            FICTIONAL_TEMPLATE["sections"][1],
        ],
    }
    with pytest.raises(CountSheetValidationError, match="left and right"):
        parse_count_sheet_template(no_right)
