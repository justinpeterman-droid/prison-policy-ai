"""Prison Policy AI — configuration."""

import os
import logging
from pathlib import Path

# Paths
ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
EXTRACTED_DIR = DATA_DIR / "extracted"
REVIEWED_DIR = DATA_DIR / "reviewed"
CHUNKS_DIR = DATA_DIR / "chunks"
TEMPLATES_DIR = ROOT / "templates"

# GCP
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0968389176")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
BUCKET_NAME = os.getenv("GCS_BUCKET", f"{PROJECT_ID}-policy-ai")

# Vertex AI
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# ── Gemini model tiers ──
# Two tiers, routed per call site (see each pipeline module):
#   FAST — cheap, structured, high-volume calls: the chat gate, incident
#          classification, and slot extraction.
#   PRO  — quality-critical prose: the chat answer synthesis and the report
#          narrative generators, where citation-following and instruction
#          adherence matter most.
# Pin a specific version here (or via env) rather than an auto-tracking alias so
# report/answer behavior doesn't shift under us on a silent model bump.
FAST_MODEL = os.getenv("FAST_MODEL", "gemini-3.6-flash")
# Gemini 3.1 Pro is still in preview (launched 2026-02-19) — Vertex only serves
# it under the literal "-preview" suffix. The bare "gemini-3.1-pro" id does not
# exist and 404s every call, which is why every PRO_MODEL call site (report
# generation, chat answers) failed while FAST_MODEL kept working: confirmed
# against the actual us-central1 Model Garden listing, which has
# gemini-3.1-pro-preview but no gemini-3.1-pro. Drop the suffix once Google
# promotes this model to GA and publishes a non-preview id.
PRO_MODEL = os.getenv("PRO_MODEL", "gemini-3.1-pro-preview")
# Back-compat alias — GENERATION_MODEL historically meant "the flash model".
# Anything still importing it gets the FAST tier; override via its own env var.
GENERATION_MODEL = os.getenv("GENERATION_MODEL", FAST_MODEL)

# Location for Gemini model calls. The Gemini 3.x models are served from the
# 'global' endpoint (not a region), so this defaults to 'global' even though the
# Agent Builder data store / corpus live in us-central1. Override with
# GCP_MODEL_LOCATION if you pin older regional models in the tiers above.
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", "global")

# ── Agent Builder / Discovery Engine (policy chat retrieval) ──
# The policy search targets an *engine* serving config. Every part of that
# resource path is an env knob: a mismatch in any one of them makes the search
# 404 and takes the whole chat down, so they must be inspectable and
# overridable without a code change.
AGENT_BUILDER_LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "global")
AGENT_BUILDER_COLLECTION = os.getenv("AGENT_BUILDER_COLLECTION", "default_collection")
AGENT_BUILDER_ENGINE_ID = os.getenv("AGENT_BUILDER_ENGINE_ID", "prison-policies-engine")
AGENT_BUILDER_SERVING_CONFIG = os.getenv("AGENT_BUILDER_SERVING_CONFIG", "default_search")


def serving_config_path() -> str:
    """Fully-qualified Discovery Engine serving config for the policy search."""
    return (
        f"projects/{PROJECT_ID}/locations/{AGENT_BUILDER_LOCATION}"
        f"/collections/{AGENT_BUILDER_COLLECTION}"
        f"/engines/{AGENT_BUILDER_ENGINE_ID}"
        f"/servingConfigs/{AGENT_BUILDER_SERVING_CONFIG}"
    )


def search_config_summary() -> dict:
    """Resolved search config, for logs and the diagnostic script.
    Contains no secrets — safe to log."""
    return {
        "project": PROJECT_ID,
        "agent_builder_location": AGENT_BUILDER_LOCATION,
        "collection": AGENT_BUILDER_COLLECTION,
        "engine_id": AGENT_BUILDER_ENGINE_ID,
        "serving_config": AGENT_BUILDER_SERVING_CONFIG,
        "serving_config_path": serving_config_path(),
        "model_location": MODEL_LOCATION,
        "fast_model": FAST_MODEL,
        "pro_model": PRO_MODEL,
    }


CORPUS_NAME = os.getenv("RAG_CORPUS_NAME", "prison-policies")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Auth — simple shared access code. Set via ACCESS_CODE env var.
# No default: omission is a deployment error. An explicitly empty value keeps
# the intentional local-development auth bypass.
ACCESS_CODE = os.getenv("ACCESS_CODE")

# Second, higher tier entered at the same login box. A user who logs in with
# ADMIN_CODE gets the whole site including the Unit Roster; a user who logs in
# with ACCESS_CODE gets everything else, and the roster is hidden from the nav
# and 404s if they go looking for it.
#
# No default, and deliberately fail-closed: with ADMIN_CODE unset nobody can
# reach the roster, rather than everybody being able to. Set it explicitly.
ADMIN_CODE = os.getenv("ADMIN_CODE", "")

# Roster persistence.
#
# Cloud Run gives each container a scratch filesystem that is discarded on
# restart, scale-to-zero and every redeploy — so roster edits made through
# /roster, and staff auto-added from gap answers, silently vanish in
# production. Setting ROSTER_BUCKET keeps the roster in GCS instead, where it
# outlives the container and is shared across instances.
#
# Unset (the default) falls back to the packaged JSON file, which is what
# local dev and the test suite use: no bucket, no credentials, no network.
ROSTER_BUCKET = os.getenv("ROSTER_BUCKET", "")
ROSTER_OBJECT = os.getenv("ROSTER_OBJECT", "staff_roster.json")
# Seconds to reuse a fetched roster before re-reading. Lookups happen per
# person per extraction, so reading GCS every time would be wasteful; writes
# bust the cache immediately, so this only bounds how long one instance can
# lag behind an edit made on another.
ROSTER_CACHE_TTL = float(os.getenv("ROSTER_CACHE_TTL", "30"))


# Temporary administrator evaluation surface. It is disabled unless explicitly
# enabled, and stores immutable review objects under a dedicated bucket prefix.
def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


REVIEW_LAB_ENABLED = _env_bool("REVIEW_LAB_ENABLED")
REVIEW_BUCKET = os.getenv("REVIEW_BUCKET", ROSTER_BUCKET or "")
REVIEW_OBJECT_PREFIX = os.getenv("REVIEW_OBJECT_PREFIX", "review-lab/submissions").strip("/")


def legacy_report_mode() -> str:
    """Return the explicit release-1 legacy browser report mode.

    It is read at request time so isolated tests and controlled rollout
    environments can exercise both modes without reloading every legacy route.
    """
    value = os.getenv("LEGACY_REPORT_MODE", "restricted").strip().lower()
    if value not in {"pilot_fallback", "restricted"}:
        raise RuntimeError("LEGACY_REPORT_MODE must be 'pilot_fallback' or 'restricted'")
    return value


# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)
