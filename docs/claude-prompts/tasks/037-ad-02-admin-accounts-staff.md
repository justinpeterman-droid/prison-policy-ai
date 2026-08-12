# Claude Code Prompt 037 — AD-02: Accounts & Staff and session management

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **037**, task **AD-02**. Deliver Admin staff/account management, one-time temporary PIN display/copy, role/status/unlock/reset lifecycle, and bounded target-session management while preserving immutable staff/report history and last-active-Admin protection.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ad-02-accounts-staff`

## Read/preflight

Read `AGENTS.md`; roadmap gates/sequence 037; Admin plan globals and complete exact heading `### Task AD-02: Accounts & Staff and session management`; Admin/identity specs; exact staff/account/session OpenAPI operations/purposes. Verify AD-01 and all its prerequisites reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require reviewed current main, baseline ancestor, green suite, clean overlapping paths. Read reviewed changes since baseline; branch from current reviewed `HEAD`, never baseline. Preserve user work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAdminAccounts.bas`
- `access-client/src/classes/CTemporaryPinResult.cls`
- `access-client/src/classes/IClipboardService.cls`
- `access-client/src/classes/CWindowsClipboardService.cls`
- `access-client/src/forms/frmAdminAccountsStaff.txt`
- `access-client/src/forms/frmAdminStaffEditor.txt`
- `access-client/src/forms/frmAdminAccountAction.txt`
- `access-client/src/forms/frmAdminTemporaryPin.txt`
- `access-client/src/forms/frmAdminSessions.txt`
- `access-client/src/forms/sfrmAdminStaffResults.txt`
- `access-client/src/forms/sfrmAdminSessionResults.txt`
- `access-client/tests/vba/TestAdminAccounts.bas`
- `access-client/tests/vba/classes/CFakeClipboardService.cls`
- `access-client/tests/fixtures/admin/staff-page.json`
- `access-client/tests/fixtures/admin/staff-created.json`
- `access-client/tests/fixtures/admin/staff-updated.json`
- `access-client/tests/fixtures/admin/account-page.json`
- `access-client/tests/fixtures/admin/account-created.json`
- `access-client/tests/fixtures/admin/account-pin-reset.json`
- `access-client/tests/fixtures/admin/account-pin-replay.json`
- `access-client/tests/fixtures/admin/account-updated.json`
- `access-client/tests/fixtures/admin/account-unlocked.json`
- `access-client/tests/fixtures/admin/account-sessions-page.json`
- `access-client/tests/fixtures/admin/account-sessions-revoked.json`
- `access-client/tests/fixtures/errors/duplicate-employee-number.json`
- `access-client/tests/fixtures/errors/last-active-admin.json`
- `access-client/tests/fixtures/errors/staff-has-history.json`
- `tests/access/test_admin_accounts.py`

Modify only:

- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modAdminAuth.bas`
- `access-client/src/modules/modErrors.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/modules/modWin32.bas`
- `access-client/src/forms/frmAdminOverview.txt`
- `access-client/src/forms/frmConfirmAction.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestAdminAuthorization.bas`
- `access-client/tests/vba/TestRunner.bas`
- `tests/unit/test_access_fixture_contracts.py`
- `tests/unit/test_access_route_parity.py`
- `tests/unit/test_access_vba_safety.py`
- `tests/access/fake_api.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. No other paths.

## Locked interfaces/security rules

- Consume AD-01 grants and existing paging/API/UUID/JSON/error/confirmation infrastructure. Produce every locked staff/account/session function, one-time PIN result, clipboard interface, and exact route helpers named in the task.
- Staff and account are distinct; stable UUIDs remain unchanged. Correct employee number without replacing staff identity/history. Staff activation and account status are independent. Never expose delete for staff/account; history is preserved.
- One account links to one eligible staff record and role is User/Admin. Server enforces normalized unique employee number, authorization-version increments, session revocation on role/status changes, and last-active-Admin protection.
- Admin creates account or resets PIN only after exact purpose step-up; one action idempotency key survives duplicate click/retry. Initial success may display one readable eight-character temporary PIN exactly once. A replay must return explicit unavailable state and never reveal it again; no retrieval route.
- `CTemporaryPinResult.TakeTemporaryPin()` clears the in-memory value. Display is modal/one-time; Copy occurs only after explicit click through injected late-bound/Win32 clipboard service and clears on close. No implicit clipboard or Office/Forms reference.
- Reset revokes target sessions and marks first-use change; unlock only clears lockout and never changes PIN. Old PIN is never displayed.
- Session page bounded with stable UUID/device/time/persistence/current data; no tokens/hashes/IP. One/all revocation scopes exact.
- All Win32 declarations central/PtrSafe; all forms unbound; no local tables; no PIN/identity/token in logs/state/recovery.

## TDD

1. Add exact failing VBA and COM account/staff/PIN/session cases from Step 1 first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAccounts_Run
python -m pytest tests/access/test_admin_accounts.py -q -m access_com
```

Expected: compile fails because `CTemporaryPinResult`/Admin account functions are undefined; COM fails because Admin account/staff forms are absent.

3. Execute every remaining checkbox exactly; validate route/fixtures:

```powershell
python -m pytest tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py -q
```

4. Focused/regression:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAccounts_Run,TestAdminAuthorization_Run,TestAuth_Run,TestSessionStore_Run,TestSafeLog_Run
python -m pytest tests/access/test_admin_accounts.py tests/access/test_admin_authorization.py tests/access/test_user_workflows.py -q -m access_com -k "staff or account or pin or role or session or user_navigation or unbound"
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: one-time PIN never replays/persists; lifecycle/session rules server-driven; last Admin protected; new UI unbound; User behavior green.

## Scope/acceptance/commit

Fictional fixtures only. No deletes, report oversight, audit/health/handoff, backend/OpenAPI/local tables, password vault, browser/deployment/signing/unrelated refactor. Accept with every checkbox/schema/purpose/privacy/accessibility/source-parity test and `git diff --name-only $taskBase` allowlist. Never stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAdminAccounts.bas',
  'access-client/src/classes/CTemporaryPinResult.cls',
  'access-client/src/classes/IClipboardService.cls',
  'access-client/src/classes/CWindowsClipboardService.cls',
  'access-client/src/forms/frmAdminAccountsStaff.txt',
  'access-client/src/forms/frmAdminStaffEditor.txt',
  'access-client/src/forms/frmAdminAccountAction.txt',
  'access-client/src/forms/frmAdminTemporaryPin.txt',
  'access-client/src/forms/frmAdminSessions.txt',
  'access-client/src/forms/sfrmAdminStaffResults.txt',
  'access-client/src/forms/sfrmAdminSessionResults.txt',
  'access-client/tests/vba/TestAdminAccounts.bas',
  'access-client/tests/vba/classes/CFakeClipboardService.cls',
  'access-client/tests/fixtures/admin/staff-page.json',
  'access-client/tests/fixtures/admin/staff-created.json',
  'access-client/tests/fixtures/admin/staff-updated.json',
  'access-client/tests/fixtures/admin/account-page.json',
  'access-client/tests/fixtures/admin/account-created.json',
  'access-client/tests/fixtures/admin/account-pin-reset.json',
  'access-client/tests/fixtures/admin/account-pin-replay.json',
  'access-client/tests/fixtures/admin/account-updated.json',
  'access-client/tests/fixtures/admin/account-unlocked.json',
  'access-client/tests/fixtures/admin/account-sessions-page.json',
  'access-client/tests/fixtures/admin/account-sessions-revoked.json',
  'access-client/tests/fixtures/errors/duplicate-employee-number.json',
  'access-client/tests/fixtures/errors/last-active-admin.json',
  'access-client/tests/fixtures/errors/staff-has-history.json',
  'tests/access/test_admin_accounts.py',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modAdminAuth.bas',
  'access-client/src/modules/modErrors.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/modules/modWin32.bas',
  'access-client/src/forms/frmAdminOverview.txt',
  'access-client/src/forms/frmConfirmAction.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestAdminAuthorization.bas',
  'access-client/tests/vba/TestRunner.bas',
  'tests/unit/test_access_fixture_contracts.py',
  'tests/unit/test_access_route_parity.py',
  'tests/unit/test_access_vba_safety.py',
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
git commit -m "feat(access): add admin account and staff management"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff SHAs/files/red/final tests, actual bitness, PIN replay/clipboard/redaction/idempotency/session evidence, diff/parity, commit, deviations/NOT RUN.

Stop on missing UUID/pagination/revocation/one-time semantics, PIN replay, unlock-changing-PIN, authorization/session inconsistency, last-Admin risk, delete route, new reference need, dirty overlap, unreviewed prerequisite, or COM/compile failure. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/change policy/reset/destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add admin account and staff management`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
