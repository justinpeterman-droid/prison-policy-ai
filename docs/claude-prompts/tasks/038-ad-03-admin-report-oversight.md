# Claude Code Prompt 038 — AD-03: All-report search, edit, revision restore, transfer, and single/bulk export

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **038**, task **AD-03**. Deliver server-authorized Admin report search/view/edit/reopen, immutable restore, owner transfer, exact saved-revision DOCX export, and bounded manifested bulk export. Every action must be attributed; no history is overwritten or deleted.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ad-03-report-oversight`

## Reading/preflight

Read `AGENTS.md`; roadmap sequence 038/gates; Admin plan globals and full exact heading `### Task AD-03: All-report search, edit, revision restore, transfer, and single/bulk export`; Admin/report specs; exact Admin report OpenAPI contracts. Verify AD-01/AD-02, AC-01–AC-09, and backend prerequisites reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Use current reviewed `HEAD`, never baseline, after reading reviewed intervening changes. Stop on failed ancestry/unreviewed conflict/missing prerequisite/dirty overlap. Preserve user work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAdminReports.bas`
- `access-client/src/classes/CAdminReportFilter.cls`
- `access-client/src/forms/frmAdminAllReports.txt`
- `access-client/src/forms/frmAdminTransferReport.txt`
- `access-client/src/forms/frmAdminBulkExport.txt`
- `access-client/src/forms/sfrmAdminReportResults.txt`
- `access-client/tests/vba/TestAdminReports.bas`
- `access-client/tests/fixtures/admin/report-page.json`
- `access-client/tests/fixtures/admin/report-detail.json`
- `access-client/tests/fixtures/admin/report-revisions-page.json`
- `access-client/tests/fixtures/admin/report-revision-detail.json`
- `access-client/tests/fixtures/admin/report-restored.json`
- `access-client/tests/fixtures/admin/report-transferred.json`
- `access-client/tests/fixtures/admin/report-saved.json`
- `access-client/tests/fixtures/admin/bulk-export.zip`
- `access-client/tests/fixtures/admin/bulk-export-metadata.json`
- `tests/access/test_admin_reports.py`

Modify only:

- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modAdminAuth.bas`
- `access-client/src/modules/modReportWorkflow.bas`
- `access-client/src/modules/modAutosave.bas`
- `access-client/src/modules/modConflict.bas`
- `access-client/src/modules/modRecovery.bas`
- `access-client/src/modules/modWordExport.bas`
- `access-client/src/modules/modErrors.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/classes/CWorkflowState.cls`
- `access-client/src/forms/frmAdminOverview.txt`
- `access-client/src/forms/frmReportEditor.txt`
- `access-client/src/forms/frmRevisionHistory.txt`
- `access-client/src/forms/frmRevisionCompare.txt`
- `access-client/src/forms/frmRevisionConflict.txt`
- `access-client/src/forms/frmExport.txt`
- `access-client/src/forms/frmConfirmAction.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestReportWorkflow.bas`
- `access-client/tests/vba/TestConflict.bas`
- `access-client/tests/vba/TestWordExport.bas`
- `access-client/tests/vba/TestRunner.bas`
- `tests/unit/test_access_fixture_contracts.py`
- `tests/unit/test_access_route_parity.py`
- `tests/unit/test_access_vba_safety.py`
- `tests/access/fake_api.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying:

- `openapi/access-v1.yaml`
- `access-client/tests/fixtures/word/fictional-report.docx`

No other files.

## Locked report/wire rules

- Consume AD grants/staff search and existing editor/autosave/recovery/conflict/export abstractions. Produce `CAdminReportFilter`, exact Admin search/open/save/restore/transfer/single/bulk functions/routes, `AdminMode`, and viewed-owner display.
- Search is authorization-first, server-side cursor pagination, default 50/cap 100, exact structured filters only (including approved employee/incident/inmate/status/category/date/update fields). Results are summaries, never narrative/notes. Search and view audits are distinct.
- Opening reuses existing editor with visible “editing another employee’s report” attribution. Admin edits use same autosave/recovery/conflict safety, base revision/idempotency, `admin_edit` attribution, and immutable next revision. Completed/Archived stay editable.
- A 409 never overwrites; preserve local controls and existing compare/recovery choices.
- Restore exact historical revision through `POST /api/v1/admin/reports/{id}/restore` with body revision number, fresh purpose `report_restore`, idempotency; append new current revision and retain all historical rows.
- Transfer keeps canonical report ID, requires active staff UUID, reason, confirmation, fresh `report_transfer`, transactional relationship update, immutable revision/audit. Never directly edit owner/account identifiers.
- Single export uses explicit saved revision and existing atomic employee-chosen DOCX behavior. Bulk requires nonempty explicit filters, reason, fresh `bulk_export`, cap 100, deterministic manifest, partial failure accounting, ZIP MIME/hash/size/filename/request metadata, atomic write. No bulk narrative edit.
- All forms unbound; no delete/overwrite/history mutation/local tables. Never log report/identity/filter-sensitive content or credentials.

## TDD

1. Add exact failing VBA/COM report-oversight tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminReports_Run
python -m pytest tests/access/test_admin_reports.py -q -m access_com
```

Expected: compile fails because `CAdminReportFilter` and `LoadAdminReportPage` are undefined; COM fails because `frmAdminAllReports` is absent.

3. Execute every remaining checkbox exactly, including route/schema fixtures, filters, attribution banner, restore/transfer, binary validation, fake audits.
4. Focused/regression:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminReports_Run,TestReportTabSwitch_Run,TestAutosave_Run,TestRecovery_Run,TestConflict_Run,TestWordExport_Run
python -m pytest tests/access/test_admin_reports.py tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py -q -m access_com -k "report or revision or restore or transfer or conflict or recovery or export"
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py tests/unit/test_filler_boxes.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: structured search, attributed Admin editing, immutable restore/transfer, conflict preservation, exact single export, bounded manifested bulk export, and all User editor/recovery/export regressions pass.

## Scope/acceptance/commit

Fictional fixtures only. No delete/bulk narrative mutation, backend/OpenAPI/local tables, audit/health/handoff, installer/updater/deployment/signing/unrelated refactor. Accept only with every checkbox/purpose/audit/revision/export/privacy/accessibility/source-parity test and allowlisted `git diff --name-only $taskBase`. Never stage `.superpowers/` or generated exports.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAdminReports.bas',
  'access-client/src/classes/CAdminReportFilter.cls',
  'access-client/src/forms/frmAdminAllReports.txt',
  'access-client/src/forms/frmAdminTransferReport.txt',
  'access-client/src/forms/frmAdminBulkExport.txt',
  'access-client/src/forms/sfrmAdminReportResults.txt',
  'access-client/tests/vba/TestAdminReports.bas',
  'access-client/tests/fixtures/admin/report-page.json',
  'access-client/tests/fixtures/admin/report-detail.json',
  'access-client/tests/fixtures/admin/report-revisions-page.json',
  'access-client/tests/fixtures/admin/report-revision-detail.json',
  'access-client/tests/fixtures/admin/report-restored.json',
  'access-client/tests/fixtures/admin/report-transferred.json',
  'access-client/tests/fixtures/admin/report-saved.json',
  'access-client/tests/fixtures/admin/bulk-export.zip',
  'access-client/tests/fixtures/admin/bulk-export-metadata.json',
  'tests/access/test_admin_reports.py',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modAdminAuth.bas',
  'access-client/src/modules/modReportWorkflow.bas',
  'access-client/src/modules/modAutosave.bas',
  'access-client/src/modules/modConflict.bas',
  'access-client/src/modules/modRecovery.bas',
  'access-client/src/modules/modWordExport.bas',
  'access-client/src/modules/modErrors.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/classes/CWorkflowState.cls',
  'access-client/src/forms/frmAdminOverview.txt',
  'access-client/src/forms/frmReportEditor.txt',
  'access-client/src/forms/frmRevisionHistory.txt',
  'access-client/src/forms/frmRevisionCompare.txt',
  'access-client/src/forms/frmRevisionConflict.txt',
  'access-client/src/forms/frmExport.txt',
  'access-client/src/forms/frmConfirmAction.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestReportWorkflow.bas',
  'access-client/tests/vba/TestConflict.bas',
  'access-client/tests/vba/TestWordExport.bas',
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
git commit -m "feat(access): add attributed admin report oversight"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff SHAs/files/red/final tests, bitness, structured-query/audit/idempotency/revision/manifest evidence, diff/parity, commit, deviations/NOT RUN.

Stop on non-authorized/unbounded search, missing filter, stale overwrite, missing attribution/revision/history, unsafe transfer, unbounded/unmanifested export, metadata gap, dirty overlap, unreviewed prerequisite, or COM/compile failure. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/change policy/reset/destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add attributed admin report oversight`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
