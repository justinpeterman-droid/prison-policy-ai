"""Regression tests that keep the repository's entry-point docs current."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
HANDOFF = ROOT / "HANDOFF.md"
CHECKLIST = ROOT / "docs" / "access-cloud-run-implementation-checklist.md"
ARCHITECTURE = ROOT / "docs" / "architecture" / "unified-platform.md"
WEB_COMPANION_SPEC = ROOT / Path(
    "docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md"
)
ARCHITECTURE_PATH = "docs/architecture/unified-platform.md"
ENTRY_DOCS = (README, HANDOFF, CHECKLIST, ARCHITECTURE)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_describes_current_and_target_platform():
    text = _read(README)

    for required in (
        "Microsoft Access",
        "React",
        "/api/v1",
        "PostgreSQL 17",
        "repository root",
    ):
        assert required in text


def test_readme_does_not_restore_retired_backend_deployment():
    text = _read(README)

    assert not (ROOT / "backend" / "scripts" / "deploy.sh").exists()
    assert "backend/scripts/deploy.sh" not in text
    assert "--source backend" not in text


def test_handoff_uses_durable_release_references():
    text = _read(HANDOFF)

    for transient in ("PR #22", "PR #23", "PR #84", "PR #85"):
        assert transient not in text
    assert "W-01" in text
    assert "OP-08" in text
    assert ARCHITECTURE_PATH in text


def test_entry_docs_do_not_depend_on_draft_pr_numbers():
    for path in ENTRY_DOCS:
        text = _read(path)
        assert "draft PR #" not in text
        assert "PR #84" not in text
        assert "PR #85" not in text


def test_unified_architecture_documents_one_authoritative_platform():
    text = _read(ARCHITECTURE)

    for required in (
        "Microsoft Access",
        "React",
        "/api/v1",
        "PostgreSQL",
        "one authoritative platform",
        "server-side authorization",
        "W-01",
        "W-05",
    ):
        assert required in text


def test_checklist_tracks_web_companion_workstream():
    text = _read(CHECKLIST)

    assert "## Web companion" in text
    assert ARCHITECTURE_PATH in text
    for task_id in ("W-01", "W-02", "W-03", "W-04", "W-05"):
        assert task_id in text


def test_permanent_markdown_documents_end_with_newline():
    for document in (ARCHITECTURE, WEB_COMPANION_SPEC):
        assert document.read_bytes().endswith(b"\n"), document
