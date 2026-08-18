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
