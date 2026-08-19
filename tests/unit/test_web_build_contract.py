from pathlib import Path


def test_dockerfile_builds_and_copies_guided_operations_assets():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:22-slim AS web-build" in dockerfile
    assert "npm install --legacy-peer-deps --no-audit --no-fund" in dockerfile
    assert "npm run build" in dockerfile
    assert (
        "COPY --from=web-build /src/backend/webapp/static/web/ "
        "/app/backend/webapp/static/web/"
    ) in dockerfile


def test_docker_context_includes_web_source_and_runtime_dispatcher():
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert "frontend/*" in dockerignore
    assert "!frontend/web/" in dockerignore
    assert "!frontend/web/**" in dockerignore
    assert "scripts/*" in dockerignore
    assert "!scripts/dispatch_outbox.py" in dockerignore
