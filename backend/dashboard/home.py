"""Authorization-scoped, content-free data for the officer Home dashboard."""
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.paperwork.contracts import PaperworkIdentity
from backend.persistence.models.forms import FormTemplate
from backend.persistence.models.paperwork import OperationalPaperworkRecord
from backend.reports.incident_library import (
    IncidentLibraryFilters,
    IncidentSummary,
    list_incident_summaries,
)


_QUICK_FORM_CODES = (
    "form_005_409",
    "cover_letter",
    "medical_documentation_checklist",
    "additional_officer_statement",
    "chain_of_custody_physical",
)


@dataclass(frozen=True)
class CountSheetHomeItem:
    record_id: UUID
    current_revision_number: int
    updated_at: datetime


@dataclass(frozen=True)
class QuickFormHomeItem:
    template_id: UUID
    code: str
    name: str
    output_kind: str


@dataclass(frozen=True)
class OfficerHomeSummary:
    continue_incident: IncidentSummary | None
    recent_incidents: tuple[IncidentSummary, ...]
    quick_forms: tuple[QuickFormHomeItem, ...]
    count_sheet: CountSheetHomeItem | None


def _count_sheet(
    session: Session,
    *,
    record_date: date,
    shift: str,
) -> CountSheetHomeItem | None:
    identity = PaperworkIdentity(
        paperwork_type="ncu_days_count",
        record_date=record_date,
        shift=shift,
        record_key="primary",
    )
    row = session.scalar(
        select(OperationalPaperworkRecord)
        .where(
            OperationalPaperworkRecord.paperwork_type == identity.paperwork_type,
            OperationalPaperworkRecord.record_date == identity.record_date,
            OperationalPaperworkRecord.shift == identity.shift,
            OperationalPaperworkRecord.record_key == identity.record_key,
            OperationalPaperworkRecord.archived_at.is_(None),
        )
        .limit(1)
    )
    if row is None:
        return None
    return CountSheetHomeItem(
        record_id=row.id,
        current_revision_number=row.current_revision_number,
        updated_at=row.updated_at,
    )


def _quick_forms(session: Session) -> tuple[QuickFormHomeItem, ...]:
    rows = list(session.scalars(
        select(FormTemplate).where(
            FormTemplate.active.is_(True),
            FormTemplate.code.in_(_QUICK_FORM_CODES),
        )
    ).all())
    by_code = {row.code: row for row in rows}
    return tuple(
        QuickFormHomeItem(
            template_id=by_code[code].id,
            code=code,
            name=by_code[code].name,
            output_kind=by_code[code].output_kind,
        )
        for code in _QUICK_FORM_CODES
        if code in by_code
    )


def get_officer_home_summary(
    session: Session,
    actor,
    *,
    record_date: date,
    shift: str,
) -> OfficerHomeSummary:
    """Return only current actor-authorized operational metadata.

    Incident notes, narratives, form values, and identity credentials are never
    part of this endpoint. The first unfinished incident is selected as the
    continuation target; no sample incident is substituted when the queue is
    empty.
    """
    page = list_incident_summaries(
        session,
        actor,
        filters=IncidentLibraryFilters(relationship="all"),
        limit=5,
        cursor=None,
    )
    incidents = tuple(page.items)
    continuation = next(
        (
            item
            for item in incidents
            if item.progress.code != "printed_or_exported"
        ),
        incidents[0] if incidents else None,
    )
    return OfficerHomeSummary(
        continue_incident=continuation,
        recent_incidents=incidents,
        quick_forms=_quick_forms(session),
        count_sheet=_count_sheet(
            session,
            record_date=record_date,
            shift=shift,
        ),
    )
