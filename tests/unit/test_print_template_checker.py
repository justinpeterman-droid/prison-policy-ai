"""Release gate for sanitized weekly and monthly print-template definitions."""

import json

from scripts.check_print_templates import check_print_templates


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_checked_in_weekly_and_monthly_templates_are_release_safe():
    assert check_print_templates() == []


def test_checker_rejects_html_and_filled_log_entries(tmp_path):
    paperwork = tmp_path / "templates" / "paperwork"
    _write(
        paperwork / "weekly" / "catalog.json",
        {"schema_version": 1, "period": "weekly", "templates": []},
    )
    _write(
        paperwork / "monthly" / "catalog.json",
        {"schema_version": 1, "period": "monthly", "templates": ["monthly_test"]},
    )
    _write(
        paperwork / "monthly" / "test.json",
        {
            "code": "monthly_test",
            "title": "<b>Unsafe</b>",
            "period": "monthly",
            "page_size": "letter",
            "orientation": "landscape",
            "definition": {"log_entries": [{"staff": "Real Person"}]},
        },
    )

    errors = check_print_templates(paperwork)

    assert any("HTML" in error for error in errors)
    assert any("log entry" in error for error in errors)
