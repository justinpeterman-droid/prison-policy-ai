"""Versioned, closed content contracts for incidents and reports.

Every model here is strict and `extra="forbid"`. That is the point: the client
may send content, and only content. Fingerprints, actor identity, ownership and
revision bookkeeping are server-owned, so an unknown key is a rejection rather
than a field the server quietly ignores.

The field-notes ceiling is imported from the single ID-02 constant rather than
restated, so the limit the client is told about in `/api/v1/client-policy` and
the limit the server enforces cannot drift apart.
"""
from datetime import date, datetime, time
import json
from math import isfinite
import re
from typing import Annotated, Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from backend.webapp.api_v1.client_policy import FIELD_NOTES_MAX_CHARACTERS


CONTENT_SCHEMA_VERSION: Final[int] = 1
MAX_NARRATIVE_CHARACTERS: Final[int] = 30_000
MAX_SHORT_TEXT: Final[int] = 200
MAX_CODE_TEXT: Final[int] = 64
MAX_LONG_ANSWER: Final[int] = 5_000
MAX_MAP_ENTRIES: Final[int] = 100
MAX_WARNINGS: Final[int] = 100
MAX_CHARGES: Final[int] = 50
MAX_CONTENT_JSON_BYTES: Final[int] = 750_000
MAX_JSON_COLLECTION_ITEMS: Final[int] = 100
MAX_JSON_DEPTH: Final[int] = 8
MAX_JSON_NODES: Final[int] = 2_000
MAX_JSON_STRING_CHARACTERS: Final[int] = 5_000
JSON_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SERVER_OWNED_CONTENT_KEYS = frozenset({
    "provenance",
    "prompt_fingerprints",
    "fast_model",
    "pro_model",
    "model_location",
    "classification_prompt_sha256",
    "generation_prompt_sha256",
    "checklist_sha256",
    "template_sha256",
    "cloud_run_revision",
    "source_commit",
    "actor_account_id",
    "owner_staff_member_id",
    "preparer_staff_member_id",
    "editor_account_id",
    "created_by_account_id",
})

#: Values a client may place inside a bounded content map.
JsonScalar = str | int | float | bool | None
ShortText = Annotated[str, Field(max_length=MAX_SHORT_TEXT)]
CodeText = Annotated[str, Field(max_length=MAX_CODE_TEXT)]
LongAnswer = Annotated[str, Field(max_length=MAX_LONG_ANSWER)]

#: Every reason a revision row can carry (mirrors RP-01 `RevisionReason`).
RevisionReasonName = Literal[
    "autosave",
    "manual_save",
    "ai_result",
    "restored",
    "status_change",
    "ownership_change",
    "recovery",
    "admin_edit",
]
#: The subset a client may ask for directly; the rest are server-generated.
SaveReasonName = Literal["autosave", "manual_save"]


def _has_nonfinite(value: object) -> bool:
    """True if a NaN or Infinity hides anywhere in a decoded content document."""
    if isinstance(value, float):
        return not isfinite(value)
    if isinstance(value, dict):
        return any(_has_nonfinite(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_nonfinite(item) for item in value)
    return False


def _validate_recursive_json(
    value: JsonValue, *, depth: int = 0, nodes: list[int] | None = None,
) -> None:
    """Bound model-produced JSON while preserving its real nested shape."""
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
        raise ValueError("nested content is too large")
    if isinstance(value, str):
        if len(value) > MAX_JSON_STRING_CHARACTERS:
            raise ValueError("nested content string is too long")
    elif isinstance(value, float) and not isfinite(value):
        raise ValueError("nested content must not contain non-finite numbers")
    elif isinstance(value, list):
        if len(value) > MAX_JSON_COLLECTION_ITEMS:
            raise ValueError("nested content collection is too large")
        for item in value:
            _validate_recursive_json(item, depth=depth + 1, nodes=nodes)
    elif isinstance(value, dict):
        if len(value) > MAX_JSON_COLLECTION_ITEMS:
            raise ValueError("nested content collection is too large")
        for key, item in value.items():
            if (
                not isinstance(key, str)
                or not JSON_KEY_PATTERN.fullmatch(key)
                or key in SERVER_OWNED_CONTENT_KEYS
            ):
                raise ValueError("nested content key is invalid")
            _validate_recursive_json(item, depth=depth + 1, nodes=nodes)


class StrictApiModel(BaseModel):
    """Closed, non-coercing base for every wire model in this module."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class BoundedContent(StrictApiModel):
    """Content whose *encoded* size is bounded, not just its field count.

    Field-level limits bound each value; this bounds the document. A map of a
    hundred five-kilobyte answers passes every individual rule and still must
    not reach a JSONB column.
    """

    @model_validator(mode="after")
    def _reject_nonfinite_or_oversized(self):
        # Checked against the python values, not the JSON dump: pydantic
        # serializes NaN and Infinity to `null` in JSON mode, which would let a
        # non-finite number through an encode-and-look check unnoticed.
        payload = self.model_dump()
        if _has_nonfinite(payload):
            raise ValueError("content must not contain non-finite numbers")
        json_payload = self.model_dump(mode="json")
        nodes = [0]
        for value in json_payload.values():
            if isinstance(value, (dict, list)):
                _validate_recursive_json(value, nodes=nodes)
        encoded = json.dumps(json_payload, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_CONTENT_JSON_BYTES:
            raise ValueError("content is too large")
        return self


class IncidentSnapshotV1(BoundedContent):
    """One immutable version of an incident's officer-supplied content."""

    schema_version: Literal[1] = CONTENT_SCHEMA_VERSION
    field_notes: str = Field(default="", max_length=FIELD_NOTES_MAX_CHARACTERS)
    incident_date: date | None = None
    incident_time: time | None = None
    facility: str | None = Field(default=None, max_length=120)
    shift: str | None = Field(default=None, max_length=32)
    location: ShortText | None = None
    category: str | None = Field(default=None, max_length=120)
    classification: dict[CodeText, JsonValue] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    extracted_facts: dict[CodeText, JsonValue] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    gap_answers: dict[CodeText, LongAnswer] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    charges: list[ShortText] = Field(default_factory=list, max_length=MAX_CHARGES)
    validation: dict[CodeText, object] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    warnings: list[ShortText] = Field(default_factory=list, max_length=MAX_WARNINGS)

class ReportContentV1(BoundedContent):
    """One immutable version of a generated report's text and review state."""

    schema_version: Literal[1] = CONTENT_SCHEMA_VERSION
    narrative: str = Field(max_length=MAX_NARRATIVE_CHARACTERS)
    editable_fields: dict[CodeText, JsonScalar] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    validation: dict[CodeText, object] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    warnings: list[ShortText] = Field(default_factory=list, max_length=MAX_WARNINGS)


class SaveIncidentRequest(IncidentSnapshotV1):
    """A client's request to append one incident revision."""

    field_notes: str = Field(default="", max_length=FIELD_NOTES_MAX_CHARACTERS)
    base_revision_number: int = Field(default=0, ge=0)
    reason: SaveReasonName = "manual_save"


class SaveReportRequest(StrictApiModel):
    """A client's request to append one report revision."""

    content: ReportContentV1
    base_revision_number: int = Field(default=0, ge=0)
    reason: SaveReasonName = "manual_save"


class RevisionSummary(StrictApiModel):
    """What a caller learns about a revision without reading its content."""

    revision_number: int = Field(ge=0)
    reason: RevisionReasonName
    changed_fields: list[CodeText] = Field(
        default_factory=list, max_length=MAX_MAP_ENTRIES)
    created_at: datetime
    editor_staff_member_id: UUID | None = None
    source_revision_number: int | None = Field(default=None, ge=0)
    client_version: str | None = Field(default=None, max_length=MAX_CODE_TEXT)


def changed_field_names(previous: dict | None, current: dict) -> list[str]:
    """Names of top-level fields that differ, never the values themselves.

    Audit rows and revision metadata record *that* the narrative changed. What
    it changed to lives in the snapshot, behind the same access rules as the
    report — not in an audit export.
    """
    previous = previous or {}
    names = {
        key for key in set(previous) | set(current)
        if previous.get(key) != current.get(key)
    }
    return sorted(name for name in names if name != "schema_version")
