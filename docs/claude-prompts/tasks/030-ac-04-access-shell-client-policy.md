# Claude Code Prompt 030 — AC-04: Startup, Guided Workspace shell, navigation, dashboard, and client policy

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **030**, task **AC-04**. Deliver deterministic startup/session restoration, the unbound User Guided Workspace shell/dashboard/navigation, corrections-professional theme assets, safe error UI, and server-authoritative client compatibility policy including a validated Review Lab origin and the required in-memory field-notes maximum. This establishes the ordinary employee experience and update/read-only gate without changing backend behavior.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-04-guided-shell`

## Read/preflight

Read `AGENTS.md`; roadmap gates/sequence 030; Access User plan global constraints, exact heading `### Task AC-04: Startup, Guided Workspace shell, navigation, dashboard, and client policy`; the user-client spec; consumed theme assets/tokens; and relevant OpenAPI policy/profile examples. AC-01–AC-03 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestor/green baseline and no unexplained allowed-path edits. Preserve user work; never reset/stash/clean/discard. If reviewed main advanced, read relevant reviewed plan/OpenAPI/theme diffs since baseline and verify AC-01–AC-03 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAppStartup.bas`
- `access-client/src/modules/modNavigation.bas`
- `access-client/src/modules/modTheme.bas`
- `access-client/src/modules/modClientPolicy.bas`
- `access-client/src/forms/frmDashboard.txt`
- `access-client/src/forms/frmUpdateNotice.txt`
- `access-client/src/forms/sfrmNavigation.txt`
- `access-client/src/assets/README.md`
- `access-client/src/assets/shield-crystal-front.png`
- `access-client/src/assets/seal.png`
- `access-client/src/assets/app.ico`
- `access-client/tests/vba/TestClientPolicy.bas`
- `access-client/tests/fixtures/policy/client-read-only.json`
- `tests/access/test_user_workflows.py`

Modify only:

- `access-client/src/forms/frmShell.txt`
- `access-client/src/forms/frmErrorDialog.txt`
- `access-client/src/macros/AutoExec.txt`
- `access-client/src/modules/modAppState.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/fake_api.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying:

- `backend/webapp/static/tokens.css`
- `backend/webapp/static/shield-crystal-front.png`
- `backend/webapp/static/seal.svg`
- `openapi/access-v1.yaml`

Plans/specs are read-only. No other path.

## Locked interfaces and behavior

- Consume AC-03 session restoration/renewal/profile/app state/API/DPAPI. Produce `AppStart`, `NavigateTo`, `ApplyTheme`, `RefreshClientPolicy() As ClientCompatibility`, `TrustedReviewLabOrigin() As String`, `FieldNotesMaxCharacters() As Long`, `RefreshDashboard`, `Test_Navigate`, expanded `Test_GetStateJson`.
- Startup order and destinations must exactly follow the plan: no token → login; valid renewal/profile/policy → User home; temporary PIN → forced change; errors → safe dialog; later tasks hook jobs/recovery only where prescribed.
- User navigation is exactly Home, New Report, My Reports, Reports I Prepared, Policy Expert, Account. Do not add Admin navigation in AC-04.
- Validate exactly the nine required public client-policy fields. `field_notes_max_characters` must be a JSON integer exactly `30000` in release one, stored only in module memory, and returned by `FieldNotesMaxCharacters()`; never source it from build metadata, an environment/registry/local table/file, or `release/version.json`. Missing/string/zero/negative/different values fail closed without replacing the last validated policy. `review_lab_origin` must be an HTTPS origin only (scheme/host/optional port, no credentials/path/query/fragment) and is the sole source for `TrustedReviewLabOrigin`; never infer it from API origin, Host, redirects, form, registry, or table. Validate semantic versions numerically.
- Required update makes writes unavailable while approved reads/export remain available. Do not bypass server policy.
- Reuse exact navy/gold tokens and approved assets without altering consumed originals. All forms/subforms are unbound and source-exported from Access.
- Minimum layout is 1366×768 at 100/125/150% Windows scaling with keyboard focus, logical tab order, visible labels, high contrast, and non-color-only state.
- Test hooks are disabled outside `TEST_BUILD`. Do not expose raw VBA/HTML/stack details.

## TDD

1. Add the exact failing policy/startup/navigation/COM tests first. Both `client-current.json` and `client-read-only.json` must contain integer `field_notes_max_characters: 30000`; `TestClientPolicy_Run` asserts `FieldNotesMaxCharacters() = 30000` for both and malformed-policy cases fail closed.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestClientPolicy_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com
```

Expected: FAIL because `RefreshClientPolicy`, `frmDashboard`, and `NavigateTo` are undefined.

3. Execute every plan checkbox, generating forms/assets through the approved Access/source process.
4. Focused/regression run (actual Access bitness):

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestClientPolicy_Run,TestAuth_Run,TestErrors_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "startup or navigation or client_policy or unbound"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: login/home/change-PIN routing is exact; User navigation exact; both policies retain the validated in-memory 30,000-character maximum; required update blocks writes but not permitted reads/export; forms unbound; no raw errors. Manually inspect shell/dashboard at 1366×768, 100/125/150%; stop on clipping or inaccessible keyboard focus.

## Scope/acceptance

Fictional tests only. No local tables, Admin forms/modules, report workflow, backend/OpenAPI edits, new artwork direction, browser changes, updater/deployment/signing, direct cloud calls, or unrelated refactor. Accept only when every checkbox and manual matrix observation passes, source/binary parity is clean, and `git diff --name-only $taskBase` is allowlisted. Do not stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAppStartup.bas',
  'access-client/src/modules/modNavigation.bas',
  'access-client/src/modules/modTheme.bas',
  'access-client/src/modules/modClientPolicy.bas',
  'access-client/src/forms/frmDashboard.txt',
  'access-client/src/forms/frmUpdateNotice.txt',
  'access-client/src/forms/sfrmNavigation.txt',
  'access-client/src/assets/README.md',
  'access-client/src/assets/shield-crystal-front.png',
  'access-client/src/assets/seal.png',
  'access-client/src/assets/app.ico',
  'access-client/tests/vba/TestClientPolicy.bas',
  'access-client/tests/fixtures/policy/client-read-only.json',
  'tests/access/test_user_workflows.py',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/forms/frmErrorDialog.txt',
  'access-client/src/macros/AutoExec.txt',
  'access-client/src/modules/modAppState.bas',
  'access-client/src/modules/modTestHooks.bas',
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
git commit -m "feat(access): add guided workspace shell"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push.

## Handoff/stops

Return branch/start/end/commit SHAs, changed files, red/final results, actual Access bitness, manual resolution/scaling/high-contrast/keyboard evidence, source parity, diff check, deviations/NOT RUN.

Stop on missing/invalid policy contract, unapproved origin semantics, dirty paths, ancestry/baseline failure, Access bitness/COM/compile failure, clipped/inaccessible UI, or forbidden scope. Never push, merge, deploy, apply, sign, publish, install, access production, request/store secrets, alter machine policy, reset, or destructively remove user work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add guided workspace shell`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
