"""Server-enforced action policy and audited persistence for incident outputs."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.audit import (
    AuditEventInput,
    AuditWriter,
    PostgresAuditWriter,
)
from backend.persistence.models.forms import (
    DocumentActionEvent,
    FormTemplate,
    IncidentPacketItem,
)
from backend.persistence.models.reporting import ReportType
from backend.reports.persistence import (
    IncidentNotFound,
    ReportNotFound,
    get_incident,
    get_report,
)


class DocumentActionNotAllowed(ValueError):
    """The requested action is not valid for the output presentation."""


class DocumentActionNotFound(LookupError):
    """The requested output target is absent or unavailable to the actor."""


@dataclass(frozen=True)
class DocumentActionEventView:
    event_id: UUID
    incident_id: UUID
    packet_item_id: UUID | None
    report_id: UUID | None
    action: str
    incident_revision_number: int
    created_at: datetime


_DOWNLOAD_ACTIONS = {
    "word": "download_word",
    "pdf": "download_pdf",
    "print": "print",
}
_EVENT_ACTIONS = frozenset({
    "preview",
    "print",
    "download_word",
    "download_pdf",
    "copy_text",
})
_COPY_REPORT_TYPES = frozenset({
    ReportType.SUPERVISOR_SUMMARY,
    ReportType.DISCIPLINARY,
})
_DOCUMENT_REPORT_TYPES = frozenset({
    ReportType.FIRST_PERSON,
    ReportType.COVER_LETTER,
    ReportType.INVESTIGATION,
    ReportType.FORM_005,
})


def allowed_form_actions(
    output_kind: str,
    definition: Mapping[str, object],
) -> frozenset[str]:
    """Return only actions explicitly supported by a catalog form definition."""
    if output_kind == "physical_only":
        return frozenset()
    if output_kind != "digital_document":
        raise DocumentActionNotAllowed(f"Unknown form output kind: {output_kind}")
    if not isinstance(definition, Mapping):
        raise DocumentActionNotAllowed("The form definition is invalid.")
    raw_formats = definition.get("download_formats", [])
    if not isinstance(raw_formats, list) or not all(
        isinstance(value, str) for value in raw_formats
    ):
        raise DocumentActionNotAllowed("The form download formats are invalid.")

    actions = {"preview"}
    for value in raw_formats:
        mapped = _DOWNLOAD_ACTIONS.get(value)
        if mapped is None:
            raise DocumentActionNotAllowed(
                f"Unsupported form download format: {value}"
            )
        actions.add(mapped)
    return frozenset(actions)


def validate_form_action(
    *,
    output_kind: str,
    definition: Mapping[str, object],
    action: str,
) -> None:
    if output_kind == "physical_only":
        raise DocumentActionNotAllowed(
            "Physical-only paperwork has no digital action."
        )
    if action not in allowed_form_actions(output_kind, definition):
        raise DocumentActionNotAllowed(
            f"{action} is not allowed for {output_kind}."
        )


def _report_type(value: str | ReportType) -> ReportType:
    if isinstance(value, ReportType):
        return value
    try:
        return ReportType(value)
    except ValueError as exc:
        raise DocumentActionNotAllowed(f"Unknown report type: {value}") from exc


def allowed_report_actions(report_type: str | ReportType) -> frozenset[str]:
    """Separate copy-to-records reports from printable document reports."""
    resolved = _report_type(report_type)
    if resolved in _COPY_REPORT_TYPES:
        return frozenset({"edit", "copy_text"})
    if resolved in _DOCUMENT_REPORT_TYPES:
        return frozenset({"edit", "preview", "print", "download_word"})
    raise DocumentActionNotAllowed(f"Unknown report type: {resolved.value}")


def validate_report_action(
    report_type: str | ReportType,
    action: str,
) -> None:
    resolved = _report_type(report_type)
    if action not in allowed_report_actions(resolved):
        raise DocumentActionNotAllowed(
            f"{action} is not allowed for {resolved.value}."
        )


def _event_view(row: DocumentActionEvent) -> DocumentActionEventView:
    return DocumentActionEventView(
        event_id=row.id,
        incident_id=row.incident_id,
        packet_item_id=row.packet_item_id,
        report_id=row.report_id,
        action=row.action,
        incident_revision_number=row.incident_revision_number,
        created_at=row.created_at,
    )


def _validate_request_metadata(request_id: str, client_version: str | None) -> None:
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 64:
        raise DocumentActionNotAllowed("The document action request ID is invalid.")
    if client_version is not None and (
        not isinstance(client_version, str) or len(client_version) > 64
    ):
        raise DocumentActionNotAllowed("The document action client version is invalid.")


def record_document_action(
    session: Session,
    actor,
    *,
    incident_id: UUID,
    incident_revision_number: int,
    action: str,
    request_id: str,
    client_version: str | None,
    packet_item_id: UUID | None = None,
    report_id: UUID | None = None,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
) -> DocumentActionEventView:
    """Validate, persist, and audit one successful document-side action."""
    if (packet_item_id is None) == (report_id is None):
        raise DocumentActionNotAllowed(
            "A document action requires exactly one document target."
        )
    if action not in _EVENT_ACTIONS:
        raise DocumentActionNotAllowed(f"Unknown document action: {action}")
    _validate_request_metadata(request_id, client_version)

    try:
        incident_view = get_incident(session, actor, incident_id)
    except IncidentNotFound:
        raise DocumentActionNotFound("Document target not found.") from None
    incident = incident_view.incident
    if incident.current_revision_number != incident_revision_number:
        raise DocumentActionNotAllowed(
            "Document actions require the current saved incident revision."
        )

    details: dict[str, object]
    target_type: str
    target_id: UUID
    if packet_item_id is not None:
        target = session.execute(
            select(IncidentPacketItem, FormTemplate)
            .join(FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id)
            .where(
                IncidentPacketItem.id == packet_item_id,
                IncidentPacketItem.incident_id == incident_id,
            )
        ).one_or_none()
        if target is None:
            raise DocumentActionNotFound("Document target not found.")
        packet_item, template = target
        if packet_item.packet_state != "selected":
            raise DocumentActionNotAllowed(
                "Only selected paperwork can receive a document action."
            )
        if packet_item.source_incident_revision_number != incident_revision_number:
            raise DocumentActionNotAllowed(
                "The paperwork packet must be rebuilt for the current saved incident revision."
            )
        validate_form_action(
            output_kind=template.output_kind,
            definition=template.definition,
            action=action,
        )
        details = {
            "target_kind": "form",
            "template_code": template.code,
        }
        target_type = "incident_packet_item"
        target_id = packet_item.id
    else:
        assert report_id is not None
        try:
            report_view = get_report(session, actor, report_id)
        except ReportNotFound:
            raise DocumentActionNotFound("Document target not found.") from None
        report = report_view.report
        if report.incident_id != incident_id:
            raise DocumentActionNotFound("Document target not found.")
        validate_report_action(report.report_type, action)
        details = {
            "target_kind": "report",
            "report_type": report.report_type.value,
        }
        target_type = "report"
        target_id = report.id

    fixed = now or datetime.now(UTC)
    row = DocumentActionEvent(
        id=uuid4(),
        incident_id=incident_id,
        packet_item_id=packet_item_id,
        report_id=report_id,
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action=action,
        incident_revision_number=incident_revision_number,
        details=details,
        request_id=request_id,
        created_at=fixed,
    )
    session.add(row)

    audit_details: dict[str, object] = {
        "document_action": action,
        "incident_id": str(incident_id),
        "incident_revision_number": incident_revision_number,
    }
    if packet_item_id is not None:
        audit_details["packet_item_id"] = str(packet_item_id)
    if report_id is not None:
        audit_details["report_id"] = str(report_id)
    (audit_writer or PostgresAuditWriter()).append(
        session,
        AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action="document.action_recorded",
            result="success",
            request_id=request_id,
            target_type=target_type,
            target_id=target_id,
            details=audit_details,
            client_version=client_version,
        ),
    )
    session.flush()
    return _event_view(row)
