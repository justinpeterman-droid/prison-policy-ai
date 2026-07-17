FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV PORT=8080
ENV PYTHONPATH=/app

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 webapp.app:create_app
