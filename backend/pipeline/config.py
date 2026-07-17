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
LOCATION = os.getenv("GCP_LOCATION", "global")
BUCKET_NAME = os.getenv("GCS_BUCKET", f"{PROJECT_ID}-policy-ai")

# Vertex AI
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gemini-3.5-flash")
CORPUS_NAME = os.getenv("RAG_CORPUS_NAME", "prison-policies")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Auth — simple shared access code. Set via ACCESS_CODE env var.
# Empty string = no auth required (open access).
ACCESS_CODE = os.getenv("ACCESS_CODE", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)
