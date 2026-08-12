# Sequence 015 — RP-06: AI-Job Idempotency Integration and Transactional Outbox

Copy everything below into a fresh Claude Code session.

---

Implement only RP-06, “AI-job idempotency integration and transactional outbox.” Use TDD, one focused commit, hand off, and stop before the worker.

## Objective

Add durable AI job/export/outbox persistence, one-transaction idempotent job submission, safe job status, row-locked claiming, stale-result protection, and the classify/extract/generate/disciplinary job API contracts. A successful API request must never produce an orphan job without an outbox record, and Cloud Tasks redelivery must apply at most one durable result.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-06-ai-jobs-outbox`
- Predecessor on current reviewed `main`: `feat: add attributed admin report oversight`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add attributed admin report oversight"
git switch -c claude/rp-06-ai-jobs-outbox
```

Require clean tracked/index state. Only untouched pre-existing `.superpowers/` is tolerated. Read all intervening reviewed plan/prerequisite changes if main advanced; stop on unreviewed/conflicting work. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; roadmap job signatures, idempotency, status, sensitive-log and HTTP rules.
- Report plan exact RP-06 section including migration records/indexes, tests, submission/result algorithm and API stages.
- Report/master specs.
- Consume-only ID-06 idempotency model/service, RP report models/policies/revisions/service, current migration chain/OpenAPI/test fixtures.

## Exact allowed files

- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Create: `backend/persistence/models/jobs.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260812_0005_jobs_exports.py`
- Create: `backend/jobs/service.py`
- Create: `backend/jobs/outbox.py`
- Create: `backend/webapp/api_v1/jobs.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_idempotency_service.py`
- Create: `tests/integration/test_job_submission.py`
- Create: `tests/integration/test_job_redelivery.py`

Consume-only: ID-06 idempotency files, report services/models, plans/specs/tests not above. Do not create another idempotency table/service, dispatcher/worker, report-engine changes, Access, docs, or infra.

## Locked interfaces and rules

- Consume ID-06 `IdempotencyRecord`, `claim_idempotency`, `complete_idempotency`; never duplicate/redefine them.
- Produce `AiJob`, `TaskOutbox`, `Export`, `submit_job()`, `claim_job()`, `apply_job_result()`, submission routes and GET job status with roadmap signatures.
- Add exactly `google-cloud-tasks>=2.23,<3.0` to both runtime requirements; do not instantiate/call it in this task or tests.
- Migration exact `20260812_0005`, predecessor `20260812_0004`; approved constraints/indexes plus outbox. Persist stable IDs/digests/status/error categories only; no raw authorization, field notes/report text, prompt/response, or secret.
- In one transaction: authorize actor+incident+base revision, claim idempotency with canonical SHA-256, create queued job, create outbox, safe audit, commit. Same key+same payload returns same job 202; changed payload is `idempotency_conflict`; rollback leaves no job/outbox/idempotency/audit fragment.
- `claim_job` uses `FOR UPDATE SKIP LOCKED`; safe redelivery may claim/apply one durable result. `apply_job_result` validates expected incident revision and returns terminal `job_result_conflict` rather than overwriting newer content.
- Exact submission paths for classify/extract/generate/disciplinary and `GET /api/v1/jobs/{job_id}`. Stable stages: queued, classifying, extracting, validating, generating, disciplinary, completed, failed.
- Job read allowed only requesting actor with current incident access or Admin. Closed schemas; required bearer/client/request/idempotency/base revision; no client actor/model/prompt hash/audit identity.

## TDD procedure

1. Add idempotency/outbox/job submission/redelivery tests first, including same key same ID, changed payload conflict, rollback atomicity, authorization, stale base, `SKIP LOCKED`, duplicate redelivery, and OpenAPI.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_idempotency_service.py tests/integration/test_job_submission.py tests/integration/test_job_redelivery.py -v
   ```

   Expected: FAIL because job/outbox/export models and routes do not exist; existing ID-06 idempotency tests remain green.
3. Add dependency and exact reversible migration/mappings/indexes.
4. Implement job/outbox services with one transaction, normalized request digest, stable response reference, locked claim and stale-result guard.
5. Register submission/status routes and OpenAPI exact stages/errors/examples.
6. On dedicated test PostgreSQL run:

   ```powershell
   python -m pytest tests/unit/test_idempotency_service.py tests/integration/test_job_submission.py tests/integration/test_job_redelivery.py tests/integration/test_report_migration.py -v
   ```

   Expected: PASS; rollback leaves neither orphan job nor outbox. Stop without dedicated DB; never SQLite/production.
7. Run allowlist/whitespace:

   ```powershell
   $allowed=@('requirements.txt','backend/requirements.txt','backend/persistence/models/jobs.py','backend/persistence/models/__init__.py','migrations/versions/20260812_0005_jobs_exports.py','backend/jobs/service.py','backend/jobs/outbox.py','backend/webapp/api_v1/jobs.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','tests/unit/test_idempotency_service.py','tests/integration/test_job_submission.py','tests/integration/test_job_redelivery.py')
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

Fictional fixtures; no Google calls/ADC. Never log/persist content, employee/inmate/name IDs, PIN/token/auth headers, provider input/output. Do not implement dispatcher/worker/Cloud Tasks network, exports, Access, infra. Acceptance: red evidence, exact migration/dependencies/models, shared-idempotency reuse, atomic submit/outbox/audit, safe stages/auth/stale/redelivery behavior, tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: add durable idempotent ai jobs"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start/ancestry/prerequisite/branch/commit/files/red/green/migration/atomicity/redelivery/security/deviation/risk. Stop for missing review/prerequisite, dirty overlap, no dedicated DB, migration/idempotency conflict, allowlist expansion, secret/prod need. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
