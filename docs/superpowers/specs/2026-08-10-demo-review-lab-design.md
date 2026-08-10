# Demo Review Lab Design

**Date:** 2026-08-10  
**Status:** Approved for implementation planning  
**Owner:** Prison Policy AI administrator

## Purpose

Add a temporary, admin-only page to the deployed Flask application where the
administrator can run the three fictional report demos, edit every generated
report into the desired final version, add review notes and a score, and save a
structured record for later analysis and prompt/report-engine refinement.

The review lab is an evaluation tool. It does not file reports, train a model,
modify prompts automatically, or accept real incident notes.

## Existing capabilities to reuse

The application already provides the necessary foundation:

- `ADMIN_CODE` grants an administrator tier through the existing secure login
  cookie. Admin-only routes return 404 to regular users.
- `templates/demo_notes.json` contains three fictional scenarios:
  `inmate_fight_dayroom`, `contraband_shakedown`, and `use_of_force_oc`.
- `/api/reports/classify`, `/api/reports/extract`, and
  `/api/reports/generate` run the production Vertex AI pipeline.
- `backend/webapp/templates/reports.html` already loads demos, displays gaps,
  generates all applicable reports, and makes the rendered report fields
  editable.
- Cloud Run already receives `ROSTER_BUCKET`, and its service account has
  `roles/storage.objectAdmin` on that private GCS bucket.
- The model configuration is centralized: classification and extraction use
  `FAST_MODEL` (currently `gemini-3.6-flash`); report generation uses
  `PRO_MODEL` (currently `gemini-3.1-pro-preview`); both use Vertex AI ADC.

The public GitHub repository and ordinary Cloud Run logs are not acceptable as
the durable review store. GitHub issues would expose submissions publicly, and
logs do not provide a stable, structured retrieval interface.

## User experience

### Entry and access

When `REVIEW_LAB_ENABLED=true`, an administrator sees a **Review Lab** link in
the navigation and may open `/review-lab`. A regular access-code user receives
the same concealed 404 behavior used by the roster. When the feature flag is
false or unset, the page and every review-lab API endpoint return 404 even to an
administrator, and the navigation link is absent.

The page clearly says that it uses fictional demo information and stores the
administrator's edits for product improvement. The field-notes area is
read-only in review mode so the canonical demo input cannot be accidentally
changed.

### Running a scenario

The page shows one card for each demo, with its label and teaching purpose. The
administrator selects a scenario and presses **Run demo**. The page then uses
the existing production APIs in their normal order:

1. Classify the canonical field notes and show the incident type and suggested
   charges.
2. Extract structured facts and show detected gaps.
3. Resolve any blocking gap.
4. Generate every applicable report and display the existing editable preview.

Only one scenario runs at a time. A batch job and background queue are not
needed for this review workflow; keeping each scenario explicit makes it easier
to review the intermediate state and avoids adding a new long-running execution
system.

### OC blocking-gap behavior

The `use_of_force_oc` notes continue to omit the OC canister manufacture year,
lot number, and PMF/serial number. The initial extraction must therefore show
the intentional blocking gap.

Review-only supplemental answers will be stored separately from the `notes`
field in `templates/demo_notes.json`. The page provides an **Apply demo-only
canister details** action that fills the missing-information controls. It does
not append those values to the original notes or bypass validation. The saved
submission records both the initially detected gap and the supplemental values
used to continue. Existing tests that prevent adding these numbers to the notes
remain valid.

### Editing and submission

After generation, the administrator can edit the reports using the existing
content-editable preview. Review mode adds:

- An overall quality score from 1 through 5.
- Optional reviewer comments.
- A **Submit review** button.
- A confirmation containing the immutable submission ID.

The page retains both the original generated text and the final edited text for
every report. Switching report tabs must first copy the active editable DOM
values back into review state so edits to more than one report cannot be lost.
The submitted record also includes reviewed form/header fields because those
fields are editable in the current preview.

After a successful submission, the page may start another demo. Duplicate
submissions are permitted because repeated model runs are useful evidence; each
receives a distinct ID.

### Reviewing saved submissions

The same page includes a compact **Saved reviews** section visible only to the
administrator. It lists recent submissions by time, scenario, score, and ID.
The administrator can download one submission as JSON or download the current
result set as JSON Lines (`.jsonl`) for later analysis. There is no deletion UI
in the first version, avoiding accidental loss of evaluation data.

## Architecture

### Routes and feature isolation

Add a `review_lab` Flask blueprint with these endpoints:

- `GET /review-lab` — render the report template in `review_mode`.
- `POST /api/review-lab/submissions` — validate and store one review.
- `GET /api/review-lab/submissions` — list recent review summaries.
- `GET /api/review-lab/submissions/<submission_id>` — download one record.
- `GET /api/review-lab/export` — download reviews as JSON Lines.

`/review-lab` is added to `ADMIN_ONLY_EXACT`; `/api/review-lab` is added to
`ADMIN_ONLY_PREFIXES`. The feature flag is checked independently in the
blueprint so an administrator cannot reach a disabled lab by typing the URL.

The existing `reports.html` is rendered with `review_mode=True` rather than
copying the 1,500-line report UI. Review-only markup and JavaScript are guarded
by that server-provided boolean. The ordinary `/reports` route renders with
`review_mode=False` and preserves its current behavior.

Review persistence lives in a small, independent
`backend/reports/review_store.py` module. It must not modify or depend on the
roster document itself; it only shares the configured bucket.

### Configuration

Add these environment-driven settings:

- `REVIEW_LAB_ENABLED`, default `false`.
- `REVIEW_BUCKET`, default to `ROSTER_BUCKET`.
- `REVIEW_OBJECT_PREFIX`, default `review-lab/submissions`.

The default deployment therefore needs only the feature flag to enable the
lab. If no review bucket is available, the lab may still render and run demos,
but submission returns a clear 503 without pretending the record was saved.

### GCS object layout

Each submission is one immutable JSON object:

```text
gs://<review-bucket>/review-lab/submissions/YYYY/MM/<submission-id>.json
```

Writes use `if_generation_match=0`, so an ID collision cannot overwrite an
existing review. Objects use `application/json`, UTF-8, and deterministic
pretty-printed JSON. Listing is prefix-scoped and bounded. The export endpoint
streams or assembles only the bounded set requested by the administrator; its
first version may cap exports at 1,000 records.

## Submission schema

The top-level JSON shape is versioned so future analyzers can distinguish
schema changes:

```json
{
  "schema_version": 1,
  "submission_id": "review_20260810T231500Z_<uuid>",
  "submitted_at": "2026-08-10T23:15:00Z",
  "scenario": {
    "scenario_id": "use_of_force_oc",
    "category": "use_of_force",
    "label": "Use of force (chemical agent)",
    "notes": "<canonical fictional field notes>"
  },
  "pipeline": {
    "classification": {},
    "extraction": {},
    "initial_gaps": {},
    "gap_answers": {},
    "generation_response": {}
  },
  "reports": [
    {
      "report_id": "use_of_force_oc:first_person:<reporter-id>",
      "report_type": "first_person",
      "reporter_id": "<stable roster identifier or null>",
      "generated_text": "<model output before review>",
      "edited_text": "<administrator's final version>",
      "changed": true
    }
  ],
  "reviewed_fields": {},
  "review": {
    "score": 4,
    "comments": "<optional comments>"
  },
  "metadata": {
    "vertex_project": "gen-lang-client-0968389176",
    "model_location": "global",
    "classification_model": "gemini-3.6-flash",
    "extraction_model": "gemini-3.6-flash",
    "generation_model": "gemini-3.1-pro-preview",
    "cloud_run_revision": "<K_REVISION or null>",
    "source_commit": "<deployed commit when available>",
    "prompt_fingerprints": {},
    "step_timings_ms": {}
  }
}
```

The server, not the browser, supplies the canonical scenario fields,
submission ID, timestamp, configured model names, deployment revision, and
prompt fingerprints. The browser supplies the intermediate responses it
actually displayed, original generated values captured before editing, final
edited values, gap answers, comments, and score.

Prompt fingerprints are SHA-256 hashes of the relevant prompt/checklist source
content. The submission does not duplicate entire prompts, which keeps records
compact while still allowing runs made under different prompt versions to be
grouped accurately.

## Validation and security

- Every page and API request requires the existing admin tier; no additional
  password or browser-side secret is introduced.
- The browser never receives or stores `ADMIN_CODE` beyond the existing
  HttpOnly authentication cookie behavior.
- Only scenario IDs present in `demo_notes.json` are accepted. The server
  reloads the canonical notes and label instead of trusting copies submitted by
  the browser.
- Report types, score range, object depth, string lengths, and total payload
  size are bounded. Unknown top-level fields are ignored or rejected
  consistently.
- The global Flask 1 MB request limit remains in force. Review-specific limits
  are lower where practical.
- GCS object names are constructed only from a server-generated ID and fixed
  prefix; user content never becomes a bucket path.
- Review data is not written to application logs or GitHub issues.
- Demo notes remain fictional. The lab does not expose an input for arbitrary
  incident notes.
- API errors return generic user-facing messages while server logs retain stack
  traces without logging the complete review payload.

## Error handling

- A classify, extract, or generate failure uses the existing report-page error
  behavior and leaves previously completed stage data available for retry.
- Blocking gaps prevent generation until answered through the existing rules.
- A failed submission does not clear edits. The button re-enables and the page
  explains whether authentication expired, validation failed, or storage was
  unavailable.
- GCS collision/precondition failures never overwrite data. A genuinely
  colliding ID is regenerated once; repeated failure surfaces as 503.
- Listing skips malformed objects with a server warning rather than breaking
  the entire history page.
- Export returns only successfully parsed records and reports the skipped count
  in a response header.

## Testing

### Unit tests

- Feature-flag parsing and fail-closed behavior.
- Admin-only page and API access, including regular-user 404 responses.
- Disabled routes return 404 to administrators.
- Submission schema validation, canonical scenario replacement, score bounds,
  length limits, stable report IDs, and server-owned metadata.
- GCS object-name construction and create-only write precondition.
- Local/fake storage behavior used by tests without requiring ADC or GCP.
- Listing and JSONL export ordering, bounds, and malformed-object handling.
- Demo supplemental answers remain outside the canonical notes and satisfy the
  expected OC blocking gaps when applied.

### Browser-facing behavior tests

- Review mode is rendered only from `/review-lab`.
- Ordinary `/reports` markup and behavior do not show review controls.
- Scenario selection loads canonical notes.
- Edits survive report-tab changes and submission includes every report's
  generated and edited text.
- Failed submission preserves the form.

### Regression verification

- Run the existing unit suite.
- Run focused review-lab tests without ADC.
- Locally exercise the page with mocked report responses.
- When ADC is available, run each live demo through classify, extract, and
  generate, verify the OC gap sequence, submit one review, retrieve it from the
  history endpoint, and compare the stored generated/edited values.
- Verify `/health`, `/reports`, regular login, admin login, roster access, and
  ordinary report download remain unchanged.

## Deployment and removal

Implementation ships with `REVIEW_LAB_ENABLED=false`. After tests pass, deploy
normally through the existing Cloud Run GitHub workflow, then set
`REVIEW_LAB_ENABLED=true` on the service. No new IAM grant is expected because
the current Cloud Run service account already has object-admin access to the
configured bucket.

Immediate shutdown requires only setting `REVIEW_LAB_ENABLED=false`. That hides
the navigation entry and returns 404 from all lab routes while leaving saved
reviews intact. Permanent removal later consists of deleting the review
blueprint/store, the guarded review-mode template blocks, tests, and the feature
configuration. The production report pipeline and stored review objects remain
independent.

## Acceptance criteria

1. Only an authenticated administrator can discover or use the lab.
2. A disabled lab is unreachable even with the admin code.
3. Each of the three canonical demos can run through the real production report
   pipeline from the lab.
4. The OC demo first exposes its intentional blocking gap and can then continue
   with separately recorded demo-only answers.
5. Every applicable generated report is editable, and edits across all report
   tabs are preserved.
6. Submission creates one immutable private JSON object containing canonical
   input, intermediate results, original reports, edited reports, reviewer
   feedback, stable identifiers, and server-owned model/deployment metadata.
7. The administrator can list and download saved reviews from the lab.
8. The ordinary report generator behaves exactly as it did before the feature.
9. The feature can be disabled without redeploying or deleting stored reviews.
10. Automated tests pass without requiring live Vertex AI credentials; a live
    ADC smoke test verifies the complete demo workflow before production use.
