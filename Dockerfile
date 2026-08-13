FROM node:22-slim AS web-build

WORKDIR /src
COPY frontend/web/package.json frontend/web/package-lock.json /src/frontend/web/
WORKDIR /src/frontend/web
RUN npm ci --legacy-peer-deps --no-audit --no-fund
COPY frontend/web/ /src/frontend/web/
RUN npm run build

FROM python:3.14-slim AS build

WORKDIR /app

COPY backend/requirements.lock .
RUN python -m venv /venv && /venv/bin/pip install --no-cache-dir --require-hashes -r requirements.lock

FROM chainguard/python@sha256:8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d

WORKDIR /app

COPY --from=build /venv /venv
COPY backend/ /app/backend/
COPY --from=web-build /src/backend/webapp/static/web/ /app/backend/webapp/static/web/
COPY templates/ /app/templates/
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
COPY scripts/dispatch_outbox.py /app/scripts/dispatch_outbox.py

USER nonroot

ENV PORT=8080
ENV PYTHONPATH=/app
ENV PATH=/venv/bin:$PATH

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"]

CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "300", "--pythonpath", "/app", "backend.webapp.app:create_app()"]
