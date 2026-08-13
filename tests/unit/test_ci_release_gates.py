import re
import subprocess
import sys
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
    assert text.count("docker build --tag prison-policy-ai:ci .") == 3
    assert "permissions: {contents: read}" in text
    assert "name: grype-sarif" in text


def test_sensitive_output_rejects_real_secret_beside_fictional_marker(tmp_path):
    candidate = tmp_path / "output.txt"
    key = "_".join(("private", "key"))
    value = "-".join(("real", "secret"))
    candidate.write_text(f'fixture-id\n{key}="{value}" https://example.invalid\n', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


def test_sensitive_output_allows_only_exact_fictional_assignment_values(tmp_path):
    candidate = tmp_path / "fixture.txt"
    pin_key = "_".join(("temporary", "pin"))
    code_key = "_".join(("access", "code"))
    candidate.write_text(f"{pin_key}='fictional-pin'\n{code_key}='local-user'\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 0
    candidate.write_text(f"{pin_key}='{'-'.join(('real', 'secret'))}'\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 1
