"""Incident packet, populated-form, physical-paperwork, and output routes."""
from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.manual import save_form_manual_fields
from backend.forms.output_events import (
    DocumentActionNotAllowed, DocumentActionNotFound, allowed_form_actions,
    record_document_action,
)
from backend.forms.packets import (
    PacketConfigurationError, PacketMutationNotAllowed, PacketNotFound,
    PacketRevisionConflict, add_additional_form, build_incident_packet,
    list_incident_packet, mark_not_applicable, remove_recommended_form,
)
from backend.forms.physical import (
    PhysicalPaperworkNotAllowed, PhysicalPaperworkNotFound,
    acknowledge_physical_paperwork, clear_physical_acknowledgment,
)
from backend.forms.population import (
    FormPopulationConfigurationError, FormPopulationNotAllowed,
    FormPopulationNotFound, FormPopulationNotReady, calculate_form_completeness,
    populate_form_instance, render_form_preview, resolve_form_fields,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.forms import (
    FormInstance, FormTemplate, IncidentPacketItem,
    PhysicalPaperworkAcknowledgment,
)
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.reporting import Report, ReportType
from backend.reports.persistence import IncidentNotFound, get_incident, get_incident_revision
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.common import (
    LOCK_CONFLICT_STATES, bounded_text, json_body, positive_int,
    request_metadata, timestamp,
)
from backend.webapp.web_api.middleware import (
    current_browser_actor, current_browser_session, require_browser_csrf,
    require_browser_session,
)

forms_bp = Blueprint("web_forms", __name__)
ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"
CHECKLIST_PATH = ROOT / "templates" / "incident_checklist_v2.json"


def _definition(template):
    value = template.definition or {}
    return {key: value.get(key) for key in (
        "description", "render_kind", "download_formats", "required_fields",
        "review_fields", "optional_fields", "obtain_from", "guidance_fields",
    )}


def _catalog(db):
    sync_form_catalog(db, load_form_catalog(CATALOG_PATH))
    db.flush()


def _complete(instance, template):
    if instance is None:
        return None
    definition = template.definition or {}
    return calculate_form_completeness(
        required_fields=tuple(definition.get("required_fields", [])),
        review_fields=tuple(definition.get("review_fields", [])),
        populated_fields=dict(instance.populated_fields or {}),
        manual_fields=dict(instance.manual_fields or {}),
    )


def _complete_data(value):
    return None if value is None else {
        "state": value.state,
        "missing_fields": list(value.missing_fields),
        "review_fields": list(value.review_fields),
    }


def _packet_item(db, view):
    template = db.scalar(select(FormTemplate).where(FormTemplate.code == view.template_code))
    if template is None:
        raise RuntimeError("packet template is unavailable")
    instance = db.scalar(select(FormInstance).where(FormInstance.packet_item_id == view.packet_item_id))
    ack = db.scalar(select(PhysicalPaperworkAcknowledgment).where(
        PhysicalPaperworkAcknowledgment.packet_item_id == view.packet_item_id
    ))
    actions = sorted(allowed_form_actions(template.output_kind, template.definition or {})) \
        if template.output_kind == "digital_document" else []
    return {
        "packet_item_id": str(view.packet_item_id),
        "template_code": view.template_code,
        "name": view.name,
        "output_kind": view.output_kind,
        "presentation": "physical" if view.output_kind == "physical_only" else "document",
        "allowed_actions": actions,
        "packet_group": view.packet_group,
        "packet_state": view.packet_state,
        "selection_reason": view.selection_reason,
        "not_applicable_reason": view.not_applicable_reason,
        "reporting_staff_member_id": str(view.reporting_staff_member_id) if view.reporting_staff_member_id else None,
        "source_incident_revision_number": view.source_incident_revision_number,
        "definition": _definition(template),
        "form_instance": None if instance is None else {
            "form_instance_id": str(instance.id),
            "source_incident_revision_number": instance.source_incident_revision_number,
            "populated_fields": dict(instance.populated_fields or {}),
            "manual_fields": dict(instance.manual_fields or {}),
            "completeness": _complete_data(_complete(instance, template)),
            "updated_at": timestamp(instance.updated_at),
        },
        "physical_acknowledgment": None if ack is None else {
            "acknowledgment_id": str(ack.id),
            "acknowledged_by_staff_member_id": str(ack.acknowledged_by_staff_member_id),
            "note": ack.note,
            "acknowledged_at": timestamp(ack.acknowledged_at),
        },
    }


def _instance(view):
    return {
        "form_instance_id": str(view.form_instance_id),
        "packet_item_id": str(view.packet_item_id),
        "incident_id": str(view.incident_id),
        "template_code": view.template_code,
        "template_name": view.template_name,
        "source_incident_revision_number": view.source_incident_revision_number,
        "populated_fields": view.populated_fields,
        "manual_fields": view.manual_fields,
        "completeness": _complete_data(view.completeness),
        "updated_at": timestamp(view.updated_at),
    }


def _preview(view):
    return {
        "form_instance_id": str(view.form_instance_id),
        "packet_item_id": str(view.packet_item_id),
        "incident_id": str(view.incident_id),
        "template_code": view.template_code,
        "template_name": view.template_name,
        "render_kind": view.render_kind,
        "fields": view.fields,
        "completeness": _complete_data(view.completeness),
    }


def _raise(error):
    if isinstance(error, (PacketNotFound, FormPopulationNotFound,
                          PhysicalPaperworkNotFound, DocumentActionNotFound,
                          IncidentNotFound)):
        raise ApiError("not_found", "Paperwork item not found.", status=404) from None
    if isinstance(error, PacketRevisionConflict):
        raise ApiError("revision_conflict", "The incident changed; rebuild the paperwork packet.", status=409) from None
    if isinstance(error, (PacketMutationNotAllowed, FormPopulationNotAllowed,
                          FormPopulationNotReady, PhysicalPaperworkNotAllowed,
                          DocumentActionNotAllowed)):
        raise ApiError("action_not_allowed", str(error), status=409) from None
    if isinstance(error, (PacketConfigurationError, FormPopulationConfigurationError)):
        raise ApiError("dependency_unavailable", "Paperwork configuration is temporarily unavailable.", status=503) from None
    raise error


def _write(operation, status=200):
    db = current_browser_session()
    try:
        value = operation(db)
        db.commit()
        return success(value, status=status)
    except (PacketNotFound, PacketRevisionConflict, PacketMutationNotAllowed,
            PacketConfigurationError, FormPopulationNotFound,
            FormPopulationNotAllowed, FormPopulationNotReady,
            FormPopulationConfigurationError, PhysicalPaperworkNotFound,
            PhysicalPaperworkNotAllowed, DocumentActionNotFound,
            DocumentActionNotAllowed, IncidentNotFound) as error:
        db.rollback(); _raise(error)
    except (ValueError, TypeError):
        db.rollback(); raise ApiError("validation_failed", "The paperwork request is invalid.", status=400) from None
    except IntegrityError:
        db.rollback(); raise ApiError("revision_conflict", "The paperwork changed; reload before continuing.", status=409) from None
    except OperationalError as error:
        db.rollback()
        state = getattr(getattr(error, "orig", None), "sqlstate", None)
        if state in LOCK_CONFLICT_STATES:
            raise ApiError("revision_conflict", "The paperwork changed; reload before continuing.", status=409) from None
        raise ApiError("dependency_unavailable", "Paperwork storage is temporarily unavailable.", status=503, retryable=True) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback(); raise ApiError("dependency_unavailable", "Paperwork storage is temporarily unavailable.", status=503, retryable=True) from None


@forms_bp.get("/forms/catalog")
@require_browser_session
def catalog_route():
    definitions = load_form_catalog(CATALOG_PATH)
    return success({"items": [{
        "template_code": item.code, "name": item.name, "category": item.category,
        "output_kind": item.output_kind, "revision_label": item.revision_label,
        "presentation": "physical" if item.output_kind == "physical_only" else "document",
        "allowed_actions": sorted(allowed_form_actions(item.output_kind, item.definition))
            if item.output_kind == "digital_document" else [],
        "definition": item.definition,
    } for item in definitions if item.active]})


@forms_bp.get("/incidents/<uuid:incident_id>/packet")
@require_browser_session
def packet_route(incident_id):
    try:
        db = current_browser_session()
        items = list_incident_packet(db, current_browser_actor(), incident_id=incident_id)
        return success({"items": [_packet_item(db, item) for item in items]})
    except (PacketNotFound, IncidentNotFound) as error:
        _raise(error)
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError("dependency_unavailable", "Paperwork storage is temporarily unavailable.", status=503, retryable=True) from None


@forms_bp.post("/incidents/<uuid:incident_id>/packet/rebuild")
@require_browser_session
@require_browser_csrf
def rebuild_route(incident_id):
    payload = json_body(exact={"incident_revision_number"})
    revision = positive_int(payload["incident_revision_number"], name="incident_revision_number")
    def operation(db):
        _catalog(db)
        items = build_incident_packet(db, current_browser_actor(), incident_id=incident_id,
                                      incident_revision_number=revision, checklist_path=CHECKLIST_PATH)
        return {"items": [_packet_item(db, item) for item in items]}
    return _write(operation)


@forms_bp.post("/incidents/<uuid:incident_id>/packet/additional")
@require_browser_session
@require_browser_csrf
def additional_route(incident_id):
    payload = json_body(exact={"incident_revision_number", "template_code"})
    revision = positive_int(payload["incident_revision_number"], name="incident_revision_number")
    code = bounded_text(payload["template_code"], name="template_code", maximum=80)
    def operation(db):
        _catalog(db)
        item = add_additional_form(db, current_browser_actor(), incident_id=incident_id,
                                   incident_revision_number=revision, template_code=code,
                                   checklist_path=CHECKLIST_PATH)
        return _packet_item(db, item)
    return _write(operation, 201)


@forms_bp.patch("/packet-items/<uuid:packet_item_id>")
@require_browser_session
@require_browser_csrf
def packet_item_route(packet_item_id):
    payload = json_body(allowed={"action", "reason"}, required={"action"})
    if payload == {"action": "remove"}:
        return _write(lambda db: _packet_item(db, remove_recommended_form(
            db, current_browser_actor(), packet_item_id=packet_item_id)))
    if set(payload) == {"action", "reason"} and payload["action"] == "not_applicable":
        reason = bounded_text(payload["reason"], name="reason", maximum=500)
        return _write(lambda db: _packet_item(db, mark_not_applicable(
            db, current_browser_actor(), packet_item_id=packet_item_id, reason=reason)))
    raise ApiError("validation_failed", "The paperwork request is invalid.", status=400)


@forms_bp.post("/packet-items/<uuid:packet_item_id>/populate")
@require_browser_session
@require_browser_csrf
def populate_route(packet_item_id):
    payload = json_body(exact={"incident_revision_number"})
    revision = positive_int(payload["incident_revision_number"], name="incident_revision_number")
    return _write(lambda db: _instance(populate_form_instance(
        db, current_browser_actor(), packet_item_id=packet_item_id,
        incident_revision_number=revision)))


@forms_bp.get("/form-instances/<uuid:form_instance_id>")
@forms_bp.get("/form-instances/<uuid:form_instance_id>/preview")
@require_browser_session
def preview_route(form_instance_id):
    try:
        return success(_preview(render_form_preview(
            current_browser_session(), current_browser_actor(), form_instance_id=form_instance_id)))
    except (FormPopulationNotFound, FormPopulationNotAllowed, FormPopulationNotReady) as error:
        _raise(error)
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError("dependency_unavailable", "Form preview is temporarily unavailable.", status=503, retryable=True) from None


@forms_bp.patch("/form-instances/<uuid:form_instance_id>")
@require_browser_session
@require_browser_csrf
def save_form_route(form_instance_id):
    payload = json_body(exact={"manual_fields", "source_incident_revision_number"})
    revision = positive_int(payload["source_incident_revision_number"], name="source_incident_revision_number")
    return _write(lambda db: _instance(save_form_manual_fields(
        db, current_browser_actor(), form_instance_id=form_instance_id,
        manual_fields=payload["manual_fields"], source_incident_revision_number=revision)))


def _physical_context(db, item, incident_view):
    staff_id = item.reporting_staff_member_id or (
        incident_view.reporting_staff_ids[0] if incident_view.reporting_staff_ids else None)
    staff = db.get(StaffMember, staff_id) if staff_id else None
    primary = " ".join(part for part in (
        staff.rank, staff.first_name, staff.last_name) if part) if staff else None
    others = []
    for value in incident_view.reporting_staff_ids:
        if value == staff_id: continue
        row = db.get(StaffMember, value)
        if row: others.append(" ".join(part for part in (row.rank, row.first_name, row.last_name) if part))
    report = db.scalar(select(Report).where(
        Report.incident_id == item.incident_id,
        Report.report_type == ReportType.FIRST_PERSON,
        Report.reporting_staff_member_id == staff_id,
    )) if staff_id else None
    narrative = (report.current_content or {}).get("narrative") if report else None
    return primary, narrative if isinstance(narrative, str) else None, others


@forms_bp.get("/packet-items/<uuid:packet_item_id>/physical")
@require_browser_session
def physical_route(packet_item_id):
    try:
        db = current_browser_session()
        row = db.execute(select(IncidentPacketItem, FormTemplate).join(
            FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id
        ).where(IncidentPacketItem.id == packet_item_id)).one_or_none()
        if row is None: raise PhysicalPaperworkNotFound("Physical paperwork item not found.")
        item, template = row
        incident = get_incident(db, current_browser_actor(), item.incident_id)
        if template.output_kind != "physical_only" or item.packet_state != "selected":
            raise PhysicalPaperworkNotAllowed("Only selected physical paperwork has handwriting guidance.")
        if item.source_incident_revision_number != incident.incident.current_revision_number:
            raise PhysicalPaperworkNotAllowed("The physical reminder must be rebuilt for the current revision.")
        revision = get_incident_revision(db, current_browser_actor(), item.incident_id,
                                         item.source_incident_revision_number)
        primary, narrative, others = _physical_context(db, item, incident)
        fields = tuple((template.definition or {}).get("guidance_fields", []))
        values = resolve_form_fields(revision.snapshot, fields, reporting_officer=primary,
                                     narrative=narrative, other_involved_officers=others)
        ack = db.scalar(select(PhysicalPaperworkAcknowledgment).where(
            PhysicalPaperworkAcknowledgment.packet_item_id == item.id))
        return success({
            "packet_item_id": str(item.id), "incident_id": str(item.incident_id),
            "template_code": template.code, "name": template.name,
            "warning": "PHYSICAL CARBON-COPY FORM REQUIRED",
            "description": (template.definition or {}).get("description"),
            "obtain_from": (template.definition or {}).get("obtain_from"),
            "guidance_fields": list(fields), "guidance_values": values,
            "source_incident_revision_number": item.source_incident_revision_number,
            "acknowledgment": None if ack is None else {
                "acknowledgment_id": str(ack.id),
                "acknowledged_by_staff_member_id": str(ack.acknowledged_by_staff_member_id),
                "note": ack.note, "acknowledged_at": timestamp(ack.acknowledged_at),
            },
            "allowed_actions": ["acknowledge_physical"],
        })
    except (PhysicalPaperworkNotFound, PhysicalPaperworkNotAllowed, IncidentNotFound) as error:
        _raise(error)
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError("dependency_unavailable", "Physical paperwork guidance is temporarily unavailable.", status=503, retryable=True) from None


@forms_bp.post("/packet-items/<uuid:packet_item_id>/physical/acknowledgment")
@require_browser_session
@require_browser_csrf
def acknowledge_route(packet_item_id):
    payload = json_body(allowed={"note"})
    req_id, version = request_metadata()
    def operation(db):
        view = acknowledge_physical_paperwork(
            db, current_browser_actor(), packet_item_id=packet_item_id,
            note=payload.get("note"), request_id=req_id, client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"])
        return {
            "acknowledgment_id": str(view.acknowledgment_id),
            "packet_item_id": str(view.packet_item_id), "incident_id": str(view.incident_id),
            "acknowledged_by_staff_member_id": str(view.acknowledged_by_staff_member_id),
            "note": view.note, "acknowledged_at": timestamp(view.acknowledged_at),
        }
    return _write(operation)


@forms_bp.delete("/packet-items/<uuid:packet_item_id>/physical/acknowledgment")
@require_browser_session
@require_browser_csrf
def clear_route(packet_item_id):
    req_id, version = request_metadata()
    return _write(lambda db: {"cleared": clear_physical_acknowledgment(
        db, current_browser_actor(), packet_item_id=packet_item_id,
        request_id=req_id, client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"])})


@forms_bp.post("/document-actions")
@require_browser_session
@require_browser_csrf
def action_route():
    payload = json_body(
        allowed={"incident_id", "incident_revision_number", "action", "packet_item_id", "report_id"},
        required={"incident_id", "incident_revision_number", "action"})
    try:
        incident_id = UUID(str(payload["incident_id"]))
        packet_id = UUID(str(payload["packet_item_id"])) if payload.get("packet_item_id") else None
        report_id = UUID(str(payload["report_id"])) if payload.get("report_id") else None
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "The document action is invalid.", status=400) from None
    revision = positive_int(payload["incident_revision_number"], name="incident_revision_number")
    action = bounded_text(payload["action"], name="action", maximum=32)
    req_id, version = request_metadata()
    def operation(db):
        view = record_document_action(
            db, current_browser_actor(), incident_id=incident_id,
            incident_revision_number=revision, action=action, request_id=req_id,
            client_version=version, packet_item_id=packet_id, report_id=report_id,
            audit_writer=current_app.config["AUDIT_WRITER"])
        return {
            "event_id": str(view.event_id), "incident_id": str(view.incident_id),
            "packet_item_id": str(view.packet_item_id) if view.packet_item_id else None,
            "report_id": str(view.report_id) if view.report_id else None,
            "action": view.action, "incident_revision_number": view.incident_revision_number,
            "created_at": timestamp(view.created_at),
        }
    return _write(operation, 201)
