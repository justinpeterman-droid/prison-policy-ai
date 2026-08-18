"""Regression tests for security findings surfaced by release PR #88."""

from pathlib import Path

import backend.reports.report_validator as report_validator


ROOT = Path(__file__).resolve().parents[2]
OCR_MANUAL = ROOT / "scripts" / "ocr_manual.py"


def test_statement_closer_repair_does_not_use_unbounded_regex_search(monkeypatch):
    """RW-014 must not run an unanchored whitespace regex over report text."""

    def reject_regex_search(*_args, **_kwargs):
        raise AssertionError("statement-closer repair must use literal suffix matching")

    monkeypatch.setattr(report_validator.re, "sub", reject_regex_search)
    report = (" " * 4096) + "not a statement closer"

    assert report_validator.repair(report) == (report, [])


def test_ocr_manual_keeps_api_key_out_of_the_request_url():
    """API keys belong in the authenticated header, never a loggable URL."""
    source = OCR_MANUAL.read_text(encoding="utf-8")

    assert "generateContent?key=" not in source
    assert '"x-goog-api-key": API_KEY' in source
    assert "headers=headers" in source
