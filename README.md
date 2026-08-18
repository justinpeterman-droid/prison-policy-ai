# Prison Policy AI

Prison Policy AI is a corrections workflow platform with two core capabilities:

- **Policy Expert** — answers policy questions with citations from the approved policy corpus.
- **Report Assistant** — turns field notes into structured facts, identifies missing information, generates reviewable narratives, and exports Word documents without silently inventing facts.

The project is evolving from a legacy Flask browser pilot into **one authoritative platform** shared by a Microsoft Access client and a web-native React companion. Both clients use the same `/api/v1` service, individual employee accounts, PostgreSQL 17 records, report revisions, AI jobs, exports, and audit trail.

> **Release status:** backend and PostgreSQL acceptance are complete, but the current Access/cloud release candidate and the planned React web companion are not automatically approved for production. See `docs/access-cloud-run-implementation-checklist.md` and `HANDOFF.md` for the active gates.

## Architecture

```text
Microsoft Access client             React web companion (planned)
          |                                      |
          +------------------+-------------------+
                             |
                       Cloud Run /api/v1
                             |
       +---------------------+----------------------+
       |            |              |                |
    Identity     Reports        AI jobs        Policy Expert
       |            |              |                |
       +---------------------+----------------------+
                             |
                        PostgreSQL 17
```

Cloud Run and PostgreSQL are the authority for identity, permissions, report ownership, revisions, job state, exports, and audit. Hiding a control in Access or React is never an authorization boundary; every operation is authorized again on the server.

The detailed target architecture is documented in `docs/architecture/unified-platform.md`. The approved web-companion design is in `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`, with executable stages under `docs/superpowers/plans/`.

## Current capabilities

| Area | Current state |
|---|---|
| Policy Expert | Retrieval-augmented policy Q&A with numbered citations and bounded history |
| Report engine | Classify → extract → detect gaps → generate → validate → export |
| Anti-fabrication | Nullable extraction, deterministic validation, invented-fact checks, and explicit supplement markers |
| Identity API | Employee-number/PIN accounts, lockout, rotating sessions, roles, Admin step-up, audit, and idempotency |
| Reports API | Officer ownership, Admin oversight, immutable revisions, provenance, concurrency protection, and Word exports |
| AI execution | Durable jobs/outbox, private worker, stale-result protection, and safe status APIs |
| Operations | Admin audit/health surfaces, Terraform, monitoring definitions, supply-chain checks, and migration runbooks |
| Microsoft Access | Source-controlled build/reconstruction harness; full application screens remain in progress |
| Browser UI | Legacy Flask pilot remains temporarily available during migration; centralized history lives only behind `/api/v1` |
| React companion | Approved and planned, not yet shipped |

## Report pipeline

```text
Field notes
    |
    v
Classification
    |
    v
Schema-constrained extraction
    |
    v
Deterministic gap and invented-fact checks
    |
    v
Officer supplies missing information
    |
    v
Narrative generation from structured facts
    |
    v
Revisioned save and deterministic DOCX export
```

Important safeguards:

- extraction is schema-constrained and permits null values;
- missing facts become questions rather than guesses;
- deterministic validation remains separate from the language model;
- generation receives structured facts rather than unrestricted raw notes;
- every durable edit creates an attributable revision;
- one Officer owns each report, while authorized Administrators can review and revise all reports.

## Repository map

```text
backend/
  identity/                 account, PIN, session, role, audit, and rate-limit services
  jobs/                     durable job, outbox, migration, roster, and bootstrap services
  persistence/              SQLAlchemy database and PostgreSQL models
  pipeline/                 policy ingestion, retrieval, citations, and model integration
  reports/                  classification, extraction, validation, generation, revisions, exports
  webapp/
    api_v1/                 versioned Access/web API
    routes/                 temporary legacy Flask browser routes
  worker/                   private AI-job worker

access-client/              Microsoft Access source/build harness
infra/                      Terraform and monitoring definitions
migrations/                 Alembic migrations and register
openapi/access-v1.yaml      versioned API contract
scripts/                    repository-root operational and verification scripts
templates/                  DOCX templates and bounded reference data
tests/                      unit, contract, PostgreSQL integration, security, eval, and Access tests
docs/                       architecture, plans, runbooks, operations, and release ledger
```

A future `web-client/` directory will contain the React + TypeScript application after the browser-auth foundation is implemented.

## Local development

Run all commands from the **repository root**.

### Python setup

```bash
python -m pip install -r requirements-dev.lock --require-hashes
```

The supported CI matrix is Python 3.12 and Python 3.14. PostgreSQL 17 is required for the integration suite; PostgreSQL 16 is not a valid substitute because the database constraints use PostgreSQL 17 jsonpath behavior.

### Legacy browser pilot

For isolated local work with the identity API disabled, explicitly disable the shared-code gate:

```bash
ACCESS_CODE="" PYTHONPATH=. python backend/webapp/app.py
```

PowerShell:

```powershell
$env:ACCESS_CODE = ""
$env:PYTHONPATH = "."
python backend/webapp/app.py
```

Do not use the legacy browser workflow as proof of centralized persistence or per-user authorization. Identity-backed development requires `ACCESS_API_ENABLED=true` plus the database, signing, hashing, version, and HTTPS-origin settings enforced by `backend/identity/config.py`.

## Tests and quality gates

```bash
python -m pytest tests/unit -q
python -m pytest tests/contract -q
python -m pytest tests/security -q
python -m ruff check backend tests scripts
python -m ruff format --check backend tests scripts
python -m mypy backend
```

With a disposable PostgreSQL 17 database:

```bash
TEST_DATABASE_URL="postgresql+psycopg://..." python -m pytest tests/integration -q
```

GitHub Actions additionally validates Terraform, OpenAPI, sensitive-output redaction, container construction, pinned runtime provenance, vulnerability scanning, and SBOM generation.

## Build and deployment policy

Container and source builds must use the **repository root** so the root Dockerfile, `backend` package, templates, migrations, and other required assets are present:

```bash
docker build -t prison-policy-ai:local .
```

The obsolete backend-local manual deployment script has been retired. Do not recreate it or deploy from a backend subdirectory. Production delivery remains gated on **OP-08 controlled delivery workflows**, protected GitHub environments, Workload Identity Federation, approved cloud configuration, and the release checklist. A manual command in an old document is not deployment authorization.

## Active roadmap

1. **W-01 — Release cleanup and current documentation:** resolve the remaining reliability issues and consolidate the release candidate.
2. **W-02 — Secure browser authentication:** HttpOnly browser sessions, renewal, CSRF protection, and individual employee login.
3. **W-03 — Officer React companion:** dashboard, report workflow, history, exports, Policy Expert, and session controls.
4. **W-04 — Administrator React companion:** accounts, roster, report oversight, revisions, audit, health, and bulk export.
5. **W-05 — Cutover and release:** cross-client verification, React at `/`, retirement of shared codes and legacy Flask pages, and controlled rollout.

The Microsoft Access employee, Administrator, signed-release, pilot, disaster-recovery, and rollout tracks remain separately gated in the 42-task implementation ledger.

## Key documents

- `docs/architecture/unified-platform.md` — current and target platform boundaries
- `docs/access-cloud-run-implementation-checklist.md` — persistent task and release-gate ledger
- `HANDOFF.md` — manual/external actions that cannot be completed by repository code alone
- `openapi/access-v1.yaml` — API contract
- `access-client/README.md` — Access source/build requirements and known gates
- `docs/runbooks/` — database, roster, secrets, edge verification, Admin enrollment, and disaster recovery
- `AGENTS.md` and `CLAUDE.md` — repository-working conventions for coding agents

## Data and safety

Use fictional data for development and tests. Do not commit real employee, inmate, incident, credential, roster, report, policy-sensitive, or production database content. Nothing in this repository authorizes automatic filing into an external corrections records system.