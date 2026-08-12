"""Import persistence mappings here so Alembic can discover all metadata."""

from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.security import AuditEvent, AuthRateLimit, BrowserHandoff, BrowserSession
from backend.persistence.models.sessions import AccessSession, AdminElevation, AdminStepUpToken, RenewalTokenHistory
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
    "AdminElevation",
    "AdminStepUpToken",
    "AuditEvent",
    "AuthRateLimit",
    "BrowserHandoff",
    "BrowserSession",
    "Incident",
    "IncidentRevision",
    "Report",
    "ReportAccess",
    "ReportRevision",
    "ReportStatus",
    "ReportType",
    "RevisionReason",
    "RenewalTokenHistory",
    "StaffMember",
]
