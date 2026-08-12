# Claude Code Prompt 036 — AD-01: Role-aware navigation, elevation, and overview

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **036**, task **AD-01**, exactly. Add role-aware navigation while preserving all User features, a PIN-confirmed Admin Center elevation that expires after 15 minutes of Admin inactivity, short purpose-scoped step-up support, and a bounded safe Admin overview. Persistent Admin account sessions are permitted, but elevation/step-up must never persist across close/reopen.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ad-01-admin-elevation`

## Reading/preflight

Read `AGENTS.md`; roadmap gates/sequence 036; full Access Admin plan global constraints, preconditions, object/interface rules, and exact complete heading `### Task AD-01: Role-aware navigation, elevation, and overview`; Admin/identity/user specs; relevant `/me`, step-up, overview, policy OpenAPI schemas. AC-01–AC-09, ID-01–ID-08, and RP-01–RP-10 must be reviewed/merged as required by the plan.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestry/green baseline, reviewed prerequisites, and no overlapping allowed-path work. If main advanced, read reviewed plan/OpenAPI changes since baseline. Create the exact branch from current reviewed `HEAD`, never the baseline SHA. Never reset/stash/clean/discard user work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAdminAuth.bas`
- `access-client/src/modules/modAdminOverview.bas`
- `access-client/src/classes/CAdminGrantState.cls`
- `access-client/src/forms/frmAdminElevation.txt`
- `access-client/src/forms/frmAdminStepUp.txt`
- `access-client/src/forms/frmAdminOverview.txt`
- `access-client/tests/vba/TestAdminAuthorization.bas`
- `access-client/tests/fixtures/profile/me-admin.json`
- `access-client/tests/fixtures/admin/elevation-admin-center.json`
- `access-client/tests/fixtures/admin/elevation-step-up.json`
- `access-client/tests/fixtures/admin/overview.json`
- `access-client/tests/fixtures/errors/admin-elevation-required.json`
- `access-client/tests/fixtures/errors/step-up-required.json`
- `tests/access/test_admin_authorization.py`

Modify only:

- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modAppStartup.bas`
- `access-client/src/modules/modAppState.bas`
- `access-client/src/modules/modNavigation.bas`
- `access-client/src/modules/modErrors.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/classes/CUserProfile.cls`
- `access-client/src/forms/frmShell.txt`
- `access-client/src/forms/sfrmNavigation.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestRunner.bas`
- `access-client/tests/fixtures/policy/client-current.json`
- `tests/unit/test_access_fixture_contracts.py`
- `tests/unit/test_access_route_parity.py`
- `tests/access/fake_api.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. No other files.

## Locked interfaces and authorization rules

- Consume existing profile/session/API/JSON/navigation/clock/error/test hooks and authoritative `/api/v1/me` role. Produce `CAdminGrantState`; role/elevation/activity/purpose/step-up functions listed in the task; Admin route helpers; exact six Admin `AppPage` enum values.
- User navigation stays exactly six destinations and cannot discover/call Admin data. Admin retains ordinary User pages and adds Overview, All Reports, Accounts & Staff, Audit Log, System Health, Review Lab.
- Role comes only from server profile; never a form/registry/local table. Authenticated session persistence does not imply Admin elevation.
- `admin_center` PIN confirmation establishes server-side elevation; it must not return/store a readable elevation token or require a client-created elevation header. Elevation expires after 15 minutes of Admin-area inactivity, not normal report activity. Touch only on approved Admin activity.
- Purpose step-up is separate, five minutes, exact purpose, and sent only as canonical `X-Admin-Step-Up` on the protected request. Never substitute generic elevation. Handle canonical `step_up_required` only.
- PIN is sent once to exact step-up endpoint, never retained/logged/state-serialized. Closing/restart/logout/profile-role/auth-version change clears all grants. A persistent Admin reopen restores profile/session only.
- Overview is bounded/sanitized; no report content, credentials, secrets, raw errors. All forms unbound; no local table.

## TDD

1. Add exact failing role/navigation/elevation/expiry VBA and COM tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAuthorization_Run
python -m pytest tests/access/test_admin_authorization.py -q -m access_com
```

Expected: VBA compile fails because `CAdminGrantState`, `IsCurrentUserAdmin`, and `PageAdminOverview` do not exist; COM fails because Admin forms/navigation are absent.

3. Execute every remaining AD-01 checkbox exactly, including route/fixture parity, grant expiry, activity boundary, unbound forms, safe errors, fake API and test-only clock hooks.
4. Run route/fixture gate:

```powershell
python -m pytest tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py -q
```

Expected: pass only when literals/fixtures match reviewed OpenAPI.

5. Focused/regression:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAuthorization_Run,TestAuth_Run,TestClientPolicy_Run,TestSafeLog_Run
python -m pytest tests/access/test_admin_authorization.py tests/access/test_user_workflows.py -q -m access_com -k "navigation or elevation or startup or persistent or unbound"
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py -q
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: User unchanged/denied; Admin retains User pages; elevation expires at 15m inactivity; restart clears grants; overview safe/bounded; forms unbound; User suite green.

## Scope/acceptance/handoff

Fictional fixtures only. No account/staff/report/audit/health/handoff implementation beyond navigation placeholders/approved overview, no backend/OpenAPI/local tables, no deployment/signing/browser change/unrelated refactor. `git diff --name-only $taskBase` must match allowlist; source/binary parity and accessibility pass; never stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAdminAuth.bas',
  'access-client/src/modules/modAdminOverview.bas',
  'access-client/src/classes/CAdminGrantState.cls',
  'access-client/src/forms/frmAdminElevation.txt',
  'access-client/src/forms/frmAdminStepUp.txt',
  'access-client/src/forms/frmAdminOverview.txt',
  'access-client/tests/vba/TestAdminAuthorization.bas',
  'access-client/tests/fixtures/profile/me-admin.json',
  'access-client/tests/fixtures/admin/elevation-admin-center.json',
  'access-client/tests/fixtures/admin/elevation-step-up.json',
  'access-client/tests/fixtures/admin/overview.json',
  'access-client/tests/fixtures/errors/admin-elevation-required.json',
  'access-client/tests/fixtures/errors/step-up-required.json',
  'tests/access/test_admin_authorization.py',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modAppStartup.bas',
  'access-client/src/modules/modAppState.bas',
  'access-client/src/modules/modNavigation.bas',
  'access-client/src/modules/modErrors.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/classes/CUserProfile.cls',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/forms/sfrmNavigation.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestRunner.bas',
  'access-client/tests/fixtures/policy/client-current.json',
  'tests/unit/test_access_fixture_contracts.py',
  'tests/unit/test_access_route_parity.py',
  'tests/access/fake_api.py',
  'access-client/SLUT-Client.accdb'
)
$changed = @((git diff --name-only), (git diff --cached --name-only), (git ls-files --others --exclude-standard)) |
  Where-Object { $_ -and $_ -notlike '.superpowers/*' } | Sort-Object -Unique
$unexpected = @($changed | Where-Object { $_ -notin $allowed })
if ($unexpected) { $unexpected; throw 'Changed-file allowlist violation.' }
git diff --check
git add -A -- $allowed
$staged = @(git diff --cached --name-only) | Where-Object { $_ } | Sort-Object -Unique
$unexpectedStaged = @($staged | Where-Object { $_ -notin $allowed })
if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
git diff --cached --name-status
git diff --cached --check
git commit -m "feat(access): add role-aware admin center"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff task/branch/start/end/commit SHAs, files, red/final tests, access bitness, grant-expiry/restart evidence, API call/header redaction evidence, diff/parity, deviations/NOT RUN.

Stop on missing/invalid schemas or expiry, readable admin-center token, client-created elevation header, User Admin access, AC-09 source mismatch, dirty overlap, unreviewed prerequisite, COM/compile/bitness failure, or forbidden scope. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/alter policy/reset or destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add role-aware admin center`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
