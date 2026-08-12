# Sequence 007 — ID-06: Bearer Middleware, Declarative Roles, Transactional Audit, Idempotency, and Identity-Aware Rate Limits

Copy everything below into a fresh Claude Code session.

---

Implement exactly ID-06, “Bearer Middleware, Declarative Roles, Transactional Audit, Idempotency, and Identity-Aware Rate Limits.” Use TDD, create one focused commit, hand off, and stop before Admin APIs.

## Objective and outcome

Resolve immutable actors from live hashed bearer sessions, add declarative authorization, concrete transaction-bound audit insertion, shared idempotency records/services, persistent privacy-preserving authentication rate limits, and protected self/session/PIN routes. This is the security enforcement layer used by every later API mutation; it must reject client-supplied identity and roll back protected changes if idempotency/audit fails.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-06-bearer-audit-idempotency`
- Required predecessor: `feat(identity): add rotating opaque sessions` and all earlier identity commits.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "feat(identity): add rotating opaque sessions"
git switch -c claude/id-06-bearer-audit-idempotency
```

Require clean tracked/index state before branching from current reviewed `main`; only existing untracked `.superpowers/` may remain and must not be touched/staged. Read and confirm review of intervening plan/spec/prerequisite changes when main advanced; baseline remains an ancestor. Stop for conflicts. Never reset/stash/clean user work. Create the branch from current HEAD without force.

## Required reading

- `AGENTS.md`; roadmap Actor/ApiError/auth guards/shared HTTP/idempotency/error rules.
- Identity plan exact ID-06 section including migration, services, decorators, routes, tests, and rate-limit dimensions.
- Identity/master specs.
- Consume-only ID-02 context/envelopes/client policy, ID-03 schema/audit function, ID-04 accounts, ID-05 sessions/auth/fixtures, and current migration chain.

## Exact allowed files

- Modify: `backend/identity/audit.py`
- Create: `backend/identity/idempotency.py`
- Create: `backend/identity/rate_limits.py`
- Modify: `backend/persistence/models/security.py`
- Create: `backend/webapp/api_v1/middleware.py`
- Modify: `backend/webapp/api_v1/auth.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `backend/webapp/api_v1/client_policy.py`
- Modify: `openapi/access-v1.yaml`
- Create: `migrations/versions/20260812_0002_identity_security_controls.py`
- Create: `tests/unit/test_auth_middleware.py`
- Create: `tests/unit/test_role_authorization.py`
- Create: `tests/unit/test_audit_writer.py`
- Create: `tests/unit/test_identity_idempotency.py`
- Create: `tests/unit/test_auth_rate_limits.py`
- Create: `tests/integration/test_bearer_isolation.py`
- Create: `tests/integration/test_audit_transactions.py`
- Create: `tests/integration/test_identity_idempotency.py`
- Create: `tests/integration/test_auth_rate_limits.py`

Consume-only: all prerequisites/plans/specs/models/services/tests not listed. Do not alter the ID-03 audit function/trigger migration, session schema, Admin/report routes, legacy auth, docs, or requirements.

## Locked interfaces and cross-plan rules

- Produce frozen `Actor(account_id, staff_member_id, session_id, role, auth_version, must_change_pin)`, `current_actor()`, `require_access_token`, `require_role("admin")`, `require_pin_changed`, `PostgresAuditWriter.append()`, `IdempotencyClaim`, `claim_idempotency()`, `complete_idempotency()`, `consume_limit()`, and exact protected routes.
- Bearer resolution uses only token digest/live DB state; ignore JSON identity/role/employee fields. Validate access expiry, revocation, active account, and exact `auth_version`. Missing/malformed/expired/revoked/unknown share `401 authentication_required`; DB unavailable is safe `503 dependency_unavailable`.
- Put only `Actor` on Flask `g`, never raw bearer text. Request-owned session closes during blueprint teardown.
- `must_change_pin` may call only `/api/v1/me`, change PIN, logout, logout-all, and renew.
- Extend typed audit input with nullable actor/client and already-HMACed device/network values; never raw values. ID-03 remains sole owner of database audit function. Protected mutation and audit commit/rollback together.
- Migration exactly `20260812_0002`, predecessor `20260812_0001`, creates only `idempotency_records`; do not recreate audit objects.
- Idempotency keys match `[A-Za-z0-9._:-]{8,128}` and uniqueness is actor/action/key. Same key+same canonical request returns durable stable response reference; changed request is `409 idempotency_conflict`; failed transaction leaves no record. Response reference never stores one-time PIN/token or sensitive bodies.
- Rate limits use HMAC subject hashes for normalized employee/device/network dimensions, row locks, bounded windows, safe `429 rate_limited`, and no raw identifiers.
- Add exactly POST logout/logout-all/change-pin, GET sessions, DELETE session by UUID, and GET me. Every mutation requires compatible client and `Idempotency-Key`. Closed bodies; no identity fields. `/me` returns safe profile/must-change state only.
- Preserve cookie/bearer isolation and exact standard envelopes/OpenAPI.

## TDD procedure

1. Add all five unit and four integration files first, covering bearer parsing/live checks, immutable actor, role/PIN guard, concrete audit, idempotency replay/conflict/rollback, rate-limit dimensions, cookie isolation, and protected routes.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_auth_middleware.py tests/unit/test_role_authorization.py tests/unit/test_audit_writer.py tests/unit/test_identity_idempotency.py tests/unit/test_auth_rate_limits.py -q
   ```

   Expected: collection fails because middleware, concrete audit writer, idempotency, and rate limiter are absent; protected endpoints are absent.
3. Implement concrete audit adapter without replacing ID-03 DB enforcement; then migration/model and transactional idempotency; then HMAC-backed rate limits.
4. Implement Actor resolution/decorators with exact error behavior and teardown. Add protected self/session/PIN routes using same-transaction idempotency+mutation+audit.
5. With dedicated test PostgreSQL, run:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m pytest tests/integration/test_bearer_isolation.py tests/integration/test_audit_transactions.py tests/integration/test_identity_idempotency.py tests/integration/test_auth_rate_limits.py -q
   ```

   Expected: cross-auth isolation, forged identity ignored, all invalid token states, replay/conflict, shared-network limits, and audit rollback pass. Stop if no dedicated DB; never use SQLite/production.
6. Run final focused/legacy/contracts:

   ```powershell
   python -m pytest tests/unit/test_auth_middleware.py tests/unit/test_role_authorization.py tests/unit/test_audit_writer.py tests/unit/test_identity_idempotency.py tests/unit/test_auth_rate_limits.py -q
   python -m pytest tests/unit/test_access_code_config.py tests/unit/test_admin_tier.py tests/unit/test_safe_next.py -q
   python -m pytest tests/contract/test_auth_contract.py tests/contract/test_access_v1_openapi.py -q
   ```

   Expected: all pass; legacy cookies remain intact but cannot satisfy bearer middleware.
7. Review for raw identifiers/tokens, migration scope, OpenAPI security, `git diff --check`, and exact allowlist:

   ```powershell
   $allowed=@('backend/identity/audit.py','backend/identity/idempotency.py','backend/identity/rate_limits.py','backend/persistence/models/security.py','backend/webapp/api_v1/middleware.py','backend/webapp/api_v1/auth.py','backend/webapp/api_v1/__init__.py','backend/webapp/api_v1/client_policy.py','openapi/access-v1.yaml','migrations/versions/20260812_0002_identity_security_controls.py','tests/unit/test_auth_middleware.py','tests/unit/test_role_authorization.py','tests/unit/test_audit_writer.py','tests/unit/test_identity_idempotency.py','tests/unit/test_auth_rate_limits.py','tests/integration/test_bearer_isolation.py','tests/integration/test_audit_transactions.py','tests/integration/test_identity_idempotency.py','tests/integration/test_auth_rate_limits.py')
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

Fictional tests only; no Google calls. Logs/audit/idempotency must exclude readable employee number, PIN, token, device ID, IP/network, field notes/report/inmate data, raw body, or auth header. Do not implement Admin elevation, staff/account admin APIs, reports, Access, infra, or alternate auth. Acceptance requires red-first evidence; exact Actor/decorators/errors; transactional audit/idempotency; migration limited to idempotency; rate-limit privacy; protected route/OpenAPI contract; all available tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat(identity): enforce bearer auth audit and rate limits"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff full branch/start/baseline/commit/files/red/green/migration/audit/idempotency/rate-limit/security/deviation/risk evidence. Stop for ancestry/prerequisite/dirt, missing dedicated DB, migration conflict, allowlist expansion, secret/prod need, or reviewed contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
