"""Versioned, closed content contracts for incidents and reports.

Every model here is strict and `extra="forbid"`. That is the point: the client
may send content, and only content. Fingerprints, actor identity, ownership and
revision bookkeeping are server-owned, so an unknown key is a rejection rather
than a field the server quietly ignores.

The field-notes ceiling is imported from the single ID-02 constant rather than
restated, so the limit the client is told about in `/api/v1/client-policy` and
the limit the server enforces cannot drift apart.
"""
from datetime import date, datetime
import json
from math import isfinite
from typing import Annotated, Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
SaveReasonName = Literal["autosave", "manual_save", "ai_result", "admin_edit"]


def _has_nonfinite(value: object) -> bool:
    """True if a NaN or Infinity hides anywhere in a decoded content document."""
    if isinstance(value, float):
        return not isfinite(value)
    if isinstance(value, dict):
        return any(_has_nonfinite(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_nonfinite(item) for item in value)
    return False


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
        encoded = json.dumps(payload, default=str, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_CONTENT_JSON_BYTES:
            raise ValueError("content is too large")
        return self


class IncidentSnapshotV1(BoundedContent):
    """One immutable version of an incident's officer-supplied content."""

    schema_version: Literal[1] = CONTENT_SCHEMA_VERSION
    field_notes: str = Field(default="", max_length=FIELD_NOTES_MAX_CHARACTERS)
    incident_type: CodeText | None = None
    category: CodeText | None = None
    incident_date: date | None = None
    incident_time: CodeText | None = None
    incident_location: ShortText | None = None
    classification: dict[CodeText, JsonScalar] = Field(
        default_factory=dict, max_length=MAX_MAP_ENTRIES)
    facts: dict[CodeText, JsonScalar] = Field(
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


class SaveIncidentRequest(StrictApiModel):
    """A client's request to append one incident revision."""

    field_notes: str = Field(default="", max_length=FIELD_NOTES_MAX_CHARACTERS)
    base_revision_number: int = Field(default=0, ge=0)
    reason: SaveReasonName = "manual_save"
    snapshot: IncidentSnapshotV1 | None = None


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
