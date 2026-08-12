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
│   │   ├── query.py             # gate → augment → search (Agent Builder) → rerank → generate
│   │   ├── rerank.py            # Semantic reranking (Ranking API); fails open
│   │   ├── gcp_auth.py          # Cached ADC access token, shared by both REST callers
│   │   ├── extract.py, chunk.py, embed.py, import_to_agent_builder.py  # corpus build
│   ├── reports/                 # v2 report engine (see "Report pipeline" below)
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
│   │   └── roster.py            # Staff roster load + fuzzy resolution + auto-persist
│   └── webapp/                  # Flask + Gunicorn
│       ├── app.py               # App factory `create_app()`, cookie auth gate
│       ├── assets.py            # `asset_url()` versioning, cache headers, gzip
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
├── requirements.txt             # Local/CI deps (backend/requirements.txt is what Docker installs; it adds google-cloud-aiplatform for corpus builds)
└── .github/workflows/           # cloud-run.yml, pages.yml, codacy.yml
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

### Auth gate (non-obvious)

Every route except `/login`, `/logout`, `/health`, and `/static/*` is gated by a
shared access code (`backend/webapp/app.py`). `ACCESS_CODE` defaults to **`slut`**
(case-insensitive; the product brand is "Standard Logistics & Unit Tools" → S-L-U-T,
navy + gold). Log in at `/login`, or bookmark any URL with `?code=slut` (sets a
cookie, redirects clean). API routes return **401 JSON**; page routes redirect to
`/login`. Set `ACCESS_CODE=""` to disable auth entirely.

**Two tiers, one login box.** `ADMIN_CODE` is a second code entered at the same
prompt. It opens everything `ACCESS_CODE` does *plus* the Unit Roster (`/roster`
and `/api/roster*`), which carries real staff names and employee numbers. A regular
user gets **404**, not 403 — the roster shouldn't advertise its existence to someone
who can't use it — and the nav link is hidden via the `is_admin` template global.
The cookie carries the tier — it stores the **configured** code that matched
(`ADMIN_CODE` or `ACCESS_CODE`), never the string the user typed. Matching is
case-insensitive so the two are equivalent, and keeping user text out of the
`Set-Cookie` header is what CodeQL's "cookie from user-supplied input" rule wants.
Don't collapse it back to one fixed value either — later requests read the cookie
to decide the tier.

For the same reason `_safe_next()` returns members of `NEXT_ALLOWED_PATHS` and a
demo-URL allowlist built from `demo_notes.json`, rather than reassembling a URL
around the submitted value — an unknown demo id drops to `/reports`.

`ADMIN_CODE` has **no default and fails closed**: unset, the roster is unreachable
for everyone (startup logs a warning). The one exception is `ACCESS_CODE=""` — with
the gate off entirely there is no tier to enforce, so everyone is admin and local
work doesn't silently lose the roster. Set it in production with:

```bash
gcloud run services update prison-policy-ai --region us-central1 \
  --update-env-vars ADMIN_CODE=<code>
```

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

## Roster persistence

The roster is the only runtime state the app writes, and it has two writers:
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

`backend/pipeline/query.py`: `answer_question()` runs **gate → augment → search →
rerank → generate**.

- **Gate** (`_classify_query`): keyword fast-path then a Gemini fallback; off-topic
  queries get a canned "you're at work" reply. Fails **open**.
- **Augment** (`retrieval.augment_query`, deterministic — no LLM): appends formal
  policy terms for known officer slang (e.g. "hooking up" → "PREA sexual misconduct")
  to the question instead of replacing it. Replaced the old LLM `_expand_query`,
  which cost a round-trip and discarded the question's semantics.
- **Search**: Vertex AI **Agent Builder / Discovery Engine** data store
  (`prison-policies-engine`) via REST — *not* the older `vertexai.preview.rag` corpus
  (that migration was to draw on the Agent Builder credit; README wording may lag).
- **Rerank** (`rerank.rerank_passages`, Vertex AI **Ranking API**): a cross-encoder
  pass that reorders the retrieved passages by how well each one answers the
  question, before `select_passages` trims them. Retrieval is tuned for recall and
  scores question and passage independently; the ranker reads them *together*.
  This matters because `select_passages` spends its per-source cap and character
  budget in list order and keeps only the first `MAX_CONTEXT_PASSAGES` — the
  ordering it is handed decides what the generator ever sees. **Fails open:** any
  error, timeout or missing permission returns the retriever's own ordering, so
  the chat is never worse than before. A *permanent* failure (400/401/403/404 —
  wrong ranking-config path, API not enabled, missing IAM) disables it for the
  process after one log line, rather than paying the latency on every turn
  forever. It ranks against the officer's **original** question, not the
  slang-augmented search query — the appended terms are a recall device for
  Discovery Engine and only dilute a semantic question/passage comparison.
  `RERANK_ENABLED=0` switches it off; `rerank_status()` reports live state and
  `scripts/check_search.py` prints it.
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

Three layers:

**1. Fast unit tests (`tests/unit/`, pytest — no GCP).** Cover the deterministic,
credential-free logic: `validate.find_gaps` (gap/marker rules), `name_fixer`, the
BMU-convention helpers in `routes/reports.py` (time normalization, incident numbers,
name/rank parsing, shift labels), the feedback rate limiter, and the policy-chat eval
scorer (`tests/eval/scorer.py`). Run on every PR; run locally with:

```bash
pip install -r requirements.txt   # pytest + deps
python3 -m pytest                 # scoped to tests/unit via pytest.ini
```

`pytest.ini` sets `testpaths = tests/unit`; the root `conftest.py` puts the repo root
on `sys.path`. The `routes/reports.py` helper tests import the Vertex SDK at module
load, so they **skip cleanly** if `google-genai` isn't installed locally and **run**
in CI. Add a test here whenever you touch a pure helper or a checklist rule.

**2. Pipeline harness (`tests/test_pipeline.py`, needs GCP ADC).** Runs fixtures
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

**3. Policy-chat eval harness (`tests/eval/`, needs GCP ADC to run).** Measures the
chat pipeline against a curated question set (`cases.jsonl`) on three signals: gate
accuracy, retrieval hit-rate, and answer correctness (must-contain facts /
must-not-contain forbidden claims — the PREA/undue-familiarity cases assert the hard
`DOMAIN_RULES`). The scorer (`scorer.py`) is pure and unit-tested in layer 1; the
runner drives the live pipeline. Expand/tune `cases.jsonl` against the real corpus.

```bash
PYTHONPATH=. python3 tests/eval/run_eval.py            # full scorecard → tests/eval/output/
PYTHONPATH=. python3 tests/eval/run_eval.py --gate-only
PYTHONPATH=. python3 tests/eval/run_eval.py --id prea_dating
PYTHONPATH=. python3 tests/eval/run_eval.py --no-rerank   # A/B the semantic reranker
```

**No baseline has ever been recorded** — `tests/eval/output/` does not exist in any
checkout, and `cases.jsonl`'s `expect_sources` are still placeholder titles rather
than real corpus doc names. Every retrieval-quality change (reranking included) is
therefore reasoned, not measured. Running the set twice — plain, then `--no-rerank`
— is the cheapest way to change that; the scorecard stamps which mode it ran in.

---

## Conventions & gotchas

- **No JS package manager anywhere** — the frontend is fully vendored React; there is
  no `package.json`. Don't add a build step to `frontend/forms/`.
- **Absolute imports only** (`from backend.reports...`). Keep the repo root on
  `PYTHONPATH`; the Dockerfile sets `PYTHONPATH=/app`.
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
- **Config is centralized** in `backend/pipeline/config.py` and read from env vars
  (`GCP_PROJECT_ID`, `GCP_LOCATION`, `FAST_MODEL`, `PRO_MODEL`, `GCP_MODEL_LOCATION`,
  `RAG_CORPUS_NAME`, `ACCESS_CODE`, `ADMIN_CODE`, `ROSTER_BUCKET`, `RERANK_ENABLED`,
  `LOG_LEVEL`, …). Add new knobs there.
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
- **Rerank config knobs** (config.py): `RERANK_ENABLED` (default on),
  `RERANK_MODEL`, and the `ranking_config_path()` parts `RERANK_LOCATION` /
  `RERANK_CONFIG_ID`. The Ranking API is a **separate resource from the search
  engine** — a working chat says nothing about whether reranking is reaching it,
  because reranking fails open and silently. `search_config_summary()` includes the
  resolved ranking config, and `scripts/check_search.py` shows whether the ranker
  ran, how long it took, and whether it changed the order. The Cloud Run service
  account needs `roles/discoveryengine.viewer` (or equivalent) for
  `discoveryengine.rankingConfigs.rank`.
- **Diagnosing a broken chat:** `PYTHONPATH=. python3 scripts/check_search.py "use of
  force"` prints the resolved config and runs one query, reporting latency, raw hit
  count, and usable passages. It distinguishes config/auth failure from an empty
  corpus from hits-with-no-readable-text. Exits non-zero on failure (needs ADC).
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
