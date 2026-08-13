# Sequence 016 — RP-07: Private Worker and Cloud Tasks Dispatcher

Copy everything below into a fresh Claude Code session.

---

Implement only RP-07, “Private worker and Cloud Tasks dispatcher.” Follow TDD, make one focused commit, hand off, and stop.

## Objective

Dispatch committed outbox rows to deterministic authenticated Cloud Tasks and add a private worker application that validates task metadata, claims jobs, calls existing route-neutral report services, applies one safe durable result, and records bounded terminal failures. Tests must use fakes and require no Google credentials.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-07-private-worker-dispatcher`
- Predecessor on reviewed `main`: `feat: add durable idempotent ai jobs`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add durable idempotent ai jobs"
git switch -c claude/rp-07-private-worker-dispatcher
```

Require clean tracked/index state; only untouched existing `.superpowers/` is tolerated. Read intervening reviewed changes; stop for missing/unreviewed/conflicting prerequisites. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; roadmap worker entrypoint/shared job interfaces/security rules.
- Report plan exact RP-07 section including task request shape, OIDC, error/retry behavior, fake clients, worker command, tests.
- Deployment spec/plan OP-04 consume-only for exact worker/IAM contract; report/master specs.
- Consume-only RP-03 services and RP-06 jobs/outbox, existing retry helper/Dockerfile.

## Exact allowed files

- Create: `backend/jobs/dispatcher.py`
- Create: `backend/worker/__init__.py`
- Create: `backend/worker/app.py`
- Create: `backend/worker/routes.py`
- Create: `backend/worker/metrics.py`
- Create: `scripts/dispatch_outbox.py`
- Modify: `Dockerfile`
- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Create: `tests/unit/test_task_dispatcher.py`
- Create: `tests/unit/test_worker_routes.py`
- Create: `tests/unit/test_worker_metrics.py`
- Create: `tests/integration/test_worker_pipeline.py`

Consume-only: RP services/models, retry code, plans/specs, Terraform plan, tests not above. No infra/workflow/OpenAPI/public API/engine prompt/README edits.

## Locked interfaces and rules

- Produce `dispatch_pending(limit: int=100) -> DispatchSummary`, `POST /internal/jobs/{job_id}/run`, CLI `python scripts/dispatch_outbox.py --limit 100`, and canonical entrypoint `backend.worker.app:create_worker_app()`.
- Dispatcher reads only committed available outbox rows, deterministic task name from project/region/queue/job UUID, exact JSON `{"job_id":"UUID"}`, OIDC task-invoker service-account email, audience equal worker origin. AlreadyExists counts success; retry safe transient errors only; persist bounded codes, never provider/body/auth details.
- Worker is private by Cloud Run IAM. App additionally requires Cloud Tasks metadata and exact route/body UUID match as defense-in-depth, not IAM replacement. Do not implement shared secret auth or trust arbitrary headers.
- Worker claims one job, runs existing injected classifier/extractor/generator adapters, updates stable stages, validates, applies via revision service, safe audit/result. Deterministic validation/auth failure records terminal category then returns 2xx to stop retry; transient failure follows documented retry.
- Redelivery applies at most one durable result. On recovered provider-repeat risk, emit exactly one real Cloud Monitoring counter point of type `custom.googleapis.com/ai_provider_repeat_risk_total`, with `job_type` as its sole metric label. The Monitoring adapter must use dependency injection in offline tests, create its Google client lazily, and emit no identity, job/request ID, or report content; crash after provider acceptance before DB commit can repeat billing, so never claim external exactly-once.
- Docker retains API default and contains required Alembic/migrations/root assets. Deployment supplies exact worker command `gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 900 "backend.worker.app:create_worker_app()"`.
- Unit/integration use `FakeTasksClient` and fake report engine; no ADC/network.

## TDD procedure

1. Add dispatcher/OIDC/deterministic-name/already-exists/retry tests, worker metadata/body/auth/claim/result/redelivery/failure tests, and fake fixtures first.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_task_dispatcher.py tests/unit/test_worker_routes.py tests/integration/test_worker_pipeline.py -v
   ```

   Expected: FAIL because dispatcher/worker app do not exist.
3. Implement dispatcher/CLI after-commit behavior. Do not call task service from the submission transaction.
4. Implement private worker factory/route with injected fakes, exact job lifecycle, safe errors/metrics.
5. Update image contents/entrypoint support without changing API default.
6. Run focused regression:

   ```powershell
   python -m pytest tests/unit/test_task_dispatcher.py tests/unit/test_worker_routes.py tests/integration/test_worker_pipeline.py tests/unit/test_retry.py -v
   ```

   Expected: PASS without Google credentials; fake Tasks and fake report engine each receive one call.
7. Run allowlist/whitespace:

   ```powershell
   $allowed=@('backend/jobs/dispatcher.py','backend/worker/__init__.py','backend/worker/app.py','backend/worker/routes.py','backend/worker/metrics.py','scripts/dispatch_outbox.py','Dockerfile','requirements.txt','backend/requirements.txt','tests/unit/test_task_dispatcher.py','tests/unit/test_worker_routes.py','tests/unit/test_worker_metrics.py','tests/integration/test_worker_pipeline.py','docs/superpowers/plans/2026-08-12-report-storage-api-implementation.md','docs/claude-prompts/tasks/016-rp-07-private-worker-dispatcher.md')
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

Only fictional UUID/content and fake clients. No real queue/ADC/provider call. Logs exclude payload/content/actor employee/inmate/name/PIN/token/auth header. Do not deploy/configure IAM/queue/Cloud Run, change engines/public API, or claim exactly-once billing. Acceptance: red evidence; deterministic OIDC dispatch; private/metadata boundary; safe job lifecycle/redelivery/failures/metric; image command support; tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: add private report job worker"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start/ancestry/prerequisite/branch/commit/files/red/green/OIDC/IAM-defense/redelivery/repeat-risk/security/deviation/risk. Stop for missing review/prerequisite, dirty overlap, unexpected network/credential need, allowlist expansion, contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
