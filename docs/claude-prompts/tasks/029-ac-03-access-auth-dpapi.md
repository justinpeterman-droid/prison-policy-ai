# Claude Code Prompt 029 — AC-03: DPAPI secure stores, device/session lifecycle, and employee authentication

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **029**, task **AC-03**, exactly. Deliver individual employee-number/PIN authentication, forced temporary-PIN change, rotating sessions, current-profile hydration, Windows-current-user DPAPI persistence, device/session lifecycle, and one bounded access-token renewal replay. This gives employees optional persistent sign-in without ever persisting an access token or exposing credentials.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-03-secure-sessions`

## Read/preflight

Read `AGENTS.md`, roadmap sequence 029/global gates, the Access User plan global constraints and exact full heading `### Task AC-03: DPAPI secure stores, device/session lifecycle, and employee authentication`, the user-client spec, and consumed OpenAPI auth/profile/session schemas. AC-01 and AC-02 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root, successful ancestry, clean task paths, and green baseline. Never reset/stash/clean/discard. If main advanced, baseline must remain its ancestor; read reviewed plan/OpenAPI changes since baseline and verify AC-01/AC-02 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAuth.bas`
- `access-client/src/modules/modDpapi.bas`
- `access-client/src/modules/modSessionStore.bas`
- `access-client/src/classes/ISecureStore.cls`
- `access-client/src/classes/CDpapiFileStore.cls`
- `access-client/src/classes/CUserProfile.cls`
- `access-client/src/classes/CSessionState.cls`
- `access-client/tests/vba/TestAuth.bas`
- `access-client/tests/vba/TestDpapi.bas`
- `access-client/tests/vba/TestSessionStore.bas`
- `access-client/tests/vba/classes/CInMemorySecureStore.cls`
- `access-client/tests/fixtures/auth/login-user.json`
- `access-client/tests/fixtures/auth/login-temporary-pin.json`
- `access-client/tests/fixtures/auth/renew-success.json`
- `access-client/tests/fixtures/auth/sessions.json`
- `access-client/tests/fixtures/profile/me-user.json`

Modify only:

- `access-client/src/modules/modWin32.bas`
- `access-client/src/modules/modApiClient.bas`
- `access-client/src/modules/modAppState.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/forms/frmLogin.txt`
- `access-client/src/forms/frmChangePin.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/fake_api.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. Plans/specs are read-only. No other path.

## Locked interfaces/wire/security rules

- Consume AC-02 `NewApiRequest`, `ApiSend`, envelope parsers/value classes, and fake transport.
- Produce `Login`, `RenewSession`, `ChangePin`, `LogoutCurrent`, `LogoutAll`, `LoadCurrentProfile`; DPAPI protect/unprotect; device ID; persistent renewal-token save/load/delete; `ISecureStore`; validated `CSessionState` and `CUserProfile`.
- PIN is 4–8 alphanumeric characters and case-insensitive per server contract; client must not invent identity/authorization. Server profile UUID/role is authoritative.
- Access token is memory-only. Persist only a rotating renewal token when Keep me signed in is selected and DPAPI current-user protection succeeds. Nonpersistent renewal stays memory-only. Closing/restart behavior must match the approved session rules.
- Device ID is a random stable UUID for this Windows-user install, not a hardware fingerprint, SID, username, machine name, employee number, or registry identity.
- All Win32 declarations live in `modWin32.bas`, are `PtrSafe`/`LongPtr`, and compile under VBA7/Win64 branches. DPAPI uses current-user scope and bounded atomic `%LOCALAPPDATA%\StandardLogisticsUnitTools` files.
- Login/renew/client-policy never bearer-renew. Only a request that carried the current bearer may receive one expired-access renewal and one replay; transport retry and auth replay are independent. Renewal atomically replaces session plus embedded profile.
- Change PIN/logout/logout-all/session delete use one idempotency key per intended action, reused for a byte-identical replay.
- Temporary PIN blocks normal navigation until successful change. Reset never reveals an old PIN.
- Never log/store PIN, access token, renewal token, employee name/number, profile content, raw DPAPI bytes, or authentication body.
- Forms remain unbound and no Access table is created.

## TDD

1. Write exact failing DPAPI/session/auth tests before implementation.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestDpapi_Run,TestSessionStore_Run,TestAuth_Run
```

Expected: compile failure because `ProtectForCurrentUser`, `Login`, and `ISecureStore` are undefined.

3. Execute every remaining AC-03 step exactly, including pointer-safe declarations, atomic store format/corruption handling, injected store tests, profile/session validation, renewal boundary, unbound login/change-PIN forms, and fake endpoints.
4. Focused and regression gate (actual runner bitness):

```powershell
python -m pytest tests/unit/test_access_fixture_contracts.py -q
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestDpapi_Run,TestSessionStore_Run,TestAuth_Run,TestApiClient_Run,TestSafeLog_Run
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: all pass; same-Windows-user persistent renewal survives reopen; corrupt DPAPI content is rejected/deleted; temporary PIN cannot pass `frmChangePin`; a 401 causes at most one renewal/one replay; test secrets/profile strings do not occur in logs/source. Cross-identity DPAPI is **NOT RUN**, never inferred, unless a controlled second identity actually executes it.

## Scope/acceptance

Fictional fixtures only. No local tables; no Admin behavior, workflow/report UI, backend/OpenAPI edits, browser changes, infrastructure, updater, signing, publishing, direct cloud connection, or unrelated refactor. Use matching-bitness PowerShell/Access and stop on COM/compile/DPAPI policy failure.

Accept only with every checkbox complete, source/binary parity clean, all forms unbound, precise session/replay/idempotency behavior proven, sensitive-marker scans clean, and `git diff --name-only $taskBase` within the allowlist. Do not stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAuth.bas',
  'access-client/src/modules/modDpapi.bas',
  'access-client/src/modules/modSessionStore.bas',
  'access-client/src/classes/ISecureStore.cls',
  'access-client/src/classes/CDpapiFileStore.cls',
  'access-client/src/classes/CUserProfile.cls',
  'access-client/src/classes/CSessionState.cls',
  'access-client/tests/vba/TestAuth.bas',
  'access-client/tests/vba/TestDpapi.bas',
  'access-client/tests/vba/TestSessionStore.bas',
  'access-client/tests/vba/classes/CInMemorySecureStore.cls',
  'access-client/tests/fixtures/auth/login-user.json',
  'access-client/tests/fixtures/auth/login-temporary-pin.json',
  'access-client/tests/fixtures/auth/renew-success.json',
  'access-client/tests/fixtures/auth/sessions.json',
  'access-client/tests/fixtures/profile/me-user.json',
  'access-client/src/modules/modWin32.bas',
  'access-client/src/modules/modApiClient.bas',
  'access-client/src/modules/modAppState.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/forms/frmLogin.txt',
  'access-client/src/forms/frmChangePin.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestRunner.bas',
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
git commit -m "feat(access): add secure employee sessions"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push.

## Handoff/stops

Report task, branch, start/end SHA, files, red failure, test commands/results, Access/PowerShell bitness, DPAPI same-user/corruption results, cross-identity NOT RUN or evidence, diff gate, commit, deviations.

Stop on missing schema/examples, unsafe persistent data, credential logging, ambiguity, dirty task paths, ancestry/baseline failure, bitness/COM/compile failure, or forbidden-file need. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/change machine policy/reset or destroy user work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add secure employee sessions`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
