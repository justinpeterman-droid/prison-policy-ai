from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pages_workflow_never_uploads_repository_root():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "path: pages-dist" in workflow
    assert "path: .\n" not in workflow
    assert "frontend/forms" in workflow
    assert "templates" not in workflow


def test_pages_distribution_allowlist_is_exact():
    script = (ROOT / "scripts" / "ci" / "build_pages_dist.py").read_text(encoding="utf-8")
    assert 'ALLOWED = ("index.html", "frontend/forms")' in script
