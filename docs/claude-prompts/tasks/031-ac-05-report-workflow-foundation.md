# Claude Code Prompt 031 — AC-05: Six-step workflow foundation, officer selection, and field notes

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **031**, task **AC-05**. Add the unbound six-step workflow foundation, server-UUID officer selection, creation of one canonical incident/report relationship, and editable field notes. The signed-in employee is auto-selected, may prepare a report for another officer without impersonation, and receives no duplicated local/cloud report copy.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-05-incident-workflow`

## Reading/preflight

Read `AGENTS.md`; roadmap sequence 031/gates; Access User plan global constraints and complete exact heading `### Task AC-05: Six-step workflow foundation, officer selection, and field notes`; user-client/report specs; consumed OpenAPI staff/incident schemas. AC-01–AC-04 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestry/green baseline/clean task paths. Never reset, clean, stash, overwrite, or discard. If main advanced, read reviewed plan/OpenAPI changes since baseline and verify AC-01–AC-04 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modReportWorkflow.bas`
- `access-client/src/classes/CWorkflowState.cls`
- `access-client/src/forms/frmIncidentOfficers.txt`
- `access-client/src/forms/frmFieldNotes.txt`
- `access-client/src/forms/sfrmStaffSearchResults.txt`
- `access-client/tests/vba/TestReportWorkflow.bas`
- `access-client/tests/fixtures/staff/search-results.json`
- `access-client/tests/fixtures/reports/incident-created-multi-officer.json`

Modify only:

- `access-client/src/forms/frmShell.txt`
- `access-client/src/forms/frmDashboard.txt`
- `access-client/src/modules/modNavigation.bas`
- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modAppState.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/fake_api.py`
- `tests/access/test_user_workflows.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. Plans/specs are read-only; no other file.

## Locked interfaces/wire rules

- Consume `CurrentProfile`, `NewApiRequest`, `ApiSend`, routes, `JsonSerialize`, success parser, `NavigateTo`, `ApplicationWritesAllowed`, and AC-04 `FieldNotesMaxCharacters() As Long` from the validated in-memory client policy.
- Produce `SearchActiveStaff`, `BeginNewIncident`, `SetFieldNotes`; `CWorkflowState`; `StartNewReport`, `ShowWorkflowStep`, `CurrentWorkflow`; Step 1/2 test hooks.
- Signed-in identity comes only from authenticated server profile UUID and is auto-selected. Search returns active staff UUIDs; never submit owner/preparer/account/employee-number identity fields or staff without UUIDs.
- Preparing another officer's report does not log into that account and does not create a copy. One canonical incident/report maintains owner/preparer/reporting-officer relationships server-side.
- Initialize every collection/dictionary in `Class_Initialize`; no form owns canonical state. Steps cannot be skipped when prerequisites are missing; AC-05 enables only Steps 1 and 2.
- `SetFieldNotes(state, value)` consumes AC-04 `FieldNotesMaxCharacters()` directly and uses a surrogate-pair-aware counter matching Pydantic decoded-Unicode-code-point length: a valid high/low pair counts as one, an unpaired surrogate is invalid, and no normalization occurs. It remains editable, accepts exactly 30,000 code points, and rejects 30,001 before any API/AI call without replacing the last accepted value. It has no caller-supplied maximum, duplicate literal/constant, environment/version/local source, or undefined-maximum stop because AC-04 already validates/stores the required policy field. The visible count/bounds use that same counter and in-memory value.
- No AI classify/extract/generate/policy call occurs while typing. Continue is only the future submission boundary.
- Writes honor client read-only policy and use exact `/api/v1` schemas/idempotency. Forms are unbound; no local table/cache.
- Preserve phrase “field notes,” trust-first copy, fictional fixtures, keyboard/accessibility/scaling rules.

## TDD

1. Write exact failing workflow/unit/COM tests and fictional fixtures first. Replace the former arbitrary maximum parameter with `SetFieldNotes state, value`; assert a 30,000-code-point fictional value is retained and a 30,001-code-point value is rejected before the fake API or any AI route is called. Also prove one valid fictional non-BMP surrogate pair counts as one and an unpaired high/low surrogate is rejected without state mutation.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportWorkflow_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "officer or field_notes"
```

Expected: FAIL because `CWorkflowState` and `frmIncidentOfficers` do not exist.

3. Implement each remaining plan checkbox in order, including exact route helpers/fixture validation/forms/source export/fake call counts.
4. Focused/regression gate:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportWorkflow_Run,TestApiRoutes_Run,TestApiClient_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "officer or field_notes"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: server UUID auto-selects signed-in User; a second officer can be added; one canonical incident returns; notes remain editable; `SetFieldNotes` consumes the validated in-memory 30,000 limit and rejects 30,001 locally; no AI route before Continue; all forms unbound.

## Scope/acceptance

Use fictional values only. Never log/store identity, PIN/token, or field-note content. No local tables; no AI implementation, report editor/revisions, Admin behavior, backend/OpenAPI edits, browser/deployment/updater/signing, direct cloud calls, or unrelated refactor.

Accept only after every checkbox, exact relationship/wire rule, source parity, UI accessibility, tests, and `git diff --name-only $taskBase` allowlist pass. Do not stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modReportWorkflow.bas',
  'access-client/src/classes/CWorkflowState.cls',
  'access-client/src/forms/frmIncidentOfficers.txt',
  'access-client/src/forms/frmFieldNotes.txt',
  'access-client/src/forms/sfrmStaffSearchResults.txt',
  'access-client/tests/vba/TestReportWorkflow.bas',
  'access-client/tests/fixtures/staff/search-results.json',
  'access-client/tests/fixtures/reports/incident-created-multi-officer.json',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/forms/frmDashboard.txt',
  'access-client/src/modules/modNavigation.bas',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modAppState.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/manifest.json',
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
git commit -m "feat(access): add incident workflow foundation"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push.

## Handoff/stops

Report task, branch, SHAs, files, red/final results, 30,000/30,001 boundary evidence, fake API call counts, actual bitness, diff/parity, commit, deviations/NOT RUN. Stop on a contradiction between the already-reviewed AC-04 policy accessor and OpenAPI, identity ambiguity, duplicate report semantics, dirty paths, ancestry/baseline/COM/compile failure, or forbidden-file need. Never push/merge/deploy/apply/sign/publish/install/use production/request secrets/change machine policy/reset or destroy user work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add incident workflow foundation`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
