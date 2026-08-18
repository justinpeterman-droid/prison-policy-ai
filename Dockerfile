FROM node:22-slim AS web-build

WORKDIR /src
COPY frontend/web/package.json /src/frontend/web/package.json
WORKDIR /src/frontend/web
RUN npm install --legacy-peer-deps --no-audit --no-fund
COPY frontend/web/ /src/frontend/web/
RUN npm run build

FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY --from=web-build /src/backend/webapp/static/web/ /app/backend/webapp/static/web/
COPY templates/ /app/templates/
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
COPY scripts/dispatch_outbox.py /app/scripts/dispatch_outbox.py

ENV PORT=8080
ENV PYTHONPATH=/app

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 300 --pythonpath /app "backend.webapp.app:create_app()"
