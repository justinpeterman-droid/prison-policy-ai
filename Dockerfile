FROM node:22-slim AS web-build

WORKDIR /src
COPY frontend/web/package.json frontend/web/package-lock.json /src/frontend/web/
WORKDIR /src/frontend/web
RUN npm ci --legacy-peer-deps --no-audit --no-fund
COPY frontend/web/ /src/frontend/web/
RUN npm run build

FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY backend/ /app/backend/
COPY --from=web-build /src/backend/webapp/static/web/ /app/backend/webapp/static/web/
COPY templates/ /app/templates/
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
COPY scripts/dispatch_outbox.py /app/scripts/dispatch_outbox.py

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

ENV PORT=8080
ENV PYTHONPATH=/app

CMD ["sh", "-c", "exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 300 --pythonpath /app 'backend.webapp.app:create_app()'"]
