"""Unit tests for report orchestration (RG-3 / RG-6).

Covers concurrency and failure handling without touching Gemini: the per-report
generator functions are monkeypatched, so nothing here makes a network call.

Importing generator.py pulls google.genai, so these run in CI where deps are
installed and skip cleanly otherwise.
"""
import time

import pytest

try:
    from backend.reports import generator
except ImportError as exc:  # pragma: no cover - environment-dependent
    generator = None
    _import_error = str(exc)

pytestmark = pytest.mark.skipif(
    generator is None,
    reason=f"google-genai not importable: {globals().get('_import_error', '')}",
)

SLOTS = {"persons": [], "charges": ""}


@pytest.fixture
def stub(monkeypatch):
    """Replace the four generators with controllable stand-ins."""
    def _apply(first=None, supervisor=None, cover=None, disciplinary=None):
        monkeypatch.setattr(generator, "generate_first_person",
                            first or (lambda *a, **k: "FIRST"))
        monkeypatch.setattr(generator, "generate_supervisor_summary",
                            supervisor or (lambda *a, **k: "SUPERVISOR"))
        monkeypatch.setattr(generator, "generate_cover_letter",
                            cover or (lambda *a, **k: "COVER"))
        monkeypatch.setattr(generator, "generate_disciplinary",
                            disciplinary or (lambda *a, **k: "DISCIPLINARY"))
    return _apply


class TestSuccessPath:
    def test_generates_the_three_base_reports(self, stub):
        stub()
        reports = generator.generate_all_reports(SLOTS)
        assert reports["first_person"] == "FIRST"
        assert reports["supervisor_summary"] == "SUPERVISOR"
        assert reports["cover_letter"] == "COVER"
        assert "_errors" not in reports

    def test_disciplinary_only_when_charges_exist(self, stub):
        stub()
        assert "disciplinary" not in generator.generate_all_reports(SLOTS)
        with_charges = dict(SLOTS, charges="12-1, 12-3")
        assert generator.generate_all_reports(with_charges)["disciplinary"] == "DISCIPLINARY"

    def test_disciplinary_receives_the_finished_first_person_report(self, stub):
        seen = {}

        def disciplinary(slots, first_person_report, auto_content=None):
            seen["source"] = first_person_report
            return "DISCIPLINARY"

        stub(disciplinary=disciplinary)
        generator.generate_all_reports(dict(SLOTS, charges="12-1"))
        # Sequenced after first_person, not run concurrently with it.
        assert seen["source"] == "FIRST"


class TestConcurrency:
    def test_independent_reports_run_in_parallel(self, stub):
        """Wall-clock should track the slowest call, not the sum of all three."""
        def slow(*a, **k):
            time.sleep(0.3)
            return "SLOW"

        stub(first=slow, supervisor=slow, cover=slow)
        started = time.monotonic()
        generator.generate_all_reports(SLOTS)
        elapsed = time.monotonic() - started
        # Sequential would be ~0.9s; parallel ~0.3s. Generous bound for CI.
        assert elapsed < 0.75


class TestFailureHandling:
    def test_one_failure_does_not_lose_the_others(self, stub):
        def boom(*a, **k):
            raise RuntimeError("upstream exploded")

        stub(supervisor=boom)
        reports = generator.generate_all_reports(SLOTS)
        assert reports["first_person"] == "FIRST"
        assert reports["cover_letter"] == "COVER"
        assert "supervisor_summary" in reports

    def test_failures_are_reported_explicitly(self, stub):
        """A failed section must be flagged, not left to pass for a finished
        report with an error line buried in the body."""
        def boom(*a, **k):
            raise RuntimeError("upstream exploded")

        stub(supervisor=boom)
        reports = generator.generate_all_reports(SLOTS)
        assert reports["_errors"] == ["supervisor_summary"]

    def test_multiple_failures_all_recorded(self, stub):
        def boom(*a, **k):
            raise RuntimeError("upstream exploded")

        stub(first=boom, cover=boom)
        reports = generator.generate_all_reports(SLOTS)
        assert set(reports["_errors"]) == {"first_person", "cover_letter"}

    def test_disciplinary_failure_recorded(self, stub):
        def boom(*a, **k):
            raise RuntimeError("upstream exploded")

        stub(disciplinary=boom)
        reports = generator.generate_all_reports(dict(SLOTS, charges="12-1"))
        assert reports["_errors"] == ["disciplinary"]
