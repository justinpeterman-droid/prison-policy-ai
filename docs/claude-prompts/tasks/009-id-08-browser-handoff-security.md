# Sequence 009 — ID-08: Browser Handoff, Individual Browser Session, Review Lab Boundary, and Identity Security Verification

Copy everything below into a fresh Claude Code session.

---

Implement exactly ID-08, “Browser Handoff, Individual Browser Session, Review Lab Boundary, and Identity Security Verification.” Use TDD, make one focused commit, deliver the evidence handoff, and stop before RP-01.

## Objective and outcome

Provide a 60-second, single-use, fragment-delivered Admin handoff into an attributable 30-minute nonpersistent Review Lab browser session, while retaining the distinguishable legacy Admin-cookie pilot path and preventing every cookie/bearer cross-authentication. Complete the identity security, migration, logging, and Argon2 verification gate.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-08-review-lab-handoff`
- Required predecessor: `feat(identity): add admin APIs and purpose-scoped step-up`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "feat(identity): add admin APIs and purpose-scoped step-up"
git switch -c claude/id-08-review-lab-handoff
```

Require clean tracked/index state before branching from current reviewed `main`; ignore only existing untracked `.superpowers/`, never touch/stage it. Read and confirm review of intervening plan/spec/prerequisite changes; baseline must remain an ancestor. Stop for conflicts. Never reset/stash/clean/discard user work. Create the branch from current HEAD without force.

## Required reading

- `AGENTS.md`; roadmap cross-client client-policy/origin/auth/security rules and Gate A.
- Identity plan exact ID-08 section including landing HTML/JS skeleton, issue/redeem algorithms, route-boundary integration, complete test suite, benchmark and scans.
- Approved identity/Admin/master specs.
- Consume-only existing Review Lab routes/store/templates/JS behavior, legacy Admin gate, ID-05 opaque credentials, ID-06 Actor/audit, ID-07 elevation/step-up, client policy origin.

## Exact allowed files

- Modify: `backend/identity/elevation.py`
- Create: `backend/identity/browser_handoffs.py`
- Modify: `backend/webapp/api_v1/admin.py`
- Create: `backend/webapp/routes/browser_handoffs.py`
- Modify: `backend/webapp/routes/review_lab.py:21-136`
- Modify: `backend/webapp/routes/__init__.py`
- Modify: `backend/webapp/app.py:13-20,38-51,138-224`
- Create: `backend/webapp/templates/access_handoff.html`
- Create: `backend/webapp/static/js/access-handoff.js`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_browser_handoff_service.py`
- Create: `tests/unit/test_browser_session_auth.py`
- Create: `tests/integration/test_browser_handoff_flow.py`
- Create: `tests/integration/test_identity_security.py`
- Create: `tests/integration/test_argon2_benchmark.py`
- Create: `tests/contract/test_browser_handoff_contract.py`

Consume-only: Review Lab store/other assets, prerequisite modules/models/config, plans/specs, existing tests. No schema change, Access code, report APIs, README, or deployment files.

## Locked interfaces and boundary rules

- Produce `BrowserHandoffResult`, `BrowserActor`, `issue_browser_handoff()`, `redeem_browser_handoff()`, `resolve_browser_session()`, `require_review_lab_access()`, `GET /access-handoff`, `POST /api/browser-handoffs/redeem`, and `POST /api/v1/admin/review-lab-handoffs`.
- Handoff requires Admin bearer, active elevation, compatible client, idempotency, and exact `review_lab_handoff` step-up consumed with issue/audit. Build URL only from validated client-policy `PUBLIC_BASE_URL`, never `Host`; token exists after `#` only.
- Handoff credential is at least 256 random bits, only digest stored, expires 60 seconds, one use under row lock. Redemption creates attributable nonpersistent browser session, stores only digest, idle-expires after 30 minutes.
- `/access-handoff` and exact `/api/browser-handoffs/redeem` alone bypass legacy gate but expose no Review Lab data. Initial page is static, `no-store`, `no-referrer`, and renders no request input.
- JS obtains fragment, immediately removes it with `history.replaceState`, sends it once in JSON POST, and never writes token to query/DOM/storage/console/error. Cookie is exactly `review_session`, `HttpOnly`, `Secure`, `SameSite=Lax`, with no Max-Age/Expires.
- Review Lab accepts either live individual browser actor or existing legacy Admin cookie during pilot. Legacy path is marked `legacy_shared_admin`. Bearer alone is ignored on Review Lab; browser/legacy cookies cannot call `/api/v1/admin/*`.
- Apply guard to Review Lab page and all submission list/get/export/create paths; preserve feature flag/store behavior.
- Handoff issue/redeem/expiry/replay/session expiry/audit rollback use safe errors without credential echo. OpenAPI marks token input write-only and uses exact safe envelopes.
- Identity verification proves no readable credentials/sensitive identifiers in logs, audit, exceptions, response error detail, or DB. Argon2 is under 500 ms on selected minimum-instance-equivalent test and respects concurrency memory limit; do not falsify/skips.

## TDD and verification procedure

1. Add handoff/session unit tests first and run red:

   ```powershell
   python -m pytest tests/unit/test_browser_handoff_service.py tests/unit/test_browser_session_auth.py -q
   ```

   Expected: missing browser-handoff modules/routes/authorization.
2. Implement transactional issue/redeem/resolve, fragment page/JS/cookie, exact exemptions, dual Review Lab guard, Admin issue route, and OpenAPI.
3. Add full fictional flow, expiry, replay, concurrent redemption, deactivated issuer, idle expiry/cookie deletion, bearer-only denial, legacy-cookie API denial, attribution, audit rollback, and captured-log tests. Run with dedicated test DB:

   ```powershell
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m pytest tests/integration/test_browser_handoff_flow.py -q
   python -m pytest tests/contract/test_browser_handoff_contract.py tests/contract/test_access_v1_openapi.py -q
   ```

   Expected: all boundaries/contracts pass. Stop if no dedicated DB; never substitute SQLite/production.
4. Run the explicit benchmark only on the approved local/test host:

   ```powershell
   $env:RUN_ARGON2_BENCHMARK="1"
   python -m pytest tests/integration/test_argon2_benchmark.py -q -s
   ```

   Expected: one verification below 500 ms and concurrency within memory. Report actual evidence; do not tune below locked parameters.
5. Run full identity/repository verification:

   ```powershell
   python -m pytest tests/unit -q
   $env:DATABASE_URL=$env:TEST_DATABASE_URL
   python -m pytest tests/integration -q
   python -m pytest tests/contract -q
   python -m alembic downgrade base
   python -m alembic upgrade head
   python -m pytest -q
   python scripts/optimize_images.py --check
   ```

   Expected: every command exits 0, credential-free defaults remain green, populated migration roundtrip succeeds, and legacy login/Admin/Review Lab/roster/report/policy regressions remain green.
6. Run final scans and manually classify hits:

   ```powershell
   rg -n "print\(|logger\.(debug|info|warning|error|exception).*?(pin|token|employee_number|device_id)|request\.get_json" backend/identity backend/webapp/api_v1 backend/webapp/routes/browser_handoffs.py
   rg -n "ACCESS_CODE|ADMIN_CODE" backend/webapp/api_v1 backend/identity
   rg -n "temporary_pin|access_token|renewal_token|step_up_token|review_session" backend/identity backend/webapp/api_v1 backend/webapp/routes/browser_handoffs.py
   ```

   Expected: no sensitive logging; no `/api/v1` or identity dependency on shared codes; readable credential names only at request parsing, request-local DTO, or one-time response serialization.
7. Enforce whitespace/allowlist:

   ```powershell
   $allowed=@('backend/identity/elevation.py','backend/identity/browser_handoffs.py','backend/webapp/api_v1/admin.py','backend/webapp/routes/browser_handoffs.py','backend/webapp/routes/review_lab.py','backend/webapp/routes/__init__.py','backend/webapp/app.py','backend/webapp/templates/access_handoff.html','backend/webapp/static/js/access-handoff.js','openapi/access-v1.yaml','tests/unit/test_browser_handoff_service.py','tests/unit/test_browser_session_auth.py','tests/integration/test_browser_handoff_flow.py','tests/integration/test_identity_security.py','tests/integration/test_argon2_benchmark.py','tests/contract/test_browser_handoff_contract.py')
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

Fictional data/nonfunctional tokens only. No external Google call. Never log/persist/expose raw handoff/session/PIN/bearer/action tokens, employee/device/network identifiers, field notes/report/inmate text. Do not change Review Lab storage/business logic, build RP/report work, Access client, infrastructure, or schema. Acceptance includes red evidence, exact fragment/cookie/origin behavior, atomic one-time redemption, dual-but-isolated boundary, full tests/migration/benchmark/scans, allowlist and whitespace.

## Commit and handoff

```powershell
git commit -m "feat(identity): add attributable Review Lab handoff"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff exact start/baseline/branch/commit/files/red/green/migration/benchmark/scan/boundary/security/deviation/risk evidence. Stop for ancestry/prerequisite/dirt, missing dedicated DB, unsafe benchmark environment, allowlist expansion, origin/config conflict, secret/production need, or any failed security boundary. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
