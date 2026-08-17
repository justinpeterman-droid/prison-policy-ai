FROM python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4 AS build

WORKDIR /app

COPY backend/requirements.txt .
# The runtime stage below is chainguard/python, which ships CPython at
# /usr/bin/python3.14 and has no /usr/local at all. A venv built here points
# its interpreter symlinks and pyvenv.cfg at this stage's /usr/local/bin, so
# once /venv is copied across, /venv/bin/python dangles and every exec of it
# fails: gunicorn (shebang #!/venv/bin/python), the HEALTHCHECK, and the Cloud
# Run jobs' command = ["python"]. Repoint both at the runtime location. Both
# stages are CPython 3.14, so site-packages and the ABI already line up.
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt \
    && PYVER="$(/venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" \
    && rm -f /venv/bin/python /venv/bin/python3 "/venv/bin/python${PYVER}" \
    && ln -s "/usr/bin/python${PYVER}" "/venv/bin/python${PYVER}" \
    && ln -s "python${PYVER}" /venv/bin/python3 \
    && ln -s "python${PYVER}" /venv/bin/python \
    && sed -i \
        -e 's|^home = .*|home = /usr/bin|' \
        -e "s|^executable = .*|executable = /usr/bin/python${PYVER}|" \
        -e "s|^command = .*|command = /usr/bin/python${PYVER} -m venv /venv|" \
        /venv/pyvenv.cfg

FROM chainguard/python@sha256:8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d

WORKDIR /app

COPY --from=build /venv /venv
COPY backend/ /app/backend/
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
