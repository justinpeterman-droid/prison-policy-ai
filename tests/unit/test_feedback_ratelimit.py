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
        assert feedback._rate_limited("1.2.3.4", now=1000 + i, max_hits=5, window=600) is False


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
