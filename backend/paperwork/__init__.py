"""Shared operational-paperwork domain and persistence services."""

from backend.paperwork.models import (
    PaperworkKind,
    PaperworkPage,
    PaperworkRevisionPage,
    PaperworkView,
)
from backend.paperwork.schemas import SavePaperworkRequest
from backend.paperwork.service import (
    PaperworkNotFound,
    PaperworkRevisionConflict,
    PaperworkRevisionNotFound,
    get_paperwork_record,
    get_paperwork_revision,
    list_paperwork_records,
    list_paperwork_revisions,
    restore_paperwork_record,
    save_paperwork_record,
)

__all__ = [
    "PaperworkKind",
    "PaperworkNotFound",
    "PaperworkPage",
    "PaperworkRevisionConflict",
    "PaperworkRevisionNotFound",
    "PaperworkRevisionPage",
    "PaperworkView",
    "SavePaperworkRequest",
    "get_paperwork_record",
    "get_paperwork_revision",
    "list_paperwork_records",
    "list_paperwork_revisions",
    "restore_paperwork_record",
    "save_paperwork_record",
]
