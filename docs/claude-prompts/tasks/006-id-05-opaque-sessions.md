# Sequence 006 — ID-05: Opaque Access and Renewal Sessions, Rotation, Replay, Logout, and PIN Change

Copy everything below into a fresh Claude Code session opened at the repository root.

---

Implement only ID-05, “Opaque Access and Renewal Sessions, Rotation, Replay, Logout, and PIN Change.” Work test-first, make the exact focused commit, hand off, and stop before bearer middleware.

## Objective and outcome

Add cryptographically random opaque access/renewal credentials, hashed device binding, login issuance, serialized renewal rotation/replay-family revocation, session revocation, logout-all, PIN-change rotation, session listing, and the unauthenticated login/renew API contracts. This gives Access a safe 15-minute access token and either 12-hour in-memory or 30-day sliding persistent renewal without storing readable credentials in Cloud SQL.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-05-opaque-rotating-sessions`
- Required predecessor subject: `feat(identity): enforce pin and account lifecycle` (and all earlier ID commits).

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "feat(identity): enforce pin and account lifecycle"
git switch -c claude/id-05-opaque-rotating-sessions
```

Require clean tracked/index state before branching from current reviewed `main`. Existing untracked `.superpowers/` is user-owned and must remain untouched/unstaged; stop for any other dirt. If reviewed main advanced, inspect intervening reviewed plan/spec/prerequisite changes, confirm review, and require baseline ancestry; stop for conflicts. Never reset, clean, stash, overwrite, or discard user work. Create the branch from current HEAD without force.

## Required reading

- `AGENTS.md`; roadmap global/session/shared HTTP/locked auth rules.
- Identity plan exact ID-05 section, including complete service algorithms, tests, response DTOs, and OpenAPI schemas.
- Approved identity/master specs.
- Consume-only ID-03 session/account mappings, ID-04 PIN/accounts services, ID-02 envelopes/settings, audit protocol, and fixture contract.

## Exact allowed files

- Create: `backend/identity/tokens.py`
- Create: `backend/identity/sessions.py`
- Create: `backend/webapp/api_v1/auth.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_tokens.py`
- Create: `tests/unit/test_session_service.py`
- Create: `tests/unit/test_pin_change.py`
- Create: `tests/integration/identity_fixtures.py`
- Modify: `tests/integration/conftest.py`
- Create: `tests/integration/test_session_rotation.py`
- Create: `tests/integration/test_session_concurrency.py`
- Create: `tests/contract/test_auth_contract.py`

Consume-only: plans/specs, existing models/config/PIN/account/audit/API helpers and legacy routes. Do not edit models, migrations, middleware, Admin routes, requirements, README, plans, or legacy auth.

## Locked interfaces and invariants

- Produce `OpaqueCredential`, `SessionTokenPair`, `hash_token()`, `hash_device_id()`, `create_session()`, `login()`, `renew_session()`, `resolve_access_session()`, `revoke_session()`, `logout_all()`, `change_pin()`, and `list_sessions()` plus the exact shared fictional account/token/header fixtures.
- Credentials contain at least 256 random bits. Persist only SHA-256 digests. Hash device IDs with configured pepper after exact validation; device labels are bounded display metadata. No raw access, renewal, device ID, or PIN may enter DB/audit/log/exception.
- One `sessions` row is one renewal family/device session. Rotation row-locks it, moves the prior renewal digest to history, replaces hashes, and preserves replay history until expiry.
- Simultaneous renewal: one wins; the loser finds the digest in history, sets reuse detection, revokes the family, and gets `401 session_reauthentication_required`. Never issue two winners.
- Renewal checks digest, expiry, device hash, account active state, and exact `auth_version` before mutation. Persistent expiry slides 30 days; nonpersistent absolute expiry never exceeds 12 hours from creation. Access expiry is 15 minutes.
- `create_session()` returns the server-owned profile (`staff_id`, `employee_number`, `display_name`, `rank`, `shift`, `role`, `status`) plus `persistent` and `requires_pin_change`. Higher-level `login()` writes exactly one login audit in the same transaction; `create_session()` alone does not.
- PIN change validates current/new PIN, increments `auth_version`, revokes existing sessions, creates the replacement session, writes safe audit, and commits atomically.
- This task exposes only `POST /api/v1/auth/login` and `POST /api/v1/auth/renew`, both OpenAPI `security: []`, both requiring `X-Client-Version`; login accepts exactly employee number/PIN/device ID/device label/persistent, renewal exactly renewal token/device ID. Mark secret inputs `writeOnly` with nonfunctional examples.
- Auth errors use exact codes/statuses in the plan. Do not create bearer-protected auth routes; ID-06 owns them.

## TDD procedure

1. Add token/session/PIN-change unit tests first, including randomness/digests, no plaintext DTO persistence, TTLs, device mismatch, account/auth-version checks, rotation/replay, logout scopes, and replacement session.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_tokens.py tests/unit/test_session_service.py tests/unit/test_pin_change.py -q
   ```

   Expected: failure because `backend.identity.tokens` and `backend.identity.sessions` do not exist.
3. Implement credential/device primitives, safe return types, issuance, login, serialized renewal, replay-family revocation, revocation/listing, and PIN change exactly as the plan. Use row locks and injected time/randomness in tests.
4. Add only login/renew routes and authoritative OpenAPI operations, returning profile in the same response so Access needs no follow-up identity lookup.
5. Extend integration support with exact builders `seed_fictional_account`, `issue_fictional_tokens`, `bearer_headers` and fixtures `fictional_user_account`, `fictional_admin_account`, `fictional_user_tokens`, `fictional_admin_tokens`, `user_bearer_headers`, `admin_bearer_headers`. Do not create competing aliases.
6. On a dedicated test PostgreSQL database, run:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m pytest tests/integration/test_session_rotation.py tests/integration/test_session_concurrency.py -q
   python -m pytest tests/contract/test_auth_contract.py -q
   ```

   Expected: rotation/replay/device/expiry/status/auth-version/concurrent cases pass and rows contain no plaintext credential. Stop if the dedicated DB is absent; never substitute SQLite/production.
7. Run focused/API regressions:

   ```powershell
   python -m pytest tests/unit/test_tokens.py tests/unit/test_session_service.py tests/unit/test_pin_change.py -q
   python -m pytest tests/unit/test_api_v1_responses.py tests/unit/test_api_v1_isolation.py -q
   ```

   Expected: all pass.
8. Inspect credential boundaries, run `git diff --check`, and enforce:

   ```powershell
   $allowed=@('backend/identity/tokens.py','backend/identity/sessions.py','backend/webapp/api_v1/auth.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','tests/unit/test_tokens.py','tests/unit/test_session_service.py','tests/unit/test_pin_change.py','tests/integration/identity_fixtures.py','tests/integration/conftest.py','tests/integration/test_session_rotation.py','tests/integration/test_session_concurrency.py','tests/contract/test_auth_contract.py')
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

All identities/tokens are fictional and nonfunctional. No Google calls. Never log/echo/persist readable PIN/token/device ID or raw authorization input. Do not implement rate limits, bearer middleware, idempotency records, Admin elevation, reports, Access, or infra. Acceptance requires red-first evidence; exact TTL/rotation/replay behavior; one winner under concurrency; same-response profile; OpenAPI security isolation; shared fixtures; all available tests pass; no unexpected files/whitespace/sensitive leakage.

## Commit and handoff

```powershell
git commit -m "feat(identity): add rotating opaque sessions"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff task/branch/start SHA/ancestry/commit/files/red/green/concurrency/OpenAPI/sensitive-data/deviation/risk details. Stop for ancestry/prerequisite/dirty tree, absent dedicated DB before DB work, interface or migration conflict, allowlist expansion, secret/production need, or unexpected regression. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
