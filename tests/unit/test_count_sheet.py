from copy import deepcopy
from datetime import time

import pytest
from pydantic import ValidationError

from backend.paperwork.count_sheet import (
    AREA_ROWS,
    HOUSING_COLUMNS,
    OPERATIONAL_FIELDS,
    CountSheetRecordV1,
    calculate_count_totals,
    validate_count_sheet,
)


def _blank_payload():
    return {
        "schema_version": 1,
        "count_started": None,
        "count_ended": None,
        "cells": {
            area: {column: None for column in HOUSING_COLUMNS}
            for area in AREA_ROWS
        },
        "in_housing": {column: None for column in HOUSING_COLUMNS},
        "operational": {field: None for field in OPERATIONAL_FIELDS},
    }


def test_count_sheet_uses_approved_source_order():
    assert HOUSING_COLUMNS == (
        "1", "2", "3", "4", "5", "6", "7", "8",
        "9", "10", "11", "12", "13", "14", "Iso", "Inf",
    )
    assert AREA_ROWS == (
        "A/W Office", "Barber Shop I/M", "Boiler Room", "Bull Pen",
        "Capt. Office", "Chapel", "Chow Hall", "Commissary",
        "Construction", "Dog Kennel", "Domestics", "Field Utility",
        "Front Office", "Garage", "Gate Pass", "Gym", "Hall Porter",
        "Horsebarn", "I.P.O.", "Infirmary", "Iso. Porter", "Kitchen",
        "Laundry", "Lawn, Inside", "Library / Law Library", "Maint. Inside",
        "Maint. Outside", "Major's Office", "Mental Health", "Mt. Home Crew",
        "Other", "Reg. Maint #1", "Reg. Maint #2", "Sally Port", "School",
        "Trail Crew", "Visitation", "W.W.T.P.", "Work Craft",
        "Yard (North)", "Yard (South)",
    )
    assert OPERATIONAL_FIELDS == (
        "on_site", "gate_pass", "transfers", "court",
        "hospital", "furlough", "other",
    )


def test_row_out_of_housing_unit_and_operational_totals_reconcile():
    payload = _blank_payload()
    payload["cells"]["A/W Office"]["1"] = 2
    payload["cells"]["Chow Hall"]["1"] = 3
    payload["in_housing"]["1"] = 10
    payload["in_housing"]["2"] = 5
    payload["operational"]["on_site"] = 17
    payload["operational"]["court"] = 3

    result = calculate_count_totals(CountSheetRecordV1.model_validate(payload))

    assert result.row_totals["A/W Office"] == 2
    assert result.row_totals["Chow Hall"] == 3
    assert result.out_of_housing["1"] == 5
    assert result.out_of_housing["2"] == 0
    assert result.unit_totals["1"] == 15
    assert result.unit_totals["2"] == 5
    assert result.column_totals == result.unit_totals
    assert result.housing_total == 20
    assert result.operational_total == 20
    assert result.difference == 0
    assert result.reconciled is True


def test_serialized_time_values_are_validated_at_storage_and_api_boundaries():
    payload = _blank_payload()
    payload["count_started"] = "14:00:00"
    payload["count_ended"] = "14:15:00"
    payload["in_housing"]["1"] = 10
    payload["operational"]["on_site"] = 10

    result = calculate_count_totals(payload)

    assert result.housing_total == 10
    assert result.operational_total == 10
    assert result.reconciled is True

    payload["cells"]["A/W Office"]["1"] = "2"
    with pytest.raises(ValidationError):
        calculate_count_totals(payload)


def test_reconciliation_difference_is_signed_and_never_balanced():
    payload = _blank_payload()
    payload["in_housing"]["1"] = 20
    payload["operational"]["on_site"] = 18

    positive = validate_count_sheet(payload)
    assert positive.difference == 2
    assert positive.reconciled is False

    payload["operational"]["on_site"] = 22
    negative = validate_count_sheet(payload)
    assert negative.difference == -2
    assert negative.reconciled is False


def test_calculation_preserves_blank_cells_and_does_not_mutate_payload():
    payload = _blank_payload()
    original = deepcopy(payload)

    result = validate_count_sheet(payload)

    assert payload == original
    assert payload["cells"]["A/W Office"]["1"] is None
    assert result.row_totals["A/W Office"] == 0
    assert result.out_of_housing["1"] == 0
    assert result.unit_totals["1"] == 0


@pytest.mark.parametrize("invalid", [-1, 1.5, True, "2"])
def test_count_values_must_be_nonnegative_strict_whole_numbers(invalid):
    payload = _blank_payload()
    payload["cells"]["A/W Office"]["1"] = invalid

    with pytest.raises(ValidationError):
        CountSheetRecordV1.model_validate(payload)


def test_unknown_or_missing_rows_columns_and_operational_fields_are_rejected():
    mutations = []

    unknown_area = _blank_payload()
    unknown_area["cells"]["Unknown Area"] = {
        column: None for column in HOUSING_COLUMNS
    }
    mutations.append(unknown_area)

    missing_area = _blank_payload()
    del missing_area["cells"]["A/W Office"]
    mutations.append(missing_area)

    unknown_column = _blank_payload()
    unknown_column["cells"]["A/W Office"]["99"] = None
    mutations.append(unknown_column)

    missing_column = _blank_payload()
    del missing_column["cells"]["A/W Office"]["1"]
    mutations.append(missing_column)

    unknown_in_housing = _blank_payload()
    unknown_in_housing["in_housing"]["99"] = None
    mutations.append(unknown_in_housing)

    missing_operational = _blank_payload()
    del missing_operational["operational"]["other"]
    mutations.append(missing_operational)

    unknown_operational = _blank_payload()
    unknown_operational["operational"]["invented"] = None
    mutations.append(unknown_operational)

    for payload in mutations:
        with pytest.raises(ValidationError):
            CountSheetRecordV1.model_validate(payload)


def test_count_end_cannot_precede_count_start():
    payload = _blank_payload()
    payload["count_started"] = time(14, 30)
    payload["count_ended"] = time(14, 15)

    with pytest.raises(ValidationError):
        CountSheetRecordV1.model_validate(payload)

    payload["count_ended"] = time(14, 45)
    model = CountSheetRecordV1.model_validate(payload)
    assert model.count_started == time(14, 30)
    assert model.count_ended == time(14, 45)
