"""Unit tests for the retry helper (RG-3) — pure, no AI, no GCP, no waiting.

`sleep` is injected so the backoff is exercised without real delays.
"""

import pytest

from backend.pipeline.retry import is_transient, with_retries


class _Recorder:
    """Stand-in for time.sleep that records the delays it was asked for."""

    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


class TestIsTransient:
    @pytest.mark.parametrize(
        "message",
        [
            "503 Service Unavailable",
            "RESOURCE_EXHAUSTED: quota exceeded",
            "429 Too Many Requests",
            "deadline exceeded",
            "the request timed out",
            "502 Bad Gateway",
            "Connection reset by peer",
        ],
    )
    def test_retryable_conditions(self, message):
        assert is_transient(RuntimeError(message)) is True

    @pytest.mark.parametrize(
        "message",
        [
            "403 PERMISSION_DENIED",
            "404 not_found: model does not exist",
            "400 INVALID_ARGUMENT: bad schema",
            "401 unauthenticated",
            "Your default credentials were not found",
        ],
    )
    def test_permanent_conditions(self, message):
        # Retrying these only costs the officer three timeouts.
        assert is_transient(RuntimeError(message)) is False

    def test_builtin_transient_types(self):
        assert is_transient(TimeoutError()) is True
        assert is_transient(ConnectionError()) is True

    def test_unknown_errors_are_not_retried(self):
        assert is_transient(ValueError("something odd")) is False

    def test_permanent_wins_over_transient_wording(self):
        # A 403 that happens to mention a timeout must still not be retried.
        assert (
            is_transient(RuntimeError("403 permission_denied after timeout")) is False
        )


class TestWithRetries:
    def test_returns_immediately_on_success(self):
        sleep = _Recorder()
        assert with_retries(lambda: "ok", sleep=sleep) == "ok"
        assert sleep.delays == []

    def test_recovers_after_a_transient_failure(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("503 Service Unavailable")
            return "recovered"

        assert with_retries(flaky, sleep=_Recorder()) == "recovered"
        assert calls["n"] == 3

    def test_reraises_after_exhausting_attempts(self):
        calls = {"n": 0}

        def always_fails():
            calls["n"] += 1
            raise RuntimeError("503 Service Unavailable")

        with pytest.raises(RuntimeError):
            with_retries(always_fails, attempts=3, sleep=_Recorder())
        assert calls["n"] == 3

    def test_permanent_failure_is_not_retried(self):
        calls = {"n": 0}

        def permanent():
            calls["n"] += 1
            raise RuntimeError("403 permission_denied")

        with pytest.raises(RuntimeError):
            with_retries(permanent, sleep=_Recorder())
        assert calls["n"] == 1  # no wasted attempts

    def test_backoff_grows(self):
        sleep = _Recorder()

        def always_fails():
            raise RuntimeError("503")

        with pytest.raises(RuntimeError):
            with_retries(always_fails, attempts=4, base_delay=1.0, sleep=sleep)
        assert len(sleep.delays) == 3
        assert sleep.delays[0] < sleep.delays[1] < sleep.delays[2]

    def test_delay_is_capped(self):
        sleep = _Recorder()

        def always_fails():
            raise RuntimeError("503")

        with pytest.raises(RuntimeError):
            with_retries(always_fails, attempts=8, base_delay=1.0, sleep=sleep)
        assert max(sleep.delays) <= 8.0 * 1.2  # cap plus jitter headroom

    def test_single_attempt_never_sleeps(self):
        sleep = _Recorder()
        with pytest.raises(RuntimeError):
            with_retries(
                lambda: (_ for _ in ()).throw(RuntimeError("503")),
                attempts=1,
                sleep=sleep,
            )
        assert sleep.delays == []

    def test_original_exception_reaches_the_caller(self):
        class Custom(Exception):
            pass

        with pytest.raises(Custom):
            with_retries(
                lambda: (_ for _ in ()).throw(Custom("permission_denied")),
                sleep=_Recorder(),
            )
