# Claude Code Prompt 039 — AD-04: Read-only audit and sanitized system health

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **039**, task **AD-04**. Deliver read-only, bounded Admin audit search/export and sanitized operational health/backup status. Admins get actionable information without report content, credentials, cloud internals, mutation controls, or raw errors.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ad-04-audit-health`

## Read/preflight

Read `AGENTS.md`; roadmap sequence 039/gates; Admin plan globals and complete exact heading `### Task AD-04: Read-only audit and sanitized system health`; Admin/report/deployment specs; RP-10/OpenAPI overview/audit/health contracts. Verify AD-01–AD-03 and all prerequisites reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Use current reviewed HEAD only; read reviewed changes since baseline. Stop on failed ancestry/unreviewed conflict/missing prerequisites/overlap. Preserve user work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAdminAudit.bas`
- `access-client/src/modules/modAdminHealth.bas`
- `access-client/src/classes/CAdminAuditFilter.cls`
- `access-client/src/forms/frmAdminAudit.txt`
- `access-client/src/forms/frmAdminHealth.txt`
- `access-client/src/forms/sfrmAdminAuditResults.txt`
- `access-client/src/forms/sfrmAdminHealthResults.txt`
- `access-client/tests/vba/TestAdminAudit.bas`
- `access-client/tests/vba/TestAdminHealth.bas`
- `access-client/tests/fixtures/admin/audit-page.json`
- `access-client/tests/fixtures/admin/audit-export.csv`
- `access-client/tests/fixtures/admin/audit-export-metadata.json`
- `access-client/tests/fixtures/admin/health-operational.json`
- `access-client/tests/fixtures/admin/health-degraded.json`
- `access-client/tests/fixtures/admin/health-unavailable.json`
- `tests/access/test_admin_operations.py`

Modify only:

- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modAdminAuth.bas`
- `access-client/src/modules/modErrors.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/forms/frmAdminOverview.txt`
- `access-client/src/forms/frmExport.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestRunner.bas`
- `tests/unit/test_access_fixture_contracts.py`
- `tests/unit/test_access_route_parity.py`
- `tests/unit/test_access_vba_safety.py`
- `tests/access/fake_api.py`
- `access-client/SLUT-Client.accdb`

Consume without modifying: `openapi/access-v1.yaml`. No other files.

## Locked interfaces/privacy rules

- Consume Admin grants/activity, paging, safe byte export/dialog/atomic write, safe errors/logging/theme/accessibility, exact RP-10 schemas. Produce `CAdminAuditFilter`, `LoadAdminAuditPage`, `ExportAdminAuditSummary`, `LoadAdminHealth`, and exact route helpers.
- Audit list is server-authorized/cursor-paginated/bounded and immutable/read-only. Filters/actions/result/reference/actor/timestamps are safe summaries. Never include report narrative/field notes/PIN/token/hash/unrestricted detail JSON; expose no update/delete route.
- Audit CSV export requires exact `audit_export` step-up, reason, idempotency, bounds, audit record, safe filename/MIME/hash/size/request metadata, employee-chosen atomic output. Do not commit generated export.
- Health is read-only and sanitized: Operational/Degraded/Unavailable plus approved service/backup/restore-exercise/last-success/age/request fields. No credentials/service account/connection string/raw stack/Cloud Logging payload/internal URL or mutation/control route. Never infer missing backup/restore fields from local/cloud tools.
- Inject sensitive markers into fake internal errors and prove none reaches response, UI, state, safe log, or COM JSON.
- All forms unbound; no local tables. Use text plus color, labels, keyboard/focus/scaling requirements.

## TDD

1. Add exact failing audit/health VBA and COM tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAudit_Run,TestAdminHealth_Run
python -m pytest tests/access/test_admin_operations.py -q -m access_com
```

Expected: compile fails because `CAdminAuditFilter`, `LoadAdminAuditPage`, and `LoadAdminHealth` do not exist; COM fails because forms are absent.

3. Execute every task checkbox exactly, including routes/fixtures, bounded export, health states, fake sensitive failures.
4. Focused/regression:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAudit_Run,TestAdminHealth_Run,TestAdminAuthorization_Run,TestSafeLog_Run
python -m pytest tests/access/test_admin_operations.py tests/access/test_admin_authorization.py -q -m access_com
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

Expected: audit search bounded/read-only; export exact/attributed; health actionable/sanitized/read-only; sensitive markers absent; User/prior Admin compile/tests green.

## Scope/acceptance/commit

Fictional fixtures only. No infrastructure controls/gcloud/SQL/cloud-console launch, raw operational logs, backend/OpenAPI/local tables, report/account mutation, Review Lab, deployment/signing/unrelated refactor. Accept only after every checkbox/schema/purpose/privacy/accessibility/source-parity test and `git diff --name-only $taskBase` is fully allowlisted. Never stage `.superpowers/` or generated CSV.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAdminAudit.bas',
  'access-client/src/modules/modAdminHealth.bas',
  'access-client/src/classes/CAdminAuditFilter.cls',
  'access-client/src/forms/frmAdminAudit.txt',
  'access-client/src/forms/frmAdminHealth.txt',
  'access-client/src/forms/sfrmAdminAuditResults.txt',
  'access-client/src/forms/sfrmAdminHealthResults.txt',
  'access-client/tests/vba/TestAdminAudit.bas',
  'access-client/tests/vba/TestAdminHealth.bas',
  'access-client/tests/fixtures/admin/audit-page.json',
  'access-client/tests/fixtures/admin/audit-export.csv',
  'access-client/tests/fixtures/admin/audit-export-metadata.json',
  'access-client/tests/fixtures/admin/health-operational.json',
  'access-client/tests/fixtures/admin/health-degraded.json',
  'access-client/tests/fixtures/admin/health-unavailable.json',
  'tests/access/test_admin_operations.py',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modAdminAuth.bas',
  'access-client/src/modules/modErrors.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/forms/frmAdminOverview.txt',
  'access-client/src/forms/frmExport.txt',
  'access-client/src/manifest.json',
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
git commit -m "feat(access): add admin audit and health views"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff SHAs/files/red/final tests, bitness, exported fixture/hash bounds, sensitive-marker results, health state evidence, diff/parity, commit, deviations/NOT RUN.

Stop on sensitive audit/health fields, unbounded/mutable audit, missing export purpose/idempotency/audit, raw cloud details, missing backup/restore schema, dirty overlap, unreviewed prerequisite, or COM/compile failure. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/change policy/reset/destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): add admin audit and health views`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
