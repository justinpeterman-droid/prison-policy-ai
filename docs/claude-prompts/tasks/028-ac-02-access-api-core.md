# Claude Code Prompt 028 — AC-02: API core, WinHTTP transport, JSON envelopes, errors, and fake contracts

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **028**, task **AC-02**, from the approved plan. Build the Access `/api/v1` client core, late-bound WinHTTP transport, strict JSON/envelope parsing, safe errors/logging, exact route helpers, fictional OpenAPI-validated fixtures, and injectable fake transport. The purpose is to establish one testable and privacy-safe wire boundary before authentication or report features are added.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Planning baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-02-api-core`

## Mandatory reading and preflight

Read `AGENTS.md`; the roadmap global gates and sequence 028; the Access User plan global constraints/preconditions/locked structure; and the entire exact heading `### Task AC-02: API core, WinHTTP transport, JSON envelopes, errors, and fake contracts`. Read the user-client spec. Read `openapi/access-v1.yaml` and the schemas/examples named by AC-02 without modifying it. AC-01 must already be reviewed and merged.

Run:

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Stop unless the root and ancestry are correct and the credential-free suite passes. Never reset/stash/clean/discard user work. If reviewed main advanced, baseline must remain an ancestor; inspect `git diff 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD -- docs/superpowers openapi/access-v1.yaml`, follow reviewed changes, and verify AC-01 was reviewed. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact file allowlist

Create only:

- `access-client/src/modules/modAppState.bas`
- `access-client/src/modules/modBuildInfo.bas`
- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modApiClient.bas`
- `access-client/src/modules/modJsonContracts.bas`
- `access-client/src/modules/modIds.bas`
- `access-client/src/modules/modUtf8.bas`
- `access-client/src/modules/modErrors.bas`
- `access-client/src/modules/modSafeLog.bas`
- `access-client/src/modules/modWin32.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/classes/IApiTransport.cls`
- `access-client/src/classes/CWinHttpTransport.cls`
- `access-client/src/classes/CApiRequest.cls`
- `access-client/src/classes/CApiResponse.cls`
- `access-client/src/classes/CApiError.cls`
- `access-client/tests/vba/TestApiRoutes.bas`
- `access-client/tests/vba/TestJsonContracts.bas`
- `access-client/tests/vba/TestApiClient.bas`
- `access-client/tests/vba/TestErrors.bas`
- `access-client/tests/vba/TestSafeLog.bas`
- `access-client/tests/vba/classes/CFakeApiTransport.cls`
- `access-client/tests/fixtures/policy/client-current.json`
- `access-client/tests/fixtures/errors/authentication-required.json`
- `access-client/tests/fixtures/errors/invalid-credentials.json`
- `access-client/tests/fixtures/errors/session-reauthentication-required.json`
- `access-client/tests/fixtures/errors/permission-denied.json`
- `access-client/tests/fixtures/errors/validation-failed.json`
- `access-client/tests/fixtures/errors/client-upgrade-required.json`
- `access-client/tests/fixtures/errors/blocking-information-required.json`
- `access-client/tests/fixtures/errors/dependency-unavailable.json`
- `tests/unit/test_access_fixture_contracts.py`
- `tests/unit/test_access_route_parity.py`
- `tests/access/conftest.py`
- `tests/access/fake_api.py`

Modify only:

- `access-client/src/manifest.json`
- `access-client/SLUT-Client.accdb`
- `access-client/tests/vba/TestRunner.bas`

Consume without modifying:

- `openapi/access-v1.yaml`

Plans/specs/instructions are also read-only. No other path is allowed.

## Locked interfaces and wire rules

- Consume AC-01 import/export/build and pinned `JsonConverter.ParseJson`/`ConvertToJson`.
- Produce `NewApiRequest`, `ApiSend`, `ConfigureApiTransportForTest`; `IApiTransport.Send`; `JsonParseObject`, `JsonSerialize`, `ParseSuccessEnvelope`, `ParseErrorEnvelope`; exact route functions; `UserGuidanceFor`; `SafeLogEvent`; `Test_SetApiBaseUrl`; `Test_GetStateJson`.
- Implement `CApiRequest`, `CApiResponse`, and `CApiError` with the exact properties/defaults in the task. Preserve arbitrary DOCX bytes in `BodyBytes`; never text-convert binary data.
- Routes must be relative `/api/v1` literals matching OpenAPI. Reject legacy `/api/chat`, `/api/reports/*`, and `/api/roster` literals. Access never calls Cloud SQL/Google AI directly.
- HTTPS is mandatory in release; only the explicit `TEST_BUILD` hook may use loopback HTTP. Use late-bound WinHTTP and the exact timeout/retry boundary. Retry once only when allowed; never recursive retry.
- Login, renew, and client-policy requests are not bearer-renewal eligible. Authentication replay state remains separate from transport retry state.
- Strictly parse the versioned success/error envelope and `X-Request-ID`; malformed JSON, wrong content type, oversized response, HTML, or unexpected schema must fail safely without mutating application state.
- `access-client/tests/fixtures/policy/client-current.json` must validate against the closed public `ClientPolicy` schema with exactly nine required data fields, including JSON integer `field_notes_max_characters: 30000`. The fixture-contract test rejects omission, string coercion, a different value, or an additional public-policy field; AC-02 does not interpret/store that policy value yet.
- Safe logs may contain request ID, stable category, version, and timestamp only. They must redact PIN, access/renewal tokens, field notes, names, and employee numbers.
- All forms remain unbound and the local table schema remains empty.

## TDD sequence

1. Add the exact Python route-parity/fixture-contract tests first.
2. Red run:

```powershell
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py -q
```

Expected: FAIL because `modApiRoutes.bas` and fictional fixtures do not exist. If OpenAPI is missing/invalid, stop and hand off the exact backend-contract failure.

3. Add the exact failing VBA route/JSON/envelope/error/log tests, then run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestApiRoutes_Run,TestJsonContracts_Run,TestErrors_Run,TestSafeLog_Run
```

Expected: compile failure because `RouteAuthLogin` and `JsonParseObject` are undefined.

4. Implement every remaining AC-02 checkbox in order, including fake API behavior, manifest updates, import/export of the source-matched binary, and no additional endpoint assumptions.
5. Focused/regression gate, using the actual Access bitness instead of `x64` when needed:

```powershell
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database $env:TEMP\SLUT-Client-AC02.accdb -Configuration Test
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database $env:TEMP\SLUT-Client-AC02.accdb -Tests TestApiRoutes_Run,TestJsonContracts_Run,TestApiClient_Run,TestErrors_Run,TestSafeLog_Run
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py -q
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database $env:TEMP\SLUT-Client-AC02.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: all VBA/Python tests pass; no legacy route; malformed/HTML responses leave state unchanged; sensitive test markers are absent from logs/source; source round-trip is clean.

## Security, privacy, scope, and acceptance

Use fictional schema-valid fixtures only. Never log/store credentials, identity, report content, or secrets. Do not add local tables, auth/session behavior, report features, Admin UI, backend/OpenAPI changes, deployment/updater/signing, direct cloud calls, or unrelated refactors.

Accept only when every plan checkbox passes, exact routes/schemas match OpenAPI, test hooks are test-build-only, all forms are unbound, manifest/source/binary parity is clean, and `git diff --name-only $taskBase` contains only the allowlist. Inspect the complete diff; do not stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAppState.bas',
  'access-client/src/modules/modBuildInfo.bas',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modApiClient.bas',
  'access-client/src/modules/modJsonContracts.bas',
  'access-client/src/modules/modIds.bas',
  'access-client/src/modules/modUtf8.bas',
  'access-client/src/modules/modErrors.bas',
  'access-client/src/modules/modSafeLog.bas',
  'access-client/src/modules/modWin32.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/classes/IApiTransport.cls',
  'access-client/src/classes/CWinHttpTransport.cls',
  'access-client/src/classes/CApiRequest.cls',
  'access-client/src/classes/CApiResponse.cls',
  'access-client/src/classes/CApiError.cls',
  'access-client/tests/vba/TestApiRoutes.bas',
  'access-client/tests/vba/TestJsonContracts.bas',
  'access-client/tests/vba/TestApiClient.bas',
  'access-client/tests/vba/TestErrors.bas',
  'access-client/tests/vba/TestSafeLog.bas',
  'access-client/tests/vba/classes/CFakeApiTransport.cls',
  'access-client/tests/fixtures/policy/client-current.json',
  'access-client/tests/fixtures/errors/authentication-required.json',
  'access-client/tests/fixtures/errors/invalid-credentials.json',
  'access-client/tests/fixtures/errors/session-reauthentication-required.json',
  'access-client/tests/fixtures/errors/permission-denied.json',
  'access-client/tests/fixtures/errors/validation-failed.json',
  'access-client/tests/fixtures/errors/client-upgrade-required.json',
  'access-client/tests/fixtures/errors/blocking-information-required.json',
  'access-client/tests/fixtures/errors/dependency-unavailable.json',
  'tests/unit/test_access_fixture_contracts.py',
  'tests/unit/test_access_route_parity.py',
  'tests/access/conftest.py',
  'tests/access/fake_api.py',
  'access-client/src/manifest.json',
  'access-client/SLUT-Client.accdb',
  'access-client/tests/vba/TestRunner.bas'
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
git commit -m "feat(access): add versioned API client core"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push.

## Handoff and stops

Report sequence/task, branch, start/end SHA, changed files, red failure, focused/full results, actual Windows/Access/PowerShell bitness for COM tests, diff/allowlist result, commit SHA, deviations, and NOT RUN items.

Stop on missing/invalid OpenAPI examples, dirty allowed files, ancestry failure, baseline failure, route/schema ambiguity, unsafe logging, bitness/COM/compile failure, source drift, or need to touch a forbidden file. Never push, merge, deploy, apply, sign, publish, install, access production, request/store secrets, change machine/Trust Center policy, reset user work, or run destructive commands.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add versioned API client core`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
