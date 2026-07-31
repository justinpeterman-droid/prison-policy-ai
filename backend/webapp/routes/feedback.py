"""Feedback endpoint for creating GitHub issues."""
import os
import json
import logging
import time
import urllib.request
import urllib.error
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
RATE_LIMIT_MAX = 5           # submissions...
RATE_LIMIT_WINDOW = 600      # ...per 10 minutes, per client
_hits: dict[str, list[float]] = defaultdict(list)
_hits_lock = Lock()


def _rate_limited(key: str, now: float | None = None,
                  max_hits: int = RATE_LIMIT_MAX,
                  window: int = RATE_LIMIT_WINDOW) -> bool:
    """Return True if *key* has already used its quota in the current window.

    Records the hit when allowed. Pure/deterministic given `now`, so it is unit
    tested without Flask.
    """
    now = time.time() if now is None else now
    cutoff = now - window
    with _hits_lock:
        times = _hits[key]
        times[:] = [t for t in times if t > cutoff]   # prune expired
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


@feedback_bp.route("/api/feedback", methods=["POST"])
def feedback_api():
    data = request.get_json(silent=True) or {}
    feedback_text = data.get("comment", "").strip()
    page_url = data.get("url", "unknown page")

    if not feedback_text:
        return jsonify({"error": "No feedback provided"}), 400

    if _rate_limited(_client_key()):
        logger.warning("Feedback rate limit hit")
        return jsonify({
            "error": "Too many feedback submissions. Please wait a few minutes and try again."
        }), 429

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN not set in environment.")
        return jsonify({"error": "Server misconfigured. Cannot create issue."}), 500

    repo = "justinpeterman-droid/prison-policy-ai"
    api_url = f"https://api.github.com/repos/{repo}/issues"
    
    # Format the issue body (real newlines — GitHub renders Markdown)
    issue_title = f"User Feedback from {page_url}"
    issue_body = f"**Page:** `{page_url}`\n\n**Feedback/Improvement:**\n{feedback_text}"
    
    payload = json.dumps({
        "title": issue_title,
        "body": issue_body,
        "labels": ["feedback"]
    }).encode("utf-8")
    
    req = urllib.request.Request(api_url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {github_token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return jsonify({"success": True, "issue_url": res_data.get("html_url")})
    except urllib.error.HTTPError as e:
        logger.error(f"GitHub API error: {e.code} {e.read().decode('utf-8')}")
        return jsonify({"error": "Failed to submit feedback to GitHub."}), 500
    except Exception:
        logger.exception("Unexpected error submitting feedback")
        return jsonify({"error": "An unexpected error occurred."}), 500
