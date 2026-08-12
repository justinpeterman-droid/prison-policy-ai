"""Shared owner, preparer, and Admin report record policies."""
from backend.persistence.models.reporting import Report
from backend.webapp.api_v1.middleware import Actor


def _has_report_access(actor: Actor, report: Report) -> bool:
    if actor.role == "admin":
        return True
    return actor.staff_member_id in {
        report.reporting_staff_member_id,
        report.prepared_by_staff_member_id,
    }


def can_read_report(actor: Actor, report: Report) -> bool:
    return _has_report_access(actor, report)


def can_edit_report(actor: Actor, report: Report) -> bool:
    return _has_report_access(actor, report)


def can_export_report(actor: Actor, report: Report) -> bool:
    return _has_report_access(actor, report)
