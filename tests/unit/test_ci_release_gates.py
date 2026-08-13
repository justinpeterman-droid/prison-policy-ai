import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
REQUIRED = {
    "backend-quality-3.12",
    "backend-quality-3.14",
    "postgres-integration-17",
    "openapi-contract",
    "security-redaction",
    "container-build",
    "sbom",
    "container-vulnerability",
    "terraform-static",
    "pages-scope",
}


def test_required_checks_are_named_and_fail_closed():
    text = "\n".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))
    assert REQUIRED <= set(re.findall(r"^  ([a-z0-9.-]+):\s*$", text, re.MULTILINE))
    assert "continue-on-error: true" not in text


def test_actions_are_full_sha_pinned():
    text = "\n".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))
    assert all(
        re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", item) for item in re.findall(r"^\s*uses:\s*([^\s#]+)", text, re.MULTILINE)
    )


def test_backend_quality_has_supported_python_and_postgres():
    text = (WORKFLOWS / "backend-quality.yml").read_text(encoding="utf-8")
    assert '"3.12"' in text and '"3.14"' in text and "postgres:17" in text


def test_container_security_uses_fixed_provenance_checked_tooling():
    text = (WORKFLOWS / "container-security.yml").read_text(encoding="utf-8")
    assert "syft-version: 1.51.0" in text
    assert "grype-version: 0.117.0" in text
    assert "cosign verify" in text
    assert "insecure-ignore-tlog" not in text
