FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY templates/ /app/templates/
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
COPY scripts/dispatch_outbox.py /app/scripts/dispatch_outbox.py

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

ENV PORT=8080
ENV PYTHONPATH=/app

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 300 --pythonpath /app "backend.webapp.app:create_app()"
