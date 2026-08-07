"""Unit tests for the deterministic BMU-convention helpers in routes/reports.py.

These are the pure functions that normalize officer input before it ever
reaches the 005 (time formats, incident numbers, name/rank parsing, shift
labels). No AI, no GCP — but importing the module pulls google.genai, so these
run in CI where requirements are installed, and are skipped gracefully if the
Vertex SDK isn't importable locally.
"""
import datetime

import pytest

# routes/reports.py imports the Vertex AI SDK at module load. In CI (deps
# installed) these tests run; if the SDK isn't importable locally, skip cleanly
# instead of erroring — the functions under test make no network calls.
try:
    from backend.webapp.routes import reports
except ImportError as exc:  # pragma: no cover - environment-dependent
    reports = None
    _import_error = str(exc)
else:
    _import_error = None

pytestmark = pytest.mark.skipif(
    reports is None,
    reason=f"google-genai SDK not importable: {_import_error}",
)


class TestTo12h:
    @pytest.mark.parametrize("raw,expected", [
        ("2200", "10:00 pm"),
        ("0930", "9:30 am"),
        ("13:00", "1:00 pm"),
        ("22:00", "10:00 pm"),
        ("10:00 PM", "10:00 pm"),
        ("approximately 10:42pm", "10:42 pm"),
    ])
    def test_normalizes_to_12_hour(self, raw, expected):
        assert reports._to_12h(raw) == expected

    def test_unparseable_returned_unchanged(self):
        assert reports._to_12h("noon") == "noon"

    def test_empty_returned_unchanged(self):
        assert reports._to_12h("") == ""


class TestValidateAndCleanTime:
    @pytest.mark.parametrize("raw,expected", [
        ("2200", ("10:00 pm", True)),
        ("1422", ("2:22 pm", True)),
        ("7:22AAm", ("7:22 am", True)),   # double-suffix typo, recovered
    ])
    def test_recoverable_inputs_are_cleaned(self, raw, expected):
        assert reports._validate_and_clean_time(raw) == expected

    def test_out_of_range_military_is_invalid(self):
        cleaned, valid = reports._validate_and_clean_time("2577")
        assert valid is False
        assert cleaned == "2577"


class TestBuildIncidentNumber:
    def test_uses_iso_date_year_month(self):
        assert reports._build_incident_number("448", "2025-06-15") == "2025-06-448"

    def test_uses_us_date_and_zero_pads(self):
        assert reports._build_incident_number("7", "03-15-2024") == "2024-03-007"

    def test_keeps_only_last_three_digits(self):
        # Falls back to the current year-month when no date is given.
        out = reports._build_incident_number("448291", None)
        assert out.endswith("-291")
        ym = datetime.datetime.now().strftime("%Y-%m")
        assert out == f"{ym}-291"

    def test_no_digits_returns_empty(self):
        assert reports._build_incident_number("", None) == ""


class TestNameAndRankParsing:
    def test_parse_last_first(self):
        assert reports._parse_name("Garcia, Luis") == ("Garcia", "Luis", "")

    def test_parse_last_first_middle(self):
        assert reports._parse_name("Quintero, Lee A") == ("Quintero", "Lee", "A")

    def test_parse_empty(self):
        assert reports._parse_name("") == ("", "", "")

    @pytest.mark.parametrize("full,expected", [
        ("Sgt. Dana Halvorsen", "Sgt."),
        ("Sergeant Dana", "Sgt."),   # spelled-out rank abbreviated
        ("Corporal Okafor", "Cpl."),
    ])
    def test_parse_rank(self, full, expected):
        assert reports._parse_rank(full) == expected

    def test_no_rank_returns_empty(self):
        assert reports._parse_rank("Dana Halvorsen") == ""


class TestFormatShift:
    @pytest.mark.parametrize("raw,expected", [
        ("A", "A Shift"),
        ("b", "B Shift"),
        ("Day Shift", "Day Shift"),  # already spelled out — left alone
        ("", ""),
    ])
    def test_format_shift(self, raw, expected):
        assert reports._format_shift(raw) == expected


class TestTitlecase:
    @pytest.mark.parametrize("raw,expected", [
        ("john", "John"),
        ("mary jane", "Mary Jane"),
        ("", ""),
    ])
    def test_titlecase(self, raw, expected):
        assert reports._titlecase(raw) == expected


class TestNormalizeLocation:
    def test_empty_passes_through(self):
        assert reports._normalize_location("") == ""

    def test_none_passes_through(self):
        assert reports._normalize_location(None) is None

    def test_returns_string_for_arbitrary_input(self):
        assert isinstance(reports._normalize_location("somewhere unmapped"), str)


class TestStyleRulings:
    """Conformance with templates/gold_reports/STYLE_RULINGS.md."""

    def test_ruling_12_narrative_time_has_a_space(self):
        assert reports._to_12h("2200") == "10:00 pm"
        assert reports._to_12h("0930") == "9:30 am"

    def test_ruling_13_form_time_uses_the_form_convention(self):
        # The 005 TIME box differs from the narrative on purpose.
        assert reports._to_form_time("2150") == "APX. 9:50 PM"
        assert reports._to_form_time("9:50pm") == "APX. 9:50 PM"

    def test_ruling_13_unparseable_form_time_passes_through(self):
        assert reports._to_form_time("noon") == "noon"
        assert reports._to_form_time("") == ""

    def test_ruling_1_and_3_form_constants(self):
        assert reports.MSF_REFERENCE == "MSF 205"
        assert reports.SEE_ABOVE == "Same as above"
