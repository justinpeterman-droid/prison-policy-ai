"""Cached OAuth access token from Application Default Credentials.

Two REST callers now need one — the Discovery Engine search in `query.py` and
the Ranking API in `rerank.py` — and they run back to back on every chat turn.
A per-module cache would refresh credentials twice for one question, so the
cache lives here and both share it.

Kept out of `query.py` deliberately: importing the whole search module to get a
token would make `rerank` depend on `query`, which imports `rerank`.
"""
import logging
import time

import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

# Refresh this many seconds before the token actually expires, so a call that
# starts just under the wire doesn't finish just over it.
EXPIRY_MARGIN_S = 60
# Used when the credential reports no expiry of its own; comfortably inside the
# one-hour lifetime GCP issues.
DEFAULT_LIFETIME_S = 3500

_token_cache: dict = {"token": None, "expiry": 0}


def get_access_token() -> str:
    """Get an OAuth token from Application Default Credentials."""
    if _token_cache["token"] and time.time() < _token_cache["expiry"] - EXPIRY_MARGIN_S:
        return _token_cache["token"]

    creds, _project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    _token_cache["token"] = creds.token
    _token_cache["expiry"] = (creds.expiry.timestamp() if creds.expiry
                              else time.time() + DEFAULT_LIFETIME_S)
    return creds.token


def reset_token_cache() -> None:
    """Drop the cached token. For tests."""
    _token_cache["token"] = None
    _token_cache["expiry"] = 0
