"""Pure officer-facing progress calculation for incident workspaces."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowProgress:
    code: str
    label: str
    blocking_count: int = 0


_LABELS = {
    "not_started": "Not started",
    "field_notes_started": "Field notes started",
    "needs_information": "Needs information",
    "ready_to_generate": "Ready to generate",
    "generating_reports": "Generating reports",
    "ready_to_review": "Ready to review",
    "awaiting_paperwork": "Awaiting paperwork",
    "ready_to_print": "Ready to print",
    "printed_or_exported": "Printed or exported",
}


def _result(code: str, *, blocking_count: int = 0) -> WorkflowProgress:
    return WorkflowProgress(
        code=code,
        label=_LABELS[code],
        blocking_count=max(0, blocking_count),
    )


def calculate_workflow_progress(
    *,
    has_output_action: bool,
    has_active_generation_job: bool,
    blocking_validation_count: int,
    facts_reviewed: bool,
    generated_report_count: int,
    reports_reviewed: bool,
    required_digital_forms_complete: bool,
    missing_physical_acknowledgment_count: int,
    has_field_notes: bool,
) -> WorkflowProgress:
    """Return one deterministic progress state using the approved precedence.

    Progress never runs backwards. Once reports exist, the packet is somewhere in
    the review-and-paperwork phase and stays there: an officer who has generated
    and reviewed a whole packet but still owes a signature must not be told the
    incident is "Not started". That is why the report-bearing cases are resolved
    together, with `awaiting_paperwork` as their fallback, rather than each being
    a separate test that can fall through to the beginning of the workflow.
    """
    if has_output_action:
        return _result("printed_or_exported")
    if has_active_generation_job:
        return _result("generating_reports")
    if blocking_validation_count > 0:
        return _result(
            "needs_information",
            blocking_count=blocking_validation_count,
        )
    if generated_report_count > 0:
        if not reports_reviewed:
            return _result("ready_to_review")
        if (
            required_digital_forms_complete
            and missing_physical_acknowledgment_count <= 0
        ):
            return _result("ready_to_print")
        return _result(
            "awaiting_paperwork",
            blocking_count=missing_physical_acknowledgment_count,
        )
    if facts_reviewed:
        return _result("ready_to_generate")
    if has_field_notes:
        return _result("field_notes_started")
    return _result("not_started")
