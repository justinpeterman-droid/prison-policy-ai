# Sequence 012 — RP-03: Route-Neutral Engine Adapters, Staff Lookup, and Incident Creation

Copy everything below into a fresh Claude Code session.

---

Implement only RP-03, “Route-neutral engine adapters, staff lookup, and incident creation.” Use TDD, one focused commit, hand off, and stop.

## Objective

Extract route-neutral adapters over the existing report pipeline without changing prompts, retrieval, validation, generation, or legacy response shapes; add SQL staff lookup, record policies, idempotent multi-officer incident creation, incident revision endpoints, and OpenAPI. This lets Access reuse proven engines while Cloud SQL replaces client-trusted roster/ownership decisions.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-03-engine-adapters-incidents`
- Predecessor: reviewed `main` contains `feat: add conflict-safe report revisions`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add conflict-safe report revisions"
git switch -c claude/rp-03-engine-adapters-incidents
```

Require clean tracked/index state; tolerate only untouched existing `.superpowers/`. Read intervening reviewed changes when main advanced; stop for missing/unreviewed/conflicting work. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`, roadmap shared engine signatures/HTTP/idempotency/security rules.
- Report plan exact RP-03 section including legacy helper inventory, routes, tests and API examples.
- Report/master specs.
- Consume-only existing classifier/extraction/validate/generator/report_validator/filler, pipeline query, roster implementation, RP models/schemas/revisions, ID Actor/idempotency/audit/OpenAPI.

## Exact allowed files

- Create: `backend/reports/service.py`
- Create: `backend/reports/persistence.py`
- Create: `backend/reports/policy.py`
- Modify: `backend/reports/roster.py`
- Modify: `backend/webapp/routes/reports.py`
- Create: `backend/webapp/api_v1/staff.py`
- Create: `backend/webapp/api_v1/incidents.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_report_service.py`
- Create: `tests/unit/test_report_policy.py`
- Create: `tests/integration/test_incident_api.py`

Consume-only: engine modules/prompts/templates, persistence/identity services, plans/specs/tests not listed. No engine prompt/logic, migration, reports API, jobs, README, or infra edits.

## Locked interfaces and wire rules

- Produce `StaffProvider`, `SqlStaffProvider`, exact route-neutral `classify_incident_notes`, `extract_incident_notes`, `generate_report_set`, `generate_disciplinary_report`, `create_incident`, `get_incident`, and shared owner/preparer/Admin policies. Preserve roadmap signatures.
- Move orchestration from named legacy route functions into services; legacy routes delegate and retain exact shapes/private helpers used by tests. Do not rewrite engine logic or call Google in tests.
- Access staff resolution uses Cloud SQL and never calls `roster_store.update()`; only active stable staff UUIDs accepted.
- Actor comes only from middleware. Ignore/reject client actor, role, employee number, ownership, model/prompt metadata.
- Incident creation validates `field_notes` through RP-02 `SaveIncidentRequest` using the shared ID-02 maximum of exactly 30,000 decoded Unicode code points, claims/completes ID-06 idempotency in the same transaction, derives preparer from Actor, creates revision 1, adds owner/preparer relationships per reporting officer, and audits safe IDs. A 30,001-code-point request returns `400 validation_failed` and creates no row/revision/idempotent success/audit. Report shells are created only at generation stage as plan specifies; no duplicate owner copies.
- Authorization occurs before disclosure; unrelated records return concealed 404.
- OpenAPI exact paths: bounded staff list, incident create/get/patch, revision list/detail, restore; incident create/save `field_notes` is `type: string` with exact `maxLength: 30000` and fictional examples; required auth/client/request/idempotency/base revision headers and stable errors include over-limit `400 validation_failed` and `422 blocking_information_required`.
- All mutations idempotent; revision changes use base revision; summaries contain no full sensitive text.

## TDD procedure

1. Add adapter parity, policy matrix, multi-officer creation/idempotency, unrelated concealment, and API contract tests first. In `tests/integration/test_incident_api.py`, send 30,001 fictional Unicode code points and assert `400 validation_failed` with no durable side effects; contract tests assert OpenAPI `maxLength: 30000`. RP-02 already owns direct exact-30,000 acceptance, including non-BMP code-point semantics, on the shared strict model; do not duplicate a competing limit.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_report_service.py tests/unit/test_report_policy.py tests/integration/test_incident_api.py -v
   ```

   Expected: FAIL because route-neutral service, SQL staff provider, policies, and routes are absent.
3. Extract orchestration with dependency injection; preserve every legacy helper/shape and no-credential unit behavior.
4. Implement policies and transactional incident creation/read/revision operations with same-transaction idempotency+revision+audit.
5. Register staff/incident routes and OpenAPI with closed schemas and fictional examples.
6. Run focused, legacy, and contract:

   ```powershell
   python -m pytest tests/unit/test_report_service.py tests/unit/test_report_policy.py tests/integration/test_incident_api.py tests/unit/test_report_helpers.py tests/unit/test_deferred_disciplinary.py tests/unit/test_generate_all_reports.py tests/contract/test_access_v1_openapi.py -v
   ```

   Expected: PASS with no Google credentials. PostgreSQL integration uses only dedicated test DB; stop rather than SQLite/production.
7. Run allowlist/whitespace:

   ```powershell
   $allowed=@('backend/reports/service.py','backend/reports/persistence.py','backend/reports/policy.py','backend/reports/roster.py','backend/webapp/routes/reports.py','backend/webapp/api_v1/staff.py','backend/webapp/api_v1/incidents.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','tests/unit/test_report_service.py','tests/unit/test_report_policy.py','tests/integration/test_incident_api.py')
   $changed=@((git diff --name-only),(git diff --cached --name-only),(git ls-files --others --exclude-standard))|Sort-Object -Unique
   $unexpected=$changed|Where-Object{$_ -notin $allowed -and $_ -notlike '.superpowers/*'}
   if($unexpected){$unexpected;throw 'Changed-file allowlist violation.'}
   git diff --check
   $taskChanged=@($changed|Where-Object{$_ -in $allowed})
   if(-not $taskChanged){throw 'No allowlisted task changes to stage.'}
   git add -A -- $taskChanged
   $staged=@(git diff --cached --name-only)|Sort-Object -Unique
   $unexpectedStaged=$staged|Where-Object{$_ -notin $allowed}
   if($unexpectedStaged){$unexpectedStaged;throw 'Staged-file allowlist violation.'}
   git diff --cached --name-status
   git diff --cached --check
   ```

## Security, non-goals, acceptance

Fictional fixtures only; no ADC/Google network; no field notes/report/name/employee/inmate/policy text in logs/audit. Do not change prompts/retrieval/validation/template behavior, create report queue/history UI, jobs, exports, Access, or infra. Acceptance: red evidence, engine parity, SQL staff provider, authorization-first concealment, multi-officer canonical relationships, shared 30,000-character route/schema/OpenAPI enforcement with 30,001 rejected atomically, idempotency/audit atomics, exact OpenAPI, tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: add authorized incident api"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start/ancestry/prerequisite/branch/commit/files/red/green/legacy parity/auth/security/deviation/risk. Stop for review/prerequisite/dirt, unavailable dedicated DB, engine behavior drift, allowlist expansion, secret/prod need, or contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
