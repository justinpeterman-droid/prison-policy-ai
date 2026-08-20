import json
import re
from pathlib import Path


def test_dockerfile_builds_and_copies_guided_operations_assets():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert re.search(r"^FROM node:22-slim@sha256:[0-9a-f]{64} AS web-build$", dockerfile, re.MULTILINE)
    assert "COPY frontend/web/package.json frontend/web/package-lock.json" in dockerfile
    assert "npm ci --legacy-peer-deps --no-audit --no-fund" in dockerfile
    assert "npm run build" in dockerfile
    assert "COPY backend/requirements.lock ." in dockerfile
    assert "pip install --no-cache-dir --require-hashes -r requirements.lock" in dockerfile
    assert 'CMD ["gunicorn", "--bind", ":8080"' in dockerfile
    assert (
        "COPY --from=web-build /src/backend/webapp/static/web/ "
        "/app/backend/webapp/static/web/"
    ) in dockerfile


def test_cloud_run_dependencies_are_hash_locked():
    requirements = Path("backend/requirements.lock").read_text(encoding="utf-8")

    assert "pip-compile with Python 3.14" in requirements
    assert "powershell -File scripts/compile_backend_requirements.ps1" in requirements
    assert "--hash=sha256:" in requirements
    assert "google-cloud-aiplatform==" in requirements
    assert "gunicorn==" in requirements


def test_docker_context_includes_web_source_and_runtime_dispatcher():
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert "frontend/*" in dockerignore
    assert "!frontend/web/" in dockerignore
    assert "!frontend/web/**" in dockerignore
    assert "scripts/*" in dockerignore
    assert "!scripts/dispatch_outbox.py" in dockerignore


def test_frontend_release_dependencies_are_locked_and_direct_versions_are_pinned():
    package = json.loads(Path("frontend/web/package.json").read_text(encoding="utf-8"))
    lock = json.loads(Path("frontend/web/package-lock.json").read_text(encoding="utf-8"))

    for group in ("dependencies", "devDependencies"):
        for version in package[group].values():
            assert version != "latest"
            assert version[0].isdigit()

    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["dependencies"] == package["dependencies"]
    assert lock["packages"][""]["devDependencies"] == package["devDependencies"]


def test_ci_runs_the_complete_guided_operations_browser_gate():
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")

    for required in (
        "npm ci --legacy-peer-deps --no-audit --no-fund",
        "npm run lint",
        "npm run typecheck",
        "npm run test",
        "npx playwright install --with-deps chromium",
        "npm run test:e2e",
        "python scripts/check_print_templates.py",
        "python -m pytest tests/contract tests/security -q",
    ):
        assert required in workflow

    assert re.search(r"uses: actions/setup-node@[0-9a-f]{40}$", workflow, re.MULTILINE)
