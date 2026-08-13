import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIGEST = "8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d"


def test_runtime_is_pinned_nonroot_and_healthy():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert all("@sha256:" in line for line in text.splitlines() if line.startswith("FROM "))
    assert re.search(rf"^FROM chainguard/python@sha256:{DIGEST}$", text, re.MULTILINE)
    assert "USER nonroot" in text
    assert "HEALTHCHECK" in text


def test_context_excludes_control_plane_sources():
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for path in ("infra/", "release/", "tests/", "docs/", "access-client/", "access-updater/"):
        assert path in text
