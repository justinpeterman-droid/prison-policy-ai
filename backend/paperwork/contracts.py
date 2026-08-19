"""Closed, bounded contracts for revisioned operational paperwork.

The generic paperwork store deliberately knows only document identity,
revision bookkeeping, and bounded structured content. Form-specific rules live
in their own validators so future daily paperwork cannot weaken the NCU count
contract or silently accept invented fields.
"""
from datetime import date
import json
from math import isfinite
import re
from typing import Final, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)


PAPERWORK_SCHEMA_VERSION: Final[int] = 1
PAPERWORK_TYPES: Final[frozenset[str]] = frozenset({
    "ncu_days_count",
    "assignment_roster",
    "uniform_inspection",
    "walkthrough_metal_detector_test",
    "perimeter_check",
    "random_searches",
    "handheld_metal_detector_signout",
})
MAX_PAPERWORK_FIELDS: Final[int] = 200
MAX_JSON_COLLECTION_ITEMS: Final[int] = 200
MAX_JSON_DEPTH: Final[int] = 8
MAX_JSON_NODES: Final[int] = 2_000
MAX_JSON_STRING_CHARACTERS: Final[int] = 30_000
MAX_CONTENT_JSON_BYTES: Final[int] = 750_000
_FIELD_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
_RECORD_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_SHIFT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,31}$")
_SERVER_OWNED_KEYS = frozenset({
    "actor_account_id",
    "actor_staff_member_id",
    "created_by_account_id",
    "created_by_staff_member_id",
    "editor_account_id",
    "editor_staff_member_id",
    "current_revision_number",
    "request_id",
    "client_version",
    "created_at",
    "updated_at",
    "archived_at",
})


class StrictPaperworkModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


def _clean_text(value: object, *, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > maximum:
        raise ValueError(f"{name} is invalid")
    return cleaned


def _validate_json(
    value: JsonValue,
    *,
    depth: int = 0,
    nodes: list[int] | None = None,
) -> None:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
        raise ValueError("paperwork content is too large")
    if isinstance(value, str):
        if len(value) > MAX_JSON_STRING_CHARACTERS:
            raise ValueError("paperwork text is too long")
        return
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("paperwork content must contain finite numbers")
    if isinstance(value, list):
        if len(value) > MAX_JSON_COLLECTION_ITEMS:
            raise ValueError("paperwork collection is too large")
        for item in value:
            _validate_json(item, depth=depth + 1, nodes=nodes)
        return
    if isinstance(value, dict):
        if len(value) > MAX_JSON_COLLECTION_ITEMS:
            raise ValueError("paperwork collection is too large")
        for key, item in value.items():
            if (
                not isinstance(key, str)
                or not _FIELD_KEY.fullmatch(key)
                or key in _SERVER_OWNED_KEYS
            ):
                raise ValueError("paperwork field name is invalid")
            _validate_json(item, depth=depth + 1, nodes=nodes)


class PaperworkIdentity(StrictPaperworkModel):
    """Stable identity used to reopen one operational document."""

    paperwork_type: str
    record_date: date
    shift: str = Field(max_length=32)
    record_key: str = Field(default="primary", max_length=80)

    @field_validator("paperwork_type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        if value not in PAPERWORK_TYPES:
            raise ValueError("paperwork type is unsupported")
        return value

    @field_validator("shift", mode="before")
    @classmethod
    def _normal_shift(cls, value: object) -> str:
        cleaned = _clean_text(value, name="shift", maximum=32)
        if not _SHIFT.fullmatch(cleaned):
            raise ValueError("shift is invalid")
        return cleaned

    @field_validator("record_key", mode="before")
    @classmethod
    def _normal_key(cls, value: object) -> str:
        cleaned = _clean_text(value, name="record key", maximum=80).lower()
        if not _RECORD_KEY.fullmatch(cleaned):
            raise ValueError("record key is invalid")
        return cleaned


class OperationalPaperworkContentV1(StrictPaperworkModel):
    """One immutable client-owned paperwork content snapshot."""

    schema_version: Literal[1] = PAPERWORK_SCHEMA_VERSION
    fields: dict[str, JsonValue] = Field(
        default_factory=dict,
        max_length=MAX_PAPERWORK_FIELDS,
    )

    @model_validator(mode="after")
    def _bounded_content(self):
        nodes = [0]
        _validate_json(self.fields, nodes=nodes)
        payload = self.model_dump(mode="json")
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > MAX_CONTENT_JSON_BYTES:
            raise ValueError("paperwork content is too large")
        return self


class SaveOperationalPaperworkRequest(StrictPaperworkModel):
    """Append one autosave or manual revision to an existing document."""

    content: OperationalPaperworkContentV1
    base_revision_number: int = Field(ge=0)
    reason: Literal["autosave", "manual_save"] = "manual_save"


def changed_field_names(
    previous: dict[str, object] | None,
    current: dict[str, object],
) -> list[str]:
    """Return changed top-level names without leaking values into metadata."""
    previous = previous or {}
    return sorted(
        key
        for key in set(previous) | set(current)
        if key != "schema_version" and previous.get(key) != current.get(key)
    )
