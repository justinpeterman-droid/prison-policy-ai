# Claude Code Prompt 034 — AC-08: Owned/prepared history, Policy Expert citations, and account/session screens

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **034**, task **AC-08**. Deliver authorization-scoped owned/prepared report history, bounded dashboard summaries, session-only Policy Expert conversation with citations, read-only employee profile, and current-user session controls. The same canonical report must appear through the correct owner/preparer relationships from any authorized workstation.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-08-history-policy`

## Read/preflight

Read `AGENTS.md`; roadmap gates/sequence 034; Access User plan globals and complete exact heading `### Task AC-08: Owned/prepared history, Policy Expert citations, and account/session screens`; user/report specs; exact OpenAPI report-list/policy/session/profile contracts. AC-01–AC-07 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestor/green baseline/clean task paths. Preserve user work; if main advanced, read reviewed plan/OpenAPI diffs since baseline and verify AC-01–AC-07 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modPolicyExpert.bas`
- `access-client/src/classes/CPagedResult.cls`
- `access-client/src/forms/frmReportHistory.txt`
- `access-client/src/forms/frmPolicyExpert.txt`
- `access-client/src/forms/frmAccount.txt`
- `access-client/src/forms/frmSessionList.txt`
- `access-client/src/forms/frmConfirmAction.txt`
- `access-client/src/forms/sfrmReportQueue.txt`
- `access-client/src/forms/sfrmPolicyCitations.txt`
- `access-client/src/forms/sfrmSessionResults.txt`
- `access-client/tests/vba/TestPolicyExpert.bas`
- `access-client/tests/fixtures/reports/owned-page.json`
- `access-client/tests/fixtures/reports/prepared-page.json`
- `access-client/tests/fixtures/policy/answer-with-citations.json`

Modify only:

- `access-client/src/modules/modReportWorkflow.bas`
- `access-client/src/modules/modAuth.bas`
- `access-client/src/modules/modAppStartup.bas`
- `access-client/src/modules/modNavigation.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/forms/frmDashboard.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestAuth.bas`
- `access-client/tests/vba/TestReportWorkflow.bas`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/fake_api.py`
- `tests/access/test_user_workflows.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. No other file.

## Locked interfaces/wire rules

- Consume authenticated session/profile, report list/detail/revisions/editor, `/api/v1/policy/questions`, and current-user session endpoints. Produce `LoadReportPage`, `AskPolicyQuestion`, `CPagedResult`, `LoadAccountSessions`, `RevokeSession`, bounded views.
- Report relationship is only `owned` or `prepared`; filters are status/incident date/category/updated date; server authorizes and cursor-paginates. Never send client identity or wildcard narrative search. List/dashboard rows are bounded summaries—no narrative, notes, extracted facts, tokens.
- Owner/preparer views reference one canonical report ID. Selecting loads authorized detail on demand. Completed/Archived remain editable; archive reversible through server status.
- Policy question uses one UUID idempotency key per explicit Ask, reused for retry; new click gets new key. Send at most the last four complete turns; keep all conversation/citations in memory only and discard on clear/close. Use the 90-second policy timeout.
- Handle `request_in_progress` by waiting; `idempotent_response_unavailable` explains that prior sensitive output was not retained and requires explicit Ask again. Never silently resend.
- Preserve ordered server citations/title/passage and exact disclaimer from the plan. Policy guidance never enters report facts automatically.
- Profile fields are read-only/server-authoritative. Sessions show bounded device/timing/persistence/current fields only—never tokens/hashes/IP/private identity. Revoke noncurrent via exact DELETE; current revoke uses logout cleanup. Confirm current-computer vs everywhere effects exactly.
- Forms remain unbound; no Access tables. Never log/store identity, report content, policy text, credentials, session values.

## TDD

1. Add exact failing owned/prepared pagination, Policy, account/session tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportHistory_Run,TestPolicyExpert_Run,TestAuth_Run
```

Expected: FAIL because `CPagedResult`, `LoadReportPage`, and `AskPolicyQuestion` are undefined.

3. Execute every remaining task checkbox exactly, including fake endpoints and COM keyboard journeys.
4. Focused/regression:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportHistory_Run,TestPolicyExpert_Run,TestAuth_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "history or policy or account or session or dashboard"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: scoped summaries; canonical report in correct relationship fixtures; at most four Policy turns/two ordered citations; account identity uneditable; revoke/logout clear only intended sessions.

## Scope/acceptance/handoff

Fictional fixtures only. No Admin UI, backend/OpenAPI edits, local tables, narrative search, persistent Policy history, report mutation beyond existing editor, browser/deployment/updater/signing, direct cloud calls, or unrelated refactor. Accept only when all checkboxes/schemas/privacy/accessibility/source parity/tests and `git diff --name-only $taskBase` allowlist pass. Do not stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modPolicyExpert.bas',
  'access-client/src/classes/CPagedResult.cls',
  'access-client/src/forms/frmReportHistory.txt',
  'access-client/src/forms/frmPolicyExpert.txt',
  'access-client/src/forms/frmAccount.txt',
  'access-client/src/forms/frmSessionList.txt',
  'access-client/src/forms/frmConfirmAction.txt',
  'access-client/src/forms/sfrmReportQueue.txt',
  'access-client/src/forms/sfrmPolicyCitations.txt',
  'access-client/src/forms/sfrmSessionResults.txt',
  'access-client/tests/vba/TestPolicyExpert.bas',
  'access-client/tests/fixtures/reports/owned-page.json',
  'access-client/tests/fixtures/reports/prepared-page.json',
  'access-client/tests/fixtures/policy/answer-with-citations.json',
  'access-client/src/modules/modReportWorkflow.bas',
  'access-client/src/modules/modAuth.bas',
  'access-client/src/modules/modAppStartup.bas',
  'access-client/src/modules/modNavigation.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/forms/frmDashboard.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestAuth.bas',
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
git commit -m "feat(access): add report history and policy expert"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff branch/SHAs/files/red/final results, API call counts/idempotency, actual bitness, diff/parity, commit, deviations/NOT RUN.

Stop on schema/authorization ambiguity, missing idempotency behavior, sensitive persistence/logging, dirty path, ancestry/baseline/COM/compile failure, or forbidden scope. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/alter machine policy/reset or destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add report history and policy expert`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
