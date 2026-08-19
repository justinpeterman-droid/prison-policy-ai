# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.
Read this first; it captures the non-obvious structure, workflows, and conventions
that the source alone won't tell you.

> Companion docs: `README.md` (product overview), `AGENTS.md` (run commands +
> learned user preferences), `VISION.md` (product vision), `REPORT_ENGINE_SPEC.md`,
> `UI_SPEC.md`, `REPORT_WRITING_RULES.md`, `docs/operations/` (release gates and
> deployment prerequisites), `docs/runbooks/`. When those and this file disagree,
> trust the **code**, then update the docs.
>
> `README.md` and `HANDOFF.md` are known to predate the Access work — they still
> describe an automatic Cloud Run deploy that no longer exists.

---

## What this is

**Prison Policy AI** is an AI assistant for Arkansas Department of Correction (ADC)
staff, focused on the BMU / Grimes Unit. It began as a single Flask app with
shared-code auth and no database. **It is now two products mid-migration**, and
almost every mistake an assistant makes here comes from not knowing which one it
is standing in.

**The legacy app** — server-rendered Jinja pages behind a shared access code,
no per-user identity, nothing persisted but the roster:

- **📋 Policy Knowledge Expert** (`/chat`) — RAG Q&A over ADC policy documents.
- **📝 Report Writing Assistant** (`/reports`) — turns an officer's free-text
  "field notes" into classified, gap-checked, generated incident reports and a
  filled-in official 005 DOCX. Still the heart of the product.
- **👥 Unit Roster** (`/roster`) — CRUD over the staff roster.
- **🔬 Demo Review Lab** (`/review-lab`) — admin-only evaluation surface. The
  blueprint always registers, but every route 404s unless `REVIEW_LAB_ENABLED`.

**Access / Guided Operations** — the replacement, built alongside it: individual
employee accounts (employee number + Argon2 PIN), Postgres-backed sessions and
audit, a versioned REST API at `/api/v1`, durable incident/report history, and a
React SPA at `/workspace`. Gated behind `ACCESS_API_ENABLED`.

**The two are wired together in one Flask process** (`create_app()`), which is the
trap: when `ACCESS_API_ENABLED=true`, the legacy report actions
(`/api/reports/classify|extract|generate|disciplinary|download`) **return 503 by
default** — see "Legacy report mode" below. A perfectly healthy `/reports` page
whose buttons all 503 is the expected state in that configuration, not a bug.

There is also a separate, build-free **static React forms app**
(`frontend/forms/`) — 6 hand-fillable ADC forms, deployed to GitHub Pages. It is
independent of both apps and has no build step. Don't conflate it with
`frontend/web/`, which is the Guided Operations SPA and does have one.

**GCP project:** `gen-lang-client-0968389176` · **Region:** `us-central1`
**Deployment is gated.** The `cloud-run.yml` workflow was deliberately deleted
(`5b21e94`); see "Deploy & CI".

---

## Repository layout

```
prison-policy-ai/
├── backend/                     # Absolute `backend.*` imports throughout
│   ├── pipeline/                # Policy RAG chat
│   │   ├── config.py            # Legacy env config + ACCESS_CODE/ADMIN_CODE + logger
│   │   ├── query.py             # gate → augment → search (Agent Builder) → generate
│   │   ├── retrieval.py         # Deterministic query augmentation + passage selection
│   │   ├── citations.py         # Pure marker renumbering; surfaces only cited passages
│   │   ├── retry.py             # is_transient() + with_retries() — shared by jobs too
│   │   └── extract.py, chunk.py, embed.py, import_to_agent_builder.py  # corpus build
│   ├── reports/                 # Report engine (see "Report pipeline" below)
│   │   ├── classifier.py        # Incident-type detection (Gemini) + charge suggestion
│   │   ├── extraction.py        # Slot extraction (Gemini, temp=0, response_schema)
│   │   ├── schema.py            # Slot schema, response_schema builder, reporter binding
│   │   ├── validate.py          # Gap detection, auto_content, invented_facts — NO AI
│   │   ├── generator.py         # 5 report generators (structured facts only)
│   │   ├── prompts.py           # Classifier prompt + charge-catalog loader
│   │   ├── prompts_v2.py        # v2 generation prompts (never see raw notes)
│   │   ├── name_fixer.py        # Deterministic first-mention/full-name enforcement
│   │   ├── report_validator.py  # Style scoring + deterministic auto-repair — NO AI
│   │   ├── filler.py            # DOCX template filling (python-docx)
│   │   ├── roster.py            # Roster load + fuzzy resolution + auto-persist
│   │   ├── roster_store.py      # The ONLY writer of the roster (file or GCS + CAS)
│   │   ├── service.py           # Route-neutral adapters — shared by legacy + /api/v1
│   │   ├── persistence.py       # Authorized incident persistence (caller owns the txn)
│   │   ├── revisions.py         # Row-locked incident/report revision history
│   │   ├── policy.py            # Owner / preparer / admin record-access policy
│   │   ├── provenance.py        # Which model, prompt and build produced a text
│   │   ├── export_service.py    # Audited DOCX export of an immutable revision
│   │   ├── deterministic_docx.py# Byte-deterministic DOCX normalization
│   │   ├── gap_answers.py       # Pure: fold reviewed gap answers back into slots
│   │   ├── demo_scenarios.py    # Canonical fictional demo scenarios
│   │   └── review_schema.py, review_store.py   # Demo Review Lab submissions (GCS)
│   ├── identity/                # Access: accounts, PINs, sessions, audit  ← NEW
│   │   ├── config.py            # IdentitySettings.from_env — fails closed, see below
│   │   ├── accounts.py, pins.py # Argon2id PINs, policy, lockout
│   │   ├── sessions.py          # Opaque access/renewal token pairs, rotation, reuse
│   │   ├── tokens.py            # issue_credential() / hash_token() / hash_device_id()
│   │   ├── browser_sessions.py  # Cookie-shaped adapter over sessions.py (the SPA)
│   │   ├── browser_handoffs.py  # One-shot handoff into the legacy Review Lab
│   │   ├── elevation.py         # Admin step-up + idle timeout
│   │   ├── rate_limits.py       # Per employee / device / network login limits
│   │   ├── idempotency.py       # Claim/complete records for retryable mutations
│   │   └── audit.py             # AuditWriter — every identity mutation is logged
│   ├── persistence/             # SQLAlchemy 2.x + Alembic  ← NEW
│   │   ├── database.py          # init_database(), session_scope(), database_ready()
│   │   └── models/              # identity, sessions, security, reporting, jobs, browser
│   ├── jobs/                    # Durable AI-job outbox → Cloud Tasks  ← NEW
│   │   ├── service.py           # Submission + idempotency + audit, one transaction
│   │   ├── outbox.py            # enqueue_job(): a row, never a network call
│   │   └── dispatcher.py        # After-commit dispatch; only UUIDs cross the boundary
│   ├── worker/                  # Private Cloud Tasks worker Flask app  ← NEW
│   └── webapp/
│       ├── app.py               # App factory `create_app()`, legacy cookie auth gate
│       ├── assets.py            # `asset_url()` versioning, cache headers, gzip
│       ├── api_v1/              # Access REST API, /api/v1  ← NEW
│       │   ├── __init__.py      # Blueprint, request logging, ApiError handler
│       │   ├── auth.py          # login, logout(-all), change-pin, sessions, step-up
│       │   ├── admin.py, admin_reports.py, admin_audit.py, admin_health.py
│       │   ├── staff.py, incidents.py, reports.py, jobs.py, policy.py
│       │   ├── errors.py        # ApiError — the shared typed failure
│       │   └── responses.py     # success()/failure() envelope; pagination.py cursors
│       ├── web_api/             # Cookie-auth API for the SPA, /api/web/v1  ← NEW
│       │   ├── auth.py          # login / session / renew / logout + cookie writing
│       │   └── middleware.py    # require_browser_session / _csrf / _role, same-origin
│       ├── routes/              # Legacy Jinja pages
│       │   ├── chat.py, reports.py, roster.py, feedback.py
│       │   ├── review_lab.py    # Admin-only Demo Review Lab
│       │   ├── browser_handoffs.py
│       │   └── web_app.py       # Serves the SPA shell at /workspace
│       ├── templates/           # Jinja HTML (server-rendered legacy pages)
│       └── static/              # style.css, tokens.css, fonts, js/  + web/ (SPA build)
├── frontend/
│   ├── forms/                   # Standalone static React app (vendored, NO npm)
│   └── web/                     # Guided Operations SPA — Vite + React 19 + TS  ← NEW
├── templates/                   # DATA the backend reads at runtime (see below)
├── migrations/versions/         # Alembic; alembic.ini at the root  ← NEW
├── openapi/                     # access-v1.yaml, web-v1.yaml — contract-tested  ← NEW
├── infra/terraform/             # bootstrap + test/production environments  ← NEW
├── tests/                       # unit, integration, contract, security, eval + harness
├── scripts/                     # OCR / corpus helpers + dispatch_outbox.py (runtime)
├── docs/                        # operations/, runbooks/, design/, release gates
├── Dockerfile                   # Two-stage: node web-build → python runtime
├── requirements.txt             # Local/CI deps; backend/requirements.txt is deployed
└── .github/workflows/           # tests, web-tests, guided-operations-foundation,
                                 # pages, codacy  (NO cloud-run.yml — see Deploy & CI)
```

### `templates/` is runtime data, not Jinja templates

The top-level `templates/` directory holds **data files the report engine loads at
runtime** — not HTML. (Jinja HTML lives in `backend/webapp/templates/`.) Key files:

| File | Role |
|------|------|
| `incident_checklist_v2.json` | **Authoritative** — 9 categories, required slots, conditional rules, gap questions, `auto_content` sentences, shared option sets. Change report behavior *here*, not in prompts. |
| `disciplinary_charges.json` | Extracted disciplinary handbook charges; classifier validates suggestions against these. |
| `staff_roster.json` | **Seed** roster (`{shifts, staff}`). **Fictional demo staff only — never commit real names or employee numbers.** In production the live roster lives in GCS (see "Roster persistence" below); this file is the starting point when the bucket has no roster yet, and the whole story locally. |
| `location_map.json` | Slang → formal BMU location names. |
| `demo_notes.json` | The three canned field-note scenarios behind the `/reports?demo=1` CTA. **Fictional people only** — staff names must resolve against `staff_roster.json`, and `use_of_force_oc` deliberately withholds the OC canister lot/MFG/serial so the blocking gap fires. `tests/unit/test_demo_notes.py` enforces both. |
| `005_template_v3.docx` | Current ADC 005 replica the filler populates (older `005*.docx` are legacy). |
| `report_style_guide.md` | Naming / tone rules the prompts + `name_fixer.py` enforce. |

---

## Running the app

Absolute `backend.*` imports mean you **must run from the repo root with the root on
`PYTHONPATH`** — never `cd backend/webapp` and run `app.py` bare.

```bash
pip install -r requirements.txt            # backend/requirements.txt is the deployed set (adds google-cloud-aiplatform)

# Dev (debug reloader on):
PYTHONPATH=. python3 backend/webapp/app.py            # → http://localhost:8080

# Prod-style:
PYTHONPATH=. gunicorn --bind :8080 "backend.webapp.app:create_app()"
```

Static forms app (no build): open `frontend/forms/index.html`, or serve the repo root
(`python3 -m http.server 8000`) and visit `/frontend/forms/`. Optional recompile:
`npx @babel/cli --presets @babel/preset-react src.jsx -o app.js`.

The Guided Operations SPA **does** have a build, and it writes into the Flask
static tree:

```bash
cd frontend/web
npm install --legacy-peer-deps       # no lockfile is committed (see gotchas)
npm test && npm run typecheck        # vitest + tsc -b
npm run build                        # → backend/webapp/static/web/  (vite.config.ts)
```

Then `/workspace` serves it. Unbuilt, `/workspace` returns **503 "Guided
Operations preview has not been built."** — that is the route working, not
failing. `backend/webapp/static/web/` is gitignored; two route tests assert the
*unbuilt* state, so a stray local build makes them fail. Delete the directory to
get back to green.

### Legacy auth gate (non-obvious)

Every legacy route except `/login`, `/logout`, `/health`, and `/static/*` is gated
by a shared access code (`backend/webapp/app.py`). Log in at `/login`, or bookmark
any URL with `?code=<code>` (sets a cookie, redirects clean). API routes return
**401 JSON**; page routes redirect to `/login`.

`ACCESS_CODE` has **no default** — the comment in `config.py` calls omission a
deployment error, but nothing enforces it: unset *or* empty, `if not ACCESS_CODE`
disables the gate entirely and the app is open (startup logs `No ACCESS_CODE set
— app is open to the public`). Set it deliberately, including locally. Matching is
case-insensitive. The product brand is "Standard Logistics & Unit Tools" →
S-L-U-T, navy + gold, which is where the cookie and Guided Operations cookie
prefixes (`slut_web_*`) come from.

**Four paths bypass this gate entirely**, because they carry their own identity:
`/api/v1/*`, `/api/web/v1/*`, `/workspace` and `/workspace/*`, plus the handoff
pair in `HANDOFF_EXEMPT`. Adding a new Access-side route means adding it here too
or it will 401 behind the shared code.

**Two tiers, one login box.** `ADMIN_CODE` is a second code entered at the same
prompt. It opens everything `ACCESS_CODE` does *plus* the admin surface —
`/roster` and `/api/roster*`, which carry real staff names and employee numbers,
and `/review-lab` and `/api/review-lab*` (`ADMIN_ONLY_EXACT` /
`ADMIN_ONLY_PREFIXES`). A regular user gets **404**, not 403 — these shouldn't
advertise their existence to someone who can't use them — and the nav links are
hidden via the `is_admin` template global.
The cookie carries the tier — it stores the **configured** code that matched
(`ADMIN_CODE` or `ACCESS_CODE`), never the string the user typed. Matching is
case-insensitive so the two are equivalent, and keeping user text out of the
`Set-Cookie` header is what CodeQL's "cookie from user-supplied input" rule wants.
Don't collapse it back to one fixed value either — later requests read the cookie
to decide the tier.

For the same reason `_safe_next()` returns members of `NEXT_ALLOWED_PATHS` and a
demo-URL allowlist built from `demo_notes.json`, rather than reassembling a URL
around the submitted value — an unknown demo id drops to `/reports`.

`ADMIN_CODE` has **no default and fails closed**: unset, the admin surface is
unreachable for everyone (startup logs a warning). The one exception is an unset or
empty `ACCESS_CODE` — with the gate off entirely there is no tier to enforce, so
everyone is admin and local work doesn't silently lose the roster. Set it in
production with:

```bash
gcloud run services update prison-policy-ai --region us-central1 \
  --update-env-vars ADMIN_CODE=<code>
```

### Legacy report mode — why `/reports` returns 503

`LEGACY_REPORT_MODE` (`restricted` by default, or `pilot_fallback`) is read **per
request** by `routes/reports.py:legacy_report_control()`. In `restricted` mode the
five legacy AI/document actions — `/api/reports/classify`, `/extract`, `/generate`,
`/disciplinary`, `/download` — return **503 "Legacy report actions are temporarily
unavailable. Use the Access workspace."**

The escape hatch is the condition above it: **the restriction only applies when
`ACCESS_API_ENABLED` is on.** With identity disabled the legacy app is the whole
product and works normally, which is why local development rarely trips over it
and a configured deployment always does. `pilot_fallback` re-opens the actions and
stamps every HTML page with a transient-history warning banner (injected in an
`after_request`, not in the templates).

An invalid value raises at request time rather than defaulting — a typo must never
silently re-open legacy generation.

### What works WITHOUT credentials vs. what needs GCP or Postgres

Boots and works with **no credentials**: home, login, `/health`, the reports/roster
UIs, `POST /api/reports/download` with a `metadata` payload (fills the 005 DOCX
locally, no LLM), roster CRUD, and the entire static forms app.

The AI features call **Google Vertex AI via Application Default Credentials (ADC)** —
there is **no API-key env var**. Without ADC they 500 with "default credentials were
not found":

- `POST /api/chat` — also needs a built Agent Builder data store (`prison-policies`).
- `POST /api/reports/classify | /extract | /generate` — Gemini calls.

Enable by providing ADC (`GOOGLE_APPLICATION_CREDENTIALS=<service-account>.json`, or
`gcloud auth application-default login`) for project `gen-lang-client-0968389176`.

**Everything under `/api/v1` and `/api/web/v1` additionally needs Postgres.**
`ACCESS_API_ENABLED` is off by default; turning it on without `DATABASE_URL`,
`IDENTITY_HASH_PEPPER`, `CURSOR_SIGNING_KEY` and an HTTPS `PUBLIC_BASE_URL` makes
`IdentitySettings.from_env()` **raise at startup** — the app will not boot half
configured. With it off, both blueprints are simply not registered and their paths
404 (`tests/unit/test_web_app_routes.py` pins that).

`POST /api/feedback` needs `GITHUB_TOKEN` in the environment to open issues.

---

## Report pipeline (v2 — three explicit steps)

This is the core design, and it is still the engine underneath both products —
`reports/service.py` adapts it for `/api/v1` while the legacy page calls it
directly. The routes below are the legacy ones (503 in `restricted` mode); the
pipeline itself is unchanged either way. The UI drives three sequential POSTs;
nothing files itself.

```
Field notes
  │ POST /api/reports/classify   → classifier.py (Gemini)
  ▼   incident_type (1 of 9) + suggested charges (officer confirms)
  │ POST /api/reports/extract    → extraction.py (Gemini, temp=0, schema)
  ▼   structured slots → roster resolution → validate.find_gaps()
  │   officer answers the "Missing Information" gap panel
  │ POST /api/reports/generate   → generator.py (reports from facts only)
  ▼   + deterministic BMU defaults + name_fixer + invented_facts scan
  │ POST /api/reports/download   → filler.py fills 005 DOCX from reviewed metadata
  ▼   .docx download (no second LLM pass)
```

The 9 incident categories (from `incident_checklist_v2.json`):
`contraband`, `inmate_fight`, `staff_assault`, `forced_cell_movement`, `prea`,
`incident_no_disciplinary`, `use_of_force`, `medical_emergency`,
`other_rule_violation`. **Nine places hardcode this list** — `VALID_CATEGORIES`,
the classifier response-schema enum, the classifier prompt, the checklist JSON,
the BMU-convention sets in `routes/reports.py`, the `reports.html` dropdown and
label map, and two parity tests. They move together or classification breaks;
`tests/unit/test_classifier_schema.py` fails on a partial change.

The generated report types: `first_person` (the 005 narrative),
`supervisor_summary`, `cover_letter`, `disciplinary` (only when charges exist),
and `investigation` (only when the notes show an investigation actually happened
— gated by `validate.investigation_occurred()`, never by the model's judgement).

### Anti-fabrication is the whole point — do not weaken it

The system's promise is that **the AI never invents facts**. Preserve these
guardrails in any change:

- **Extraction runs at `temp=0` with a `response_schema`** (`schema.py`) — output is
  guaranteed-valid JSON. **Every slot is nullable**; `null` means "the notes didn't
  say," which *forces a gap question* rather than letting the model fill it in.
- **`validate.py` contains NO AI.** Gaps, checklist state, `auto_content`, and
  `[TO BE SUPPLEMENTED: ...]` markers are pure rules read verbatim from the JSON
  checklist. Put report *logic* here, not in prompts.
- **Generators receive structured facts only** (`prompts_v2.py`) — never the raw
  notes. They write prose; **code renders every header field** from slots.
- **`invented_facts()`** scans generated text for ADC#s/dates not present in the
  source and flags them (yellow highlight in the UI). ADC numbers compare on
  their **digits** — officers write `Roe 111111` in notes while the report
  renders `ADC# 111111`, and a literal comparison read every correct citation as
  invented.
- **`report_validator.py`** scores every generated report against
  `STYLE_RULINGS.md` (no AI). `repair_all()` runs first and applies only
  *mechanical* fixes — ADC# spacing, a missing rank period, a stray statement
  closer — then `validate_all()` + `summarize()` produce the `style` block in
  the `/generate` response. **A repair can never add, remove or change a fact**;
  it reformats text that is already there. Its first duty is not to cry wolf: a
  rule that flags correct output trains officers to ignore the panel, so
  `tests/unit/test_report_validator.py` opens by asserting a ruling-perfect
  report scores 1.0 with zero violations.
- **`name_fixer.enforce_naming()`** deterministically guarantees first mention =
  full form (`Inmate Last, First ADC#…` / `Rank First Last`), later mentions short.
- **Per-officer reports**: each staff member's 005 shows only *their* actions;
  `bind_reporter()` re-binds the reporter block when the officer switches.

Deterministic BMU conventions applied in `routes/reports.py` (not the model): 12-hour
time normalization, `today()` date fallback, `YYYY-MM-###` incident numbers from the
officer's last-3 digits, medical/drug-test disposition defaults, and "fights/assaults
end in Restrictive Housing." Medical detail is intentionally **left blank** on the 005.

---

## Access identity (`backend/identity/` + `/api/v1`)

Individual employee accounts, gated by `ACCESS_API_ENABLED`. The shape to hold in
your head:

- **Credentials.** Employee number + PIN. PINs are **Argon2id** (`pins.py`,
  `time_cost=3`, `memory_cost=64 MiB`), 4–8 alphanumerics, uppercased, and
  rejected if obvious (all one character, a run of the digit or letter sequence
  forwards or backwards) or equal to the employee number.
- **Sessions are opaque, never JWTs.** `issue_credential()` mints
  `secrets.token_urlsafe(32)`; only the **SHA-256 digest** is stored. Every
  lookup hashes the presented value and compares digests, so a database dump
  yields no usable token. Device IDs are HMAC'd with `IDENTITY_HASH_PEPPER`.
- **An access token plus a renewal token**, with the renewal token rotating on
  every use and `RenewalTokenHistory` catching replay of a spent one. TTLs live
  on `IdentitySettings` (15 min access; 12 h non-persistent / 30 d persistent
  renewal; 5 min step-up; 30 min browser idle).
- **Admin is a step-up, not a role flag alone** (`elevation.py`) — elevation
  expires on an idle timeout and is re-proved.
- **Every mutation writes an audit event** through an `AuditWriter`, in the same
  transaction as the change it describes.
- **Rate limits** are per employee, per device and per network
  (`_consume_login_limits`), and signal by raising `ApiError(..., status=429)`.

**The caller owns the transaction.** `service.py`, `persistence.py`,
`revisions.py`, `jobs/service.py` and friends all take a `Session` and never
commit — `session_scope()` (`persistence/database.py`) commits once on clean exit
and rolls back on any exception. This is what makes "the job row, its outbox
intent, the idempotency claim and the audit entry either all land or none do"
true. Don't add a `commit()` inside a service function.

**`ApiError` is the typed failure**, and it needs a handler on *each* blueprint
that can raise it — `api_v1_bp` and `web_api_bp` register their own. A blueprint
without one turns a deliberate 429 into a 500 through its `Exception` catch-all.

`openapi/access-v1.yaml` and `openapi/web-v1.yaml` are the published contracts.
`tests/contract/` guards them, but **mind what it actually checks**: mostly
properties of the spec documents themselves (valid OpenAPI, the auth surface is
closed, no readable identity credential appears in a response schema, the
documented examples are well-formed). Only `test_auth_contract.py` drives the real
app. **Nothing fails if a route's shape silently drifts from its spec** — so
updating the YAML alongside the route is a discipline you have to keep, not one
CI keeps for you.

### Jobs, outbox and the worker

Long AI work does not run in the request. `jobs/service.py` writes an `AiJob` and
`jobs/outbox.py` adds a `TaskOutbox` row — **a row, never a network call** —
inside the caller's transaction. `jobs/dispatcher.py` runs afterwards, reads
*committed* rows and creates deterministically named OIDC-authenticated Cloud
Tasks; `scripts/dispatch_outbox.py` is its entry point (and the reason that one
script is un-ignored in `.dockerignore`). `backend/worker/` is a separate Flask
app that receives them. **Only UUID control metadata crosses that boundary** —
no field notes, no report text.

### Guided Operations web client (`frontend/web/`, `/api/web/v1`)

The SPA authenticates with **cookies**, not bearer tokens, so `web_api/` is a
separate blueprint from `api_v1` with its own guards:

- `slut_web_access` / `slut_web_renewal` / `slut_web_device` are `HttpOnly` and
  path-scoped to the API that consumes them.
- `slut_web_csrf` is deliberately **readable and written at `Path=/`**. It is the
  visible half of a double-submit pair. It cannot be scoped to `/api/web/v1`:
  `document.cookie` matches on the **page's** path, and the page is `/workspace`,
  so an API-scoped cookie is invisible to the client, no `X-CSRF-Token` goes out,
  and every mutation 403s — silently, because `signOut()` clears the UI in a
  `finally` while the server session lives on. Backend tests cannot see this
  (the Flask test client matches the *request* path); the frontend suite runs at
  `http://localhost/workspace` so it can.
- Mutations require **all three** of: a same-origin check (`Sec-Fetch-Site` +
  `Origin` vs. host, first inside `require_browser_csrf` — note the decorator
  order puts `require_browser_session` ahead of it, so the session is resolved
  before the origin is checked, contrary to that function's docstring), the
  double-submit cookie/header match, and the header hashed against the
  per-session digest in `BrowserSessionBinding`. Compare with `compare_digest`.
- `require_browser_session` opens a `session_scope()` into `g` and the blueprint's
  `teardown_request` closes it. Views use `current_browser_session()`, not their
  own scope.

`/workspace` serves `index.html` for every sub-path (client-side routing) and is
registered **unconditionally**, while `web_api_bp` registers only when identity is
enabled — so with identity off the shell loads against a 404ing API.

---

## Roster persistence

The roster is the only runtime state the *legacy* app writes, and it has two writers:
`/api/roster` CRUD and `add_staff_from_gap_answer()` (auto-adding an officer named
in field notes). Both go through **`backend/reports/roster_store.py`** — never write
`staff_roster.json` directly.

- **No `ROSTER_BUCKET` (default): the packaged file.** What local dev and the test
  suite use — no bucket, no credentials, no network.
- **`ROSTER_BUCKET` set: a GCS object.** Cloud Run's filesystem is scratch space
  discarded on restart, scale-to-zero and every redeploy, so file-backed roster edits
  vanish in production and instances never see each other's writes.

Every mutation goes through `roster_store.update(mutate)`, which re-reads, re-applies
and retries on conflict, using the GCS object generation as a compare-and-swap. **The
`mutate` callback can run more than once**, so re-check preconditions (duplicate
checks especially) *inside* it rather than before the call — a check made once up front
is exactly the race that used to drop a new staff member silently. Returning `None`
from `mutate` means "nothing changed" and skips the write.

Reads are cached for `ROSTER_CACHE_TTL` seconds (default 30) because lookups run per
person per extraction; writes bust the cache immediately, so the TTL only bounds how
long one instance can lag behind another's edit.

To enable in production:
```bash
gsutil mb -l us-central1 gs://<bucket>          # once
gcloud run services update prison-policy-ai --region us-central1 \
  --update-env-vars ROSTER_BUCKET=<bucket>
```
The Cloud Run service account needs `roles/storage.objectAdmin` on that bucket. The
object is created on the first roster edit, seeded from `templates/staff_roster.json`.

## Policy chat pipeline

`backend/pipeline/query.py`: `answer_question()` runs **gate → expand → search →
generate**.

- **Gate** (`_classify_query`): keyword fast-path then a Gemini fallback; off-topic
  queries get a canned "you're at work" reply. Fails **open**.
- **Augment** (`retrieval.augment_query`, deterministic — no LLM): appends formal
  policy terms for known officer slang (e.g. "hooking up" → "PREA sexual misconduct")
  to the question instead of replacing it. Replaced the old LLM `_expand_query`,
  which cost a round-trip and discarded the question's semantics.
- **Search**: Vertex AI **Agent Builder / Discovery Engine** data store
  (`prison-policies-engine`) via REST — *not* the older `vertexai.preview.rag` corpus
  (that migration was to draw on the Agent Builder credit; README wording may lag).
- **Generate**: Gemini with `CHAT_SYSTEM_PROMPT`, which embeds hard-coded
  `DOMAIN_RULES` (PREA zero-tolerance, undue familiarity) the model must never
  contradict. The top `MAX_CONTEXT_PASSAGES` passages (deduped + per-source-capped
  by `retrieval.select_passages`) are numbered and the model
  is told to cite them inline as `[n]`; `citations.py` (pure) then renumbers the
  markers 1..k and surfaces **only the cited passages**. An answer that cites
  nothing is flagged with an `UNGROUNDED_NOTE` rather than presented as
  document-backed. Returns `{answer, citations, sources, retrieved_sources}`
  (`retrieved_sources` = all retrieved labels, for eval/debug).

---

## Testing

Six layers. **`pytest.ini` sets `testpaths = tests/unit`, so a bare
`python3 -m pytest` runs only layer 1** — the other pytest directories exist and
are green, but you have to name them. Don't read "1262 passed" as full coverage.

```bash
pip install -r requirements.txt   # pytest + deps
python3 -m pytest                 # layer 1 only (tests/unit, via pytest.ini)
python3 -m pytest tests/unit tests/contract tests/security -q     # no services
python3 -m pytest tests/integration -q                            # needs Postgres
```

**1. Fast unit tests (`tests/unit/`, ~76 files, no GCP, no DB).** The deterministic,
credential-free logic: `validate.find_gaps` (gap/marker rules), `name_fixer`, the
BMU-convention helpers in `routes/reports.py` (time normalization, incident numbers,
name/rank parsing, shift labels), the feedback rate limiter, the policy-chat eval
scorer, and now the identity/browser-session/CSRF units. The root `conftest.py`
puts the repo root on `sys.path`. The `routes/reports.py` helper tests import the
Vertex SDK at module load, so they **skip cleanly** if `google-genai` isn't
installed locally and **run** in CI. Add a test here whenever you touch a pure
helper or a checklist rule.

**2. Integration (`tests/integration/`, ~33 files, needs Postgres).** Real
SQLAlchemy against a live database via `TEST_DATABASE_URL`; CI runs a `postgres:17`
service container. Not collected by a bare `pytest` run — CI invokes the directory
explicitly.

**3. Contract (`tests/contract/`).** Guards `openapi/access-v1.yaml` and
`openapi/web-v1.yaml` — that the spec is valid, the auth surface is closed, no
readable credential appears in a response schema, and the documented examples are
well-formed. Only `test_auth_contract.py` exercises the app; the rest read the YAML.
See the caveat under Access identity: route drift is **not** caught.

**4. Security (`tests/security/`).** Cookie flags and paths, and the safe-profile
shape (asserting no PIN or token field can leak into a serialized profile).

**5. Pipeline harness (`tests/test_pipeline.py`, needs GCP ADC).** Runs fixtures
through classify → extract → generate, writes every intermediate to
`tests/output/<name>/`, and can diff against a saved snapshot. It is **not** collected
by pytest (excluded via `testpaths`).

```bash
PYTHONPATH=. python3 tests/test_pipeline.py fixtures/inmate_fight_01.txt
PYTHONPATH=. python3 tests/test_pipeline.py fixtures/inmate_fight_01.txt --step extract
PYTHONPATH=. python3 tests/test_pipeline.py --demo list          # the demo scenarios
PYTHONPATH=. python3 tests/test_pipeline.py --demo use_of_force_oc --compare
PYTHONPATH=. python3 tests/test_pipeline.py --all --compare
```

Fixtures live in `tests/fixtures/*.txt` (real-style field notes). **Running the AI
steps needs GCP ADC**; `--step classify`/`extract` still call Gemini. Snapshots are
saved under `tests/output/<name>_snapshot/` on first `--compare`.

**6. Policy-chat eval harness (`tests/eval/`, needs GCP ADC to run).** Measures the
chat pipeline against a curated question set (`cases.jsonl`) on three signals: gate
accuracy, retrieval hit-rate, and answer correctness (must-contain facts /
must-not-contain forbidden claims — the PREA/undue-familiarity cases assert the hard
`DOMAIN_RULES`). The scorer (`scorer.py`) is pure and unit-tested in layer 1; the
runner drives the live pipeline. Expand/tune `cases.jsonl` against the real corpus.

```bash
PYTHONPATH=. python3 tests/eval/run_eval.py            # full scorecard → tests/eval/output/
PYTHONPATH=. python3 tests/eval/run_eval.py --gate-only
PYTHONPATH=. python3 tests/eval/run_eval.py --id prea_dating
```

**Frontend tests (`frontend/web/`, vitest + Testing Library).** `npm test` from
`frontend/web`. The suite runs at `http://localhost/workspace`
(`environmentOptions.jsdom.url` in `vitest.config.ts`) so browser cookie-path
scoping behaves the way it does in production — a test run at `/` cannot see the
class of bug described under Guided Operations above.

---

## Conventions & gotchas

- **No JS package manager anywhere** — the frontend is fully vendored React; there is
  no `package.json`. Don't add a build step to `frontend/forms/`. **This no longer
  applies repo-wide** — `frontend/web/` is a normal npm project with Vite. Keep the
  two straight.
- **`frontend/web/` has no committed lockfile**, and CI installs with
  `npm install --legacy-peer-deps`, so CI, the Docker `web-build` stage and a
  developer's machine can resolve different trees for the auth client. If you touch
  dependencies, raise this rather than quietly working around it.
- **Two workflows build the SPA** (`web-tests.yml` and the `frontend` job of
  `guided-operations-foundation.yml`) with near-identical steps, which is why every
  PR shows duplicate frontend checks.
- **Absolute imports only** (`from backend.reports...`). Keep the repo root on
  `PYTHONPATH`; the Dockerfile sets `PYTHONPATH=/app`.
- **`.dockerignore` excludes `scripts/` and `frontend/` wholesale, then re-includes
  exactly two things**: `!scripts/dispatch_outbox.py` and `!frontend/web/**`. A new
  `COPY` in the Dockerfile for anything else under those trees fails the build with
  a confusing `"not found"` on a file that plainly exists — the path is simply not
  in the build context.
- **Never hardcode `/static/...` in a template** — use `{{ asset_url('file.ext') }}`
  (`backend/webapp/assets.py`). It appends a content hash, which is what lets static
  responses carry a 1-year `immutable` cache header. A hardcoded URL silently drops to
  a 1-hour cache, and `tests/unit/test_assets.py` covers the policy either way.
- **The shield art is WebP; the `.png` files are sources, not assets.** Templates load
  only `shield-*.webp`, generated by `scripts/optimize_images.py` and kept out of the
  runtime image by `.dockerignore`. Edit a source PNG → re-run the script, or CI's
  `--check` step fails. (`claw-rips.png` stays PNG — WebP came out larger.)
- **Fonts are self-hosted; don't add a font CDN.** `fonts.css` carries Inter, Open Sans
  and the italic-latin cut of Instrument Serif. A `fonts.googleapis.com` link is two
  blocking round-trips to a third party on first paint.
- **Change report behavior in `incident_checklist_v2.json` first**, then wire it in
  `validate.py`. Prompts are for *prose*, not logic or field values.
- **Roster shift codes**: single letters `A/B/C/D/U/F` (A/B=Day, C/D=Night,
  U=Utility, F=Field). Reports render `A` as `"A Shift"`; omit clock times from labels.
- **Copy conventions** (from `AGENTS.md`): say "field notes", never "shift notes";
  "Forms page" usually means `/reports` (the Report Writing Assistant), not
  `frontend/forms/`. Trust-first, corrections-professional tone (navy/gold, light-blue
  LIVE/CTA accents). Keep nav brand markup consistent across pages.
- **Config lives in two places, and which one depends on the product.** Legacy and
  pipeline knobs go in `backend/pipeline/config.py` (`GCP_PROJECT_ID`, `GCP_LOCATION`,
  `FAST_MODEL`, `PRO_MODEL`, `GCP_MODEL_LOCATION`, `RAG_CORPUS_NAME`, `ACCESS_CODE`,
  `ADMIN_CODE`, `ROSTER_BUCKET`, `REVIEW_LAB_ENABLED`, `LEGACY_REPORT_MODE`,
  `LOG_LEVEL`, …), read at import time. Access/identity knobs go on
  `IdentitySettings` in `backend/identity/config.py` (`ACCESS_API_ENABLED`,
  `DATABASE_URL`, `IDENTITY_HASH_PEPPER`, `CURSOR_SIGNING_KEY`, `PUBLIC_BASE_URL`,
  `RELEASE_VERSION`, the `*_CLIENT_VERSION` pair, TTLs), read once at startup and
  **validated hard** — a bad value raises rather than defaulting.
- **Two Gemini tiers** (config.py): `FAST_MODEL` (default `gemini-3.6-flash`) drives the
  chat gate, incident classifier, and slot extraction; `PRO_MODEL` (default
  `gemini-3.1-pro-preview` — Vertex only serves this model under the "-preview" suffix
  while it's in preview status) drives the chat answer synthesis and the report
  generators. Both are
  served from `MODEL_LOCATION` (default `global` — Gemini 3.x is global-only, even though
  the Agent Builder data store lives in us-central1). `GENERATION_MODEL` remains as a
  back-compat alias for the FAST tier.
- **Search config knobs** (config.py): the chat's Discovery Engine serving config is
  assembled by `serving_config_path()` from `AGENT_BUILDER_LOCATION`,
  `AGENT_BUILDER_COLLECTION`, `AGENT_BUILDER_ENGINE_ID`, and
  `AGENT_BUILDER_SERVING_CONFIG` — a mismatch in any one 404s every search. The
  resolved values are logged at startup (`log_search_config()`) and printed by
  `scripts/check_search.py`. **Ingestion and search target different resources:**
  `import_to_agent_builder.py` writes into the *data store*
  (`AGENT_BUILDER_DATA_STORE`), while the chat searches the *engine* built on it — if
  the engine is attached to a different store, imports succeed and search still finds
  nothing.
- **Diagnosing a broken chat:** `PYTHONPATH=. python3 scripts/check_search.py "use of
  force"` prints the resolved config and runs one query, reporting latency, raw hit
  count, and usable passages. It distinguishes config/auth failure from an empty
  corpus from hits-with-no-readable-text. Exits non-zero on failure (needs ADC).
- **Feedback widget** (`static/js/feedback.js` + `/api/feedback`) files GitHub issues
  into `justinpeterman-droid/prison-policy-ai`; requires `GITHUB_TOKEN`.

---

## Deploy & CI

**There is no automatic Cloud Run deploy.** `cloud-run.yml`, `backend/scripts/deploy.sh`
and `scripts/merge_and_deploy.py` were all removed in `5b21e94` ("gate implementation
and deployment prerequisites") — deliberately, pending the release gates in
`docs/operations/`. `README.md` and `HANDOFF.md` still show the old command; they lag.
Don't re-add a deploy workflow without checking `docs/operations/release-gates.md`
first. The manual command still works if someone with credentials runs it:

```bash
gcloud run deploy prison-policy-ai --source . --region us-central1 \
  --project gen-lang-client-0968389176 --allow-unauthenticated
```

The root `Dockerfile` is **two-stage**: a `node:22-slim` `web-build` stage runs
`npm run build` for `frontend/web/`, then the `python:3.14-slim` runtime stage copies
only the built assets forward (`COPY --from=web-build`), installs
`backend/requirements.txt`, and runs gunicorn with `PYTHONPATH=/app`. It also copies
`alembic.ini`, `migrations/` and `scripts/dispatch_outbox.py`.

Workflows:

- **`tests.yml`** — pytest on 3.12 and 3.14 against a `postgres:17` service
  container: `pytest -q` (unit), then `pytest tests/integration -q`, then
  `scripts/optimize_images.py --check`.
- **`web-tests.yml`** — the SPA: install, `npm test`, typecheck, build.
- **`guided-operations-foundation.yml`** — path-filtered; frontend + a named list of
  browser/identity backend tests, then a `docker build .` gated on both. Adding a
  test file to `tests/unit` does **not** put it in that job — the list is explicit.
- **`pages.yml`** — publishes the whole repo to GitHub Pages on push to `main`; the
  root `index.html` redirects to `/frontend/forms/`.
- **`codacy.yml`** — static analysis. CodeQL also runs on this repo.

---

## Working agreement for AI assistants

- Do the smallest change that satisfies the request; match surrounding style.
- **Know which product you are in.** Legacy Jinja + shared code, or Access +
  per-employee identity. A fix in the wrong one is wasted, and wiring the two
  together casually is how the shared-code gate ends up in front of an
  authenticated API (or, worse, off in front of a legacy one).
- Never dilute the anti-fabrication guardrails to make a report "look complete."
- **Don't weaken an auth guard to make a test pass.** The same-origin check, the
  double-submit pair and the per-session digest are three separate defenses on
  purpose. If one is failing, the cookie or the wiring is wrong — not the guard.
- **A green test suite is weaker evidence here than it looks.** A bare `pytest`
  runs one of six layers; the browser-auth defects found in review all had passing
  tests that asserted a fiction the server never produced. When you fix a bug,
  revert the source with your new test in place and watch it fail before you claim
  it covers anything.
- When you change report rules, add/adjust a `tests/fixtures/*.txt` case and run the
  harness with `--compare`.
- Update `openapi/*.yaml` in the same change as the route it describes — no test
  will catch you if you don't.
- Report outcomes honestly: if the AI steps couldn't run for lack of ADC or
  Postgres, say so.
- Commit to the designated feature branch with clear messages; open a **draft** PR.
