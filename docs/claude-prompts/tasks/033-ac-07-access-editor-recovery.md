# Claude Code Prompt 033 — AC-07: Report editor, immutable revisions, autosave, encrypted recovery, and conflicts

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **033**, task **AC-07**. Deliver an unbound multi-report editor with immutable cloud revisions, 60-second idle autosave, manual save through the same service, DPAPI-encrypted atomic crash recovery, revision browsing/comparison/restoration, and explicit conflict choices. No stale revision may overwrite server state and no employee work may silently disappear.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-07-revision-recovery`

## Required reading/preflight

Read `AGENTS.md`; roadmap gates/sequence 033; Access User plan globals and complete exact heading `### Task AC-07: Report editor, immutable revisions, autosave, encrypted recovery, and conflicts`; user/report specs; exact report/incident/revision/recovery OpenAPI operations. AC-01–AC-06 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestor/green baseline/clean task paths. Never reset/stash/clean/discard. If reviewed main advanced, read reviewed plan/OpenAPI changes since baseline and verify AC-01–AC-06 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAutosave.bas`
- `access-client/src/modules/modRecovery.bas`
- `access-client/src/modules/modConflict.bas`
- `access-client/src/classes/IRecoveryStore.cls`
- `access-client/src/classes/CAtomicRecoveryStore.cls`
- `access-client/src/classes/IClock.cls`
- `access-client/src/classes/CSystemClock.cls`
- `access-client/src/classes/CReportState.cls`
- `access-client/src/forms/frmReportEditor.txt`
- `access-client/src/forms/frmRevisionHistory.txt`
- `access-client/src/forms/frmRevisionCompare.txt`
- `access-client/src/forms/frmRevisionConflict.txt`
- `access-client/src/forms/frmRecoveryPrompt.txt`
- `access-client/src/forms/sfrmReportTabs.txt`
- `access-client/src/forms/sfrmRevisionList.txt`
- `access-client/tests/vba/TestAutosave.bas`
- `access-client/tests/vba/TestRecovery.bas`
- `access-client/tests/vba/TestConflict.bas`
- `access-client/tests/vba/classes/CInMemoryRecoveryStore.cls`
- `access-client/tests/vba/classes/CFakeClock.cls`
- `access-client/tests/fixtures/reports/report-detail.json`
- `access-client/tests/fixtures/reports/revision-page.json`
- `access-client/tests/fixtures/reports/revision-conflict.json`
- `access-client/tests/fixtures/reports/recovery-created.json`
- `access-client/tests/fixtures/recovery/workflow-state-v1.json`
- `tests/access/test_recovery_after_termination.py`

Modify only:

- `access-client/src/modules/modWin32.bas`
- `access-client/src/modules/modReportWorkflow.bas`
- `access-client/src/modules/modAppStartup.bas`
- `access-client/src/modules/modAppState.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/classes/CWorkflowState.cls`
- `access-client/src/forms/frmShell.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestReportWorkflow.bas`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/fake_api.py`
- `tests/access/test_user_workflows.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. No other files.

## Locked interfaces and invariants

- Consume generated report state, DPAPI, API/errors, exact report/incident revision endpoints. Produce report control/state copy/load/tab functions; `MarkDirty`, `SaveNow`, `OnIdleTimer`; recovery/clock interfaces; serialization/detection/conflict/recovery-revision functions; validated `CReportState`.
- Forms are unbound; `CWorkflowState`/`CReportState` are canonical in-memory state. Copy controls before tab switch; edits to each tab survive switching.
- Each change marks dirty. One save begins only 60,000 monotonic milliseconds after the latest change; shell timer checks every second without saving per tick/keystroke. Prevent reentry.
- Before any cloud save, atomically write the exact bounded versioned recovery shape as current-user DPAPI ciphertext directly beneath `%LOCALAPPDATA%\StandardLogisticsUnitTools\Recovery`. Validate paths; write `.tmp`, flush/close, `MoveFileExW` replace/write-through; delete only matching temp/final files. All declarations are central, pointer-safe.
- Recovery JSON excludes profile display, employee number, PIN/tokens, diagnostics, API base URL. Ciphertext must not contain fictional plaintext markers.
- Save sequence is recovery snapshot → incident PATCH → each dirty report PATCH with base revision and distinct action idempotency keys → apply only server revisions/editor metadata. Delete snapshot only after all required saves succeed. A partial/network failure preserves work/snapshot and never reports success.
- A 409 never auto-writes/merges. Keep local controls; offer only Open newest (GET), Save local work as a separate recovery revision (dedicated idempotent POST), or Cancel.
- Restore creates a new current immutable revision; historical rows never change. Completed/Archived remain editable according to server authorization.
- Startup recovery appears after auth/profile/policy. Same-base recovery requires confirmation; newer cloud state creates a separate recovery revision. Older-than-seven-day files require explicit discard.
- Forced-termination test may close only its own test Access instance; never kill unrelated Access.
- Never log/store plaintext report/field notes/identity/credentials outside encrypted recovery and authoritative cloud requests. No local tables.

## TDD

1. Add exact failing tab/revision/autosave/recovery/conflict tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportTabSwitch_Run,TestAutosave_Run,TestRecovery_Run,TestConflict_Run
```

Expected: FAIL because `CReportState`, `MarkDirty`, and `IRecoveryStore` are undefined.

3. Implement every remaining checkbox in order, including exact control list/state fields, monotonic clock, atomic encryption, save sequencing, revision UI, startup decisions, and forced-termination COM test.
4. Focused/regression:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportTabSwitch_Run,TestAutosave_Run,TestRecovery_Run,TestConflict_Run
python -m pytest tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py -q -m access_com -k "report or revision or autosave or recovery or conflict"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: tab edits persist; exactly one idle save at 60s; snapshots ciphertext; failure preserves work; complete success removes matching snapshot; 409 causes no automatic write; newer-state recovery is a separate revision; forced termination offers recovery.

## Scope/acceptance/handoff

Fictional fixtures only. No backend/OpenAPI changes, local tables, automatic merge, deletion/history mutation, Admin functionality, Word export, browser/deployment/updater/signing, direct cloud calls, or unrelated refactor. Accept only with every checkbox and security invariant proven, source/binary parity clean, unbound/accessibility rules met, and `git diff --name-only $taskBase` allowlisted. Never stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAutosave.bas',
  'access-client/src/modules/modRecovery.bas',
  'access-client/src/modules/modConflict.bas',
  'access-client/src/classes/IRecoveryStore.cls',
  'access-client/src/classes/CAtomicRecoveryStore.cls',
  'access-client/src/classes/IClock.cls',
  'access-client/src/classes/CSystemClock.cls',
  'access-client/src/classes/CReportState.cls',
  'access-client/src/forms/frmReportEditor.txt',
  'access-client/src/forms/frmRevisionHistory.txt',
  'access-client/src/forms/frmRevisionCompare.txt',
  'access-client/src/forms/frmRevisionConflict.txt',
  'access-client/src/forms/frmRecoveryPrompt.txt',
  'access-client/src/forms/sfrmReportTabs.txt',
  'access-client/src/forms/sfrmRevisionList.txt',
  'access-client/tests/vba/TestAutosave.bas',
  'access-client/tests/vba/TestRecovery.bas',
  'access-client/tests/vba/TestConflict.bas',
  'access-client/tests/vba/classes/CInMemoryRecoveryStore.cls',
  'access-client/tests/vba/classes/CFakeClock.cls',
  'access-client/tests/fixtures/reports/report-detail.json',
  'access-client/tests/fixtures/reports/revision-page.json',
  'access-client/tests/fixtures/reports/revision-conflict.json',
  'access-client/tests/fixtures/reports/recovery-created.json',
  'access-client/tests/fixtures/recovery/workflow-state-v1.json',
  'tests/access/test_recovery_after_termination.py',
  'access-client/src/modules/modWin32.bas',
  'access-client/src/modules/modReportWorkflow.bas',
  'access-client/src/modules/modAppStartup.bas',
  'access-client/src/modules/modAppState.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/classes/CWorkflowState.cls',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestReportWorkflow.bas',
  'access-client/tests/vba/TestRunner.bas',
  'tests/access/fake_api.py',
  'tests/access/test_user_workflows.py',
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
git commit -m "feat(access): add revision-safe recovery editing"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff branch/SHAs/files/red/final tests, actual bitness, snapshot plaintext scan, forced-termination ownership evidence, diff/parity, commit, deviations/NOT RUN.

Stop on schema ambiguity, unsafe path/encryption/deletion, stale-overwrite risk, partial-success ambiguity, dirty paths, ancestry/baseline/COM/compile failure, or forbidden file need. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/change policy/reset or destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add revision-safe recovery editing`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
