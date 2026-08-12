# Sequence 002 — ID-01: Dependency, Database, and Alembic Foundation

Copy everything below into a fresh Claude Code session opened for this repository.

---

You are implementing exactly Task ID-01, “Dependency, Database, and Alembic Foundation,” for the Access + Cloud Run program. Work test-first, make one focused commit, and stop after the handoff report. Do not begin ID-02.

## Objective, outcome, and rationale

Add the dependency, validated configuration, SQLAlchemy lifecycle, Alembic, PostgreSQL integration-test, CI, and container foundations required by all individual identity work. The outcome must let the legacy Flask process boot with the Access API disabled while making an enabled but incomplete identity configuration fail safely. This separates the new Cloud SQL-backed API from the existing shared-code browser pilot and prevents schema changes from running implicitly at application startup.

## Repository and reviewed baseline

- Repository root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed planning baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Work branch: `claude/id-01-database-alembic`
- Required predecessor: OP-01, commit subject `chore: gate implementation and deployment prerequisites`, must be present on current reviewed `main`. It may be absent only after a reviewed plan amendment changes the dependency.

Run from the repository root before editing:

```powershell
git status --short --untracked-files=all
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if ($LASTEXITCODE -ne 0) { throw "Reviewed planning baseline is not an ancestor of HEAD." }
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "chore: gate implementation and deployment prerequisites"
git switch -c claude/id-01-database-alembic
```

The tracked worktree and index must be clean before branching from current reviewed `main`. Pre-existing untracked `.superpowers/` content is user-owned and may remain; do not read, edit, stage, or delete it. Stop for any other pre-existing change. If reviewed `main` has advanced, the baseline must still be an ancestor; inspect every intervening reviewed plan/spec/prerequisite change, confirm it was reviewed, and implement the current reviewed contract. Stop for unreviewed or conflicting changes. Never reset, clean, stash, overwrite, or discard user work. Create the branch from current HEAD without force; if it already exists unexpectedly, stop.

## Required reading before editing

1. `AGENTS.md`
2. `docs/superpowers/plans/2026-08-12-access-cloud-run-program-roadmap.md`, especially Global Constraints, Locked Repository Structure, Shared Python Interfaces, Shared HTTP Rules, dependency order, and Gate A.
3. `docs/superpowers/plans/2026-08-12-cloud-identity-foundation-implementation.md`, from the exact heading `### Task ID-01: Dependency, Database, and Alembic Foundation` through its task-ending divider. Treat its tests and code skeletons as authoritative.
4. `docs/superpowers/specs/2026-08-12-cloud-identity-foundation-design.md`
5. `docs/superpowers/specs/2026-08-12-access-cloud-run-master-design.md`
6. Existing `conftest.py`, `backend/pipeline/config.py`, `backend/webapp/app.py`, `Dockerfile`, both requirement files, and `.github/workflows/tests.yml` as consume-only context.

## Exact allowed files

The task plan authorizes only these edits:

- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Modify: `Dockerfile:5-12`
- Modify: `.github/workflows/tests.yml:13-32`
- Create: `backend/persistence/__init__.py`
- Create: `backend/persistence/base.py`
- Create: `backend/persistence/database.py`
- Create: `backend/persistence/models/__init__.py`
- Create: `backend/identity/__init__.py`
- Create: `backend/identity/config.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `tests/unit/test_identity_config.py`
- Create: `tests/unit/test_database.py`
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_database_foundation.py`

Consume-only: every required-reading file not listed above. Do not edit plans, specs, README files, application routes, legacy configuration, or any other path. If an allowed-file expansion is genuinely required, stop and request a reviewed plan amendment.

## Locked interfaces and rules

- Produce `IdentitySettings.from_env(env: Mapping[str, str]) -> IdentitySettings`, `init_database(settings: IdentitySettings) -> None`, `session_scope() -> Iterator[Session]`, `database_ready() -> bool`, Alembic-importable `Base` metadata, and fixtures `db_engine`, `db_session_factory`, `db_session`, and `api_client`.
- `ACCESS_API_ENABLED` defaults false. When true, absence of `DATABASE_URL`, `IDENTITY_HASH_PEPPER`, or `CURSOR_SIGNING_KEY` raises `RuntimeError` naming only missing variable names.
- Preserve `ACCESS_CODE` as an independent setting in `backend/pipeline/config.py`.
- Never log or echo a database URL. Use SQLAlchemy 2, Psycopg 3, `pool_pre_ping=True`, UTC PostgreSQL sessions, and explicit `session_scope()` commit/rollback/close.
- Do not run Alembic in `create_app()`. Alembic requires `DATABASE_URL`, uses `compare_type=True`, and imports all model metadata.
- Validate public semantic versions, one safe bounded release-notes line, and pathless HTTPS `PUBLIC_BASE_URL` exactly as the task specifies. Preserve explicit development sentinels while identity is disabled.
- PostgreSQL-dependent tests require `TEST_DATABASE_URL`, skip with exactly `TEST_DATABASE_URL is not configured` when absent, and never fall back to SQLite.
- Root requirements support local/CI contract tests; `backend/requirements.txt` remains the deployed source. Keep `google-cloud-aiplatform` deployed-only.

## Test-first procedure

1. Create only the two unit test files first, using the exact cases and expectations in the ID-01 plan for disabled/enabled settings, safe versions/release notes/origin validation, and transaction rollback/close.
2. Run the red test:

   ```powershell
   python -m pytest tests/unit/test_identity_config.py tests/unit/test_database.py -q
   ```

   Expected: collection fails with `ModuleNotFoundError: No module named 'backend.identity'` or `No module named 'backend.persistence'`. If it passes before implementation or fails for an unrelated reason, investigate and document the mismatch before proceeding.
3. Add the exact compatible dependency ranges in the plan to both runtime files, with `openapi-spec-validator` only in root requirements. Do not upgrade unrelated packages.
4. Implement `IdentitySettings` and its exact safety validation, then the declarative base and database lifecycle. Keep readable credentials out of errors/logs.
5. Add credential-free `alembic.ini`, `migrations/env.py`, and `migrations/script.py.mako`; create no schema migration in this task.
6. Add the PostgreSQL 17 integration fixture/service and CI Python 3.12/3.14 matrix exactly as planned. With a dedicated fictional test database configured, run:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m alembic upgrade head
   python -m alembic downgrade base
   python -m pytest tests/integration/test_database_foundation.py -q
   ```

   Expected: Alembic connects in UTC, upgrade/downgrade exit 0, and readiness passes. If `TEST_DATABASE_URL` is absent, stop and report the integration test as not run; do not create or guess a database.
7. Copy Alembic assets into the image after the existing template copy, then run the focused and legacy regressions:

   ```powershell
   python -m pytest tests/unit/test_identity_config.py tests/unit/test_database.py -q
   python -m pytest tests/unit/test_access_code_config.py tests/unit/test_admin_tier.py -q
   ```

   Expected: all pass, and the legacy app boots when identity is explicitly disabled.
8. Run `git diff --check`, inspect the complete diff, and verify the changed-file allowlist before committing:

   ```powershell
   $allowed = @('requirements.txt','backend/requirements.txt','Dockerfile','.github/workflows/tests.yml','backend/persistence/__init__.py','backend/persistence/base.py','backend/persistence/database.py','backend/persistence/models/__init__.py','backend/identity/__init__.py','backend/identity/config.py','alembic.ini','migrations/env.py','migrations/script.py.mako','tests/unit/test_identity_config.py','tests/unit/test_database.py','tests/integration/conftest.py','tests/integration/test_database_foundation.py')
   $changed = @((git diff --name-only), (git diff --cached --name-only), (git ls-files --others --exclude-standard)) | Sort-Object -Unique
   $unexpected = $changed | Where-Object { $_ -notin $allowed -and $_ -notlike '.superpowers/*' }
   if ($unexpected) { $unexpected; throw 'Changed-file allowlist violation.' }
   git diff --check
   $taskChanged = @($changed | Where-Object { $_ -in $allowed })
   if (-not $taskChanged) { throw 'No allowlisted task changes to stage.' }
   git add -A -- $taskChanged
   $staged = @(git diff --cached --name-only) | Sort-Object -Unique
   $unexpectedStaged = $staged | Where-Object { $_ -notin $allowed }
   if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
   git diff --cached --name-status
   git diff --cached --check
   ```

## Security, privacy, and non-goals

Use fictional-only database names and fixtures. Never use production ADC, production Cloud SQL, real staff data, PINs, tokens, employee numbers, field notes, report narrative, or inmate identifiers. This task adds no request logging or application telemetry; ID-02 exclusively owns the later exact privacy-safe `request_event` contract, so do not create a competing event or log raw exception text here. Do not build identity models, authentication routes, application migrations, report persistence, Access UI, infrastructure, or deployments. Do not refactor unrelated Flask behavior.

## Acceptance checklist

- [ ] Red tests failed for the planned missing modules before implementation.
- [ ] Disabled identity boots without database secrets; enabled identity validates every required value safely.
- [ ] Session lifecycle commits on success and rolls back/closes on failure.
- [ ] Alembic is explicit, credential-free in source, UTC, reversible at the empty foundation, and not invoked by Flask startup.
- [ ] PostgreSQL fixtures expose only the four approved base fixture names and never use SQLite.
- [ ] CI and Docker changes match the supported runtimes and deployed dependency source.
- [ ] Focused, available integration, and legacy regression commands have the expected outcomes.
- [ ] `git diff --check` and the changed-file allowlist pass.
- [ ] No secrets or sensitive data appear in code, tests, logs, artifacts, or commit text.

## Commit and handoff

Commit exactly once with:

```powershell
git commit -m "chore(identity): add database and migration foundation"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Return this handoff:

```text
Task: ID-01
Branch: claude/id-01-database-alembic
Starting HEAD and baseline ancestry: reported
Commit: SHA and exact subject
Files changed: complete list
Red test: command and observed failure
Green tests: commands and results, including any PostgreSQL skip
Security review: database URL/log/fixture findings
Plan deviations: none, or exact reviewed reason
Residual risks or follow-ups: concise list
```

Stop immediately if the baseline is not an ancestor, prerequisites are absent, unrelated work is dirty, an allowed-file expansion is needed, a test would touch a nondedicated database, a secret/production resource is required, or the plan conflicts with newer reviewed instructions. Never push, merge, deploy, apply Terraform, sign, publish, alter secrets, access production, delete data/resources, use destructive Git commands, or modify `.superpowers/`.
