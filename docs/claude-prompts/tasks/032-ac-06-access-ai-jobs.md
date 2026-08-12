# Claude Code Prompt 032 — AC-06: AI jobs, classification/extraction, fact review, gaps, and resume

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **032**, task **AC-06**, exactly. Add durable Cloud Run AI-job submission/poll/resume orchestration, editable classification/extraction review, explicit charge/fact confirmation, server-defined gap questions, and generation gating. Employees stay in control; Access never invents facts or generates narrative locally.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-06-ai-review-jobs`

## Required reading/preflight

Read `AGENTS.md`; roadmap gates/sequence 032; Access User plan global constraints and complete heading `### Task AC-06: AI jobs, classification/extraction, fact review, gaps, and resume`; user/report specs; exact OpenAPI job/gap/error schemas. AC-01–AC-05 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestor/green baseline and clean allowed paths. Never reset/stash/clean/discard user work. If reviewed main advanced, inspect reviewed plans/OpenAPI since baseline and verify AC-01–AC-05 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modJobs.bas`
- `access-client/src/classes/CJobState.cls`
- `access-client/src/forms/frmFactReview.txt`
- `access-client/src/forms/frmGapReview.txt`
- `access-client/src/forms/frmJobProgress.txt`
- `access-client/src/forms/sfrmGapQuestions.txt`
- `access-client/tests/vba/TestJobs.bas`
- `access-client/tests/fixtures/jobs/queued.json`
- `access-client/tests/fixtures/jobs/running.json`
- `access-client/tests/fixtures/jobs/succeeded.json`
- `access-client/tests/fixtures/jobs/failed.json`
- `access-client/tests/fixtures/errors/blocking-information-required.json`

Modify only:

- `access-client/src/modules/modReportWorkflow.bas`
- `access-client/src/modules/modAppStartup.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/classes/CWorkflowState.cls`
- `access-client/src/forms/frmFieldNotes.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestReportWorkflow.bas`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/fake_api.py`
- `tests/access/test_user_workflows.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. Plans/specs read-only; no other paths.

## Locked interfaces and wire behavior

- Consume AC-05 workflow, AC-02 API core, documented classify/extract/generate/disciplinary job routes, and server-defined gaps. Produce `SubmitJob`, `PollJob`, `NextPollDelaySeconds`, `ResumeKnownJobs`, `CJobState`, `ApplyClassificationResult`, `ApplyExtractionResult`, `ConfirmFactReview`, `CollectGapAnswers`, `CanSubmitGeneration`.
- Validate durable job ID, incident ID, type, state/stage/timestamps/result/error. Allowed states/stages are exactly those in the plan.
- One intended button action gets one idempotency key, reused until submission response; a new explicit action gets a new key. Disable the initiating control before POST. Same key with changed input is a conflict. Never duplicate a job/provider request.
- Poll by safe `GET /jobs/{job_id}` only. Use timer delays 2/4/6/8/10 seconds, cap at 10, disable timer during network calls to prevent reentry. Closing stops local polling, not cloud work; resume known IDs with GET only.
- Classification/charges/extracted facts/provenance are suggestions and remain editable. Charges may only use server-recognized codes; nothing is auto-applied. Explicit fact confirmation is required.
- Render server gaps for text/choice/yes_no. A blocking gap must be answered; `UNKNOWN` is valid only when `allow_unknown=true`. Server `422 blocking_information_required` remains authoritative and maps back without clearing answers.
- Generate submits confirmed facts/answers/charges/reporters/base revision, not invented values. Disciplinary job follows only when required; preserve already completed reports on later failure.
- Access never calls AI providers directly or generates narrative in VBA. Do not send raw notes outside exact OpenAPI request schemas.
- All UI remains unbound; no local tables. Preserve visible work on failure. Never log notes, facts, names, employee numbers, PINs, tokens, job results, or report content.

## TDD

1. Add exact failing backoff/job/idempotency plus fact/gap/COM tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestJobs_Run,TestReportWorkflow_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "classification or extraction or gap or job"
```

Expected: FAIL because `NextPollDelaySeconds`, `CJobState`, `frmFactReview`, and `frmGapReview` are undefined.

3. Execute every remaining task checkbox exactly, including fake queued→running→succeeded counters and changed-body idempotency conflict.
4. Focused/regression gate using actual Access bitness:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestJobs_Run,TestReportWorkflow_Run,TestErrors_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "classification or extraction or gap or job"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: exact backoff; no duplicate submission; edits/charge choices survive; blocking gaps prevent generation; allowed UNKNOWN works; failures preserve work; resume uses GET only.

## Scope, acceptance, handoff

Fictional fixtures only. No local tables, backend/OpenAPI changes, direct provider calls, autosave/recovery/editor work, Admin UI, browser/deployment/updater/signing, or unrelated refactor. Accept only when every checkbox passes, schemas/routes are exact, source/binary parity and unbound/accessibility rules hold, and `git diff --name-only $taskBase` is fully allowlisted. Do not stage `.superpowers/`.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modJobs.bas',
  'access-client/src/classes/CJobState.cls',
  'access-client/src/forms/frmFactReview.txt',
  'access-client/src/forms/frmGapReview.txt',
  'access-client/src/forms/frmJobProgress.txt',
  'access-client/src/forms/sfrmGapQuestions.txt',
  'access-client/tests/vba/TestJobs.bas',
  'access-client/tests/fixtures/jobs/queued.json',
  'access-client/tests/fixtures/jobs/running.json',
  'access-client/tests/fixtures/jobs/succeeded.json',
  'access-client/tests/fixtures/jobs/failed.json',
  'access-client/tests/fixtures/errors/blocking-information-required.json',
  'access-client/src/modules/modReportWorkflow.bas',
  'access-client/src/modules/modAppStartup.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/classes/CWorkflowState.cls',
  'access-client/src/forms/frmFieldNotes.txt',
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
git commit -m "feat(access): add resumable AI review workflow"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff task/branch/start/end/commit SHAs, files, red/final results, job POST/GET/idempotency counts, bitness, diff/parity, deviations and NOT RUN.

Stop on missing/invalid schemas, job/gap ambiguity, duplicate-provider risk, dirty paths, ancestry/baseline/COM/compile failure, or forbidden scope. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/alter machine policy/reset or destroy user work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add resumable AI review workflow`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
