"""Definition-driven, non-coercing count-sheet calculation.

The engine intentionally contains no invented official row labels. A reviewed
form definition supplies rows and columns; this module validates whole-number
entries, calculates totals, and always exposes the signed reconciliation
difference rather than changing an officer's values to make them balance.
"""
from dataclasses import dataclass
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
MAX_CELL_VALUE = 99_999
MAX_ROWS = 100
MAX_COLUMNS = 40


class CountCellInvalid(ValueError):
    """A count cell or total lies outside the closed count contract."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CountRowDefinition(_StrictModel):
    id: str = Field(max_length=64)
    label: str = Field(min_length=1, max_length=120)
    section: str = Field(max_length=64)

    @field_validator("id", "section")
    @classmethod
    def _identifier(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError("count definition identifier is invalid")
        return value

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("count row label is required")
        return cleaned


class CountColumnDefinition(_StrictModel):
    id: str = Field(max_length=64)
    label: str = Field(min_length=1, max_length=120)

    @field_validator("id")
    @classmethod
    def _identifier(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError("count definition identifier is invalid")
        return value

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("count column label is required")
        return cleaned


class CountSheetDefinition(_StrictModel):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=200)
    rows: list[CountRowDefinition] = Field(min_length=1, max_length=MAX_ROWS)
    columns: list[CountColumnDefinition] = Field(
        min_length=1,
        max_length=MAX_COLUMNS,
    )
    operational_total_column: str = "present"

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("count title is required")
        return cleaned

    @field_validator("operational_total_column")
    @classmethod
    def _operational_column_identifier(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError("operational total column is invalid")
        return value

    @model_validator(mode="after")
    def _unique_and_resolvable(self):
        row_ids = [row.id for row in self.rows]
        column_ids = [column.id for column in self.columns]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("count rows must have unique identifiers")
        if len(column_ids) != len(set(column_ids)):
            raise ValueError("count columns must have unique identifiers")
        if self.operational_total_column not in set(column_ids):
            raise ValueError("operational total column is not defined")
        return self


@dataclass(frozen=True)
class CountSheetCalculation:
    row_totals: dict[str, int]
    column_totals: dict[str, int]
    section_totals: dict[str, int]
    operational_total: int
    expected_operational_total: int
    reconciliation_difference: int
    is_reconciled: bool


def _whole_count(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_CELL_VALUE:
        raise CountCellInvalid(
            f"Count cells must be whole numbers from 0 through {MAX_CELL_VALUE}."
        )
    return value


def validate_count_values(
    definition: CountSheetDefinition,
    values: object,
) -> dict[str, dict[str, int]]:
    """Return a validated sparse copy; omitted cells remain omitted and mean zero."""
    definition = CountSheetDefinition.model_validate(definition)
    if type(values) is not dict:
        raise CountCellInvalid("Count values must be a row object.")
    row_ids = {row.id for row in definition.rows}
    column_ids = {column.id for column in definition.columns}
    if not set(values) <= row_ids:
        raise CountCellInvalid("Count values contain an unknown row.")

    normalized: dict[str, dict[str, int]] = {}
    for row_id, raw_columns in values.items():
        if type(row_id) is not str or type(raw_columns) is not dict:
            raise CountCellInvalid("Count row values are invalid.")
        if not set(raw_columns) <= column_ids:
            raise CountCellInvalid("Count values contain an unknown column.")
        normalized[row_id] = {
            column_id: _whole_count(value)
            for column_id, value in raw_columns.items()
        }
    return normalized


def calculate_count_sheet(
    definition: CountSheetDefinition,
    values: object,
    *,
    expected_operational_total: int,
) -> CountSheetCalculation:
    """Calculate totals without mutating or rebalancing any supplied cell."""
    definition = CountSheetDefinition.model_validate(definition)
    sparse = validate_count_values(definition, values)
    expected = _whole_count(expected_operational_total)
    column_ids = tuple(column.id for column in definition.columns)

    row_totals: dict[str, int] = {}
    column_totals = {column_id: 0 for column_id in column_ids}
    section_totals: dict[str, int] = {}

    for row in definition.rows:
        row_values = sparse.get(row.id, {})
        row_total = 0
        for column_id in column_ids:
            value = row_values.get(column_id, 0)
            row_total += value
            column_totals[column_id] += value
        row_totals[row.id] = row_total
        section_totals[row.section] = section_totals.get(row.section, 0) + row_total

    operational_total = column_totals[definition.operational_total_column]
    difference = operational_total - expected
    return CountSheetCalculation(
        row_totals=row_totals,
        column_totals=column_totals,
        section_totals=section_totals,
        operational_total=operational_total,
        expected_operational_total=expected,
        reconciliation_difference=difference,
        is_reconciled=difference == 0,
    )
