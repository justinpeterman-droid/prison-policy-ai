"""Pure, template-driven count-sheet calculations.

The official NCU layout is data, not calculation code.  A template declares
which rows appear in each section and which sections belong on the left and
right sides of reconciliation.  This keeps the arithmetic testable without
inventing or silently changing an official form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping


ReconciliationSide = Literal["left", "right", "informational"]
MAX_COUNT_VALUE = 99_999


class CountSheetValidationError(ValueError):
    """The template or entered values violate the closed count-sheet contract."""


@dataclass(frozen=True)
class CountRowDefinition:
    row_id: str
    label: str
    help_text: str | None = None


@dataclass(frozen=True)
class CountSectionDefinition:
    section_id: str
    label: str
    reconciliation_side: ReconciliationSide
    rows: tuple[CountRowDefinition, ...]


@dataclass(frozen=True)
class CountSheetTemplate:
    schema_version: int
    template_code: str
    title: str
    sections: tuple[CountSectionDefinition, ...]


@dataclass(frozen=True)
class CountSheetCalculation:
    values: dict[str, int | None]
    row_ids: tuple[str, ...]
    section_totals: dict[str, int]
    left_total: int
    right_total: int
    difference: int
    balanced: bool
    missing_row_ids: tuple[str, ...]


def _identifier(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise CountSheetValidationError(f"{name} must be text.")
    cleaned = value.strip()
    if (
        not 1 <= len(cleaned) <= 80
        or not cleaned[0].isalpha()
        or any(not (character.islower() or character.isdigit() or character == "_") for character in cleaned)
    ):
        raise CountSheetValidationError(f"{name} is invalid.")
    return cleaned


def _label(value: object, *, name: str, maximum: int = 160) -> str:
    if not isinstance(value, str):
        raise CountSheetValidationError(f"{name} must be text.")
    cleaned = " ".join(value.split())
    if not 1 <= len(cleaned) <= maximum:
        raise CountSheetValidationError(f"{name} is invalid.")
    return cleaned


def parse_count_sheet_template(value: object) -> CountSheetTemplate:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "template_code",
        "title",
        "sections",
    }:
        raise CountSheetValidationError("Count-sheet template is invalid.")
    if value["schema_version"] != 1:
        raise CountSheetValidationError("Count-sheet template version is unsupported.")
    raw_sections = value["sections"]
    if not isinstance(raw_sections, list) or not 2 <= len(raw_sections) <= 20:
        raise CountSheetValidationError("Count-sheet sections are invalid.")

    sections: list[CountSectionDefinition] = []
    section_ids: set[str] = set()
    row_ids: set[str] = set()
    side_counts = {"left": 0, "right": 0, "informational": 0}
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict) or set(raw_section) != {
            "section_id",
            "label",
            "reconciliation_side",
            "rows",
        }:
            raise CountSheetValidationError("Count-sheet section is invalid.")
        section_id = _identifier(raw_section["section_id"], name="Section ID")
        if section_id in section_ids:
            raise CountSheetValidationError("Count-sheet section IDs must be unique.")
        section_ids.add(section_id)
        side = raw_section["reconciliation_side"]
        if side not in side_counts:
            raise CountSheetValidationError("Reconciliation side is invalid.")
        side_counts[side] += 1
        raw_rows = raw_section["rows"]
        if not isinstance(raw_rows, list) or not 1 <= len(raw_rows) <= 100:
            raise CountSheetValidationError("Count-sheet rows are invalid.")
        rows: list[CountRowDefinition] = []
        for raw_row in raw_rows:
            if not isinstance(raw_row, dict) or set(raw_row) != {
                "row_id",
                "label",
                "help_text",
            }:
                raise CountSheetValidationError("Count-sheet row is invalid.")
            row_id = _identifier(raw_row["row_id"], name="Row ID")
            if row_id in row_ids:
                raise CountSheetValidationError("Count-sheet row IDs must be unique.")
            row_ids.add(row_id)
            help_text = raw_row["help_text"]
            if help_text is not None:
                help_text = _label(help_text, name="Row help text", maximum=300)
            rows.append(CountRowDefinition(
                row_id=row_id,
                label=_label(raw_row["label"], name="Row label"),
                help_text=help_text,
            ))
        sections.append(CountSectionDefinition(
            section_id=section_id,
            label=_label(raw_section["label"], name="Section label"),
            reconciliation_side=side,
            rows=tuple(rows),
        ))

    if side_counts["left"] == 0 or side_counts["right"] == 0:
        raise CountSheetValidationError(
            "Count-sheet reconciliation requires left and right sections."
        )
    return CountSheetTemplate(
        schema_version=1,
        template_code=_identifier(value["template_code"], name="Template code"),
        title=_label(value["title"], name="Template title", maximum=200),
        sections=tuple(sections),
    )


def _count(value: object, *, row_id: str) -> int | None:
    if value is None or value == "":
        return None
    if type(value) is not int or not 0 <= value <= MAX_COUNT_VALUE:
        raise CountSheetValidationError(
            f"Count for {row_id} must be a whole number from 0 through {MAX_COUNT_VALUE}."
        )
    return value


def calculate_count_sheet(
    template: CountSheetTemplate,
    values: Mapping[str, object],
) -> CountSheetCalculation:
    if not isinstance(template, CountSheetTemplate):
        raise CountSheetValidationError("Count-sheet template is invalid.")
    if not isinstance(values, Mapping):
        raise CountSheetValidationError("Count-sheet values must be an object.")

    ordered_rows = tuple(
        row.row_id
        for section in template.sections
        for row in section.rows
    )
    unknown = set(values) - set(ordered_rows)
    if unknown:
        raise CountSheetValidationError(
            f"Count-sheet values contain an unknown row: {sorted(unknown)[0]}."
        )
    normalized = {
        row_id: _count(values.get(row_id), row_id=row_id)
        for row_id in ordered_rows
    }
    section_totals: dict[str, int] = {}
    for section in template.sections:
        section_totals[section.section_id] = sum(
            normalized[row.row_id] or 0
            for row in section.rows
        )
    left_total = sum(
        section_totals[section.section_id]
        for section in template.sections
        if section.reconciliation_side == "left"
    )
    right_total = sum(
        section_totals[section.section_id]
        for section in template.sections
        if section.reconciliation_side == "right"
    )
    difference = left_total - right_total
    missing = tuple(row_id for row_id in ordered_rows if normalized[row_id] is None)
    return CountSheetCalculation(
        values=normalized,
        row_ids=ordered_rows,
        section_totals=section_totals,
        left_total=left_total,
        right_total=right_total,
        difference=difference,
        balanced=difference == 0 and not missing,
        missing_row_ids=missing,
    )


def count_sheet_content(
    template: CountSheetTemplate,
    values: Mapping[str, object],
    *,
    notes: object = "",
) -> dict[str, object]:
    """Build the persisted, calculation-complete NCU count content document."""
    if not isinstance(notes, str):
        raise CountSheetValidationError("Count-sheet notes must be text.")
    cleaned_notes = notes.strip()
    if len(cleaned_notes) > 5_000:
        raise CountSheetValidationError(
            "Count-sheet notes must be 5,000 characters or fewer."
        )
    calculation = calculate_count_sheet(template, values)
    return {
        "schema_version": 1,
        "template_code": template.template_code,
        "values": calculation.values,
        "section_totals": calculation.section_totals,
        "left_total": calculation.left_total,
        "right_total": calculation.right_total,
        "difference": calculation.difference,
        "balanced": calculation.balanced,
        "missing_row_ids": list(calculation.missing_row_ids),
        "notes": cleaned_notes,
    }
