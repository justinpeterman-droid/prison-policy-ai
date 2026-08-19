"""Exact NCU Days Count structure, payload validation, and reconciliation."""
from dataclasses import dataclass
from datetime import time
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[2]
STRUCTURE_PATH = ROOT / "templates" / "paperwork" / "count_sheet.json"


def _load_structure() -> dict[str, object]:
    value = json.loads(STRUCTURE_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema_version",
        "title",
        "columns",
        "areas",
        "operational_fields",
        "attachment_reminders",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise RuntimeError("count sheet structure is invalid")
    if value["schema_version"] != 1:
        raise RuntimeError("count sheet structure version is unsupported")
    return value


_STRUCTURE = _load_structure()
HOUSING_COLUMNS = tuple(str(value) for value in _STRUCTURE["columns"])
AREA_ROWS = tuple(str(value) for value in _STRUCTURE["areas"])
OPERATIONAL_FIELDS = tuple(
    str(value) for value in _STRUCTURE["operational_fields"]
)
ATTACHMENT_REMINDERS = tuple(
    str(value) for value in _STRUCTURE["attachment_reminders"]
)
COUNT_SHEET_TITLE = str(_STRUCTURE["title"])

if (
    len(HOUSING_COLUMNS) != len(set(HOUSING_COLUMNS))
    or len(AREA_ROWS) != len(set(AREA_ROWS))
    or len(OPERATIONAL_FIELDS) != len(set(OPERATIONAL_FIELDS))
    or not set(ATTACHMENT_REMINDERS) <= set(OPERATIONAL_FIELDS)
):
    raise RuntimeError("count sheet structure contains duplicate or invalid entries")


CountValue = Annotated[int, Field(strict=True, ge=0)] | None


class CountSheetRecordV1(BaseModel):
    """Only officer-entered values; all totals are server-calculated."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    count_started: time | None = None
    count_ended: time | None = None
    cells: dict[str, dict[str, CountValue]]
    in_housing: dict[str, CountValue]
    operational: dict[str, CountValue]

    @model_validator(mode="after")
    def validate_structure_and_times(self):
        if set(self.cells) != set(AREA_ROWS):
            raise ValueError("count sheet area rows do not match the approved structure")
        for row in self.cells.values():
            if set(row) != set(HOUSING_COLUMNS):
                raise ValueError(
                    "count sheet housing columns do not match the approved structure"
                )
        if set(self.in_housing) != set(HOUSING_COLUMNS):
            raise ValueError("in-housing columns do not match the approved structure")
        if set(self.operational) != set(OPERATIONAL_FIELDS):
            raise ValueError("operational fields do not match the approved structure")
        if (
            self.count_started is not None
            and self.count_ended is not None
            and self.count_ended < self.count_started
        ):
            raise ValueError("count end cannot precede count start")
        return self


@dataclass(frozen=True)
class CountSheetValidation:
    row_totals: dict[str, int]
    out_of_housing: dict[str, int]
    unit_totals: dict[str, int]
    column_totals: dict[str, int]
    housing_total: int
    operational_total: int
    difference: int
    reconciled: bool


def integer_or_zero(value: int | None) -> int:
    return 0 if value is None else value


def calculate_count_totals(payload: CountSheetRecordV1) -> CountSheetValidation:
    """Calculate the approved totals without mutating officer-entered values."""
    model = CountSheetRecordV1.model_validate(payload)
    row_totals = {
        area: sum(
            integer_or_zero(model.cells[area][column])
            for column in HOUSING_COLUMNS
        )
        for area in AREA_ROWS
    }
    out_of_housing = {
        column: sum(
            integer_or_zero(model.cells[area][column])
            for area in AREA_ROWS
        )
        for column in HOUSING_COLUMNS
    }
    unit_totals = {
        column: out_of_housing[column]
        + integer_or_zero(model.in_housing[column])
        for column in HOUSING_COLUMNS
    }
    housing_total = sum(unit_totals.values())
    operational_total = sum(
        integer_or_zero(model.operational[field])
        for field in OPERATIONAL_FIELDS
    )
    difference = housing_total - operational_total
    return CountSheetValidation(
        row_totals=row_totals,
        out_of_housing=out_of_housing,
        unit_totals=unit_totals,
        column_totals=dict(unit_totals),
        housing_total=housing_total,
        operational_total=operational_total,
        difference=difference,
        reconciled=difference == 0,
    )


def validate_count_sheet(
    payload: CountSheetRecordV1 | dict[str, object],
) -> CountSheetValidation:
    model = (
        payload
        if isinstance(payload, CountSheetRecordV1)
        else CountSheetRecordV1.model_validate(payload)
    )
    return calculate_count_totals(model)


def count_sheet_structure() -> dict[str, object]:
    """Return a defensive copy for the browser API and frontend schema."""
    return json.loads(json.dumps(_STRUCTURE))
