# Sequence 014 — RP-05: Admin Report Search, Edit, Restore, Transfer, and Attribution

Copy everything below into a fresh Claude Code session.

---

Implement only RP-05, “Admin report search, edit, restore, transfer, and attribution.” Use TDD, create one focused commit, hand off, and stop before AI jobs.

## Objective

Add bounded structured Admin search and attributable view/edit/history/restore/ownership-transfer over the same canonical report/revision services. Admin actions must require server-side elevation, exact-purpose single-use step-up where sensitive, and immutable revisions rather than hidden overwrite.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-05-admin-report-api`
- Predecessor: current reviewed `main` includes `feat: add shared report history and recovery`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add shared report history and recovery"
git switch -c claude/rp-05-admin-report-api
```

Require clean tracked/index; ignore only untouched existing `.superpowers/`. Read intervening reviewed changes on advanced main; stop for missing/unreviewed/conflicting work. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; roadmap exact Admin report routes, step-up errors, export handoff, Actor/revision/idempotency contracts.
- Report plan exact RP-05 section including full `AdminReportFilters`, migration/index rules, route bodies, tests.
- Report/Admin/master specs.
- Consume-only ID-07 guards/fixtures, RP-02/04 policy/revision/persistence/OpenAPI.

## Exact allowed files

- Create: `backend/webapp/api_v1/admin_reports.py`
- Modify: `backend/reports/persistence.py`
- Modify: `backend/reports/revisions.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `migrations/versions/20260812_0004_report_search_indexes.py`
- Create: `tests/integration/test_admin_report_api.py`
- Create: `tests/integration/test_admin_report_search.py`

Consume-only: ID guards/fixtures, report models/services, plans/specs/tests not above. No User route, export, job, engine, legacy, docs, Access, or infra edits.

## Locked interfaces and exact routes

- Exact paths: GET admin reports/list/detail/revisions/revision detail; PATCH report; POST `{report_id}/restore`; POST `{report_id}/transfer`. RP-09 owns export routes. Obsolete `/revisions/{n}/restore` must be rejected/not defined.
- Every Admin route requires Admin role and active server-side elevation. Save uses no step-up but remains attributed/idempotent; restore requires `report_restore`; transfer requires `report_transfer`. Only header `X-Admin-Step-Up`; missing/wrong/replayed/expired is `step_up_required`.
- Search migration exact revision `20260812_0004`, predecessor `20260812_0003`; add bounded indexes only.
- One closed `AdminReportFilters` reused later by bulk export. Fields are exactly the 20 fields in RP-05 plan. Unknown/empty query is `400 validation_failed`; explicit sort allowlist; signed cursor; default 50/max 100.
- Search structured columns, not narrative text. Audit normalized filter names and result count only, never values/inmate/report content.
- Admin opening another employee’s report writes `report.viewed_by_admin`.
- Admin save calls shared `save_report(... reason="admin_edit")`, closed body content+base revision. Restore body exactly `{"revision_number":2}` and creates a new restored revision referencing immutable source. Transfer body exact new owner, optional preparer, nonblank reason <=500; validate active targets, lock/replace access transactionally, create ownership revision/audit.
- Every mutation claims/completes ID-06 idempotency in same transaction with step-up consumption/revision/audit.
- Revision responses include safe immutable attribution/snapshots as authorized; no audit internals, session/PIN, delete/overwrite. Users cannot discover Admin routes.

## TDD procedure

1. Add failing search/filter/index/pagination, User denial, elevation, Admin view audit, edit conflict, restore exact path/purpose, transfer purpose/atomic, attribution/idempotency tests.
2. Run red:

   ```powershell
   python -m pytest tests/integration/test_admin_report_api.py tests/integration/test_admin_report_search.py -v
   ```

   Expected: FAIL because Admin report routes/indexes are absent.
3. Add reversible `20260812_0004` search indexes and closed shared filters/queries.
4. Add exact routes reusing shared policies/revisions and same-transaction idempotency/step-up/audit.
5. Update OpenAPI exact paths/bodies/headers/errors/attribution/conflict; assert obsolete restore absent.
6. On dedicated test PostgreSQL run:

   ```powershell
   python -m pytest tests/integration/test_admin_report_api.py tests/integration/test_admin_report_search.py tests/integration/test_report_concurrency.py tests/unit/test_report_policy.py -v
   ```

   Expected: PASS; Users cannot discover routes; expired/wrong-purpose grants rejected. Stop without dedicated DB; never SQLite/production.
7. Run allowlist/whitespace:

   ```powershell
   $allowed=@('backend/webapp/api_v1/admin_reports.py','backend/reports/persistence.py','backend/reports/revisions.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','migrations/versions/20260812_0004_report_search_indexes.py','tests/integration/test_admin_report_api.py','tests/integration/test_admin_report_search.py')
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

Fictional fixtures only. Never log/audit filter values, inmate/name/employee IDs, report text, PIN/token/session data, raw body. No Google calls. Do not implement exports/jobs/audit UI/Access/infra or delete/merge. Acceptance: red evidence; exact filters/index migration/routes; elevation/step-up/idempotency atomics; immutable Admin edits/restores/transfers; attribution; authorization; OpenAPI/tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: add attributed admin report oversight"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff all start/ancestry/prerequisite/branch/commit/files/red/green/migration/route/purpose/audit/security/deviation/risk. Stop for missing review/prerequisite, dirty overlap, no dedicated DB, migration/contract conflict, allowlist expansion, secret/prod need. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
