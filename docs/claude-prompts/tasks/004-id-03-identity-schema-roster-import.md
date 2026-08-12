# Sequence 004 — ID-03: Identity, Audit, Session, Rate-Limit, Browser-Session Schema and Roster Import

Copy everything below into a fresh Claude Code session opened at the repository root.

---

Implement only Task ID-03, “Identity, Audit, Session, Rate-Limit, Browser-Session Schema and Roster Import.” Use strict TDD, one focused commit, then stop before ID-04.

## Objective and outcome

Create the reversible PostgreSQL identity/security schema, safe normalization, database-enforced append-only audit boundary, and idempotent roster import. The schema must support later opaque sessions, elevation, handoffs, rate limits, and audit without persisting readable credentials. The importer migrates the existing checked-in roster into Cloud SQL safely while leaving the legacy roster source and GCS behavior unchanged.

## Repository, baseline, and prerequisites

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-03-identity-schema-roster`
- Required predecessor subjects: `chore(identity): add database and migration foundation`; `feat(api): add versioned Access API foundation`.

Run the standard preflight:

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "chore(identity): add database and migration foundation","feat(api): add versioned Access API foundation"
git switch -c claude/id-03-identity-schema-roster
```

Require clean tracked/index state before branching from current reviewed `main`; tolerate only existing untracked `.superpowers/` and never touch/stage it. If reviewed main advanced, inspect intervening reviewed plan/spec/prerequisite changes, confirm review, and require baseline ancestry. Stop for unreviewed/conflicting changes. Never reset/stash/clean user work. Create `claude/id-03-identity-schema-roster` from current HEAD without force; stop on collision.

## Required reading

- `AGENTS.md`.
- Roadmap global constraints/interfaces/wire rules/dependency order.
- Identity plan exact section `### Task ID-03: Identity, Audit, Session, Rate-Limit, Browser-Session Schema and Roster Import`, including the complete Required schema table and code/test examples.
- Approved identity/master specs.
- Consume-only: ID-01 persistence/Alembic code, ID-02 request context, `templates/staff_roster.json`, existing roster modules/tests, and current migration head.

## Exact allowed files

- Modify: `backend/persistence/models/__init__.py`
- Create: `backend/persistence/models/identity.py`
- Create: `backend/persistence/models/sessions.py`
- Create: `backend/persistence/models/security.py`
- Create: `backend/identity/normalization.py`
- Create: `backend/identity/audit.py`
- Create: `backend/identity/roster_import.py`
- Create: `migrations/versions/20260812_0001_identity_foundation.py`
- Create: `scripts/import_roster_to_postgres.py`
- Create: `tests/unit/test_identity_normalization.py`
- Create: `tests/unit/test_audit_schema.py`
- Create: `tests/unit/test_roster_import.py`
- Create: `tests/integration/test_identity_migration.py`
- Create: `tests/integration/test_roster_import.py`

Consume-only: `templates/staff_roster.json`, plans/specs, Alembic/base/database code, and existing legacy roster code/tests. Do not edit the roster JSON, GCS settings/objects, OpenAPI, routes, README, plans, or other files.

## Locked interfaces and invariants

- Consume `Base`, `session_scope()`, `IdentitySettings`, ID-02 request IDs, and `templates/staff_roster.json`.
- Produce exact ORM classes `StaffMember`, `Account`, `AccessSession`, `RenewalTokenHistory`, `AdminElevation`, `AdminStepUpToken`, `BrowserHandoff`, `BrowserSession`, `AuthRateLimit`, and `AuditEvent`; exact normalization functions; `AuditEventInput`; `AuditWriter`; and `import_roster(session, records, apply) -> RosterImportSummary`.
- Implement every column, named check, unique/index, FK, server UUID, and UTC timestamp in the task’s Required schema. Do not omit fields because a later service is not implemented yet.
- Migration is exactly revision `20260812_0001` with the task-specified predecessor. It creates `pgcrypto`, schema, append-only protections, and validated `append_audit_event`; downgrade reverses in dependency order.
- Employee numbers trim/uppercase; device labels are bounded safe display metadata. UUIDs come from PostgreSQL `gen_random_uuid()` and are never derived from employee numbers.
- Audit details are action-specific and closed. App runtime cannot update/delete audit rows; insertion is only through the database function. No sensitive value is accepted into audit JSON.
- Roster import validates the complete input before mutation, supports dry-run, computes a stable SHA-256 checksum, is idempotent by normalized employee number, preserves UUIDs, and never creates accounts.
- No readable PIN/token/hash input, real roster output, raw record, or database URL may be logged.

## TDD procedure

1. Add failing normalization, audit-schema, roster-import, migration, and integration tests first using only fictional records except consume-only validation of the checked-in source count.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_identity_normalization.py tests/unit/test_audit_schema.py tests/unit/test_roster_import.py -q
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m alembic upgrade head
   python -m pytest tests/integration/test_identity_migration.py tests/integration/test_roster_import.py -q
   ```

   Expected: unit collection fails on missing modules; migration tests fail because identity tables and `append_audit_event` do not exist. If no dedicated `TEST_DATABASE_URL` exists, record the unit red result and stop before database commands; never substitute SQLite or another database.
3. Implement normalization and all mappings, then the reversible `20260812_0001` migration and database audit protections exactly from the plan.
4. Implement validated `AuditEventInput` and the `AuditWriter` protocol boundary; do not implement the concrete writer reserved for ID-06.
5. Implement importer and CLI. Verify dry-run:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python scripts/import_roster_to_postgres.py --input templates/staff_roster.json --dry-run
   ```

   Expected: `source_count=13`, `inserted_count=13`, `existing_count=0`, `applied=false`, and a 64-character checksum; `staff_members` stays empty.
6. On a dedicated test DB only, verify first/second apply, immutable UUIDs, audit write protections, and migration roundtrip:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m alembic upgrade head
   python scripts/import_roster_to_postgres.py --input templates/staff_roster.json --apply
   python scripts/import_roster_to_postgres.py --input templates/staff_roster.json --apply
   python -m pytest tests/integration/test_identity_migration.py tests/integration/test_roster_import.py -q
   python -m alembic downgrade base
   python -m alembic upgrade head
   ```

   Expected: first apply inserts 13; second inserts 0/reports 13 existing; UUIDs unchanged; forbidden audit mutations fail; downgrade/re-upgrade exit 0.
7. Run final unit/legacy roster regressions:

   ```powershell
   python -m pytest tests/unit/test_identity_normalization.py tests/unit/test_audit_schema.py tests/unit/test_roster_import.py -q
   python -m pytest tests/unit/test_roster_routes.py tests/unit/test_roster_store.py -q
   ```

   Expected: all pass and legacy roster/GCS sources are untouched.
8. Review migration SQL/downgrade, run `git diff --check`, and enforce the exact allowlist:

   ```powershell
   $allowed=@('backend/persistence/models/__init__.py','backend/persistence/models/identity.py','backend/persistence/models/sessions.py','backend/persistence/models/security.py','backend/identity/normalization.py','backend/identity/audit.py','backend/identity/roster_import.py','migrations/versions/20260812_0001_identity_foundation.py','scripts/import_roster_to_postgres.py','tests/unit/test_identity_normalization.py','tests/unit/test_audit_schema.py','tests/unit/test_roster_import.py','tests/integration/test_identity_migration.py','tests/integration/test_roster_import.py')
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

## Security, non-goals, and acceptance

Fixtures and test records must be fictional. Never emit real roster rows into logs/artifacts/issues. Do not implement PIN policy, session logic, API routes, concrete audit writes, reports, Access client, or infrastructure. Acceptance requires exact schema/migration identity, reversible lifecycle, append-only audit enforcement, safe/idempotent roster dry-run/apply, unchanged source roster/GCS behavior, expected tests, allowlist, and whitespace checks.

## Commit and handoff

```powershell
git commit -m "feat(identity): add identity schema and roster import"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Report task/branch, start SHA/ancestry, commit, changed files, red evidence, each green/migration/import result, sensitive-data review, deviations, and follow-ups. Stop for missing ancestry/prerequisites, dirty unrelated files, missing dedicated test DB before DB work, migration-chain conflict, allowlist expansion, secret/production need, or reviewed-contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete resources or data/use destructive Git/touch `.superpowers/`.
