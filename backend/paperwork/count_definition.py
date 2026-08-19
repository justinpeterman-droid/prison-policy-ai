"""Reviewed configuration boundary for the official NCU Days Count sheet."""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from backend.paperwork.contracts import OperationalPaperworkContentV1
from backend.paperwork.counts import (
    CountSheetDefinition,
    calculate_count_sheet,
    validate_count_values,
)


DEFAULT_COUNT_DEFINITION_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2]
    / "templates"
    / "paperwork"
    / "ncu_days_count.json"
)


class CountDefinitionUnavailable(RuntimeError):
    """The reviewed official count layout is missing or structurally invalid."""


@dataclass(frozen=True)
class LoadedCountSheetDefinition:
    definition: CountSheetDefinition
    sha256: str
    source_path: Path


def load_count_sheet_definition(
    path: str | Path = DEFAULT_COUNT_DEFINITION_PATH,
) -> LoadedCountSheetDefinition:
    source = Path(path)
    try:
        raw = source.read_bytes()
        decoded = json.loads(raw.decode("utf-8"))
        definition = CountSheetDefinition.model_validate(decoded)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
        raise CountDefinitionUnavailable(
            "The reviewed NCU Days Count definition is unavailable."
        ) from None
    return LoadedCountSheetDefinition(
        definition=definition,
        sha256=sha256(raw).hexdigest(),
        source_path=source,
    )


def build_count_paperwork_content(
    loaded: LoadedCountSheetDefinition,
    *,
    values: object,
    expected_operational_total: int,
) -> OperationalPaperworkContentV1:
    """Store sparse entries plus totals independently recalculated by the server."""
    validated_values = validate_count_values(loaded.definition, values)
    calculation = calculate_count_sheet(
        loaded.definition,
        validated_values,
        expected_operational_total=expected_operational_total,
    )
    return OperationalPaperworkContentV1(fields={
        "definition_sha256": loaded.sha256,
        "values": validated_values,
        "row_totals": calculation.row_totals,
        "column_totals": calculation.column_totals,
        "section_totals": calculation.section_totals,
        "operational_total": calculation.operational_total,
        "expected_operational_total": calculation.expected_operational_total,
        "reconciliation_difference": calculation.reconciliation_difference,
        "is_reconciled": calculation.is_reconciled,
    })
