"""Import persistence mappings here so Alembic can discover all metadata."""

from backend.persistence.models.browser import BrowserSessionBinding
from backend.persistence.models.forms import (
    DocumentActionEvent,
    FormInstance,
    FormTemplate,
    IncidentPacketItem,
    PhysicalPaperworkAcknowledgment,
)
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.paperwork import PaperworkRecord, PaperworkRevision
from backend.persistence.models.security import (
    AuditEvent,
    AuthRateLimit,
    BrowserHandoff,
    BrowserSession,
    IdempotencyRecord,
)
from backend.persistence.models.sessions import (
    AccessSession,
    AdminElevation,
    AdminStepUpToken,
    RenewalTokenHistory,
)
from backend.persistence.models.jobs import AiJob, Export, TaskOutbox
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
    ReportRevision,
    ReportStatus,
    ReportType,
    RevisionReason,
)

__all__ = [
    "AccessSession",
    "Account",
    "AiJob",
    "AdminElevation",
    "AdminStepUpToken",
    "AuditEvent",
    "AuthRateLimit",
    "BrowserHandoff",
    "BrowserSession",
    "BrowserSessionBinding",
    "DocumentActionEvent",
    "Export",
    "FormInstance",
    "FormTemplate",
    "Incident",
    "IncidentPacketItem",
    "IncidentRevision",
    "IdempotencyRecord",
    "PaperworkRecord",
    "PaperworkRevision",
    "PhysicalPaperworkAcknowledgment",
    "Report",
    "ReportAccess",
    "ReportRevision",
    "ReportStatus",
    "ReportType",
    "RevisionReason",
    "RenewalTokenHistory",
    "StaffMember",
    "TaskOutbox",
]
