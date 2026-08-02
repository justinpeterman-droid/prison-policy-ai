"""Bounded retry with exponential backoff for transient upstream failures.

Every Gemini and Discovery Engine call in this app is a single point of failure
for something the officer is waiting on: one 503 during report generation used
to bake "[Error generating first person report]" into their document, with no
second attempt. These are network calls to a shared, rate-limited service, so
transient failure is normal operating condition rather than an exception.

Retrying is only correct for failures a retry could actually fix. A bad model
id or a missing permission fails identically every time, so those re-raise
immediately instead of costing the officer three timeouts before showing an
error.

Pure Python — no AI, no GCP — so it is unit tested directly.
"""
import logging
import random
import time

logger = logging.getLogger(__name__)

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 1.0
MAX_DELAY = 8.0

# Matched against the exception's type name + message, because the SDK raises
# several different exception classes for what is operationally the same
# transient condition.
_TRANSIENT_MARKERS = (
    "resource_exhausted", "rate limit", "ratelimit", "quota",
    "unavailable", "deadline", "timed out", "timeout",
    "internal error", "internalservererror", "connection reset",
    "connection aborted", "server error",
    "500", "502", "503", "504", "429",
)

# Checked first: retrying these is pure latency, the answer will not change.
_PERMANENT_MARKERS = (
    "permission_denied", "unauthenticated", "invalid_argument",
    "not_found", "failed_precondition", "default credentials were not found",
    "400", "401", "403", "404",
)


def is_transient(exc: BaseException) -> bool:
    """True when retrying the same call could plausibly succeed."""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    text = f"{type(exc).__name__} {exc}".lower()
    if any(marker in text for marker in _PERMANENT_MARKERS):
        return False
    return any(marker in text for marker in _TRANSIENT_MARKERS)


def with_retries(fn, *, attempts: int = DEFAULT_ATTEMPTS,
                 base_delay: float = DEFAULT_BASE_DELAY,
                 sleep=time.sleep, describe: str = "upstream call"):
    """Call `fn()`, retrying transient failures with exponential backoff.

    Permanent failures and the final attempt re-raise, so the caller always sees
    the real exception rather than a swallowed one. `sleep` is injectable so
    tests exercise the backoff without actually waiting.
    """
    attempts = max(1, attempts)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt >= attempts or not is_transient(exc):
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), MAX_DELAY)
            delay += random.uniform(0, delay * 0.1)  # jitter: avoid retry convoys
            # Log the type, not the message — upstream errors can echo back
            # request content, and these prompts carry inmate/staff detail.
            logger.warning("%s failed (attempt %d/%d), retrying in %.1fs: %s",
                           describe, attempt, attempts, delay, type(exc).__name__)
            sleep(delay)
