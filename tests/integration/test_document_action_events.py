"""PostgreSQL contracts for server-enforced output actions and safe audit events."""
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.output_events import (
    DocumentActionNotAllowed,
    record_document_action,
)
from backend.persistence.models import AuditEvent
from backend.persistence.models.forms import (
    DocumentActionEvent,
    FormTemplate,
    IncidentPacketItem,
)
from backend.persistence.models.reporting import ReportType


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"


def _packet_item(
    db_session,
    *,
    incident,
    account,
    template_code,
):
    sync_form_catalog(db_session, load_form_catalog(CATALOG_PATH))
    db_session.flush()
    template = db_session.scalar(
        select(FormTemplate).where(FormTemplate.code == template_code)
    )
    item = IncidentPacketItem(
        incident_id=incident.id,
        form_template_id=template.id,
        reporting_staff_member_id=(
            account.staff_member_id if template_code == "form_005_409" else None
        ),
        packet_group="required",
        packet_state="selected",
        source_incident_revision_number=incident.current_revision_number,
        selection_reason="Fictional document-action fixture.",
        added_by_account_id=account.id,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_printing_a_digital_form_records_one_safe_event_and_audit(
    db_session,
    fictional_reporting_incident,
    fictional_staff_and_accounts,
    identity_fixed_now,
    user_actor,
):
    item = _packet_item(
        db_session,
        incident=fictional_reporting_incident,
        account=fictional_staff_and_accounts.user,
        template_code="form_005_409",
    )
    fixed = identity_fixed_now + timedelta(minutes=40)

    view = record_document_action(
        db_session,
        user_actor,
        incident_id=fictional_reporting_incident.id,
        incident_revision_number=fictional_reporting_incident.current_revision_number,
        packet_item_id=item.id,
        action="print",
        request_id="request_fictional_form_print",
        client_version="1.0.0",
        now=fixed,
    )

    assert view.incident_id == fictional_reporting_incident.id
    assert view.packet_item_id == item.id
    assert view.report_id is None
    assert view.action == "print"
    assert (
        view.incident_revision_number
        == fictional_reporting_incident.current_revision_number
    )
    assert view.created_at == fixed
    assert db_session.scalar(
        select(func.count()).select_from(DocumentActionEvent)
    ) == 1

    audit = db_session.scalar(select(AuditEvent).where(
        AuditEvent.action == "document.action_recorded",
        AuditEvent.target_id == item.id,
    ))
    assert audit is not None
    assert audit.details == {
        "document_action": "print",
        "incident_id": str(fictional_reporting_incident.id),
        "incident_revision_number": (
            fictional_reporting_incident.current_revision_number
        ),
        "packet_item_id": str(item.id),
    }


def test_physical_form_rejects_print_without_event_or_audit(
    db_session,
    fictional_reporting_incident,
    fictional_staff_and_accounts,
    user_actor,
):
    item = _packet_item(
        db_session,
        incident=fictional_reporting_incident,
        account=fictional_staff_and_accounts.user,
        template_code="chain_of_custody_physical",
    )

    with pytest.raises(
        DocumentActionNotAllowed,
        match="Physical-only paperwork has no digital action",
    ):
        record_document_action(
            db_session,
            user_actor,
            incident_id=fictional_reporting_incident.id,
            incident_revision_number=(
                fictional_reporting_incident.current_revision_number
            ),
            packet_item_id=item.id,
            action="print",
            request_id="request_fictional_physical_print",
            client_version="1.0.0",
        )

    assert db_session.scalar(
        select(func.count()).select_from(DocumentActionEvent)
    ) == 0
    assert db_session.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.action == "document.action_recorded"
    )) == 0


def test_copy_only_report_accepts_copy_and_rejects_print(
    db_session,
    fictional_incident,
    fictional_report,
    identity_fixed_now,
    user_actor,
):
    fictional_report.report_type = ReportType.SUPERVISOR_SUMMARY
    db_session.flush()

    copied = record_document_action(
        db_session,
        user_actor,
        incident_id=fictional_incident.id,
        incident_revision_number=fictional_incident.current_revision_number,
        report_id=fictional_report.id,
        action="copy_text",
        request_id="request_fictional_supervisor_copy",
        client_version="1.0.0",
        now=identity_fixed_now + timedelta(minutes=41),
    )
    assert copied.action == "copy_text"
    assert copied.report_id == fictional_report.id

    with pytest.raises(
        DocumentActionNotAllowed,
        match="print is not allowed for supervisor_summary",
    ):
        record_document_action(
            db_session,
            user_actor,
            incident_id=fictional_incident.id,
            incident_revision_number=fictional_incident.current_revision_number,
            report_id=fictional_report.id,
            action="print",
            request_id="request_fictional_supervisor_print",
            client_version="1.0.0",
        )

    assert db_session.scalar(
        select(func.count()).select_from(DocumentActionEvent)
    ) == 1


def test_action_requires_exactly_one_current_authorized_target(
    db_session,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    user_actor,
):
    item = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="form_005_409",
    )

    for packet_item_id, report_id in ((None, None), (item.id, fictional_report.id)):
        with pytest.raises(
            DocumentActionNotAllowed,
            match="exactly one document target",
        ):
            record_document_action(
                db_session,
                user_actor,
                incident_id=fictional_incident.id,
                incident_revision_number=fictional_incident.current_revision_number,
                packet_item_id=packet_item_id,
                report_id=report_id,
                action="preview",
                request_id="request_fictional_invalid_target",
                client_version="1.0.0",
            )

    with pytest.raises(
        DocumentActionNotAllowed,
        match="current saved incident revision",
    ):
        record_document_action(
            db_session,
            user_actor,
            incident_id=fictional_incident.id,
            incident_revision_number=999,
            packet_item_id=item.id,
            action="preview",
            request_id="request_fictional_stale_action",
            client_version="1.0.0",
        )
