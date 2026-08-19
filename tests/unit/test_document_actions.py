"""Closed presentation/action policy for incident outputs."""

import pytest

from backend.forms.output_events import (
    DocumentActionNotAllowed,
    allowed_form_actions,
    allowed_report_actions,
    validate_form_action,
    validate_report_action,
)


def test_digital_form_actions_follow_catalog_download_formats():
    assert allowed_form_actions(
        "digital_document",
        {"download_formats": ["word", "print"]},
    ) == frozenset({"preview", "print", "download_word"})
    assert allowed_form_actions(
        "digital_document",
        {"download_formats": ["pdf", "print"]},
    ) == frozenset({"preview", "print", "download_pdf"})
    assert allowed_form_actions(
        "digital_document",
        {"download_formats": ["print"]},
    ) == frozenset({"preview", "print"})


def test_physical_only_forms_expose_no_digital_actions():
    assert allowed_form_actions(
        "physical_only",
        {"download_formats": ["word", "pdf", "print"]},
    ) == frozenset()

    with pytest.raises(
        DocumentActionNotAllowed,
        match="Physical-only paperwork has no digital action",
    ):
        validate_form_action(
            output_kind="physical_only",
            definition={"download_formats": []},
            action="print",
        )


def test_unknown_output_kinds_and_formats_fail_closed():
    with pytest.raises(DocumentActionNotAllowed, match="output kind"):
        allowed_form_actions("unknown", {})
    with pytest.raises(DocumentActionNotAllowed, match="download format"):
        allowed_form_actions(
            "digital_document",
            {"download_formats": ["html"]},
        )


def test_copy_text_is_only_available_for_copy_to_records_reports():
    assert allowed_report_actions("supervisor_summary") == frozenset(
        {"edit", "copy_text"}
    )
    assert allowed_report_actions("disciplinary") == frozenset(
        {"edit", "copy_text"}
    )
    assert "copy_text" not in allowed_report_actions("first_person")
    assert "print" not in allowed_report_actions("supervisor_summary")
    assert "download_word" not in allowed_report_actions("disciplinary")

    validate_report_action("supervisor_summary", "copy_text")
    validate_report_action("disciplinary", "copy_text")
    with pytest.raises(
        DocumentActionNotAllowed,
        match="copy_text is not allowed for first_person",
    ):
        validate_report_action("first_person", "copy_text")
    with pytest.raises(
        DocumentActionNotAllowed,
        match="print is not allowed for supervisor_summary",
    ):
        validate_report_action("supervisor_summary", "print")
