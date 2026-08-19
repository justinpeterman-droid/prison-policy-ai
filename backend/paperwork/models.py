"""Route-neutral domain models for operational paperwork."""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from backend.persistence.models.paperwork import PaperworkRevision


class PaperworkKind(str, Enum):
    COUNT_SHEET = "count_sheet"
    ASSIGNMENT_ROSTER = "assignment_roster"
    UNIFORM_INSPECTION = "uniform_inspection"
    METAL_DETECTOR_TEST = "metal_detector_test"
    PERIMETER_CHECK = "perimeter_check"
    RANDOM_SEARCH_LOG = "random_search_log"
    DETECTOR_SIGN_OUT = "detector_sign_out"


PaperworkAction = Literal["preview", "print", "download_pdf"]


@dataclass(frozen=True)
class PaperworkView:
    record_id: UUID
    kind: PaperworkKind
    work_date: date
    shift: str | None
    current_revision_number: int
    payload: dict[str, object]
    created_by_staff_member_id: UUID
    last_editor_staff_member_id: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PaperworkPage:
    items: tuple[PaperworkView, ...]
    next_cursor: dict[str, str] | None


@dataclass(frozen=True)
class PaperworkRevisionPage:
    items: tuple[PaperworkRevision, ...]
    next_cursor: dict[str, str] | None


@dataclass(frozen=True)
class PaperworkActionReceipt:
    recorded: Literal[True]
    record_id: UUID
    kind: PaperworkKind
    revision_number: int
    action: PaperworkAction
