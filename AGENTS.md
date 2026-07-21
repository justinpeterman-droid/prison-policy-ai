# AGENTS.md

## Cursor Cloud specific instructions

Prison Policy AI is a single **Flask web app** (`backend/`) that serves two AI tools
(Policy Knowledge Expert chat + Report Writing Assistant) plus a standalone, build-free
**static React forms app** (`frontend/forms/`). See `README.md` and `VISION.md` for product
context; standard commands live in `README.md` and the root `Dockerfile`.

### Services & how to run them

- **Backend Flask app (the product).** Absolute `backend.*` imports mean you must run it
  from the repo root with the repo root on `PYTHONPATH`, NOT via `cd backend/webapp`:
  - Dev: `PYTHONPATH=/workspace python3 backend/webapp/app.py` → http://localhost:8080 (debug reloader on).
  - Prod-style: `PYTHONPATH=/workspace gunicorn --bind :8080 "backend.webapp.app:create_app()"`.
- **Static forms app (optional).** No build/npm — React is vendored. Just open
  `frontend/forms/index.html`, or serve the repo root (`python3 -m http.server 8000`) and
  visit `/frontend/forms/`. Optional recompile of `src.jsx`: `npx @babel/cli --presets @babel/preset-react src.jsx -o app.js`.

### Auth gate (non-obvious)

Every route except `/health`, `/login`, `/logout`, `/static/*` is gated by a shared
access code. `ACCESS_CODE` defaults to **`slut`** (case-insensitive); log in at `/login`
or append `?code=slut`. Set `ACCESS_CODE=""` to disable auth entirely.

### What works WITHOUT credentials vs what needs GCP

The app boots and the following work with **no credentials**: home page, login, `/health`,
the reports page UI, and `POST /api/reports/download` with a `metadata` payload (fills the
official `templates/005*.docx` form locally — no LLM pass), and the entire static forms app.

The AI features call **Google Vertex AI via Application Default Credentials (ADC)** — there
is no API-key env var. Without ADC these return HTTP 500 "default credentials were not found":
- `POST /api/chat` (Policy Expert) — also requires a pre-built Vertex RAG corpus `prison-policies`.
- `POST /api/reports/classify`, `/extract`, `/generate` (the report UI's Generate button).
To enable them, provide ADC (e.g. `GOOGLE_APPLICATION_CREDENTIALS` service-account JSON or
`gcloud auth application-default login`) for GCP project `gen-lang-client-0968389176`.

### Dependencies / gotchas

- No JS package manager — frontend is fully vendored, no `package.json` anywhere.
- Python deps install into the user/global site via `--break-system-packages` (this Ubuntu
  Python is PEP-668 externally-managed and `python3-venv` is not preinstalled). The update
  script handles this; console-scripts land in `~/.local/bin` (not needed since we invoke
  `python3 -m` / module entrypoints).
