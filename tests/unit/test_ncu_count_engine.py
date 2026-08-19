import pytest

from backend.paperwork.counts import (
    CountCellInvalid,
    CountSheetDefinition,
    calculate_count_sheet,
    validate_count_values,
)


FICTIONAL_DEFINITION = CountSheetDefinition.model_validate({
    "schema_version": 1,
    "title": "Fictional NCU Days Count Training Sheet",
    "rows": [
        {"id": "housing_alpha", "label": "Housing Alpha", "section": "in_housing"},
        {"id": "housing_bravo", "label": "Housing Bravo", "section": "in_housing"},
        {"id": "infirmary", "label": "Infirmary", "section": "out_of_housing"},
    ],
    "columns": [
        {"id": "assigned", "label": "Assigned"},
        {"id": "present", "label": "Present"},
        {"id": "temporary", "label": "Temporary"},
    ],
})


def test_calculation_returns_row_column_section_and_signed_reconciliation_totals():
    values = {
        "housing_alpha": {"assigned": 20, "present": 18, "temporary": 1},
        "housing_bravo": {"assigned": 17, "present": 17, "temporary": 0},
        "infirmary": {"assigned": 0, "present": 2, "temporary": 0},
    }

    result = calculate_count_sheet(
        FICTIONAL_DEFINITION,
        values,
        expected_operational_total=38,
    )

    assert result.row_totals == {
        "housing_alpha": 39,
        "housing_bravo": 34,
        "infirmary": 2,
    }
    assert result.column_totals == {
        "assigned": 37,
        "present": 37,
        "temporary": 1,
    }
    assert result.section_totals == {
        "in_housing": 73,
        "out_of_housing": 2,
    }
    assert result.operational_total == 37
    assert result.expected_operational_total == 38
    assert result.reconciliation_difference == -1
    assert result.is_reconciled is False


def test_reconciliation_never_changes_entered_values_or_silently_balances():
    values = {
        "housing_alpha": {"assigned": 10, "present": 9, "temporary": 0},
        "housing_bravo": {"assigned": 0, "present": 0, "temporary": 0},
        "infirmary": {"assigned": 0, "present": 0, "temporary": 0},
    }
    original = {
        row: dict(columns)
        for row, columns in values.items()
    }

    result = calculate_count_sheet(
        FICTIONAL_DEFINITION,
        values,
        expected_operational_total=10,
    )

    assert values == original
    assert result.operational_total == 9
    assert result.reconciliation_difference == -1


@pytest.mark.parametrize(
    "values",
    [
        {"housing_alpha": {"assigned": -1}},
        {"housing_alpha": {"assigned": 1.5}},
        {"housing_alpha": {"assigned": True}},
        {"housing_alpha": {"assigned": "1"}},
        {"housing_alpha": {"unknown": 1}},
        {"unknown": {"assigned": 1}},
        {"housing_alpha": {"assigned": 100_000}},
    ],
)
def test_count_values_reject_negative_coerced_unknown_or_unbounded_cells(values):
    with pytest.raises(CountCellInvalid):
        validate_count_values(FICTIONAL_DEFINITION, values)


def test_missing_cells_are_zero_without_mutating_the_saved_shape():
    values = {"housing_alpha": {"present": 3}}
    validated = validate_count_values(FICTIONAL_DEFINITION, values)
    result = calculate_count_sheet(
        FICTIONAL_DEFINITION,
        values,
        expected_operational_total=3,
    )

    assert validated == {"housing_alpha": {"present": 3}}
    assert result.column_totals == {
        "assigned": 0,
        "present": 3,
        "temporary": 0,
    }
    assert values == {"housing_alpha": {"present": 3}}
