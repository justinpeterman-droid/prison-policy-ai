from backend.reports.workflow_progress import (
    WorkflowProgress,
    calculate_workflow_progress,
)


def progress(**overrides) -> WorkflowProgress:
    values = {
        "has_output_action": False,
        "has_active_generation_job": False,
        "blocking_validation_count": 0,
        "facts_reviewed": False,
        "generated_report_count": 0,
        "reports_reviewed": False,
        "required_digital_forms_complete": False,
        "missing_physical_acknowledgment_count": 0,
        "has_field_notes": False,
    }
    values.update(overrides)
    return calculate_workflow_progress(**values)


def test_progress_precedence_prefers_printed_or_exported():
    result = progress(
        has_output_action=True,
        has_active_generation_job=True,
        blocking_validation_count=3,
    )
    assert result.code == "printed_or_exported"


def test_progress_precedence_prefers_active_generation_over_gaps():
    result = progress(has_active_generation_job=True, blocking_validation_count=3)
    assert result.code == "generating_reports"


def test_progress_reports_blocking_information_count():
    result = progress(blocking_validation_count=2, has_field_notes=True)
    assert result == WorkflowProgress(
        code="needs_information",
        label="Needs information",
        blocking_count=2,
    )


def test_progress_marks_reviewed_facts_ready_to_generate():
    assert progress(facts_reviewed=True).code == "ready_to_generate"


def test_progress_marks_generated_unreviewed_reports_ready_to_review():
    assert progress(
        facts_reviewed=True,
        generated_report_count=2,
        reports_reviewed=False,
    ).code == "ready_to_review"


def test_progress_marks_complete_packet_ready_to_print():
    assert progress(
        facts_reviewed=True,
        generated_report_count=2,
        reports_reviewed=True,
        required_digital_forms_complete=True,
        missing_physical_acknowledgment_count=0,
    ).code == "ready_to_print"


def test_progress_treats_required_physical_paperwork_as_blocking_information():
    result = progress(
        facts_reviewed=True,
        generated_report_count=2,
        reports_reviewed=True,
        required_digital_forms_complete=True,
        missing_physical_acknowledgment_count=1,
        has_field_notes=True,
    )
    assert result == WorkflowProgress(
        code="needs_information",
        label="Needs information",
        blocking_count=1,
    )


def test_progress_combines_validation_and_physical_blockers():
    result = progress(
        blocking_validation_count=2,
        missing_physical_acknowledgment_count=3,
    )
    assert result.blocking_count == 5


def test_progress_distinguishes_started_and_not_started():
    assert progress(has_field_notes=True).code == "field_notes_started"
    assert progress().code == "not_started"
