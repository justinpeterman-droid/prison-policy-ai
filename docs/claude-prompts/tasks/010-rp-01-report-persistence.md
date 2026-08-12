# Sequence 010 — RP-01: Incident, Report, Access, and Revision Persistence

Copy everything below into a fresh Claude Code session opened at the repository root.

---

Implement only RP-01, “Incident, report, access, and revision persistence.” Use TDD, create one focused commit, hand off, and stop before RP-02.

## Objective and rationale

Add the bounded PostgreSQL domain model and reversible migration for incidents, canonical reports, owner/preparer access, and immutable revisions. This creates efficient current rows plus append-only snapshots without changing existing report engines or legacy routes. The model must support one shared report rather than owner/preparer copies and must keep Completed/Archived editable.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed planning baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-01-report-persistence`
- Required predecessor: all ID-01–ID-08 reviewed and merged into current `main`; verify the latest exact subject `feat(identity): add attributable Review Lab handoff`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "feat(identity): add attributable Review Lab handoff"
git switch -c claude/rp-01-report-persistence
```

Before branch creation, tracked/index state must be clean. Existing untracked `.superpowers/` is user-owned and may remain but must never be touched/staged; stop for any other change. If main advanced, baseline must remain an ancestor and all intervening plan/prerequisite changes must be reviewed and read. Stop on unreviewed/conflicting changes or missing prerequisites. Never reset, clean, stash, overwrite, or discard user work.

## Required reading

- `AGENTS.md`.
- Roadmap global constraints, locked structure, shared Python/HTTP/wire/error/version contracts, dependency order and Gate B.
- Report plan exact section `### Task RP-01: Incident, report, access, and revision persistence`, including complete domain fields, test support, migration rules, and code examples.
- Approved report/master specs and identity plan’s shared fixture contract.
- Consume-only current persistence base/identity models/migrations and existing report model concepts.

## Exact allowed files

- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Create: `backend/persistence/models/reporting.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260812_0003_report_storage.py`
- Create: `tests/support/reporting.py`
- Modify: `tests/integration/conftest.py`
- Create: `tests/unit/test_reporting_models.py`
- Create: `tests/integration/test_report_migration.py`

Consume-only: plans/specs, all existing engines/routes/models/migrations/tests not above. Do not edit OpenAPI, API routes, legacy routes, README, identity models, or prior migrations.

## Locked interfaces and model rules

- Consume `Base`, identity UUID FKs, UTC helpers, and the ID migration framework.
- Produce `Incident`, `IncidentRevision`, `Report`, `ReportAccess`, `ReportRevision`, `ReportStatus`, `ReportType`, `RevisionReason`, plus migration `20260812_0003` with `down_revision="20260812_0002"`.
- Add exact `pydantic>=2.13,<3.0` to both runtime requirement files; no second validation library or unrelated dependency changes.
- Implement every approved domain field using PostgreSQL JSONB, `Uuid(as_uuid=True)`, explicit FKs, named checks, unique `(parent_id,revision_number)`, nonnegative revisions, and indexes for approved status/date/category/owner/preparer/updated queries.
- `ReportAccess.relationship` is only `owner|preparer`; revoked relationships are preserved. One owner report per reporting officer, with one preparer relation for authenticated creator when different; no copied report.
- Report status exact `in_progress|completed|archived`; status never prevents future revision. Report type enum exact values in plan. Revision reasons exact list including admin edit/recovery/ownership.
- Current rows and immutable revision 1 must be transactionally compatible for later services; historical rows are never updated/deleted.
- Extend shared tests with exact fictional fixtures/names in the report plan. No real roster or SQLite fallback.

## TDD procedure

1. Write model and migration tests first, including duplicate revision rejection, bounded owner/preparer relation, checks/enums/indexes/FKs, fixture contracts, and upgrade/downgrade/re-upgrade.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_reporting_models.py tests/integration/test_report_migration.py -v
   ```

   Expected: FAIL because reporting models and migration `20260812_0003` do not exist. PostgreSQL tests may skip only with the preapproved missing-`TEST_DATABASE_URL` reason; stop rather than using SQLite/production.
3. Add Pydantic dependency and all bounded models/fixture builders exactly as the plan. Do not begin schemas/services.
4. Add the reversible expansion migration, documenting expected empty-DB duration, locks, test-only downgrade, and verification queries. Production rollback retains expansion; do not encode destructive production automation.
5. On dedicated PostgreSQL 17, run green lifecycle:

   ```powershell
   python -m pytest tests/unit/test_reporting_models.py tests/integration/test_report_migration.py -v
   ```

   Expected: PASS; upgrade, downgrade, second upgrade leave correct tables/head. If DB is absent, stop and report not run.
6. Run `git diff --check`, inspect model/migration/requirements, and enforce:

   ```powershell
   $allowed=@('requirements.txt','backend/requirements.txt','backend/persistence/models/reporting.py','backend/persistence/models/__init__.py','migrations/versions/20260812_0003_report_storage.py','tests/support/reporting.py','tests/integration/conftest.py','tests/unit/test_reporting_models.py','tests/integration/test_report_migration.py')
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

All fixtures fictional; no real employees, inmates, reports, PINs, or tokens; no Google calls. Do not log JSON content. Do not implement services/routes/OpenAPI/jobs/exports/Access/infra. Acceptance: red-first evidence, exact models/constraints/enums/indexes/migration chain, immutable revision/access semantics, exact fixture contract, both requirement files correct, lifecycle tests pass, allowlist/whitespace pass.

## Commit and handoff

```powershell
git commit -m "feat: add incident and report revision schema"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start SHA/ancestry/prerequisites/branch/commit/files/red/green/migration/security/deviation/risk. Stop for missing ancestry/review/prerequisite, dirty overlap, dedicated DB absence before DB work, migration conflict, allowlist expansion, secret/production need, or reviewed-contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
