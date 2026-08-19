"""Deterministic checklist planning and persistence for incident paperwork packets."""
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models.forms import FormTemplate, IncidentPacketItem
from backend.reports.persistence import (
    IncidentNotFound,
    IncidentRevisionNotFound,
    get_incident,
    get_incident_revision,
)


PacketGroup = Literal["required", "recommended", "additional"]
RequirementScope = Literal["global", "officer"]
DEFAULT_CHECKLIST_PATH = (
    Path(__file__).resolve().parents[2] / "templates" / "incident_checklist_v2.json"
)


class PacketConfigurationError(RuntimeError):
    """Checklist-to-catalog configuration is incomplete or unsafe."""


class PacketNotFound(LookupError):
    """The incident or packet item is not visible to the actor."""


class PacketRevisionConflict(RuntimeError):
    """Packet generation was requested for a stale incident revision."""


class PacketMutationNotAllowed(ValueError):
    """The requested packet state transition is not permitted."""


@dataclass(frozen=True)
class PlannedPacketItem:
    template_code: str
    packet_group: Literal["required", "recommended"]
    selection_reason: str
    reporting_staff_member_id: UUID | None = None


@dataclass(frozen=True)
class IncidentPacketItemView:
    packet_item_id: UUID
    template_code: str
    name: str
    output_kind: str
    packet_group: PacketGroup
    packet_state: str
    selection_reason: str
    not_applicable_reason: str | None
    reporting_staff_member_id: UUID | None
    source_incident_revision_number: int


@dataclass(frozen=True)
class _Requirement:
    template_codes: tuple[str, ...]
    condition: str = "always"
    scope: RequirementScope = "global"


# Generated report outputs are not form templates. They remain in the report
# area and are deliberately excluded from printable/physical packet planning.
_REPORT_OUTPUT_REQUIREMENTS = {
    "major_disciplinary_form": "disciplinary",
    "use_of_force_report_409": "first_person",
}


_REQUIREMENTS: dict[str, _Requirement] = {
    "cover_letter": _Requirement(("cover_letter",)),
    "005_409": _Requirement(("form_005_409",), scope="officer"),
    "photo_video": _Requirement(("photo_video_attachment",), "photo_video"),
    "chain_of_custody": _Requirement(("chain_of_custody_physical",)),
    "confiscation_f401": _Requirement(("confiscation_f401_physical",)),
    "field_test_result": _Requirement(
        ("field_test_result_attachment",), "suspected_drugs"
    ),
    "medical_report": _Requirement(
        ("medical_documentation_checklist",), "medical_documentation"
    ),
    "inmate_drug_test": _Requirement(
        ("inmate_drug_test_reminder",), "drug_test"
    ),
    "money_receipt_business_office": _Requirement(
        ("business_office_receipt_reminder",), "money_confiscated"
    ),
    "weapon_chain_of_custody_f401": _Requirement(
        ("chain_of_custody_physical", "confiscation_f401_physical"),
        "weapon_involved",
    ),
    "witness_statements": _Requirement(
        ("additional_officer_statement",), "witness_statements"
    ),
    "enemy_alert_form": _Requirement(("enemy_alert_form",), "enemy_alert"),
    "24_hour_review": _Requirement(("review_24_hour",)),
    "72_hour_review": _Requirement(("review_72_hour",)),
    "emergency_gate_pass_if_treated_outside": _Requirement(
        ("emergency_gate_pass",), "outside_medical"
    ),
    "injured_staff_company_nurse": _Requirement(
        ("company_nurse_confirmation",), "staff_injured"
    ),
    "officer_accident_report": _Requirement(
        ("officer_accident_report",), "staff_injured"
    ),
    "forced_cell_movement_fact_sheet": _Requirement(
        ("forced_cell_movement_fact_sheet",)
    ),
    "prea_checklist": _Requirement(("prea_checklist",)),
    "prea_notification": _Requirement(("prea_notification",)),
}

_OFFICER_SCOPED_TEMPLATE_CODES = frozenset(
    template_code
    for requirement in _REQUIREMENTS.values()
    if requirement.scope == "officer"
    for template_code in requirement.template_codes
)


_REQUIREMENT_LABELS = {
    "cover_letter": "cover letter",
    "005_409": "005/409 incident report",
    "photo_video": "photograph or video evidence",
    "chain_of_custody": "physical Chain of Custody form",
    "confiscation_f401": "F401 confiscation form",
    "field_test_result": "field-test result documentation",
    "medical_report": "medical documentation",
    "inmate_drug_test": "inmate drug-test documentation",
    "money_receipt_business_office": "Business Office money receipt",
    "weapon_chain_of_custody_f401": "weapon custody and F401 paperwork",
    "witness_statements": "witness statements",
    "enemy_alert_form": "Enemy Alert form",
    "24_hour_review": "24-hour review",
    "72_hour_review": "72-hour review",
    "emergency_gate_pass_if_treated_outside": "emergency medical gate pass",
    "injured_staff_company_nurse": "Company Nurse confirmation",
    "officer_accident_report": "Officer Accident Report",
    "forced_cell_movement_fact_sheet": "Forced Cell Movement Fact Sheet",
    "prea_checklist": "PREA step-by-step checklist",
    "prea_notification": "PREA incident notification",
}


def _load_checklist(path: str | Path) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PacketConfigurationError(
            "incident checklist could not be read as UTF-8 JSON"
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("categories"), list):
        raise PacketConfigurationError("incident checklist categories are invalid")
    return payload


def _category(payload: dict, category: str) -> dict:
    matches = [
        item
        for item in payload["categories"]
        if isinstance(item, dict) and item.get("name") == category
    ]
    if len(matches) != 1:
        raise PacketConfigurationError(
            f"incident checklist category is unknown: {category}"
        )
    row = matches[0]
    forms = row.get("forms_required")
    if not isinstance(forms, list) or not all(
        isinstance(value, str) for value in forms
    ):
        raise PacketConfigurationError(
            f"incident checklist forms are invalid for category: {category}"
        )
    return row


def _nested_fact(snapshot: dict, key: str):
    # Reviewed officer answers override extracted suggestions. Top-level fields
    # remain available for canonical incident values such as category/date.
    for container_name in ("gap_answers", "extracted_facts", "classification"):
        container = snapshot.get(container_name)
        if isinstance(container, dict) and key in container:
            return container[key]
    return snapshot.get(key)


def _normalized(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip().lower()
        return cleaned or None
    return str(value).strip().lower() or None


def _is_true(value: object) -> bool:
    return _normalized(value) in {
        "yes",
        "true",
        "1",
        "completed",
        "conducted",
        "filed",
        "obtained",
    }


def _is_false(value: object) -> bool:
    return _normalized(value) in {
        "no",
        "false",
        "0",
        "n/a",
        "na",
        "not applicable",
        "n/a - no injuries reported",
    }


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _has_injury(value: object) -> bool:
    normalized = _normalized(value)
    if normalized in {
        None,
        "no",
        "none",
        "no injury",
        "no injuries",
        "none reported",
        "no injuries reported",
        "n/a",
        "not applicable",
    }:
        return False
    return _has_value(value)


def _group_for(
    condition: str, snapshot: dict
) -> Literal["required", "recommended"] | None:
    if condition == "always":
        return "required"
    if condition == "photo_video":
        value = _nested_fact(snapshot, "photo_video_obtained")
        if _is_true(value):
            return "required"
        return None if _is_false(value) else "recommended"
    if condition == "medical_documentation":
        value = _nested_fact(snapshot, "medical_disposition")
        injuries = (
            _has_injury(_nested_fact(snapshot, "inmate_injuries"))
            or _has_injury(_nested_fact(snapshot, "officer_injuries"))
        )
        if _is_false(value):
            return None
        if value is not None or injuries:
            return "required"
        return "recommended"
    if condition == "drug_test":
        value = _nested_fact(snapshot, "drug_test_disposition")
        if _is_false(value):
            return None
        return "required" if value is not None else "recommended"
    if condition == "suspected_drugs":
        suspected = _nested_fact(snapshot, "contraband_is_suspected_drugs")
        result = _nested_fact(snapshot, "field_test_result_summary")
        if _is_true(suspected) or _has_value(result):
            return "required"
        return None if _is_false(suspected) else "recommended"
    if condition == "money_confiscated":
        includes_money = _nested_fact(snapshot, "contraband_includes_money")
        receipt = _nested_fact(snapshot, "money_receipt_number")
        if _is_true(includes_money) or _has_value(receipt):
            return "required"
        return None if _is_false(includes_money) else "recommended"
    if condition == "weapon_involved":
        weapon = _nested_fact(snapshot, "weapon_involved")
        custody = _nested_fact(snapshot, "weapon_custody_officer")
        if _is_true(weapon) or _has_value(custody):
            return "required"
        return None if _is_false(weapon) else "recommended"
    if condition == "witness_statements":
        value = _nested_fact(snapshot, "witness_statements_collected")
        if _is_true(value):
            return "required"
        return None if _is_false(value) else "recommended"
    if condition == "enemy_alert":
        value = _nested_fact(snapshot, "enemy_alert_filed")
        if _is_true(value):
            return "required"
        return None if _is_false(value) else "recommended"
    if condition == "outside_medical":
        disposition = _normalized(_nested_fact(snapshot, "medical_disposition"))
        gate_pass = _nested_fact(snapshot, "emergency_gate_pass")
        if (
            disposition == "sent by ambulance to outside facility"
            or _is_true(gate_pass)
        ):
            return "required"
        return "recommended" if disposition is None else None
    if condition == "staff_injured":
        value = _nested_fact(snapshot, "staff_injured")
        injuries = _nested_fact(snapshot, "officer_injuries")
        if _is_true(value) or _has_injury(injuries):
            return "required"
        return None if _is_false(value) else "recommended"
    raise PacketConfigurationError(f"unknown packet condition: {condition}")


def _reason(category_label: str, requirement_name: str, group: str) -> str:
    label = _REQUIREMENT_LABELS.get(
        requirement_name, requirement_name.replace("_", " ")
    )
    prefix = (
        "Required"
        if group == "required"
        else "Recommended while information is incomplete"
    )
    reason = f"{prefix} by {category_label} checklist: {label}."
    if len(reason) > 240:
        raise PacketConfigurationError("packet selection reason exceeds storage limit")
    return reason


def _merge_plan(
    planned: dict[tuple[str, UUID | None], PlannedPacketItem],
    item: PlannedPacketItem,
) -> None:
    key = (item.template_code, item.reporting_staff_member_id)
    previous = planned.get(key)
    if previous is None:
        planned[key] = item
        return
    group = (
        "required"
        if "required" in {previous.packet_group, item.packet_group}
        else "recommended"
    )
    reasons = list(dict.fromkeys((previous.selection_reason, item.selection_reason)))
    reason = " ".join(reasons)
    if len(reason) > 240:
        reason = reasons[0]
    planned[key] = PlannedPacketItem(
        template_code=item.template_code,
        packet_group=group,
        selection_reason=reason,
        reporting_staff_member_id=item.reporting_staff_member_id,
    )


def plan_incident_packet(
    *,
    category: str,
    snapshot: dict,
    reporting_staff_ids: tuple[UUID, ...],
    catalog_codes: set[str] | frozenset[str],
    checklist_path: str | Path = DEFAULT_CHECKLIST_PATH,
) -> tuple[PlannedPacketItem, ...]:
    """Translate one saved incident revision into a closed packet plan."""
    if not isinstance(snapshot, dict):
        raise PacketConfigurationError("incident snapshot must be an object")
    if not reporting_staff_ids:
        raise PacketConfigurationError(
            "an incident packet requires a reporting officer"
        )
    checklist = _load_checklist(checklist_path)
    category_row = _category(checklist, category)
    category_label = str(category_row.get("label") or category)
    planned: dict[tuple[str, UUID | None], PlannedPacketItem] = {}

    for requirement_name in category_row["forms_required"]:
        if requirement_name in _REPORT_OUTPUT_REQUIREMENTS:
            continue
        requirement = _REQUIREMENTS.get(requirement_name)
        if requirement is None:
            raise PacketConfigurationError(
                f"unknown checklist requirement: {requirement_name}"
            )
        group = _group_for(requirement.condition, snapshot)
        if group is None:
            continue
        for template_code in requirement.template_codes:
            if template_code not in catalog_codes:
                raise PacketConfigurationError(
                    f"missing active catalog template: {template_code}"
                )
            scopes: tuple[UUID | None, ...] = (
                tuple(reporting_staff_ids)
                if requirement.scope == "officer"
                else (None,)
            )
            for staff_id in scopes:
                _merge_plan(
                    planned,
                    PlannedPacketItem(
                        template_code=template_code,
                        packet_group=group,
                        selection_reason=_reason(
                            category_label, requirement_name, group
                        ),
                        reporting_staff_member_id=staff_id,
                    ),
                )

    group_order = {"required": 0, "recommended": 1}
    return tuple(
        sorted(
            planned.values(),
            key=lambda item: (
                group_order[item.packet_group],
                item.template_code,
                str(item.reporting_staff_member_id or ""),
            ),
        )
    )


def _authorized_incident(session: Session, actor, incident_id: UUID):
    try:
        return get_incident(session, actor, incident_id)
    except IncidentNotFound:
        raise PacketNotFound("Incident not found.") from None


def _current_revision(
    session: Session, actor, incident_id: UUID, revision_number: int
):
    view = _authorized_incident(session, actor, incident_id)
    if view.incident.current_revision_number != revision_number:
        raise PacketRevisionConflict(
            "Packet changes require the current saved incident revision."
        )
    try:
        revision = get_incident_revision(
            session, actor, incident_id, revision_number
        )
    except (IncidentNotFound, IncidentRevisionNotFound):
        raise PacketNotFound("Incident not found.") from None
    return view, revision


def _views(
    session: Session, incident_id: UUID
) -> tuple[IncidentPacketItemView, ...]:
    rows = session.execute(
        select(IncidentPacketItem, FormTemplate)
        .join(
            FormTemplate,
            FormTemplate.id == IncidentPacketItem.form_template_id,
        )
        .where(IncidentPacketItem.incident_id == incident_id)
        .order_by(
            IncidentPacketItem.packet_group,
            FormTemplate.name,
            IncidentPacketItem.reporting_staff_member_id,
            IncidentPacketItem.id,
        )
    ).all()
    return tuple(
        IncidentPacketItemView(
            packet_item_id=item.id,
            template_code=template.code,
            name=template.name,
            output_kind=template.output_kind,
            packet_group=item.packet_group,
            packet_state=item.packet_state,
            selection_reason=item.selection_reason or "",
            not_applicable_reason=item.not_applicable_reason,
            reporting_staff_member_id=item.reporting_staff_member_id,
            source_incident_revision_number=item.source_incident_revision_number,
        )
        for item, template in rows
    )


def build_incident_packet(
    session: Session,
    actor,
    *,
    incident_id: UUID,
    incident_revision_number: int,
    checklist_path: str | Path = DEFAULT_CHECKLIST_PATH,
    now: datetime | None = None,
) -> tuple[IncidentPacketItemView, ...]:
    """Idempotently reconcile required/recommended items for a saved revision."""
    view, revision = _current_revision(
        session, actor, incident_id, incident_revision_number
    )
    templates = list(
        session.scalars(
            select(FormTemplate).where(FormTemplate.active.is_(True))
        ).all()
    )
    template_by_code = {template.code: template for template in templates}
    plan = plan_incident_packet(
        category=view.incident.category,
        snapshot=revision.snapshot,
        reporting_staff_ids=view.reporting_staff_ids,
        catalog_codes=set(template_by_code),
        checklist_path=checklist_path,
    )
    fixed = now or datetime.now(UTC)

    existing_rows = session.execute(
        select(IncidentPacketItem, FormTemplate)
        .join(
            FormTemplate,
            FormTemplate.id == IncidentPacketItem.form_template_id,
        )
        .where(IncidentPacketItem.incident_id == incident_id)
        .with_for_update()
    ).all()
    existing = {
        (template.code, item.reporting_staff_member_id): item
        for item, template in existing_rows
    }
    desired_keys: set[tuple[str, UUID | None]] = set()

    for planned in plan:
        key = (planned.template_code, planned.reporting_staff_member_id)
        desired_keys.add(key)
        item = existing.get(key)
        if item is None:
            item = IncidentPacketItem(
                id=uuid4(),
                incident_id=incident_id,
                form_template_id=template_by_code[planned.template_code].id,
                reporting_staff_member_id=planned.reporting_staff_member_id,
                packet_group=planned.packet_group,
                packet_state="selected",
                source_incident_revision_number=incident_revision_number,
                selection_reason=planned.selection_reason,
                not_applicable_reason=None,
                added_by_account_id=actor.account_id,
                created_at=fixed,
                updated_at=fixed,
            )
            session.add(item)
            existing[key] = item
            continue

        previous_group = item.packet_group
        item.packet_group = planned.packet_group
        item.source_incident_revision_number = incident_revision_number
        item.selection_reason = planned.selection_reason
        item.updated_at = fixed
        if planned.packet_group == "required" and item.packet_state == "removed":
            item.packet_state = "selected"
            item.not_applicable_reason = None
        elif (
            planned.packet_group == "recommended"
            and item.packet_state == "not_applicable"
        ):
            # `not_applicable` is meaningful only for a required item. Preserve
            # the officer's dismissal when the checklist relaxes to recommended.
            item.packet_state = "removed"
            item.not_applicable_reason = None
        elif previous_group == "additional" and planned.packet_group != "additional":
            item.packet_state = "selected"
            item.not_applicable_reason = None

    for key, item in existing.items():
        if key in desired_keys or item.packet_group == "additional":
            continue
        item.packet_state = "removed"
        item.not_applicable_reason = None
        item.source_incident_revision_number = incident_revision_number
        item.updated_at = fixed

    session.flush()
    return _views(session, incident_id)


def list_incident_packet(
    session: Session,
    actor,
    *,
    incident_id: UUID,
) -> tuple[IncidentPacketItemView, ...]:
    _authorized_incident(session, actor, incident_id)
    return _views(session, incident_id)


def _packet_item(session: Session, actor, packet_item_id: UUID):
    row = session.execute(
        select(IncidentPacketItem, FormTemplate)
        .join(
            FormTemplate,
            FormTemplate.id == IncidentPacketItem.form_template_id,
        )
        .where(IncidentPacketItem.id == packet_item_id)
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise PacketNotFound("Paperwork item not found.")
    item, template = row
    _authorized_incident(session, actor, item.incident_id)
    return item, template


def _view(
    item: IncidentPacketItem, template: FormTemplate
) -> IncidentPacketItemView:
    return IncidentPacketItemView(
        packet_item_id=item.id,
        template_code=template.code,
        name=template.name,
        output_kind=template.output_kind,
        packet_group=item.packet_group,
        packet_state=item.packet_state,
        selection_reason=item.selection_reason or "",
        not_applicable_reason=item.not_applicable_reason,
        reporting_staff_member_id=item.reporting_staff_member_id,
        source_incident_revision_number=item.source_incident_revision_number,
    )


def remove_recommended_form(
    session: Session,
    actor,
    *,
    packet_item_id: UUID,
    now: datetime | None = None,
) -> IncidentPacketItemView:
    item, template = _packet_item(session, actor, packet_item_id)
    if item.packet_group != "recommended":
        raise PacketMutationNotAllowed(
            "Only recommended forms can be removed."
        )
    item.packet_state = "removed"
    item.not_applicable_reason = None
    item.updated_at = now or datetime.now(UTC)
    session.flush()
    return _view(item, template)


def mark_not_applicable(
    session: Session,
    actor,
    *,
    packet_item_id: UUID,
    reason: str,
    now: datetime | None = None,
) -> IncidentPacketItemView:
    item, template = _packet_item(session, actor, packet_item_id)
    if item.packet_group != "required":
        raise PacketMutationNotAllowed(
            "Only required forms can be marked not applicable."
        )
    cleaned = " ".join(reason.split()) if isinstance(reason, str) else ""
    if not cleaned or len(cleaned) > 500:
        raise PacketMutationNotAllowed(
            "A not-applicable reason of 1 through 500 characters is required."
        )
    item.packet_state = "not_applicable"
    item.not_applicable_reason = cleaned
    item.updated_at = now or datetime.now(UTC)
    session.flush()
    return _view(item, template)


def add_additional_form(
    session: Session,
    actor,
    *,
    incident_id: UUID,
    incident_revision_number: int,
    template_code: str,
    checklist_path: str | Path = DEFAULT_CHECKLIST_PATH,
    now: datetime | None = None,
) -> IncidentPacketItemView:
    # Keep the injected checklist boundary in the public interface so browser
    # adapters and tests use one consistent packet configuration contract.
    del checklist_path
    _current_revision(session, actor, incident_id, incident_revision_number)
    template = session.scalar(
        select(FormTemplate).where(
            FormTemplate.code == template_code,
            FormTemplate.active.is_(True),
        )
    )
    if template is None:
        raise PacketNotFound("Form template not found.")
    if template.code in _OFFICER_SCOPED_TEMPLATE_CODES:
        raise PacketMutationNotAllowed(
            "This form is created for each reporting officer and cannot be "
            "added as one incident-wide form."
        )

    item = session.scalar(
        select(IncidentPacketItem)
        .where(
            IncidentPacketItem.incident_id == incident_id,
            IncidentPacketItem.form_template_id == template.id,
            IncidentPacketItem.reporting_staff_member_id.is_(None),
        )
        .with_for_update()
    )
    fixed = now or datetime.now(UTC)
    if item is None:
        item = IncidentPacketItem(
            id=uuid4(),
            incident_id=incident_id,
            form_template_id=template.id,
            reporting_staff_member_id=None,
            packet_group="additional",
            packet_state="selected",
            source_incident_revision_number=incident_revision_number,
            selection_reason=(
                "Added by an authorized officer from the Forms Library."
            ),
            not_applicable_reason=None,
            added_by_account_id=actor.account_id,
            created_at=fixed,
            updated_at=fixed,
        )
        session.add(item)
    elif item.packet_group in {"recommended", "additional"}:
        # Selecting a form from the library re-enables an existing recommendation
        # instead of creating a duplicate or silently leaving it removed.
        item.packet_state = "selected"
        item.not_applicable_reason = None
        item.source_incident_revision_number = incident_revision_number
        item.updated_at = fixed
    session.flush()
    return _view(item, template)
