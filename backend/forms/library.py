"""Searchable, capability-aware Forms Library service."""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models.forms import FormTemplate


class FormLibraryNotFound(LookupError):
    """A requested active form is unavailable."""


class FormLibrarySelectionInvalid(ValueError):
    """A selection is empty, duplicated, oversized, or references missing forms."""


@dataclass(frozen=True)
class FormLibraryItem:
    template_id: UUID
    code: str
    name: str
    category: str
    purpose: str
    when_used: str
    output_kind: str
    revision_label: str
    capabilities: frozenset[str]
    frequent: bool
    obtain_from: str | None
    definition: dict[str, object]


@dataclass(frozen=True)
class FormLibraryPage:
    items: tuple[FormLibraryItem, ...]
    next_offset: int | None


@dataclass(frozen=True)
class FormSelectionPlan:
    items: tuple[FormLibraryItem, ...]
    digital_items: tuple[FormLibraryItem, ...]
    physical_items: tuple[FormLibraryItem, ...]


_FREQUENT_CODES = frozenset({
    "form_005_409",
    "cover_letter",
    "medical_documentation_checklist",
    "additional_officer_statement",
    "chain_of_custody_physical",
    "photo_video_attachment",
})
_OFFICER_SCOPED_CODES = frozenset({"form_005_409"})
_WHEN_USED = {
    "incident": "Use when the approved incident workflow or checklist requires this form.",
    "evidence": "Use when evidence is collected, preserved, attached, or transferred.",
    "medical": "Use when medical evaluation, treatment, testing, or transport is documented.",
    "review": "Use when the incident checklist requires a scheduled supervisory review.",
    "staff": "Use when staff involvement or injury requires supporting documentation.",
    "use_of_force": "Use when a force-related incident requires the approved supporting paperwork.",
    "prea": "Use when the approved PREA response and notification workflow applies.",
}


def _capabilities(template: FormTemplate) -> frozenset[str]:
    definition = template.definition if isinstance(template.definition, dict) else {}
    capabilities: set[str] = set()
    if template.output_kind == "physical_only":
        capabilities.add("physical_guidance")
    elif template.output_kind == "digital_document":
        capabilities.add("preview")
        formats = definition.get("download_formats")
        if isinstance(formats, list):
            if "print" in formats:
                capabilities.add("print")
            if "word" in formats:
                capabilities.add("download_word")
            if "pdf" in formats:
                capabilities.add("download_pdf")
        if definition.get("render_kind") == "browser_form":
            capabilities.update({"fillable", "blank"})
    if template.code not in _OFFICER_SCOPED_CODES:
        capabilities.add("attach_to_incident")
    return frozenset(capabilities)


def form_library_item(template: FormTemplate) -> FormLibraryItem:
    definition = template.definition if isinstance(template.definition, dict) else {}
    purpose = definition.get("description")
    if not isinstance(purpose, str) or not purpose.strip():
        purpose = "Approved operational form."
    obtain_from = definition.get("obtain_from")
    return FormLibraryItem(
        template_id=template.id,
        code=template.code,
        name=template.name,
        category=template.category,
        purpose=purpose.strip(),
        when_used=_WHEN_USED.get(
            template.category,
            "Use when the approved operational workflow requires this form.",
        ),
        output_kind=template.output_kind,
        revision_label=template.revision_label or "Current approved revision",
        capabilities=_capabilities(template),
        frequent=template.code in _FREQUENT_CODES,
        obtain_from=(
            obtain_from.strip()
            if isinstance(obtain_from, str) and obtain_from.strip()
            else None
        ),
        definition=dict(definition),
    )


def filter_form_library(
    items: list[FormLibraryItem] | tuple[FormLibraryItem, ...],
    *,
    q: str | None,
    category: str | None,
    limit: int,
    offset: int,
) -> FormLibraryPage:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("form library page size is invalid")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("form library offset is invalid")
    query = " ".join(q.split()).casefold() if isinstance(q, str) else ""
    selected_category = (
        " ".join(category.split()).casefold()
        if isinstance(category, str)
        else ""
    )
    filtered = []
    for item in items:
        if selected_category and item.category.casefold() != selected_category:
            continue
        haystack = " ".join((
            item.code,
            item.name,
            item.category,
            item.purpose,
            item.when_used,
        )).casefold()
        if query and query not in haystack:
            continue
        filtered.append(item)
    filtered.sort(key=lambda item: (
        0 if item.frequent else 1,
        item.name.casefold(),
        item.code,
        str(item.template_id),
    ))
    page = filtered[offset:offset + limit]
    next_offset = offset + limit if offset + limit < len(filtered) else None
    return FormLibraryPage(tuple(page), next_offset)


def search_form_library(
    session: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> FormLibraryPage:
    templates = list(session.scalars(
        select(FormTemplate).where(FormTemplate.active.is_(True))
    ).all())
    return filter_form_library(
        [form_library_item(template) for template in templates],
        q=q,
        category=category,
        limit=limit,
        offset=offset,
    )


def get_form_library_item(
    session: Session,
    template_id: UUID,
) -> FormLibraryItem:
    template = session.get(FormTemplate, template_id)
    if template is None or not template.active:
        raise FormLibraryNotFound("Form not found.")
    return form_library_item(template)


def plan_form_selection(
    items: list[FormLibraryItem] | tuple[FormLibraryItem, ...],
) -> FormSelectionPlan:
    selected = tuple(items)
    if not 1 <= len(selected) <= 50:
        raise FormLibrarySelectionInvalid(
            "Select between 1 and 50 forms."
        )
    ids = [item.template_id for item in selected]
    if len(ids) != len(set(ids)):
        raise FormLibrarySelectionInvalid("A form can be selected only once.")
    return FormSelectionPlan(
        items=selected,
        digital_items=tuple(
            item for item in selected if item.output_kind == "digital_document"
        ),
        physical_items=tuple(
            item for item in selected if item.output_kind == "physical_only"
        ),
    )


def get_form_selection(
    session: Session,
    template_ids: list[UUID] | tuple[UUID, ...],
) -> FormSelectionPlan:
    if not 1 <= len(template_ids) <= 50 or len(template_ids) != len(set(template_ids)):
        raise FormLibrarySelectionInvalid("The form selection is invalid.")
    items: list[FormLibraryItem] = []
    for template_id in template_ids:
        try:
            items.append(get_form_library_item(session, template_id))
        except FormLibraryNotFound:
            raise FormLibrarySelectionInvalid(
                "The form selection is invalid."
            ) from None
    return plan_form_selection(items)
