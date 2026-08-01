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
PRO_MODEL = os.getenv("PRO_MODEL", "gemini-3.1-pro")
# Back-compat alias — GENERATION_MODEL historically meant "the flash model".
# Anything still importing it gets the FAST tier; override via its own env var.
GENERATION_MODEL = os.getenv("GENERATION_MODEL", FAST_MODEL)

# Location for Gemini model calls. The Gemini 3.x models are served from the
# 'global' endpoint (not a region), so this defaults to 'global' even though the
# Agent Builder data store / corpus live in us-central1. Override with
# GCP_MODEL_LOCATION if you pin older regional models in the tiers above.
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", "global")

CORPUS_NAME = os.getenv("RAG_CORPUS_NAME", "prison-policies")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Auth — simple shared access code. Set via ACCESS_CODE env var.
# Defaults to "slut"; matching is case-insensitive (see webapp auth).
# Set ACCESS_CODE="" explicitly to disable auth (open access).
ACCESS_CODE = os.getenv("ACCESS_CODE", "slut")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)
