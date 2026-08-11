# Demo Review Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a removable admin-only web lab for running, editing, saving, listing, and exporting the three report demos, while bringing the credentialed CLI demo runner to feature parity.

**Architecture:** Reuse the existing report APIs and `reports.html` through a server-selected review mode. Keep canonical demo loading, gap-answer merging, submission validation, and GCS persistence in small backend modules; store each review as an immutable JSON object under a dedicated prefix in the existing private bucket. Keep the normal report page unchanged unless `review_mode=True`, and hide the entire lab behind both `ADMIN_CODE` and `REVIEW_LAB_ENABLED`.

**Tech Stack:** Python 3, Flask, pytest, Google Cloud Storage, Vertex AI through Google ADC, server-rendered Jinja, build-free browser JavaScript, Cloud Run.

## Global Constraints

- Use **field notes**, never “shift notes,” in user-facing copy.
- `REVIEW_LAB_ENABLED` defaults to `false`; disabled page and API routes return 404.
- Both `/review-lab` and `/api/review-lab/*` require the existing admin tier and remain undiscoverable to regular users.
- The review lab accepts only the three fictional scenarios from `templates/demo_notes.json`; it does not accept arbitrary incident notes.
- Keep OC supplemental values outside the canonical `notes` string and record both the initial gap and supplied answer.
- Use `FAST_MODEL` for classification/extraction and `PRO_MODEL` for report generation; never introduce an API-key path.
- Store reviews in private GCS as create-only JSON objects; never send review payloads to GitHub issues or ordinary logs.
- The ordinary `/reports` workflow and DOCX download behavior must remain operational.
- No new JavaScript package manager, framework, database, queue, or Word review packet.
- Implement test-first, run focused tests after every change, and commit each independently testable task.

---

## File map

- Create `backend/reports/demo_scenarios.py`: canonical demo lookup and immutable copies.
- Create `backend/reports/gap_answers.py`: pure gap-answer merge used by web and CLI.
- Create `backend/reports/review_schema.py`: payload validation, stable IDs, prompt fingerprints, and server-owned metadata.
- Create `backend/reports/review_store.py`: immutable GCS write, bounded list/get/export.
- Create `backend/webapp/routes/review_lab.py`: feature-gated page and JSON APIs.
- Create `backend/webapp/static/js/review-lab.js`: review-only browser state, edit capture, submit, and history.
- Modify `backend/pipeline/config.py`: review feature and storage settings.
- Modify `backend/webapp/app.py`: blueprint registration, admin route concealment, safe redirects, and template globals.
- Modify `backend/webapp/routes/reports.py`: use shared demo/answer helpers and render ordinary mode explicitly.
- Modify `backend/webapp/templates/reports.html`: guarded review mode, event hooks, editable report tabs, and review controls.
- Modify `backend/webapp/templates/home.html`, `chat.html`, and `roster.html`: guarded Review Lab navigation link.
- Modify `templates/demo_notes.json`: separate OC `review_answers` value.
- Modify `tests/test_pipeline.py`: all-demo iteration, output root, gap resolution, and manifest.
- Create `tests/unit/test_demo_scenarios.py`, `test_pipeline_cli.py`, `test_review_schema.py`, `test_review_store.py`, and `test_review_lab_routes.py`.
- Modify `tests/unit/test_demo_notes.py` and `test_admin_tier.py`: demo-answer and admin-link regressions.

---

### Task 1: Canonical demo catalog and deterministic gap answers

**Files:**
- Create: `backend/reports/demo_scenarios.py`
- Create: `backend/reports/gap_answers.py`
- Modify: `backend/webapp/routes/reports.py`
- Modify: `templates/demo_notes.json`
- Create: `tests/unit/test_demo_scenarios.py`
- Modify: `tests/unit/test_demo_notes.py`

**Interfaces:**
- Produces: `load_demo_scenarios() -> tuple[dict, ...]`, `get_demo_scenario(scenario_id: str) -> dict | None`, and `merge_gap_answers(slots: dict, answers: dict) -> dict`.
- Consumed by: report routes, review schema/routes, and CLI harness.

- [ ] **Step 1: Write failing demo-catalog and gap-answer tests**

```python
def test_demo_lookup_returns_a_copy():
    first = get_demo_scenario("use_of_force_oc")
    first["notes"] = "changed"
    assert get_demo_scenario("use_of_force_oc")["notes"] != "changed"

def test_oc_review_answer_is_separate_and_closes_chemical_gap():
    scenario = get_demo_scenario("use_of_force_oc")
    assert all(word not in scenario["notes"].lower()
               for word in ("lot", "mfg", "serial", "pmf"))
    slots = {"force_type": "chemical", "chemical_agent": None}
    merged = merge_gap_answers(slots, scenario["review_answers"])
    assert merged["chemical_agent"] == scenario["review_answers"]["chemical_agent"]
    assert not any(g["slot"] == "chemical_agent" and g["blocking"]
                   for g in find_gaps("use_of_force", merged)["gaps"])
```

- [ ] **Step 2: Run the focused tests and confirm missing-module/data failures**

Run: `python -m pytest tests/unit/test_demo_scenarios.py tests/unit/test_demo_notes.py -v`

Expected: FAIL because the two modules and `review_answers` do not exist.

- [ ] **Step 3: Add the shared demo and answer helpers**

```python
# backend/reports/demo_scenarios.py
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

DEMO_NOTES_PATH = Path(__file__).parents[2] / "templates" / "demo_notes.json"

@lru_cache(maxsize=1)
def _cached_scenarios() -> tuple[dict, ...]:
    payload = json.loads(DEMO_NOTES_PATH.read_text(encoding="utf-8"))
    return tuple(payload.get("scenarios", []))

def load_demo_scenarios() -> tuple[dict, ...]:
    return tuple(deepcopy(item) for item in _cached_scenarios())

def get_demo_scenario(scenario_id: str) -> dict | None:
    match = next((item for item in _cached_scenarios()
                  if item.get("id") == scenario_id), None)
    return deepcopy(match) if match else None
```

```python
# backend/reports/gap_answers.py
from copy import deepcopy

def merge_gap_answers(slots: dict, answers: dict) -> dict:
    merged = deepcopy(slots or {})
    for key, value in (answers or {}).items():
        if isinstance(key, str) and value not in (None, ""):
            merged[key] = value
    return merged
```

Add this separate fictional field to `use_of_force_oc` without changing its notes:

```json
"review_answers": {
  "chemical_agent": "OC spray; MFG 2025; lot DEMO-OC-042; PMF/serial DEMO-409-017"
}
```

Replace the private demo loader in `routes/reports.py` with the shared loader, and use `merge_gap_answers()` before the existing first-name and roster-specific handling in `_prepare_generation()`.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/unit/test_demo_scenarios.py tests/unit/test_demo_notes.py tests/unit/test_report_helpers.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the shared demo behavior**

```bash
git add backend/reports/demo_scenarios.py backend/reports/gap_answers.py backend/webapp/routes/reports.py templates/demo_notes.json tests/unit/test_demo_scenarios.py tests/unit/test_demo_notes.py
git commit -m "feat: centralize demo scenarios and review answers"
```

---

### Task 2: CLI batch execution, output roots, OC resolution, and manifests

**Files:**
- Modify: `tests/test_pipeline.py`
- Create: `tests/unit/test_pipeline_cli.py`

**Interfaces:**
- Consumes: `load_demo_scenarios()`, `merge_gap_answers()`, and `find_gaps()`.
- Produces: `build_parser()`, `run_pipeline(..., output_root: Path, scenario: dict | None) -> int`, `run_demo_batch(...) -> int`, and `build_manifest(...) -> dict`.

- [ ] **Step 1: Write failing credential-free CLI helper tests**

```python
def test_output_dir_controls_run_and_snapshot_paths(tmp_path):
    paths = pipeline.output_paths(tmp_path, "case_one")
    assert paths.run_dir == tmp_path / "case_one"
    assert paths.snapshot_dir == tmp_path / "case_one_snapshot"

def test_demo_all_runs_declared_order(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(pipeline, "run_pipeline",
                        lambda **kw: seen.append(kw["scenario"]["id"]) or 0)
    assert pipeline.run_demo_batch(output_root=tmp_path) == 0
    assert seen == ["inmate_fight_dayroom", "contraband_shakedown", "use_of_force_oc"]

def test_manifest_contains_models_gaps_and_artifacts(tmp_path):
    manifest = pipeline.build_manifest(
        run_id="run-1", name="use_of_force_oc", output_root=tmp_path,
        timing={"classify": 1.2}, errors=[], initial_blocking=1,
        final_blocking=0, artifacts=["01_classify.json"])
    assert manifest["schema_version"] == 1
    assert manifest["models"]["generation"] == PRO_MODEL
    assert manifest["gaps"] == {"initial_blocking": 1, "final_blocking": 0}
```

- [ ] **Step 2: Run the tests and confirm helper failures**

Run: `python -m pytest tests/unit/test_pipeline_cli.py -v`

Expected: FAIL because the helper interfaces do not exist.

- [ ] **Step 3: Refactor paths and parser without calling Vertex**

Add a frozen `OutputPaths` dataclass and make `--output-dir` a `Path`:

```python
@dataclass(frozen=True)
class OutputPaths:
    run_dir: Path
    snapshot_dir: Path

def output_paths(output_root: Path, name: str) -> OutputPaths:
    return OutputPaths(output_root / name, output_root / f"{name}_snapshot")
```

Pass `output_root` into `run_pipeline()` and use it for the run directory and snapshot directory. Add `--demo all` handling before single-demo lookup.

- [ ] **Step 4: Preserve initial gaps, apply review answers, and emit a manifest**

For demo scenarios, save `03_gaps_initial.json`, apply `review_answers` through `merge_gap_answers()`, save `03_gap_answers.json` when non-empty, recompute and save `03_gaps_final.json`, and refuse generation if `blocking_remaining` remains nonzero. Save `manifest.json` in a `finally` path so failed runs retain timings and errors.

The manifest must use this stable shape:

```python
{
    "schema_version": 1,
    "run_id": run_id,
    "name": name,
    "started_at": started_at,
    "finished_at": finished_at,
    "models": {"classification": FAST_MODEL, "extraction": FAST_MODEL,
               "generation": PRO_MODEL, "location": MODEL_LOCATION},
    "timing_seconds": timing,
    "gaps": {"initial_blocking": initial_blocking,
             "final_blocking": final_blocking},
    "errors": [{"step": step, "message": message} for step, message in errors],
    "artifacts": sorted(artifacts),
}
```

- [ ] **Step 5: Run CLI unit tests and argument smoke checks**

Run: `python -m pytest tests/unit/test_pipeline_cli.py -v`

Run: `python tests/test_pipeline.py --demo list`

Expected: PASS; list prints the three demos without ADC.

- [ ] **Step 6: Commit the CLI improvements**

```bash
git add tests/test_pipeline.py tests/unit/test_pipeline_cli.py
git commit -m "feat: batch demos and preserve pipeline manifests"
```

---

### Task 3: Versioned review submission schema

**Files:**
- Create: `backend/reports/review_schema.py`
- Create: `tests/unit/test_review_schema.py`

**Interfaces:**
- Consumes: `get_demo_scenario()` and model constants from `backend.pipeline.config`.
- Produces: `ReviewValidationError`, `build_review_submission(payload: dict, *, now: datetime | None = None, id_factory: Callable[[], str] | None = None) -> dict`, and `review_summary(record: dict) -> dict`.

- [ ] **Step 1: Write failing schema tests**

```python
def test_server_owns_scenario_notes_ids_and_model_metadata():
    record = build_review_submission(valid_payload(
        scenario_id="inmate_fight_dayroom", notes="attacker supplied"),
        now=FIXED_NOW, id_factory=lambda: "abc123")
    assert record["submission_id"] == "review_20260810T231500Z_abc123"
    assert record["scenario"]["notes"] != "attacker supplied"
    assert record["metadata"]["classification_model"] == FAST_MODEL

def test_report_ids_are_stable_and_both_versions_are_retained():
    record = build_review_submission(valid_payload())
    report = record["reports"][0]
    assert report["report_id"].startswith("inmate_fight_dayroom:first_person:")
    assert report["generated_text"] == "generated"
    assert report["edited_text"] == "edited"
    assert report["changed"] is True

@pytest.mark.parametrize("score", [0, 6, "five"])
def test_score_must_be_an_integer_from_one_to_five(score):
    with pytest.raises(ReviewValidationError):
        build_review_submission(valid_payload(score=score))
```

- [ ] **Step 2: Run and verify missing-module failure**

Run: `python -m pytest tests/unit/test_review_schema.py -v`

Expected: FAIL because `review_schema.py` does not exist.

- [ ] **Step 3: Implement strict normalization and server metadata**

Allow only `first_person`, `supervisor_summary`, `cover_letter`, `disciplinary`, and `investigation`. Bound comments to 5,000 characters, each report version to 30,000 characters, reviewed fields to 100 keys/5,000 characters per value, and reports to 25 entries. Require at least one report and score 1–5.

Create prompt fingerprints over these files using SHA-256:

```python
PROMPT_SOURCES = {
    "classification": ROOT / "backend/reports/prompts.py",
    "generation": ROOT / "backend/reports/prompts_v2.py",
    "checklist": ROOT / "templates/incident_checklist_v2.json",
    "charges": ROOT / "templates/disciplinary_charges.json",
}
```

Use `K_REVISION` and `SOURCE_COMMIT` only from `os.environ`; ignore metadata values sent by the browser. Normalize reporter IDs to lowercase alphanumerics, underscore, and hyphen before constructing `scenario_id:report_type:reporter_id-or-primary`.

- [ ] **Step 4: Run schema tests**

Run: `python -m pytest tests/unit/test_review_schema.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the schema**

```bash
git add backend/reports/review_schema.py tests/unit/test_review_schema.py
git commit -m "feat: validate versioned review submissions"
```

---

### Task 4: Immutable private GCS review store

**Files:**
- Create: `backend/reports/review_store.py`
- Create: `tests/unit/test_review_store.py`

**Interfaces:**
- Consumes: normalized records from `build_review_submission()`.
- Produces: `ReviewStore(bucket_name: str, prefix: str, client_factory=None)`, `save(record: dict) -> str`, `get(submission_id: str) -> dict | None`, `list_records(limit: int = 50) -> list[dict]`, and `export_jsonl(limit: int = 1000) -> tuple[bytes, int]`.

- [ ] **Step 1: Write fake-GCS tests**

```python
def test_save_is_create_only(fake_client, record):
    store = ReviewStore("private-bucket", "review-lab/submissions",
                        client_factory=lambda: fake_client)
    object_name = store.save(record)
    blob = fake_client.bucket_obj.blobs[object_name]
    assert blob.if_generation_match == 0
    assert blob.content_type == "application/json"

def test_get_rejects_untrusted_ids(fake_client):
    store = ReviewStore("b", "p", client_factory=lambda: fake_client)
    with pytest.raises(ValueError):
        store.get("../../roster.json")

def test_export_is_newest_first_and_bounded(fake_client):
    store = seeded_store(fake_client, count=3)
    payload, skipped = store.export_jsonl(limit=2)
    rows = [json.loads(line) for line in payload.decode().splitlines()]
    assert [r["submission_id"] for r in rows] == ["review_3", "review_2"]
    assert skipped == 0
```

- [ ] **Step 2: Run and verify missing-store failures**

Run: `python -m pytest tests/unit/test_review_store.py -v`

Expected: FAIL because `ReviewStore` does not exist.

- [ ] **Step 3: Implement the store with lazy Google imports**

Construct the object name from `submitted_at[:7].replace("-", "/")` and the validated submission ID. Serialize with `json.dumps(record, indent=2, sort_keys=True) + "\n"`. Call `upload_from_string(..., content_type="application/json", if_generation_match=0)`.

Validate IDs with:

```python
SUBMISSION_ID_RE = re.compile(r"^review_[0-9]{8}T[0-9]{6}Z_[a-zA-Z0-9_-]{6,64}$")
```

List only under `prefix + "/"`, parse JSON defensively, sort by `submitted_at` descending, and stop at the bounded limit. Do not log object bodies.

- [ ] **Step 4: Run store tests**

Run: `python -m pytest tests/unit/test_review_store.py -v`

Expected: PASS without GCP credentials.

- [ ] **Step 5: Commit the store**

```bash
git add backend/reports/review_store.py tests/unit/test_review_store.py
git commit -m "feat: persist immutable review records in gcs"
```

---

### Task 5: Feature configuration, concealed admin routes, and review APIs

**Files:**
- Modify: `backend/pipeline/config.py`
- Modify: `backend/webapp/app.py`
- Create: `backend/webapp/routes/review_lab.py`
- Create: `tests/unit/test_review_lab_routes.py`
- Modify: `tests/unit/test_admin_tier.py`
- Modify: `tests/unit/test_safe_next.py`

**Interfaces:**
- Consumes: `build_review_submission()`, `review_summary()`, `ReviewStore`, and `load_demo_scenarios()`.
- Produces: `review_lab_bp` and feature-gated page/list/get/export/submit endpoints.

- [ ] **Step 1: Write failing feature/auth/API tests**

```python
@pytest.mark.parametrize("path", ["/review-lab", "/api/review-lab/submissions"])
def test_regular_users_get_concealed_404(tiered_review_app, path):
    client = logged_in(tiered_review_app, REGULAR)
    response = client.get(path) if path == "/review-lab" else client.post(path, json={})
    assert response.status_code == 404

def test_disabled_lab_returns_404_to_admin(monkeypatch):
    app = configured_app(monkeypatch, enabled=False)
    assert logged_in(app, ADMIN).get("/review-lab").status_code == 404

def test_admin_submission_is_saved(monkeypatch, fake_store, valid_payload):
    app = configured_app(monkeypatch, enabled=True, store=fake_store)
    response = logged_in(app, ADMIN).post(
        "/api/review-lab/submissions", json=valid_payload)
    assert response.status_code == 201
    assert response.get_json()["submission_id"].startswith("review_")
    assert len(fake_store.saved) == 1
```

- [ ] **Step 2: Run focused routes/auth tests and confirm failures**

Run: `python -m pytest tests/unit/test_review_lab_routes.py tests/unit/test_admin_tier.py tests/unit/test_safe_next.py -v`

Expected: FAIL because the settings, blueprint, and routes do not exist.

- [ ] **Step 3: Add review settings and app registration**

```python
def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

REVIEW_LAB_ENABLED = _env_bool("REVIEW_LAB_ENABLED")
REVIEW_BUCKET = os.getenv("REVIEW_BUCKET", ROSTER_BUCKET or "")
REVIEW_OBJECT_PREFIX = os.getenv("REVIEW_OBJECT_PREFIX", "review-lab/submissions").strip("/")
```

Register `review_lab_bp`; add `/review-lab` to `ADMIN_ONLY_EXACT`, `/api/review-lab` to `ADMIN_ONLY_PREFIXES`, and `/review-lab` to the safe-next allowlist. Permit only `/review-lab?demo=<known-id>` through the same canonical demo allowlist pattern used by `/reports`.

- [ ] **Step 4: Implement the blueprint APIs**

Every route begins with a shared `require_lab_enabled()` check that returns the existing 404 template for pages and `{"error": "Not found."}` for APIs. `POST` validates then saves and returns `201`. Storage-unavailable errors return `503` without clearing client state. `GET /export` returns `application/x-ndjson` with `Content-Disposition: attachment; filename=review-lab-submissions.jsonl` and `X-Review-Records-Skipped`.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/unit/test_review_lab_routes.py tests/unit/test_admin_tier.py tests/unit/test_safe_next.py tests/unit/test_access_code_config.py -v`

Expected: PASS.

- [ ] **Step 6: Commit backend routes and configuration**

```bash
git add backend/pipeline/config.py backend/webapp/app.py backend/webapp/routes/review_lab.py tests/unit/test_review_lab_routes.py tests/unit/test_admin_tier.py tests/unit/test_safe_next.py
git commit -m "feat: add feature-gated admin review api"
```

---

### Task 6: Review-mode UI, complete edit capture, and submission history

**Files:**
- Modify: `backend/webapp/routes/reports.py`
- Modify: `backend/webapp/templates/reports.html`
- Modify: `backend/webapp/templates/home.html`
- Modify: `backend/webapp/templates/chat.html`
- Modify: `backend/webapp/templates/roster.html`
- Create: `backend/webapp/static/js/review-lab.js`
- Modify: `tests/unit/test_review_lab_routes.py`
- Modify: `tests/unit/test_assets.py`

**Interfaces:**
- Consumes: review blueprint template context, the three report API responses, and submission/history APIs.
- Produces: `window.ReviewLab`, report lifecycle events, and a complete browser submission payload.

- [ ] **Step 1: Write failing rendered-HTML and asset tests**

```python
def test_review_page_has_controls_and_readonly_demo_notes(admin_review_client):
    body = admin_review_client.get(
        "/review-lab?demo=inmate_fight_dayroom").get_data(as_text=True)
    assert 'id="reviewSubmit"' in body
    assert 'id="reviewScore"' in body
    assert 'id="notes"' in body and "readonly" in body
    assert "js/review-lab.js" in body

def test_ordinary_reports_has_no_review_controls(regular_client):
    body = regular_client.get("/reports").get_data(as_text=True)
    assert 'id="reviewSubmit"' not in body
    assert "js/review-lab.js" not in body
```

- [ ] **Step 2: Run the UI-facing tests and confirm failures**

Run: `python -m pytest tests/unit/test_review_lab_routes.py tests/unit/test_assets.py -v`

Expected: FAIL because review mode and its asset are absent.

- [ ] **Step 3: Add guarded template mode and lifecycle events**

Render `/reports` with `review_mode=False`; render `/review-lab` with `review_mode=True`. In `reports.html`, define `PAGE_PATH` from the mode, make field notes read-only only in review mode, and guard scenario cards, score/comments, submit status, and saved-review markup with `{% if review_mode %}`.

Dispatch cloned payloads after each successful stage:

```javascript
function emitReportEvent(name, detail) {
  window.dispatchEvent(new CustomEvent(name, {detail: structuredClone(detail)}));
}
// report:classified, report:extracted, report:generated,
// report:before-form-switch, report:after-form-render
```

Emit `report:before-form-switch` before `_activeForm` changes and `report:after-form-render` after the new preview DOM exists. Preserve the ordinary page when no listener is registered.

- [ ] **Step 4: Implement review-only browser state and editing**

`review-lab.js` keeps this state:

```javascript
const state = {
  scenarioId: new URLSearchParams(location.search).get('demo'),
  classification: null,
  extraction: null,
  initialGaps: null,
  gapAnswers: {},
  generationResponse: null,
  reports: new Map(),
  reviewedFields: {}
};
```

On generation, add each original report once under `scenario:type:reporter-or-primary`. On `report:after-form-render`, mark the active narrative `contenteditable=true` and attach `data-review-report-type`. On `report:before-form-switch` and before submit, copy `innerText` into `edited_text`; for the 005 form also capture `collectMetadata()`.

On the first `report:extracted` event, retain an immutable copy as
`initialGaps`. If the selected scenario has `review_answers`, add an **Apply
demo-only canister details** button beside the blocking gap. Its click handler
finds each matching `[data-slot]` input, assigns the canonical fictional value,
dispatches an `input` event so existing progress logic runs, and copies the
same values into `state.gapAnswers`. It must not modify the field-notes
textarea or call generation directly; the existing Continue action revalidates
the answered slots.

Submit this exact client shape:

```javascript
{
  scenario_id: state.scenarioId,
  pipeline: {
    classification: state.classification,
    extraction: state.extraction,
    initial_gaps: state.initialGaps,
    gap_answers: collectAnswers(),
    generation_response: state.generationResponse
  },
  reports: [...state.reports.values()],
  reviewed_fields: state.reviewedFields,
  review: {score: Number(score.value), comments: comments.value.trim()}
}
```

Keep edits and re-enable submit after any failure. After success, display the returned submission ID and refresh the bounded history list. History download links point only to the admin API.

- [ ] **Step 5: Add admin-only navigation consistently**

Add a Review Lab link in home, reports, chat, and roster navigation only when both `is_admin` and `review_lab_enabled` are true. Preserve existing brand markup and navy/gold styling.

- [ ] **Step 6: Run UI/backend regression tests**

Run: `python -m pytest tests/unit/test_review_lab_routes.py tests/unit/test_admin_tier.py tests/unit/test_assets.py tests/unit/test_demo_notes.py -v`

Expected: PASS.

- [ ] **Step 7: Commit the review UI**

```bash
git add backend/webapp/routes/reports.py backend/webapp/templates/reports.html backend/webapp/templates/home.html backend/webapp/templates/chat.html backend/webapp/templates/roster.html backend/webapp/static/js/review-lab.js tests/unit/test_review_lab_routes.py tests/unit/test_assets.py
git commit -m "feat: add editable admin demo review lab"
```

---

### Task 7: Full verification, live smoke test, deployment, and feature enablement

**Files:**
- Modify only if verification finds a scoped defect in files already listed above.

**Interfaces:**
- Consumes: all completed tasks.
- Produces: verified commits, a deployed Cloud Run revision, and an enabled admin lab.

- [ ] **Step 1: Run the complete credential-free suite**

Run: `python -m pytest`

Expected: all collected unit tests PASS with no new warnings attributable to the feature.

- [ ] **Step 2: Run formatting and repository integrity checks**

Run: `git diff --check origin/main...HEAD`

Run: `git status --short`

Expected: no whitespace errors; only intentional commits and no untracked implementation files.

- [ ] **Step 3: Start a local feature-enabled Flask smoke instance**

PowerShell:

```powershell
$env:ACCESS_CODE='local-user'
$env:ADMIN_CODE='local-admin'
$env:REVIEW_LAB_ENABLED='true'
$env:PYTHONPATH='.'
python backend/webapp/app.py
```

Verify `/health` returns 200, regular users get 404 on `/review-lab`, administrators see the three scenarios, `/reports` has no review controls, and a mocked or deliberately unavailable store returns a visible 503 without clearing edits.

- [ ] **Step 4: Run the live ADC demo batch into an isolated output directory**

Run: `python tests/test_pipeline.py --demo all --output-dir tests/output/review-lab-smoke`

Expected: three scenario directories; each contains input, classification, extraction, initial/final gaps, reports, summary, and manifest. The OC directory additionally contains gap answers and reports zero final blocking gaps.

- [ ] **Step 5: Inspect the final diff and commit any verification-only fix**

Run: `git diff origin/main...HEAD --stat`

If a scoped fix was necessary, stage only its files and commit with `fix: correct review lab verification issue`; otherwise create no empty commit.

- [ ] **Step 6: Push the tested commits to `main` and monitor deployment**

Run: `git push origin main`

Run: `gh run list --workflow cloud-run.yml --limit 1`

Run: `gh run watch <run-id> --exit-status`

Expected: Cloud Run workflow succeeds.

- [ ] **Step 7: Enable the feature without exposing secret values**

Run:

```bash
gcloud run services update prison-policy-ai --project gen-lang-client-0968389176 --region us-central1 --update-env-vars REVIEW_LAB_ENABLED=true
```

Expected: a new ready revision. Do not modify `ACCESS_CODE`, `ADMIN_CODE`, `GITHUB_TOKEN`, or `ROSTER_BUCKET`.

- [ ] **Step 8: Verify production access, one saved review, and retrieval**

Log in with the existing admin code, run one demo, edit at least one report sentence, submit it, confirm the returned ID appears in Saved Reviews, download its JSON, and verify the GCS object is under `review-lab/submissions/YYYY/MM/`. Confirm a regular access-code session receives 404.

- [ ] **Step 9: Record final evidence**

Report the deployed revision, test totals, live CLI run result, review submission ID, storage object path, and immediate shutdown command:

```bash
gcloud run services update prison-policy-ai --project gen-lang-client-0968389176 --region us-central1 --update-env-vars REVIEW_LAB_ENABLED=false
```
