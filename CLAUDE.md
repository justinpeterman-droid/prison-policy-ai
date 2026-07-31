# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.
Read this first; it captures the non-obvious structure, workflows, and conventions
that the source alone won't tell you.

> Companion docs: `README.md` (product overview), `AGENTS.md` (run commands +
> learned user preferences), `VISION.md` (product vision), `REPORT_ENGINE_SPEC.md`,
> `UI_SPEC.md`, `REPORT_WRITING_RULES.md`. When those and this file disagree, trust
> the **code**, then update the docs.

---

## What this is

**Prison Policy AI** is an AI assistant for Arkansas Department of Correction (ADC)
staff, focused on the BMU / Grimes Unit. It is a single **Flask web app**
(`backend/`) exposing two tools plus a staff-roster manager:

- **📋 Policy Knowledge Expert** (`/chat`) — RAG Q&A over ADC policy documents,
  answers with citations.
- **📝 Report Writing Assistant** (`/reports`) — turns an officer's free-text
  "field notes" into classified, gap-checked, generated incident reports and a
  filled-in official 005 DOCX. This is the heart of the product.
- **👥 Unit Roster** (`/roster`) — CRUD over `templates/staff_roster.json`.

There is also a separate, build-free **static React forms app**
(`frontend/forms/`) — 6 hand-fillable ADC forms, deployed to GitHub Pages. It is
independent of the Flask app; don't conflate the two.

**Deployed:** Cloud Run — `https://prison-policy-ai-403037827694.us-central1.run.app`
**GCP project:** `gen-lang-client-0968389176` · **Region:** `us-central1`

---

## Repository layout

```
prison-policy-ai/
├── backend/                     # THE Flask product (absolute `backend.*` imports)
│   ├── pipeline/                # Policy RAG chat
│   │   ├── config.py            # All env-driven config + ACCESS_CODE + logger
│   │   ├── query.py             # gate → expand → search (Agent Builder) → generate
│   │   ├── extract.py, chunk.py, embed.py, import_to_agent_builder.py  # corpus build
│   ├── reports/                 # v2 report engine (see "Report pipeline" below)
│   │   ├── classifier.py        # Incident-type detection (Gemini) + charge suggestion
│   │   ├── extraction.py        # Slot extraction (Gemini, temp=0, response_schema)
│   │   ├── schema.py            # Slot schema, response_schema builder, reporter binding
│   │   ├── validate.py          # Gap detection, auto_content, invented_facts — NO AI
│   │   ├── generator.py         # 4 report generators (structured facts only)
│   │   ├── prompts.py           # Classifier prompt + charge-catalog loader
│   │   ├── prompts_v2.py        # v2 generation prompts (never see raw notes)
│   │   ├── name_fixer.py        # Deterministic first-mention/full-name enforcement
│   │   ├── report_validator.py  # Extra report checks
│   │   ├── filler.py            # DOCX template filling (python-docx)
│   │   └── roster.py            # Staff roster load + fuzzy resolution + auto-persist
│   └── webapp/                  # Flask + Gunicorn
│       ├── app.py               # App factory `create_app()`, cookie auth gate
│       ├── routes/
│       │   ├── chat.py          # /chat, POST /api/chat
│       │   ├── reports.py       # /reports + the v2 3-step + /download API
│       │   ├── roster.py        # /api/roster* CRUD
│       │   └── feedback.py      # POST /api/feedback → opens a GitHub issue
│       ├── templates/           # home/chat/reports/roster/login .html (server-rendered)
│       └── static/              # style.css, tokens.css, fonts, seal.svg, js/feedback.js
├── frontend/forms/              # Standalone static React app (vendored React, no npm)
├── templates/                   # DATA the backend reads at runtime (see below)
├── tests/                       # Pipeline harness + fixtures + golden output
├── scripts/                     # One-off OCR / corpus / deploy helpers
├── Dockerfile                   # Cloud Run image (root context, PYTHONPATH=/app)
├── requirements.txt             # Root mirror of backend/requirements.txt
└── .github/workflows/           # cloud-run.yml, pages.yml, codacy.yml
```

### `templates/` is runtime data, not Jinja templates

The top-level `templates/` directory holds **data files the report engine loads at
runtime** — not HTML. (Jinja HTML lives in `backend/webapp/templates/`.) Key files:

| File | Role |
|------|------|
| `incident_checklist_v2.json` | **Authoritative** — 7 categories, required slots, conditional rules, gap questions, `auto_content` sentences, shared option sets. Change report behavior *here*, not in prompts. |
| `disciplinary_charges.json` | Extracted disciplinary handbook charges; classifier validates suggestions against these. |
| `staff_roster.json` | The live unit roster (`{shifts, staff}`). Read+written by `/api/roster` and auto-persisted from gap answers. |
| `location_map.json` | Slang → formal BMU location names. |
| `005_template_v3.docx` | Current ADC 005 replica the filler populates (older `005*.docx` are legacy). |
| `report_style_guide.md` | Naming / tone rules the prompts + `name_fixer.py` enforce. |

---

## Running the app

Absolute `backend.*` imports mean you **must run from the repo root with the root on
`PYTHONPATH`** — never `cd backend/webapp` and run `app.py` bare.

```bash
pip install -r requirements.txt            # or backend/requirements.txt (identical)

# Dev (debug reloader on):
PYTHONPATH=. python3 backend/webapp/app.py            # → http://localhost:8080

# Prod-style:
PYTHONPATH=. gunicorn --bind :8080 "backend.webapp.app:create_app()"
```

Static forms app (no build): open `frontend/forms/index.html`, or serve the repo root
(`python3 -m http.server 8000`) and visit `/frontend/forms/`. Optional recompile:
`npx @babel/cli --presets @babel/preset-react src.jsx -o app.js`.

### Auth gate (non-obvious)

Every route except `/login`, `/logout`, `/health`, and `/static/*` is gated by a
shared access code (`backend/webapp/app.py`). `ACCESS_CODE` defaults to **`slut`**
(case-insensitive; the product brand is "Standard Logistics & Unit Tools" → S-L-U-T,
navy + gold). Log in at `/login`, or bookmark any URL with `?code=slut` (sets a
cookie, redirects clean). API routes return **401 JSON**; page routes redirect to
`/login`. Set `ACCESS_CODE=""` to disable auth entirely.

### What works WITHOUT credentials vs. what needs GCP

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

`POST /api/feedback` needs `GITHUB_TOKEN` in the environment to open issues.

---

## Report pipeline (v2 — three explicit steps)

This is the core design. The UI drives three sequential POSTs; nothing files itself.

```
Field notes
  │ POST /api/reports/classify   → classifier.py (Gemini)
  ▼   incident_type (1 of 7) + suggested charges (officer confirms)
  │ POST /api/reports/extract    → extraction.py (Gemini, temp=0, schema)
  ▼   structured slots → roster resolution → validate.find_gaps()
  │   officer answers the "Missing Information" gap panel
  │ POST /api/reports/generate   → generator.py (4 reports from facts only)
  ▼   + deterministic BMU defaults + name_fixer + invented_facts scan
  │ POST /api/reports/download   → filler.py fills 005 DOCX from reviewed metadata
  ▼   .docx download (no second LLM pass)
```

The 7 incident categories (from `incident_checklist_v2.json`):
`contraband`, `inmate_fight`, `staff_assault`, `forced_cell_movement`, `prea`,
`incident_no_disciplinary`, `other_rule_violation`.

The four generated report types: `first_person` (the 005 narrative),
`supervisor_summary`, `cover_letter`, and `disciplinary` (only when charges exist).

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
  source and flags them (yellow highlight in the UI).
- **`name_fixer.enforce_naming()`** deterministically guarantees first mention =
  full form (`Inmate Last, First ADC#…` / `Rank First Last`), later mentions short.
- **Per-officer reports**: each staff member's 005 shows only *their* actions;
  `bind_reporter()` re-binds the reporter block when the officer switches.

Deterministic BMU conventions applied in `routes/reports.py` (not the model): 12-hour
time normalization, `today()` date fallback, `YYYY-MM-###` incident numbers from the
officer's last-3 digits, medical/drug-test disposition defaults, and "fights/assaults
end in Restrictive Housing." Medical detail is intentionally **left blank** on the 005.

---

## Policy chat pipeline

`backend/pipeline/query.py`: `answer_question()` runs **gate → expand → search →
generate**.

- **Gate** (`_classify_query`): keyword fast-path then a Gemini fallback; off-topic
  queries get a canned "you're at work" reply. Fails **open**.
- **Expand** (`_expand_query`): rewrites colloquial officer language into formal
  policy terms (e.g. "hooking up with an inmate" → "PREA sexual misconduct").
- **Search**: Vertex AI **Agent Builder / Discovery Engine** data store
  (`prison-policies-engine`) via REST — *not* the older `vertexai.preview.rag` corpus
  (that migration was to draw on the Agent Builder credit; README wording may lag).
- **Generate**: Gemini with `CHAT_SYSTEM_PROMPT`, which embeds hard-coded
  `DOMAIN_RULES` (PREA zero-tolerance, undue familiarity) the model must never
  contradict. Returns `{answer, citations, sources}`.

---

## Testing

There is a **pipeline harness**, not a pytest suite. It runs fixtures through
classify → extract → generate, writes every intermediate to `tests/output/<name>/`,
and can diff against a saved snapshot.

```bash
PYTHONPATH=. python3 tests/test_pipeline.py fixtures/inmate_fight_01.txt
PYTHONPATH=. python3 tests/test_pipeline.py fixtures/inmate_fight_01.txt --step extract
PYTHONPATH=. python3 tests/test_pipeline.py --all --compare
```

Fixtures live in `tests/fixtures/*.txt` (real-style field notes). **Running the AI
steps needs GCP ADC**; `--step classify`/`extract` still call Gemini. Snapshots are
saved under `tests/output/<name>_snapshot/` on first `--compare`.

---

## Conventions & gotchas

- **No JS package manager anywhere** — the frontend is fully vendored React; there is
  no `package.json`. Don't add a build step to `frontend/forms/`.
- **Absolute imports only** (`from backend.reports...`). Keep the repo root on
  `PYTHONPATH`; the Dockerfile sets `PYTHONPATH=/app`.
- **Change report behavior in `incident_checklist_v2.json` first**, then wire it in
  `validate.py`. Prompts are for *prose*, not logic or field values.
- **Roster shift codes**: single letters `A/B/C/D/U/F` (A/B=Day, C/D=Night,
  U=Utility, F=Field). Reports render `A` as `"A Shift"`; omit clock times from labels.
- **Copy conventions** (from `AGENTS.md`): say "field notes", never "shift notes";
  "Forms page" usually means `/reports` (the Report Writing Assistant), not
  `frontend/forms/`. Trust-first, corrections-professional tone (navy/gold, light-blue
  LIVE/CTA accents). Keep nav brand markup consistent across pages.
- **Config is centralized** in `backend/pipeline/config.py` and read from env vars
  (`GCP_PROJECT_ID`, `GCP_LOCATION`, `GENERATION_MODEL`, `RAG_CORPUS_NAME`,
  `ACCESS_CODE`, `LOG_LEVEL`, …). Add new knobs there.
- **Feedback widget** (`static/js/feedback.js` + `/api/feedback`) files GitHub issues
  into `justinpeterman-droid/prison-policy-ai`; requires `GITHUB_TOKEN`.

---

## Deploy & CI

- **Cloud Run** (the Flask product): pushing to `main` triggers
  `.github/workflows/cloud-run.yml` (`gcloud run deploy --source .`). Manual:
  ```bash
  gcloud run deploy prison-policy-ai --source . --region us-central1 \
    --project gen-lang-client-0968389176 --allow-unauthenticated
  ```
  Image builds from the root `Dockerfile` (Python 3.14-slim, gunicorn, `PYTHONPATH=/app`).
- **GitHub Pages** (the static forms app): `.github/workflows/pages.yml` publishes the
  whole repo on push to `main`; root `index.html` redirects to `/frontend/forms/`.
- **Codacy**: `.github/workflows/codacy.yml` runs static analysis.

---

## Working agreement for AI assistants

- Do the smallest change that satisfies the request; match surrounding style.
- Never dilute the anti-fabrication guardrails to make a report "look complete."
- When you change report rules, add/adjust a `tests/fixtures/*.txt` case and run the
  harness with `--compare`.
- Report outcomes honestly: if the AI steps couldn't run for lack of ADC, say so.
- Commit to the designated feature branch with clear messages; open a **draft** PR.
