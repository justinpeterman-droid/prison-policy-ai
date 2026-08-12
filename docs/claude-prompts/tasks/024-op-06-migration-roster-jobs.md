# Claude Code Prompt 024 — OP-06: Package Alembic Migration and Roster Import as Dedicated Cloud Run Jobs

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **024**, task **OP-06: Package Alembic Migration and Roster Import as Dedicated Cloud Run Jobs**.

## Objective, outcome, and rationale

Add deterministic, locally testable, noninteractive migration, roster-import, and one-time initial-Admin bootstrap entry points, package their assets in the backend image, and define dedicated Cloud Run jobs that precede dependent traffic. The implementation must reject ambiguous/changed roster data, expose no production downgrade, make first-Admin creation impossible after any account exists, log only safe status/count/code/reference values, and never execute a cloud job, change a secret, or use real roster/account data during this task.

## Repository, baseline, and branch

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-06-migration-roster-jobs`
- Commit: `feat: add controlled migration and roster import jobs`

Run this preflight before recording the task start or creating the branch:

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The baseline must be an ancestor of current reviewed `main`. When `HEAD` advanced, inspect `git log --oneline $TaskBase..HEAD` plus predecessor plans/handoffs and verify every commit is reviewed, required ID/RP and OP-01 through OP-05 outputs exist, and no conflict exists. Create `claude/op-06-migration-roster-jobs` from current `HEAD`. Stop on failed ancestry/review/prerequisites, existing branch, or dirty overlap/unsafe switching. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; approved deployment design; roadmap global constraints/shared Python interfaces/program gates/agent protocol; identity/report Alembic/database/staff contracts; ID-04 `bootstrap_first_admin()` and audit contract; OP-03 migration/bootstrap identities, WIF, and secret resources; OP-04 digest/service/private request-prefix contract; and the detailed plan from the exact OP-06 heading to the OP-07 separator. Inspect `alembic.ini`, `migrations/env.py`, every committed migration, `backend.persistence.database.session_scope()`, `backend.identity.normalization.normalize_employee_number`, identity staff/account services, current roster importer, and Dockerfile. Those are consume-only unless explicitly allowed below.

## Exact allowed files

Create only:

- `backend/jobs/migration.py`
- `backend/jobs/roster_import.py`
- `backend/jobs/admin_bootstrap.py`
- `scripts/verify_migration.py`
- `migrations/MIGRATION_REGISTER.md`
- `infra/terraform/modules/access_platform/jobs.tf`
- `tests/unit/test_roster_import_job.py`
- `tests/unit/test_admin_bootstrap_job.py`
- `tests/integration/test_deployment_migrations.py`
- `tests/integration/test_admin_bootstrap_job.py`
- `docs/runbooks/database-migration-and-roster-import.md`
- `docs/runbooks/initial-admin-enrollment.md`

Modify only:

- `scripts/import_roster_to_postgres.py`
- `Dockerfile`
- `infra/terraform/modules/access_platform/variables.tf`
- `infra/terraform/modules/access_platform/outputs.tf`
- `infra/terraform/environments/test/main.tf`
- `infra/terraform/environments/production/main.tf`
- `infra/terraform/tests/access_platform.tftest.hcl`

No deletion is authorized. `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/*.py`, identity/report modules, and source roster content are consume-only.

## Locked interfaces

- Migration CLI: `python -m backend.jobs.migration upgrade` and `python -m backend.jobs.migration verify`; production entry point exposes no downgrade.
- Python signatures exactly:
  - `upgrade() -> str`
  - `verify() -> dict[str, str]`
  - `main(argv: list[str] | None = None) -> int`
- Alembic Python API, exactly one head, structured JSON with only status/revision/duration, nonzero on failure.
- Immutable dataclasses `RosterFinding`, `RosterImportPlan`, and `RosterImportResult`; functions `build_roster_plan()` and `apply_roster_plan()`.
- CLI inputs exactly `--source-uri`, `--corrections-uri`, `--report-uri`, `--expected-sha256`, and opt-in `--apply`; omission of `--apply` is validation-only.
- Employee-number normalization uses the identity module. Valid shifts are only `A/B/C/D/U/F`. Reject missing IDs, duplicates after normalization, ambiguous mappings, invalid shifts, unapproved corrections, and source-hash mismatch. Never guess.
- Employee-number normalization imports exactly `normalize_employee_number` from `backend/identity/normalization.py` (`backend.identity.normalization.normalize_employee_number`), never from `backend.identity.config`.
- Preserve staff UUID on corrections; create new UUID only through identity service. Apply is one transaction and refuses any finding/hash mismatch.
- Detailed findings go only to the explicit private report URI. Logs/output contain counts, source hash, opaque finding codes, import run UUID, migration revision, request/operation ID—never names or employee numbers. Never log a temporary Admin PIN.
- `scripts/import_roster_to_postgres.py` is a thin wrapper over `backend.jobs.roster_import.main()`.
- Migration register covers every `alembic history` revision with ID, phase, duration, lock risk, old/new compatibility, rollback, verification query, and owner role. No same-release contract migration with a minimum-client increase.
- Docker image copies Alembic config/migrations, runs non-root, preserves command override, and excludes tests, Access sources, Terraform, release output, `.git`, and operational records.
- Bootstrap request object has exactly `schema_version: 1`, v4 `operation_id`, v4 `staff_member_id`, and bounded visible-ASCII `approval_reference`; no extras. CLI inputs are only `--request-uri` and `--expected-sha256`. URI is an opaque `gs://<private-configuration-bucket>/admin-bootstrap-requests/<operation-uuid>.json`; it and command line contain no staff UUID/name/employee number/approval reference/PIN. Verify lowercase 64-hex SHA-256 over exact bytes before parsing, max 4 KiB, exact bucket/prefix, and path UUID equals `operation_id`.
- Produce protocols `BootstrapRequestReader.read_exact(*, bucket: str, object_name: str, max_bytes: int) -> bytes` and `SecretVersionAdder.add_version(*, parent: str, payload: bytes) -> str`; exact signatures `load_bootstrap_request(storage_client: BootstrapRequestReader, *, request_uri: str, expected_sha256: str, expected_bucket: str, expected_prefix: str = "admin-bootstrap-requests/") -> AdminBootstrapRequest`, `execute_admin_bootstrap(session_factory: Callable[[], Session], secret_client: SecretVersionAdder, *, request: AdminBootstrapRequest, initial_admin_pin_secret: str, now: datetime) -> AdminBootstrapResult`, and `main(argv: list[str] | None = None) -> int`. `AdminBootstrapResult` fields are `operation_id: UUID`, `status: Literal["bootstrapped", "bootstrap_refused", "pin_version_add_failed", "pin_version_outcome_unknown_cleanup_required", "orphan_pin_version_cleanup_required"]`, `expires_at: datetime | None`, and `secret_version_reference: str | None`. JSON keys are exactly those four; reference is resource-relative `initial-admin-pin/versions/<numeric-version>`. Never return/log request URI/body, staff/account IDs, approval reference/hash, PIN, payload, project/bucket, or raw exception.
- Transaction ordering is mandatory: open PostgreSQL transaction; call ID-04 to advisory-lock and flush the one Admin plus `system.initial_admin_bootstrapped`; while still uncommitted pass plaintext PIN directly to `initial-admin-pin` add-version; only after a version resource name is definitively returned commit DB. The adapter makes one non-idempotent add RPC with `retry=None` and `timeout=10.0`, validates the returned name against the configured parent/numeric version, and never repeats it. Deterministic add rejection rolls back and returns `pin_version_add_failed`; ambiguous timeout/cancellation/transport loss rolls back and returns `pin_version_outcome_unknown_cleanup_required` with null version reference; commit failure after a known version returns `orphan_pin_version_cleanup_required` plus only that safe resource-relative name. Ambiguous/orphan cases block retry until custodian metadata reconciliation, disable/destruction, and external evidence. No PIN can authenticate because no Account committed. No automatic retry.
- Cloud Run jobs exactly `access-{environment}-migrate`, `access-{environment}-roster-import`, and `access-{environment}-bootstrap-admin`, all using the API/worker digest. First two use migration identity; bootstrap uses OP-03 bootstrap runtime. Only OP-03 `admin-bootstrap` workflow identity receives invoker on the bootstrap job. Jobs are not scheduled/public/application-invoked.
- Verification compares DB revision to single code head and checks expected tables/indexes/constraints through SQLAlchemy without row content.

## TDD and validation

1. Create `tests/unit/test_roster_import_job.py` from OP-06 Step 1 with fictional `FX-100`/`FX-200` rows.
2. Create the PostgreSQL 17 lifecycle test from Step 2: upgrade, one head/core tables, fictional inserts through services, idempotent upgrade, only supported non-destructive isolated downgrade, and no production downgrade command.
3. Create the exact bootstrap unit/integration tests from OP-06 Step 3 before implementation. Unit tests cover URI/prefix/size/hash/schema/path UUID, CLI/body separation, closed output, and redaction. PostgreSQL integration covers active/absent/inactive/existing account, concurrency, safe audit, deterministic Secret Manager add rejection, injected outcome-ambiguous timeout with null reference, DB commit-after-known-version failure, non-authenticating PIN, and retry-blocking cleanup status.
4. Run red tests:

```powershell
python -m pytest tests/unit/test_roster_import_job.py -q
python -m pytest tests/integration/test_deployment_migrations.py -q
python -m pytest tests/unit/test_admin_bootstrap_job.py tests/integration/test_admin_bootstrap_job.py -q
```

Expected: unit collection fails because `backend.jobs.roster_import` and `backend.jobs.admin_bootstrap` are absent; integration fails because deployment migration/bootstrap entry points are absent. Diagnose unrelated fixture/environment errors rather than claiming red.
5. Implement in detailed-plan order. Keep plaintext PIN request-local, add the secret version before DB commit, erase references after add-version, and implement the exact definitive-failure/ambiguous-timeout/known-orphan statuses. Every output/log is status + operation ID and only a definitively returned non-secret version resource name. Create both runbooks and all three private jobs. Then run:

```powershell
python -m pytest tests/unit/test_roster_import_job.py -q
python -m pytest tests/integration/test_deployment_migrations.py -q
python -m pytest tests/unit/test_admin_bootstrap_job.py tests/integration/test_admin_bootstrap_job.py -q
python -m pytest tests/unit tests/integration -q
docker build --tag prison-policy-ai:op06-local .
docker run --rm --entrypoint python prison-policy-ai:op06-local -m backend.jobs.migration --help
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
git diff --check
```

Expected: PostgreSQL 17 tests including transaction/secret ordering, image/help, Terraform mocked-job assertions, and regressions pass. No Google job or Secret Manager operation runs.

## External gates and local-only boundary

Required upstream migrations must be one reviewed linear head. Real source/corrections/report/bootstrap URIs, approved hashes, roster corrections, EXT-12 request/PIN custodians and cleanup evidence, production migration review/lock budget/backups, and protected approval are external. Tests use only fictional rows and isolated PostgreSQL plus fake GCS/Secret Manager clients. Do not invoke import `--apply` against operational data, run migration/bootstrap against any shared/test/production cloud DB, invoke Cloud Run jobs, add/read/disable/destroy a real secret version, upload/download GCS data, or authenticate to Google.

## Security/privacy and non-goals

Never log/store real names, employee numbers, shifts, approval references, PINs, roster/request rows, DB URLs, tokens, report data, or secret values. Do not invent corrections or import historical Word documents. Do not modify schema revisions, identity/report behavior, deployment workflows, or cloud infrastructure outside exact job wiring. Do not add production downgrade, an account-creation route, a bootstrap retry loop, or secret read permission. Do not push, merge, deploy, apply/destroy Terraform, run migration/roster/bootstrap operations against cloud/real data, sign, publish, change secrets, access production, or perform destructive Git/filesystem actions.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Both named red states observed first.
- [ ] Migration CLI has only upgrade/verify and rejects multiple heads.
- [ ] Roster planning is deterministic, validation-first, hash-bound, and no-guess.
- [ ] Apply is opt-in, one transaction, and logs only safe metadata.
- [ ] Every current migration has complete operational metadata.
- [ ] Image contains Alembic assets, runs non-root, and excludes forbidden sources.
- [ ] Migration and roster-import jobs share the immutable image and are private/unscheduled.
- [ ] Third exact bootstrap job uses bootstrap runtime and only admin-bootstrap workflow invocation; no broader role exists.
- [ ] Exact private request/hash/schema and ID-04 zero-account active-staff Admin contract are enforced.
- [ ] Secret version is added before DB commit; deterministic add failure, ambiguous timeout, and commit-after-known-version failure are separately tested with exact safe status/reference behavior and no authenticating account.
- [ ] Success/orphan PIN custodian retrieval, immediate disable, post-forced-change destruction, missing-result reconciliation, enrollment-incident, and no-retry procedures are complete and external.
- [ ] Local unit/integration/image/Terraform checks pass with fictional data only.
- [ ] Only exact allowed paths changed and exact one-commit message used.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; inspect the complete task diff and test output for roster values, identifiers, secrets, downgrade/public/schedule behavior. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'backend/jobs/migration.py'
    'backend/jobs/roster_import.py'
    'backend/jobs/admin_bootstrap.py'
    'scripts/verify_migration.py'
    'migrations/MIGRATION_REGISTER.md'
    'infra/terraform/modules/access_platform/jobs.tf'
    'tests/unit/test_roster_import_job.py'
    'tests/unit/test_admin_bootstrap_job.py'
    'tests/integration/test_deployment_migrations.py'
    'tests/integration/test_admin_bootstrap_job.py'
    'docs/runbooks/database-migration-and-roster-import.md'
    'docs/runbooks/initial-admin-enrollment.md'
    'scripts/import_roster_to_postgres.py'
    'Dockerfile'
    'infra/terraform/modules/access_platform/variables.tf'
    'infra/terraform/modules/access_platform/outputs.tf'
    'infra/terraform/environments/test/main.tf'
    'infra/terraform/environments/production/main.tf'
    'infra/terraform/tests/access_platform.tftest.hcl'
)
$changed = @(
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
) | Sort-Object -Unique
$unexpected = $changed | Where-Object { $_ -notin $allowed -and $_ -notlike '.superpowers/*' }
if ($unexpected) { $unexpected; throw 'Changed-file allowlist violation.' }
git diff --name-status $TaskStart
git diff --check
git add -A -- $allowed
$staged = @(git diff --cached --name-only) | Sort-Object -Unique
$unexpectedStaged = $staged | Where-Object { $_ -notin $allowed }
if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
git diff --cached --name-status
git diff --cached --check
git commit -m "feat: add controlled migration and roster import jobs"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including migration head/register, roster, image, bootstrap request/output/transaction ordering, secret failure/orphan cleanup, and all three job contracts; security/privacy results plus no-cloud/no-real-data/no-real-secret confirmation; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, bootstrapped, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production. Independent specification review precedes code-quality review.

Stop without committing if migrations are nonlinear/destructive, roster ambiguity exists, an upstream API is absent, real data/credentials are needed, safe logging cannot be guaranteed, or any prohibited operation would be necessary. Never weaken validation or fabricate corrections.
