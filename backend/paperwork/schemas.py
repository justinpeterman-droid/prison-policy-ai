"""Closed, bounded payload contracts for operational paperwork."""
from datetime import date
import json
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from backend.paperwork.models import PaperworkKind


MAX_PAPERWORK_JSON_BYTES = 750_000
MAX_TOP_LEVEL_PAYLOAD_FIELDS = 100
MAX_SHIFT_CHARACTERS = 32


class StrictPaperworkModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class SavePaperworkRequest(StrictPaperworkModel):
    schema_version: Literal[1] = 1
    work_date: date
    shift: str | None = Field(default=None, max_length=MAX_SHIFT_CHARACTERS)
    payload: dict[str, JsonValue] = Field(max_length=MAX_TOP_LEVEL_PAYLOAD_FIELDS)
    base_revision_number: int | None = Field(default=None, ge=1)
    reason: Literal["autosave", "manual_save", "recovery"] = "manual_save"

    @field_validator("shift", mode="before")
    @classmethod
    def normalize_shift(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("shift must be text")
        cleaned = " ".join(value.split())
        return cleaned or None

    @model_validator(mode="after")
    def bound_payload(self):
        def has_nonfinite(value: object) -> bool:
            if isinstance(value, float):
                return not isfinite(value)
            if isinstance(value, dict):
                return any(has_nonfinite(item) for item in value.values())
            if isinstance(value, list):
                return any(has_nonfinite(item) for item in value)
            return False

        if has_nonfinite(self.payload):
            raise ValueError("paperwork payload must not contain non-finite numbers")
        encoded = json.dumps(
            self.payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > MAX_PAPERWORK_JSON_BYTES:
            raise ValueError("paperwork payload is too large")
        return self


class PaperworkSnapshotV1(StrictPaperworkModel):
    schema_version: Literal[1] = 1
    kind: Literal[
        "count_sheet",
        "assignment_roster",
        "uniform_inspection",
        "metal_detector_test",
        "perimeter_check",
        "random_search_log",
        "detector_sign_out",
    ]
    work_date: date
    shift: str | None = Field(default=None, max_length=MAX_SHIFT_CHARACTERS)
    payload: dict[str, JsonValue] = Field(max_length=MAX_TOP_LEVEL_PAYLOAD_FIELDS)


def snapshot_for_request(
    kind: PaperworkKind,
    request: SavePaperworkRequest,
) -> dict[str, object]:
    return PaperworkSnapshotV1(
        kind=kind.value,
        work_date=request.work_date,
        shift=request.shift,
        payload=dict(request.payload),
    ).model_dump(mode="json")


def changed_field_paths(
    previous: dict[str, object] | None,
    current: dict[str, object],
) -> tuple[str, ...]:
    """Return bounded field paths without storing changed values.

    Payload changes stop at the first stable payload section (for example,
    ``payload.cells``) so row labels, employee names, notes, and other record
    content never become revision or audit metadata.
    """
    previous = previous or {}
    paths: set[str] = set()
    for key in set(previous) | set(current):
        if key == "schema_version":
            continue
        before = previous.get(key)
        after = current.get(key)
        if before == after:
            continue
        if key == "payload" and isinstance(before, dict) and isinstance(after, dict):
            for section in set(before) | set(after):
                if before.get(section) != after.get(section):
                    safe = str(section)
                    if safe and safe.replace("_", "").isalnum():
                        paths.add(f"payload.{safe}")
                    else:
                        paths.add("payload")
        else:
            paths.add(key)
    return tuple(sorted(paths))


def validate_payload_for_kind(
    kind: PaperworkKind,
    payload: dict[str, JsonValue],
) -> dict[str, object]:
    """Return a JSON-safe copy after exact kind-specific validation."""
    if not isinstance(kind, PaperworkKind):
        raise ValueError("paperwork kind is invalid")
    if kind is PaperworkKind.COUNT_SHEET:
        from backend.paperwork.count_sheet import CountSheetRecordV1

        model = CountSheetRecordV1.model_validate_json(
            json.dumps(payload, ensure_ascii=False, allow_nan=False)
        )
        return model.model_dump(mode="json")
    return json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))
