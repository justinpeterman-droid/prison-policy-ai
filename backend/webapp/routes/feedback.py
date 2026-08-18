"""Feedback endpoint for creating GitHub issues."""

import os
import json
import logging
import math
import time
import urllib.request
import urllib.error
import urllib.parse
from collections import defaultdict
from threading import Lock

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
feedback_bp = Blueprint("feedback", __name__)

# ── Simple in-memory rate limit ───────────────────────────────────
# Each feedback submission opens a GitHub issue, so throttle abusive bursts.
# Fixed window per client key; in-memory is sufficient for the single Gunicorn
# worker (state resets on restart — acceptable for spam protection). Everyone
# shares one access code, so we key on client IP rather than the cookie.
RATE_LIMIT_MAX = 5  # submissions...
RATE_LIMIT_WINDOW = 600  # ...per 10 minutes, per client
_hits: dict[str, list[float]] = defaultdict(list)
_hits_lock = Lock()

# ── Payload limits ────────────────────────────────────────────────
# Bound what we accept so a huge or malformed payload can't create an
# unwieldy issue (the front-end maps 413 to a "shorten it" message).
MAX_COMMENT_LEN = 5000  # feedback body
MAX_NAME_LEN = 120  # optional reporter name
MAX_URL_LEN = 2000  # page URL
MAX_CONTEXT_VALUE_LEN = 500  # per browser-context field

# GitHub must never be allowed to hold a Gunicorn thread indefinitely. The
# environment setting is intentionally clamped so a typo cannot disable the
# operational protection by selecting an infinite or extremely large timeout.
DEFAULT_GITHUB_FEEDBACK_TIMEOUT_SECONDS = 10.0
MIN_GITHUB_FEEDBACK_TIMEOUT_SECONDS = 1.0
MAX_GITHUB_FEEDBACK_TIMEOUT_SECONDS = 30.0

# Query params stripped from the reported URL before it ever leaves the
# server — the shared access code rides along in `?code=…` bookmarks and
# must not be written into a GitHub issue.
_SENSITIVE_QUERY_KEYS = {"code", "access_code", "token"}

# Browser-context fields the client may send. Whitelisted so the issue body
# only ever renders known keys, never arbitrary attacker-supplied labels.
_CONTEXT_FIELDS = {
    "pageTitle": "Page title",
    "userAgent": "User agent",
    "viewport": "Viewport",
    "screen": "Screen",
    "referrer": "Referrer",
    "language": "Language",
}


def _rate_limited(
    key: str,
    now: float | None = None,
    max_hits: int = RATE_LIMIT_MAX,
    window: int = RATE_LIMIT_WINDOW,
) -> bool:
    """Return True if *key* has already used its quota in the current window.

    Records the hit when allowed. Pure/deterministic given `now`, so it is unit
    tested without Flask.
    """
    now = time.time() if now is None else now
    cutoff = now - window
    with _hits_lock:
        times = _hits[key]
        times[:] = [t for t in times if t > cutoff]  # prune expired
        if len(times) >= max_hits:
            return True
        times.append(now)
        return False


def _client_key() -> str:
    """Best-effort client identifier. Behind Cloud Run the real IP is the first
    hop of X-Forwarded-For; fall back to remote_addr."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _github_timeout_seconds() -> float:
    """Return the finite, bounded timeout for the outbound GitHub request."""
    raw = os.environ.get(
        "FEEDBACK_GITHUB_TIMEOUT_SECONDS",
        str(DEFAULT_GITHUB_FEEDBACK_TIMEOUT_SECONDS),
    )
    try:
        value = float(raw)
    except ValueError:
        logger.warning("feedback_github_timeout_config_invalid")
        return DEFAULT_GITHUB_FEEDBACK_TIMEOUT_SECONDS
    if not math.isfinite(value):
        logger.warning("feedback_github_timeout_config_invalid")
        return DEFAULT_GITHUB_FEEDBACK_TIMEOUT_SECONDS
    return min(
        max(value, MIN_GITHUB_FEEDBACK_TIMEOUT_SECONDS),
        MAX_GITHUB_FEEDBACK_TIMEOUT_SECONDS,
    )


def _sanitize_url(url: str) -> str:
    """Strip the shared access code (and other secrets) from a page URL.

    A URL bookmarked as `…/reports?code=slut` would otherwise leak the access
    code into a GitHub issue. Pure/deterministic — unit tested without Flask.
    """
    url = (url or "").strip()
    if not url:
        return "unknown page"
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "unknown page"
    if not parts.query:
        return url
    kept = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _SENSITIVE_QUERY_KEYS
    ]
    cleaned = urllib.parse.urlencode(kept)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, cleaned, parts.fragment))


def _clean_field(value, max_len: int) -> str:
    """Coerce a client-supplied value to a bounded, single-line string.

    Collapses newlines and trims length so context values can't break out of
    the Markdown table or blow up the issue body.
    """
    if not isinstance(value, str):
        return ""
    value = value.replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()
    if len(value) > max_len:
        value = value[:max_len] + "…"
    return value


def _build_issue_body(feedback_text: str, page_url: str, name: str, context: dict) -> str:
    """Assemble the Markdown issue body. Pure — unit tested without network."""
    reporter = f" from **{name}**" if name else ""
    lines = [
        f"**Page:** `{page_url}`",
        f"**Reported by:**{reporter or ' (anonymous)'}",
        "",
        "**Feedback / bug report:**",
        feedback_text,
    ]

    rows = []
    for key, label in _CONTEXT_FIELDS.items():
        val = _clean_field((context or {}).get(key, ""), MAX_CONTEXT_VALUE_LEN)
        if val:
            rows.append(f"| {label} | {val} |")
    if rows:
        lines += [
            "",
            "<details><summary>Browser context</summary>",
            "",
            "| Field | Value |",
            "| --- | --- |",
            *rows,
            "",
            "</details>",
        ]
    return "\n".join(lines)


@feedback_bp.route("/api/feedback", methods=["POST"])
def feedback_api():
    data = request.get_json(silent=True) or {}
    feedback_text = data.get("comment", "").strip()
    page_url = _sanitize_url(data.get("url", ""))
    name = _clean_field(data.get("name", ""), MAX_NAME_LEN)
    raw_context = data.get("context")
    context: dict[str, object] = raw_context if isinstance(raw_context, dict) else {}

    if not feedback_text:
        return jsonify({"error": "No feedback provided"}), 400

    if len(feedback_text) > MAX_COMMENT_LEN or len(page_url) > MAX_URL_LEN:
        return jsonify({"error": "Feedback is too long. Please shorten it."}), 413

    if _rate_limited(_client_key()):
        logger.warning("Feedback rate limit hit")
        return jsonify({"error": "Too many feedback submissions. Please wait a few minutes and try again."}), 429

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN not set in environment.")
        return jsonify({"error": "Server misconfigured. Cannot create issue."}), 500

    repo = "justinpeterman-droid/prison-policy-ai"
    api_url = f"https://api.github.com/repos/{repo}/issues"

    issue_title = f"User Feedback from {page_url}"
    issue_body = _build_issue_body(feedback_text, page_url, name, context)

    payload = json.dumps({"title": issue_title, "body": issue_body, "labels": ["feedback"]}).encode("utf-8")

    req = urllib.request.Request(api_url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {github_token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=_github_timeout_seconds()) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return jsonify({"success": True, "issue_url": res_data.get("html_url")})
    except TimeoutError:
        logger.warning("feedback_github_timeout")
        return jsonify({"error": "Feedback service is temporarily unavailable. Please try again."}), 503
    except urllib.error.HTTPError as error:
        logger.error("GitHub API error: %s %s", error.code, error.read().decode("utf-8"))
        return jsonify({"error": "Failed to submit feedback to GitHub."}), 500
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            logger.warning("feedback_github_timeout")
            return jsonify({"error": "Feedback service is temporarily unavailable. Please try again."}), 503
        logger.error("GitHub API transport error: %s", error.reason)
        return jsonify({"error": "Failed to submit feedback to GitHub."}), 502
    except Exception:
        logger.exception("Unexpected error submitting feedback")
        return jsonify({"error": "An unexpected error occurred."}), 500
