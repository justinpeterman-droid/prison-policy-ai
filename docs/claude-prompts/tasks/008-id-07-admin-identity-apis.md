# Sequence 008 — ID-07: Admin Staff, Account, Session APIs, Elevation, and Purpose-Scoped Step-Up

Copy everything below into a fresh Claude Code session.

---

Implement only ID-07, “Admin Staff, Account, Session APIs, Elevation, and Purpose-Scoped Step-Up.” Work test-first, produce one focused commit, hand off, and stop before browser handoff.

## Objective and outcome

Add server-side 15-minute-inactivity Admin Center elevation, five-minute single-use purpose tokens, last-active-Admin safeguards, bounded staff/account/session management, one-time account/reset PIN responses, and exact Admin API/OpenAPI contracts. Persistent Admin sign-in remains allowed, but no sensitive Admin mutation succeeds solely because a renewal session persisted.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-07-admin-elevation-accounts`
- Required predecessor: `feat(identity): enforce bearer auth audit and rate limits`.

Run baseline/clean/prerequisite checks:

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "feat(identity): enforce bearer auth audit and rate limits"
git switch -c claude/id-07-admin-elevation-accounts
```

Tracked/index state must be clean before branching from current reviewed `main`; only pre-existing untracked `.superpowers/` may remain and is untouchable. Read and confirm review of intervening plan/spec/prerequisite changes when main advanced; stop for conflicts. Never reset/stash/clean user work. Create the branch from current HEAD without force; stop on collision.

## Required reading

- `AGENTS.md`; roadmap auth/Admin wire contracts and stable errors.
- Identity plan exact ID-07 section, especially purpose list, one-time response union, session-list/revoke shapes, service locking, fixtures, and tests.
- Approved identity/admin/master specs.
- Consume-only ID-04 account lifecycle, ID-05 sessions, ID-06 Actor/middleware/idempotency/audit, existing schema/cursors/OpenAPI.

## Exact allowed files

- Modify: `backend/identity/accounts.py`
- Create: `backend/identity/elevation.py`
- Create: `backend/webapp/api_v1/admin.py`
- Modify: `backend/webapp/api_v1/auth.py`
- Modify: `backend/webapp/api_v1/middleware.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_admin_elevation.py`
- Create: `tests/unit/test_admin_account_service.py`
- Create: `tests/unit/test_last_admin.py`
- Create: `tests/unit/test_admin_pagination.py`
- Create: `tests/integration/test_admin_api.py`
- Create: `tests/integration/test_admin_step_up.py`
- Create: `tests/integration/test_admin_session_revocation.py`
- Create: `tests/contract/test_admin_contract.py`

Consume-only: all prerequisite modules/models/migrations/plans/specs/tests not listed. No schema/migration changes, report APIs, Review Lab, README, plans, or deployment files.

## Locked interfaces and exact wire rules

- Produce `ElevationResult`, `confirm_admin_pin()`, `require_admin_elevation`, `require_step_up(purpose)`, `consume_step_up()`, and bounded Admin services/routes.
- `POST /api/v1/auth/admin-step-up` accepts exactly PIN+purpose, Admin bearer, compatible client, and idempotency. It is the only Admin mutation not requiring pre-existing elevation/action token. `admin_center` returns refreshed expiry and no action token. Sensitive purpose confirms PIN, refreshes elevation, returns one raw five-minute token once, stores only digest.
- Exact purposes: `staff_write`, `account_create`, `account_role_status`, `account_reset_pin`, `account_unlock`, `account_revoke_sessions`, `report_restore`, `report_transfer`, `bulk_export`, `audit_export`, `review_lab_handoff`.
- `X-Admin-Step-Up` is the only action-token header. Token must match session+exact purpose and be consumed in the same transaction as mutation/idempotency/audit. Missing/expired/replayed/wrong-purpose/wrong-session is only `403 step_up_required`; `admin_step_up_required` is forbidden. Server-side absent/idle elevation is `403 admin_elevation_required`.
- Step-up idempotency hashes canonical session ID+purpose, never PIN. `admin_center` replay returns durable expiry; sensitive replay returns `409 idempotent_response_unavailable`, never token replay.
- Implement exact routes listed in the plan: auth admin-step-up; Admin staff list/create/patch; account list/create/patch/reset/unlock; account session list; account revoke-sessions. GET/list requires current elevation. Other mutations require matching purpose.
- Lists are signed-cursor `(created_at,id)`, default 50/max 100. Closed schemas; no client actor/role/authorization.
- Account create links one existing staff, writes one correctly attributed audit, returns temp PIN once. First create/reset response has `operation_reference_id`, `account_id`, `temporary_pin`, `one_time_value_unavailable:false`; identical-key replay omits PIN and sets true. OpenAPI closed `oneOf`, PIN `writeOnly`.
- Role/status values exact. Lock all active Admins before last-admin decision. Any role/status change increments auth version; role change/deactivation revokes live sessions. Reactivation restores no old session. Reset revokes/increments and makes 24-hour change-required temp PIN. Unlock clears lock state, leaves PIN unchanged.
- Account session list is bounded exact safe fields. Revoke body is exactly scope all or scope one+session ID; success exact IDs/count. Conceal foreign/nonexistent session 404; concurrency conflict `account_conflict`.
- Reserve exact errors from roadmap: duplicate employee, staff history, account exists, last active Admin, account conflict.

## TDD procedure

1. Add elevation/step-up tests first, then account/last-admin/pagination/revocation tests and OpenAPI contract tests. Include persistent Admin without elevation, idle expiry, wrong/replayed purposes, concurrent last-admin changes, one-time values, and transactional rollback.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_admin_elevation.py tests/unit/test_admin_account_service.py tests/unit/test_last_admin.py tests/unit/test_admin_pagination.py -q
   ```

   Expected: failure because elevation/Admin routes are absent and account lifecycle lacks last-admin mutation methods.
3. Implement elevation and purpose credentials, then declarative guards. Decorator records only pending safe token state; mutation service consumes it transactionally.
4. Implement staff/account/session services, active-Admin locking, session revocation, safe one-time DTOs, and idempotency semantics.
5. Implement all exact routes/OpenAPI and add fresh fixtures for every exact-purpose step-up header, including report/export/audit/handoff consumers.
6. On dedicated test PostgreSQL, run:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m pytest tests/integration/test_admin_api.py tests/integration/test_admin_step_up.py tests/integration/test_admin_session_revocation.py -q
   python -m pytest tests/contract/test_admin_contract.py tests/contract/test_access_v1_openapi.py -q
   ```

   Expected: role denials, elevation idle timeout, purpose/replay/expiry, one-time PIN, last-admin, role/status revocation, unlock, pagination, session scopes, and audit attribution pass. Stop if no dedicated DB.
7. Run focused identity regressions:

   ```powershell
   python -m pytest tests/unit/test_admin_elevation.py tests/unit/test_admin_account_service.py tests/unit/test_last_admin.py tests/unit/test_admin_pagination.py -q
   python -m pytest tests/unit/test_pin_policy.py tests/unit/test_account_lifecycle.py tests/unit/test_session_service.py tests/unit/test_auth_middleware.py tests/unit/test_role_authorization.py -q
   ```

   Expected: all pass.
8. Review one-time response serialization/purpose checks, run `git diff --check`, enforce:

   ```powershell
   $allowed=@('backend/identity/accounts.py','backend/identity/elevation.py','backend/webapp/api_v1/admin.py','backend/webapp/api_v1/auth.py','backend/webapp/api_v1/middleware.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','tests/unit/test_admin_elevation.py','tests/unit/test_admin_account_service.py','tests/unit/test_last_admin.py','tests/unit/test_admin_pagination.py','tests/integration/test_admin_api.py','tests/integration/test_admin_step_up.py','tests/integration/test_admin_session_revocation.py','tests/contract/test_admin_contract.py')
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

Fictional identities/PINs/tokens only. Never log/store/echo readable PIN/action token, employee number, device/network, session hash, raw body, or report data. Do not add report operations, browser handoff, Access UI, infra, schema migration, deletion/merge, or elevation credential/header. Acceptance: red-first, exact elevation/purpose/idempotency semantics, last-admin concurrency protection, one-time values, exact route/shapes/errors, all tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat(identity): add admin APIs and purpose-scoped step-up"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff branch/start/baseline/commit/files/red/green/transaction/purpose/one-time/security/deviation/risk evidence. Stop for baseline/prerequisite/dirt, absent dedicated DB, contract conflict, allowed-file expansion, secret/production need, or unexpected regression. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
