# Sequence 013 — RP-04: Employee Reports, Queues, Revision History, Restore, and Recovery

Copy everything below into a fresh Claude Code session.

---

Implement only RP-04, “Employee reports, queues, revision history, restore, and recovery.” Work TDD-first, make one focused commit, hand off, and stop.

## Objective

Add User-facing owned/prepared report lists, canonical report detail/save, immutable history, restore, recovery revision, and reversible status changes with authorization-first SQL pagination and conflict-safe writes. Owner and preparer must see/edit the same report, including Completed/Archived; local recovery never silently overwrites newer cloud content.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-04-user-report-api`
- Predecessor on current reviewed `main`: `feat: add authorized incident api`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add authorized incident api"
git switch -c claude/rp-04-user-report-api
```

Require clean tracked/index state; only untouched pre-existing `.superpowers/` tolerated. Read intervening reviewed changes if main advanced; stop for missing/unreviewed/conflicting prerequisites. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; roadmap record-policy/save signatures, HTTP/idempotency/conflict rules.
- Report plan exact RP-04 section with route list, filters, conflict/recovery semantics, examples/tests.
- Report/master/User client specs.
- Consume-only RP-01–03 models/schemas/policies/persistence/revisions, ID Actor/idempotency/OpenAPI.

## Exact allowed files

- Create: `backend/webapp/api_v1/reports.py`
- Modify: `backend/reports/persistence.py`
- Modify: `backend/reports/revisions.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/integration/test_employee_report_api.py`
- Create: `tests/integration/test_report_concurrency.py`
- Create: `tests/contract/test_report_examples.py`

Consume-only: all plans/specs/prerequisite code/tests not above. No migration, Admin routes, engines, jobs, exports, legacy, README, Access, or infra changes.

## Locked interfaces and wire rules

- Produce owned/prepared list, detail/save, revision list/detail, restore, recovery, and status-save paths exactly in approved API/OpenAPI. Access consumers are `modReportWorkflow`, `modAutosave`, `modConflict`, `frmReportHistory`.
- Apply `can_read/edit/export` authorization in SQL before cursor pagination. Unrelated User receives concealed `404 not_found`; never disclose existence/count/revision.
- List page default 25/max 50; exact filters status, incident date range, category, updated range. Summaries contain no narrative/full field notes.
- Owner and preparer lists reference same report UUID; no copy. Completed/Archived remain editable and status changes are revisions.
- Every mutation claims/completes ID-06 idempotency in the same transaction as current update, immutable revision, and audit.
- Save accepts base revision. If both `If-Match: "7"` and body base supplied, they must agree. Stale write is `409 revision_conflict`, with safe current revision/editor display/time/changed-field names, never content.
- Restore copies selected immutable snapshot into new current revision. Recovery appends local content as separate `recovery` revision and returns ID without promotion over newer current.
- Closed schemas; no client actor/owner/preparer/model/audit identity. Exact standard envelopes/headers/errors/OpenAPI examples.

## TDD procedure

1. Add owner/preparer same-ID, unrelated 404, pagination/filter, history/detail, stale concurrency, completed edit, restore, recovery, status, idempotency and contract tests first.
2. Run red:

   ```powershell
   python -m pytest tests/integration/test_employee_report_api.py tests/integration/test_report_concurrency.py tests/contract/test_report_examples.py -v
   ```

   Expected: FAIL because `/api/v1/reports` is not registered.
3. Implement authorization-first persistence queries/summaries, then exact detail/save/history/restore/recovery/status routes with atomics.
4. Add every employee endpoint/schema/error/fictional example to OpenAPI; do not define delete or permanent locking.
5. Run focused authorization/regressions on dedicated test PostgreSQL:

   ```powershell
   python -m pytest tests/integration/test_employee_report_api.py tests/integration/test_report_concurrency.py tests/contract/test_report_examples.py tests/unit/test_report_policy.py tests/unit/test_auth_middleware.py -v
   ```

   Expected: PASS; unrelated User receives concealed 404. Stop if test DB absent; never SQLite/production.
6. Run allowlist/whitespace:

   ```powershell
   $allowed=@('backend/webapp/api_v1/reports.py','backend/reports/persistence.py','backend/reports/revisions.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','tests/integration/test_employee_report_api.py','tests/integration/test_report_concurrency.py','tests/contract/test_report_examples.py')
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

Fictional report content only; no Google calls; never log/audit field notes, narrative, names, employee/inmate IDs, raw bodies, PIN/token. Do not implement Admin oversight, AI jobs, exports, Access UI, infra, or engine changes. Acceptance: red evidence; same canonical owner/preparer report; authorization-before-pagination; exact conflict/restore/recovery/status/idempotency behavior; OpenAPI/tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: add shared report history and recovery"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start/baseline/prerequisite/branch/commit/files/red/green/auth/conflict/recovery/security/deviation/risk. Stop for missing review/prerequisite, dirty overlap, no dedicated DB, allowlist expansion, secret/prod need, or contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
