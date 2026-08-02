"""Shared upstream-error classification for the API routes.

Introduced for the chat endpoint (RC-3) and shared with reports: a generic
"Classification failed" tells the officer nothing and tells whoever is
debugging even less. Credentials, an upstream API rejection and a timeout all
need different responses, so they get different messages and log lines.
"""
import socket


def classify_error(exc: Exception) -> tuple[str, int]:
    """Classify an upstream exception into (category, http_status)."""
    msg = str(exc).lower()

    try:
        from google.auth.exceptions import DefaultCredentialsError
        if isinstance(exc, DefaultCredentialsError):
            return "credentials", 503
    except ImportError:
        pass
    if "default credentials were not found" in msg:
        return "credentials", 503

    # Model/route problems are a distinct, very common misconfiguration: a
    # model id that does not exist in this project or region.
    if ("not found" in msg and "model" in msg) or "was not found" in msg:
        return "model", 503
    if "permission" in msg or "403" in msg:
        return "permission", 503

    if isinstance(exc, RuntimeError) and "search api error" in msg:
        return "upstream", 500

    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "timeout", 500
    if "timed out" in msg or "deadline" in msg:
        return "timeout", 500

    if "resource_exhausted" in msg or "429" in msg or "quota" in msg:
        return "quota", 503

    return "internal", 500


ERROR_MESSAGES = {
    "credentials": "Application is not properly configured. Please contact the administrator.",
    "model": "The AI model is not available for this project. Please contact the administrator.",
    "permission": "The application lacks permission for a required service. Please contact the administrator.",
    "upstream": "The policy search service is temporarily unavailable. Please try again in a moment.",
    "timeout": "The request took too long. Please try again with a shorter or more specific question.",
    "quota": "The service is rate limited right now. Please try again in a moment.",
    "internal": "An unexpected error occurred. Please try again. If the problem persists, contact the administrator.",
}
