"""Which models, prompts, and build produced a piece of generated text.

Every report the system stores is an artifact of a specific model tier, a
specific prompt file, and a specific checklist. When an officer disputes a
report months later, "which version of the system wrote this" has to be
answerable from the record rather than reconstructed from deploy history — so
the fingerprints are captured at write time, by the server, from the files on
disk.

Review Lab had this behavior first; it now consumes this helper so reports,
exports, and Review Lab cannot disagree about what produced a document.
"""
import hashlib
import os
from pathlib import Path

from backend.pipeline.config import FAST_MODEL, MODEL_LOCATION, PRO_MODEL


ROOT = Path(__file__).parents[2]
#: The inputs whose contents change what the pipeline produces.
PROVENANCE_SOURCES: dict[str, Path] = {
    "classification": ROOT / "backend" / "reports" / "prompts.py",
    "generation": ROOT / "backend" / "reports" / "prompts_v2.py",
    "checklist": ROOT / "templates" / "incident_checklist_v2.json",
    "charges": ROOT / "templates" / "disciplinary_charges.json",
    "template": ROOT / "templates" / "005_template_v3.docx",
}


def file_sha256(path: Path) -> str:
    """SHA-256 of one provenance source file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_fingerprints(names: tuple[str, ...]) -> dict[str, str]:
    """Digests for the named provenance sources, keyed by name."""
    return {name: file_sha256(PROVENANCE_SOURCES[name]) for name in names}


def collect_provenance() -> dict[str, str | None]:
    """The server-owned fingerprint stamped onto generated content.

    Deployment identity is nullable on purpose: outside Cloud Run there is no
    revision to report, and a fabricated value would be worse than an absent
    one.
    """
    return {
        "fast_model": FAST_MODEL,
        "pro_model": PRO_MODEL,
        "model_location": MODEL_LOCATION,
        "classification_prompt_sha256": file_sha256(
            PROVENANCE_SOURCES["classification"]),
        "generation_prompt_sha256": file_sha256(PROVENANCE_SOURCES["generation"]),
        "checklist_sha256": file_sha256(PROVENANCE_SOURCES["checklist"]),
        "template_sha256": file_sha256(PROVENANCE_SOURCES["template"]),
        "cloud_run_revision": os.getenv("K_REVISION") or None,
        "source_commit": os.getenv("SOURCE_COMMIT") or None,
    }
