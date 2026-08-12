# Sequence 005 — ID-04: PIN Policy, Account Lifecycle, Temporary PINs, and Lockout

Copy everything below into a fresh Claude Code session at the repository root.

---

Implement exactly ID-04, “PIN Policy, Account Lifecycle, Temporary PINs, and Lockout.” Follow TDD, make one focused commit, hand off, and stop before session/token work.

## Objective and rationale

Implement the exact 4–8 character case-insensitive PIN policy, Argon2id protection, one-time temporary PIN creation, generic credential failure behavior, serialized account verification/lock cycles, safe unlock/reset helpers, transactional account-created audit, and the fail-closed service used to create the first Admin. The outcome gives each employee an individual account without making employee numbers secrets, leaking whether an account exists, leaving plaintext credentials recoverable, or creating a reusable unauthenticated enrollment path.

## Root, baseline, branch, and prerequisites

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-04-pin-account-lifecycle`
- Required predecessors: exact subjects `feat(identity): add identity schema and roster import`, `feat(api): add versioned Access API foundation`, and earlier foundation commit.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "feat(identity): add identity schema and roster import"
git switch -c claude/id-04-pin-account-lifecycle
```

Tracked/index state must be clean before branching from current reviewed `main`. Only existing untracked `.superpowers/` may remain and must not be touched/staged. Stop rather than reset/stash/clean user work. If reviewed main advanced, read and confirm review of intervening plan/spec/prerequisite updates and retain baseline ancestry; stop for conflicts. Create the branch from current HEAD without force.

## Required reading

- `AGENTS.md`; roadmap global constraints/shared interfaces/error rules.
- Identity plan exact ID-04 section and all its code/test examples.
- Approved identity/master specs.
- Consume-only ID-03 account model, normalization/audit protocols, database transaction helper, and existing shared-code config/tests.

## Exact allowed files

- Modify: `backend/persistence/models/identity.py`
- Modify: `backend/identity/audit.py`
- Create: `backend/identity/errors.py`
- Create: `backend/identity/pins.py`
- Create: `backend/identity/accounts.py`
- Create: `tests/unit/test_pin_policy.py`
- Create: `tests/unit/test_account_lifecycle.py`
- Create: `tests/unit/test_lockout.py`
- Create: `tests/integration/test_account_creation.py`

Consume-only: every required-reading/prerequisite file not above. Do not edit migration, API, OpenAPI, roster, requirements, docs, or legacy auth files.

## Locked behavior and interfaces

- Consume `StaffMember`, `Account`, `normalize_employee_number()`, `AuditWriter`, SQLAlchemy `Session`, and injected UTC clock.
- Produce `PinPolicyError`, `InvalidCredentials`, `InitialAdminBootstrapRefused`, `TemporaryPinResult`, `normalize_pin()`, `validate_new_pin()`, `hash_pin()`, `verify_pin()`, `needs_rehash()`, `generate_temporary_pin()`, `create_account()`, `bootstrap_first_admin(session: Session, *, staff_member_id: UUID, now: datetime, audit_writer: AuditWriter, operation_id: UUID, approval_reference_sha256: str) -> TemporaryPinResult`, `verify_login_pin()`, `reset_failed_attempts()`, and `unlock_account()` with exact task signatures.
- PINs are strings: ASCII alphanumeric only, 4–8 chars, letters uppercase, leading zeroes preserved. Reject PIN equal to normalized employee number and repeated/sequential ascending/descending patterns including numeric and alphabetic examples in the plan. `validate_new_pin()` returns the normalized PIN for immediate request-local use only.
- Argon2id is exactly 64 MiB, 3 iterations, parallelism 1, 16-byte random salt, 32-byte hash. Unknown account verification performs one check against a process-local dummy hash.
- Externally exposed unknown employee, wrong PIN, inactive/deactivated, locked, and expired temporary PIN all use `InvalidCredentials("The employee number or PIN is invalid.")` and stable `invalid_credentials`; do not enumerate status.
- Lock after five failures. Lock cycle durations are 15, 30, 60, then double to a 1,440-minute cap. Expiry starts a new five-attempt cycle while retaining cycle count; success resets attempts and cycle.
- Temporary PIN uses cryptographic randomness, plaintext lives only in `TemporaryPinResult`, returns once, must be changed on first use, expires exactly as planned, and is never retrievable from DB/log/audit.
- `create_account` row-locks applicable staff/account state, prevents duplicates, persists only hash, writes the safe account-created audit with authenticated Admin IDs when supplied, and lets audit failure roll back account creation.
- `bootstrap_first_admin()` acquires PostgreSQL transaction-scoped advisory lock `6002266223756136276`, then succeeds only if the entire `Account` table has zero rows and the selected staff UUID exists and is active. It always creates role `admin`, generates the same random eight-character temporary PIN, forces change, and expires it after exactly 24 hours. It flushes but does not commit.
- Bootstrap validates a lowercase 64-hex external approval-reference SHA-256 and opaque operation UUID, then writes exactly one `system.initial_admin_bootstrapped` audit event in the same transaction. Both actor IDs are null only for this action; details are exactly `operation_id` and `approval_reference_sha256`. Update `backend.identity.audit` validation so unknown `auth.login_failed` remains the only other both-null actor case and every other event requires both actor IDs.
- If any account already exists, staff is absent/inactive, approval hash is invalid, or the audit append fails, no bootstrap success is returned. Audit/account failure rolls back atomically; after any account exists every later bootstrap raises `InitialAdminBootstrapRefused` without generating a PIN or changing data. Concurrent attempts create at most one account.

## TDD procedure

1. Add PIN/Argon2 tests first, then account lifecycle/lock/bootstrap tests, matching every exact case in the plan including leading zeroes, case normalization, invalid patterns, hash variability/verification, dummy path, clock boundaries, bootstrap approval-hash validation, active staff, zero-account refusal, null-actor audit validation, concurrency, and rollback.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_pin_policy.py tests/unit/test_account_lifecycle.py tests/unit/test_lockout.py -q
   ```

   Expected: failure because `backend.identity.pins`, `backend.identity.accounts`, and their exceptions do not exist.
3. Implement normalization/policy/hashing/temp generation without logging or retaining plaintext. Keep hashing concurrency concerns documented but do not add infrastructure.
4. Implement account creation and row-locked verification/lock transitions using injected clock and generic external errors. Implement the exact advisory-locked first-Admin service and audit exception. Ensure each audit and state mutation shares the caller-owned transaction; do not add a route, job, command, secret, or workflow here.
5. With a dedicated `TEST_DATABASE_URL`, run integration:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m pytest tests/integration/test_account_creation.py -q
   ```

   Expected: ordinary/first-Admin creation, safe audit, advisory-lock concurrency, permanent post-first-account refusal, lock transitions, and rollback pass; no plaintext PIN can be selected. Stop if the dedicated DB is absent; never use SQLite or production.
6. Run green and legacy regressions:

   ```powershell
   python -m pytest tests/unit/test_pin_policy.py tests/unit/test_account_lifecycle.py tests/unit/test_lockout.py -q
   python -m pytest tests/unit/test_access_code_config.py tests/unit/test_admin_tier.py -q
   ```

   Expected: all pass and legacy shared codes/routes are unchanged.
7. Inspect for plaintext leakage, run `git diff --check`, and enforce:

   ```powershell
   rg -n "print\(|logger\.|temporary_pin|pin_hash|approval_reference" backend/identity tests/unit/test_pin_policy.py tests/unit/test_account_lifecycle.py tests/unit/test_lockout.py tests/integration/test_account_creation.py
   $allowed=@('backend/persistence/models/identity.py','backend/identity/audit.py','backend/identity/errors.py','backend/identity/pins.py','backend/identity/accounts.py','tests/unit/test_pin_policy.py','tests/unit/test_account_lifecycle.py','tests/unit/test_lockout.py','tests/integration/test_account_creation.py')
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

Review each grep hit manually; names in private implementation/tests are not by themselves leakage, but values must never be printed/logged/persisted/audited.

## Security, non-goals, and acceptance

Use fictional test accounts, operation UUIDs, and approval hashes only. Never use real employee numbers, approval references, or readable production credentials. Do not add routes, sessions, bearer tokens, elevation, Admin UI, reports, infrastructure, jobs, workflows, secrets, or migrations. Acceptance: red-first evidence; exact policy and Argon2 parameters; constant-shape credential failures; tested row locking/lock cycles; advisory-locked zero-account bootstrap; active-staff/Admin-only/24-hour forced-change rules; at-most-one concurrency; safe null-actor system audit; one-time temp PIN; atomic audit rollback; all focused/available integration/legacy tests pass; allowlist and whitespace pass; no plaintext leakage.

## Commit and handoff

```powershell
git commit -m "feat(identity): enforce pin and account lifecycle"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff: task/branch, starting SHA/baseline ancestry, commit SHA/subject, exact changed files, red evidence, green/integration results, Argon2/PIN/leak review, deviations, remaining risks. Stop for ancestry/prerequisite/dirty-tree issues, absent dedicated DB before DB tests, interface conflict, allowlist expansion, unexpected legacy regression, or secret/production need. Never push, merge, deploy, apply, sign, publish, change secrets, access production, delete resources/data, destructive-Git, or touch `.superpowers/`.
