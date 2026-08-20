# Prison Policy AI — Guided Operations

Prison Policy AI is an officer-focused operations platform for policy questions, incident reporting, required paperwork, and individually authenticated staff workflows.

The current application is intentionally deployed as a **companion** to the existing Access and legacy browser experiences. Replacing or retiring either legacy surface requires a separate pilot and explicit approval.

## Current product surface

### Guided Operations web workspace

The React workspace is served under:

```text
/workspace
```

It currently includes:

- individual employee-number and PIN sign-in;
- secure browser sessions and CSRF protection;
- officer Home with authorized live summaries;
- six-stage New Report workflow;
- incident-centered Reports library;
- Incident Document Studio;
- required, recommended, and additional paperwork packets;
- reviewed-fact digital form population;
- copy-only records outputs;
- physical-only Chain of Custody guidance and acknowledgment;
- NCU Days Count;
- approved Forms Library;
- citation-backed Policy Expert; and
- personal PIN and browser-session management.

### Existing companion surfaces

The repository also retains:

- the Access-oriented bearer API under `/api/v1`;
- the existing Flask/Jinja browser pages during the pilot period;
- the deterministic report engine and Word exports; and
- Review Lab and administrator services that will be integrated into the later Admin Command Center milestone.

## Architecture

```text
React + TypeScript + Vite
          │
          │ cookie-authenticated /api/web/v1
          ▼
Flask application and browser adapters
          │
          ├── identity, browser sessions, PINs, audit, idempotency
          ├── incidents, revisions, reports, AI jobs
          ├── form catalog, packets, population, output policy
          ├── operational paperwork and Count Sheet revisions
          └── policy retrieval and citation-backed answers
          │
          ▼
PostgreSQL 17 + approved document templates + model providers
```

The browser API reuses the same route-neutral Python services as the Access API. It does not call `/api/v1` over HTTP internally.

## Safety rules

The implementation is built around these invariants:

- The model may extract suggestions, but officers review facts before official forms are populated.
- Raw unsaved field notes never populate official forms.
- Unknown information remains blank or becomes an explicit missing-information question.
- Officers do not manually set records-management workflow status.
- Supervisor Summary and Disciplinary Supplement remain copy-only.
- Chain of Custody remains an official physical carbon-copy form with no generated substitute.
- Count Sheet mismatches are displayed and never silently corrected.
- Identity credentials use opaque HttpOnly cookies and are never returned in readable JSON.
- Sensitive notes, narratives, form contents, and PINs are excluded from audit metadata.
- Tests, screenshots, and fixtures use fictional information only.

## Repository map

```text
backend/
├── dashboard/                 # Safe officer Home summaries
├── forms/                     # Catalog, packets, population, physical/output rules
├── identity/                  # Accounts, PINs, sessions, elevation, audit, idempotency
├── jobs/                      # Durable AI-job and outbox services
├── paperwork/                 # Revisioned operational paperwork and Count Sheet
├── persistence/               # SQLAlchemy models and database setup
├── pipeline/                  # Policy retrieval, ranking, and grounded generation
├── reports/                   # Incident/report persistence and report engine
└── webapp/
    ├── api_v1/                # Access bearer API
    ├── web_api/               # Cookie-authenticated Guided Operations API
    ├── routes/                # Legacy Flask/Jinja routes
    └── static/                # Built web assets

frontend/web/                  # Guided Operations React application
migrations/                    # Alembic migrations
openapi/                       # Access and browser API contracts
templates/                     # Approved report/form/checklist definitions
tests/                         # Unit, integration, contract, security, and browser tests
docs/design/guided-operations # Product implementation notes
```

## Local development

### Prerequisites

- Python 3.12 or a supported newer version
- Node.js 22
- PostgreSQL 17 — **required, not a preference.** The migrations use jsonpath
  methods introduced in 17. On PostgreSQL 16 `alembic upgrade head` fails part
  way through with an opaque `syntax error at or near "(" of jsonpath input`.

The AI-backed features — Policy Expert answers and incident classification,
extraction, and report generation — call Google Vertex AI through Application
Default Credentials. There is no API-key setting. Without ADC the rest of the
workspace runs normally and those surfaces report themselves as unavailable.
Supply credentials with `gcloud auth application-default login`, or point
`GOOGLE_APPLICATION_CREDENTIALS` at a service-account key.

### Install dependencies

From the repository root:

```bash
python -m pip install -r requirements.txt pytest
cd frontend/web
npm install --legacy-peer-deps --no-audit --no-fund
cd ../..
```

### Configure a local identity database

Use development-only values. Never reuse production secrets or commit an `.env` file.

```bash
export ACCESS_CODE=""
export ACCESS_API_ENABLED="true"
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/access_dev"
export IDENTITY_HASH_PEPPER="development-pepper-change-this-value"
export CURSOR_SIGNING_KEY="development-cursor-key-change-this"
export PUBLIC_BASE_URL="https://localhost"
```

PowerShell equivalent:

```powershell
$env:ACCESS_CODE=""
$env:ACCESS_API_ENABLED="true"
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/access_dev"
$env:IDENTITY_HASH_PEPPER="development-pepper-change-this-value"
$env:CURSOR_SIGNING_KEY="development-cursor-key-change-this"
$env:PUBLIC_BASE_URL="https://localhost"
```

Apply migrations:

```bash
python -m alembic upgrade head
```

The application does not ship a default employee login, and there is no
account-provisioning command yet. Until one exists, seed a fictional officer by
reusing the integration test fixture. Run from the repository root with the
environment above exported:

```bash
PYTHONPATH=. python - <<'PY'
import os
from datetime import datetime, UTC

from backend.identity.config import IdentitySettings
from backend.persistence.database import init_database, session_scope
from tests.integration.identity_fixtures import seed_fictional_account

init_database(IdentitySettings.from_env(os.environ))
with session_scope() as session:
    seed_fictional_account(
        session, employee_number="TEST-1001", role="user",
        pin="Z9Y8X7", now=datetime.now(UTC),
    )
    seed_fictional_account(
        session, employee_number="TEST-9001", role="admin",
        pin="Q7W9E2", now=datetime.now(UTC),
    )
PY
```

Sign in at `/workspace` with employee number `TEST-1001` and PIN `Z9Y8X7`. Use
fictional values only, and never seed real staff names or employee numbers.

### Build and run the workspace

```bash
cd frontend/web
npm run build
cd ../..
PYTHONPATH=. python -m backend.webapp.app
```

Then open the Flask application and navigate to `/workspace`.

Two consequences of the settings above are worth knowing before you go looking
for a bug:

- An empty `ACCESS_CODE` disables the legacy shared-code gate entirely, which
  also means every visitor is treated as an administrator. That is convenient
  locally and wrong anywhere else.
- With `ACCESS_API_ENABLED=true`, the legacy report actions under
  `/api/reports/*` return `503` by default. `LEGACY_REPORT_MODE` controls this
  and defaults to `restricted`; set it to `pilot_fallback` to reopen them. A
  legacy `/reports` page whose buttons all return `503` is the configured
  behavior, not a failure.

For frontend-only UI development:

```bash
cd frontend/web
npm run dev
```

## Verification

`pytest.ini` sets `testpaths = tests/unit`, so a bare run covers only the fast,
credential-free unit tests. The other layers exist and are green, but they are
collected only when you name them:

```bash
python -m pytest -q                                    # unit only
python -m pytest tests/contract tests/security -q      # no services needed
python -m pytest tests/integration -q                  # needs TEST_DATABASE_URL
```

A green `python -m pytest -q` is therefore not evidence that the API contracts
or the browser security suites still pass.

Frontend checks:

```bash
cd frontend/web
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

`npm run lint` is currently an alias for the same `tsc -b` invocation as
`npm run typecheck`; there is no separate linter configured.

The browser workflows use Playwright with fictional API fixtures. PostgreSQL integration tests use `TEST_DATABASE_URL` and run against PostgreSQL 17 in CI.

## Major design and implementation documents

- `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`
- `docs/superpowers/plans/2026-08-18-guided-operations-web-program-roadmap.md`
- `docs/superpowers/plans/2026-08-18-guided-operations-incident-workspace-implementation.md`
- `docs/superpowers/plans/2026-08-18-guided-operations-officer-utilities-implementation.md`
- `docs/design/guided-operations/officer-utilities.md`
- `REPORT_ENGINE_SPEC.md`

## Release status

Guided Operations remains in staged development and pilot preparation. A passing repository test matrix does not by itself authorize production traffic changes, real roster import, legacy-route retirement, or records-policy decisions. Those actions require the documented rollout gates and explicit repository-owner approval.