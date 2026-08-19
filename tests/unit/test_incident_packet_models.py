from sqlalchemy import CheckConstraint, UniqueConstraint

from backend.persistence.models.forms import (
    DocumentActionEvent,
    FormInstance,
    FormTemplate,
    IncidentPacketItem,
    PhysicalPaperworkAcknowledgment,
)
from backend.persistence.models.reporting import Incident


def _check_text(table) -> str:
    return " ".join(
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    )


def _unique_columns(table) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_incident_has_official_number_and_descriptive_name_contract():
    table = Incident.__table__

    assert table.c.incident_number.nullable is True
    assert table.c.incident_number.type.length == 11
    assert table.c.incident_name.nullable is True
    assert table.c.incident_name.type.length == 160

    number_index = next(
        index for index in table.indexes
        if index.name == "uq_incidents_incident_number"
    )
    assert number_index.unique is True
    assert tuple(column.name for column in number_index.columns) == ("incident_number",)
    assert number_index.dialect_options["postgresql"]["where"] is not None


def test_incident_packet_tables_and_closed_values_are_declared():
    assert FormTemplate.__table__.name == "form_templates"
    assert IncidentPacketItem.__table__.name == "incident_packet_items"
    assert FormInstance.__table__.name == "form_instances"
    assert (
        PhysicalPaperworkAcknowledgment.__table__.name
        == "physical_paperwork_acknowledgments"
    )
    assert DocumentActionEvent.__table__.name == "document_action_events"

    assert "digital_document" in _check_text(FormTemplate.__table__)
    assert "physical_only" in _check_text(FormTemplate.__table__)
    packet_checks = _check_text(IncidentPacketItem.__table__)
    for value in ("required", "recommended", "additional"):
        assert value in packet_checks
    for value in ("selected", "not_applicable", "removed"):
        assert value in packet_checks
    action_checks = _check_text(DocumentActionEvent.__table__)
    for value in ("preview", "print", "download_word", "download_pdf", "copy_text"):
        assert value in action_checks


def test_form_instance_and_physical_acknowledgment_are_one_to_one():
    assert ("packet_item_id",) in _unique_columns(FormInstance.__table__)
    assert (
        "packet_item_id",
    ) in _unique_columns(PhysicalPaperworkAcknowledgment.__table__)
    assert (
        "incident_id",
        "form_template_id",
    ) in _unique_columns(IncidentPacketItem.__table__)
