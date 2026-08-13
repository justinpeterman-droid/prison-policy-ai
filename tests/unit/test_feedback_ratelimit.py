"""Unit tests for the in-memory feedback rate limiter (no network, no GCP).

Uses an injected `now` so the fixed-window behavior is deterministic.
"""

import pytest

# feedback.py only imports flask + stdlib, so this runs locally and in CI.
try:
    from backend.webapp.routes import feedback
except ImportError as exc:  # pragma: no cover
    feedback = None
    _err = str(exc)
else:
    _err = None

pytestmark = pytest.mark.skipif(feedback is None, reason=f"import failed: {_err}")


@pytest.fixture(autouse=True)
def _clear_hits():
    """Each test starts with an empty hit table."""
    feedback._hits.clear()
    yield
    feedback._hits.clear()


def test_allows_up_to_the_limit():
    for i in range(5):
        assert (
            feedback._rate_limited("1.2.3.4", now=1000 + i, max_hits=5, window=600)
            is False
        )


def test_blocks_after_the_limit():
    for i in range(5):
        feedback._rate_limited("1.2.3.4", now=1000 + i, max_hits=5, window=600)
    # 6th within the window is blocked.
    assert feedback._rate_limited("1.2.3.4", now=1005, max_hits=5, window=600) is True


def test_window_resets_after_expiry():
    for i in range(5):
        feedback._rate_limited("1.2.3.4", now=1000 + i, max_hits=5, window=600)
    assert feedback._rate_limited("1.2.3.4", now=1005, max_hits=5, window=600) is True
    # Well past the window — quota is fresh again.
    assert feedback._rate_limited("1.2.3.4", now=2000, max_hits=5, window=600) is False


def test_keys_are_independent():
    for i in range(5):
        feedback._rate_limited("1.1.1.1", now=1000 + i, max_hits=5, window=600)
    # A different client is unaffected by the first client's quota.
    assert feedback._rate_limited("2.2.2.2", now=1005, max_hits=5, window=600) is False


# ── URL sanitization ──────────────────────────────────────────────


def test_sanitize_url_strips_access_code():
    out = feedback._sanitize_url("https://x.app/reports?code=slut&tab=1")
    assert "code=slut" not in out
    assert "code" not in out
    assert "tab=1" in out


def test_sanitize_url_strips_case_insensitively():
    out = feedback._sanitize_url("https://x.app/chat?CODE=slut&Token=abc")
    assert "slut" not in out
    assert "abc" not in out


def test_sanitize_url_keeps_clean_url_untouched():
    assert feedback._sanitize_url("https://x.app/reports") == "https://x.app/reports"


def test_sanitize_url_handles_blank():
    assert feedback._sanitize_url("") == "unknown page"
    assert feedback._sanitize_url("   ") == "unknown page"


# ── Field cleaning ────────────────────────────────────────────────


def test_clean_field_flattens_and_escapes():
    out = feedback._clean_field("line1\nline2 | col", 500)
    assert "\n" not in out
    assert "\\|" in out


def test_clean_field_truncates():
    out = feedback._clean_field("a" * 100, 10)
    assert out == "a" * 10 + "…"


def test_clean_field_rejects_non_strings():
    assert feedback._clean_field(None, 10) == ""
    assert feedback._clean_field({"x": 1}, 10) == ""


# ── Issue body ────────────────────────────────────────────────────


def test_build_issue_body_includes_reporter_and_context():
    body = feedback._build_issue_body(
        "It broke",
        "https://x.app/reports",
        "Sgt Smith",
        {"userAgent": "Firefox", "viewport": "800×600"},
    )
    assert "Sgt Smith" in body
    assert "It broke" in body
    assert "Browser context" in body
    assert "Firefox" in body


def test_build_issue_body_anonymous_without_name():
    body = feedback._build_issue_body("hi", "https://x.app", "", {})
    assert "anonymous" in body
    # No context table when nothing usable was supplied.
    assert "Browser context" not in body


def test_build_issue_body_ignores_unknown_context_keys():
    body = feedback._build_issue_body(
        "hi",
        "https://x.app",
        "",
        {"evil": "injected"},
    )
    assert "injected" not in body
