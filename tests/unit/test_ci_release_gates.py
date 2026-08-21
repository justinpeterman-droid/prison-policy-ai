import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATE_SBOM = ROOT / "scripts/ci/validate_sbom.py"
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


def _load_sbom_validator():
    spec = importlib.util.spec_from_file_location("validate_sbom", VALIDATE_SBOM)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validator_inputs(tmp_path):
    output = tmp_path / "sbom.spdx.json"
    output.write_text(
        json.dumps(
            {
                "spdxVersion": "SPDX-2.3",
                "packages": [{"licenseDeclared": "MIT", "licenseConcluded": "MIT"}],
            }
        ),
        encoding="utf-8",
    )
    return output, tmp_path / "sbom.provenance.json"


def _mock_inspect(
    module,
    monkeypatch,
    *,
    built_id="sha256:built",
    runtime_id="sha256:runtime",
    runtime_digest=None,
    built_layers=None,
    runtime_layers=None,
):
    runtime_digest = runtime_digest or f"cgr.dev/chainguard/python@{module.DIGEST}"
    responses = {
        "candidate": {
            "Id": built_id,
            "RootFS": {"Layers": built_layers or ["sha256:runtime-layer", "sha256:built-layer"]},
        },
        "runtime": {
            "Id": runtime_id,
            "RepoDigests": [runtime_digest],
            "RootFS": {"Layers": runtime_layers or ["sha256:runtime-layer"]},
        },
    }
    monkeypatch.setattr(module.subprocess, "check_output", lambda command, text: json.dumps([responses[command[-1]]]))


def _args(output, provenance):
    return type(
        "Args",
        (),
        {
            "image": "candidate",
            "runtime_image": "runtime",
            "output": str(output),
            "provenance": str(provenance),
            "generate_provenance": False,
        },
    )()


def test_required_checks_are_named_and_fail_closed():
    text = "\n".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))
    job_ids = set(re.findall(r"^  ([a-z0-9-]+):\s*$", text, re.MULTILINE))
    display_names = set(re.findall(r"^    name:\s*([a-z0-9.-]+)\s*$", text, re.MULTILINE))
    assert REQUIRED <= job_ids | display_names
    assert "continue-on-error: true" not in text


def test_actions_are_full_sha_pinned():
    text = "\n".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))
    assert all(
        re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", item) for item in re.findall(r"^\s*uses:\s*([^\s#]+)", text, re.MULTILINE)
    )


def test_backend_quality_has_supported_python_and_postgres():
    text = (WORKFLOWS / "backend-quality.yml").read_text(encoding="utf-8")
    assert '"3.12"' in text and '"3.14"' in text and "postgres:17" in text


def test_container_security_uses_signed_release_asset_provenance():
    text = (WORKFLOWS / "container-security.yml").read_text(encoding="utf-8")
    assert "https://github.com/anchore/syft/releases/download/v1.51.0/syft_1.51.0_checksums.txt" in text
    assert "https://github.com/anchore/grype/releases/download/v0.117.0/grype_0.117.0_checksums.txt" in text
    assert "cosign verify-blob" in text
    assert "https://github.com/anchore/syft/.github/workflows/release.yaml@refs/heads/main" in text
    assert "https://github.com/anchore/grype/.github/workflows/release.yaml@refs/heads/main" in text
    assert "sha256sum --check --strict" in text
    assert "cosign verify --certificate-identity-regexp '^https://github.com/anchore/(syft|grype)/'" not in text
    assert "docker.io/anchore/syft@" not in text
    assert "docker.io/anchore/grype@" not in text
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


def test_sensitive_output_rejects_unquoted_secret_and_person_identifiers(tmp_path):
    candidate = tmp_path / "source.yaml"
    password_key = "pass" + "word"
    employee_key = "employee" + "_id"
    inmate_key = "inmate" + "_id"
    candidate.write_text(
        f"{password_key}: real-secret\n{employee_key}: 123\n{inmate_key}: 456\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 1


def test_sensitive_output_allows_explicit_fictional_unquoted_values(tmp_path):
    candidate = tmp_path / "source.yaml"
    employee_key = "employee" + "_id"
    inmate_key = "inmate" + "_id"
    candidate.write_text(
        f"{employee_key}: fictional-employee\n{inmate_key}: fixture-inmate\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 0


def test_sensitive_output_checks_every_assignment_on_a_line(tmp_path):
    candidate = tmp_path / "source.py"
    password_key = "pass" + "word"
    employee_key = "employee" + "_id"
    candidate.write_text(
        f"{password_key}='fictional-pass'; {employee_key}=123\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 1


def test_sensitive_output_rejects_nonfictional_getenv_literal_fallback(tmp_path):
    candidate = tmp_path / "source.py"
    password_key = "pass" + "word"
    candidate.write_text(
        f"{password_key}=os.getenv('PASSWORD', 'real-secret')\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 1


def test_sensitive_output_allows_getenv_without_nonfictional_literal(tmp_path):
    candidate = tmp_path / "source.py"
    password_key = "pass" + "word"
    code_key = "access" + "_code"
    admin_key = "admin" + "_code"
    candidate.write_text(
        f"{password_key}=os.getenv('PASSWORD')\n"
        f"{code_key}=os.getenv('ACCESS_CODE', 'fictional-access')\n"
        f"{admin_key}=os.getenv('ADMIN_CODE', '')\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 0


def test_sensitive_output_allows_typed_fields_counts_and_explicit_fixture_pin(tmp_path):
    candidate = tmp_path / "fixture.ts"
    key = "temporary" + "_pin"
    candidate.write_text(
        f"interface Result {{ {key}: string }}\n"
        f"const schema = {{ {key}: z.number().int(), count: {{ {key}: 1 }} }}\n"
        f"const fixture = {{ {key}: 'FX9R4K' }}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 0


def test_sensitive_output_still_rejects_numeric_pin_value(tmp_path):
    candidate = tmp_path / "source.ts"
    key = "temporary" + "_pin"
    candidate.write_text(f"const value = {{ {key}: 123456 }}\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci/check_sensitive_output.py"), "--paths", str(candidate)]
    )
    assert result.returncode == 1


def test_sbom_validator_rejects_missing_and_forged_provenance(tmp_path, monkeypatch):
    module = _load_sbom_validator()
    output, provenance = _validator_inputs(tmp_path)
    _mock_inspect(module, monkeypatch)
    args = _args(output, provenance)
    assert module.validate(args) == 1
    provenance.write_text("{}", encoding="utf-8")
    assert module.validate(args) == 1


def test_sbom_validator_rejects_provenance_binding_mismatches(tmp_path, monkeypatch):
    module = _load_sbom_validator()
    output, provenance = _validator_inputs(tmp_path)
    _mock_inspect(module, monkeypatch)
    args = _args(output, provenance)
    args.generate_provenance = True
    assert module.validate(args) == 0
    args.generate_provenance = False
    assert module.validate(args) == 0

    for key, replacement in (
        ("image_id", "sha256:forged"),
        ("runtime_repo_digests", ["cgr.dev/chainguard/python@sha256:forged"]),
    ):
        data = json.loads(provenance.read_text(encoding="utf-8"))
        data[key] = replacement
        provenance.write_text(json.dumps(data), encoding="utf-8")
        assert module.validate(args) == 1
        args.generate_provenance = True
        assert module.validate(args) == 0
        args.generate_provenance = False

    output.write_text(output.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert module.validate(args) == 1


def test_sbom_validator_rejects_non_prefix_runtime_layers(tmp_path, monkeypatch):
    module = _load_sbom_validator()
    output, provenance = _validator_inputs(tmp_path)
    _mock_inspect(module, monkeypatch)
    args = _args(output, provenance)
    args.generate_provenance = True
    assert module.validate(args) == 0
    args.generate_provenance = False
    _mock_inspect(module, monkeypatch, built_layers=["sha256:built-layer"], runtime_layers=["sha256:runtime-layer"])
    assert module.validate(args) == 1
