# Claude Code Prompt 040 — AD-05: One-time Review Lab handoff and full Admin/Windows regression

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **040**, task **AD-05**. Add the strictly validated one-time Admin Review Lab browser handoff, extend the existing smoke harness for the entire Admin journey, and produce honest source/build/authorization/accessibility evidence for each supported Windows/Access row. Access issues/opens the handoff only; it never redeems or reimplements Review Lab.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ad-05-review-lab-regression`

## Read/preflight

Read `AGENTS.md`; roadmap gates/sequence 040; Admin plan globals/completion gate and full exact heading `### Task AD-05: One-time Review Lab handoff and full Admin/Windows regression`; Admin/user/identity specs; exact handoff/client-policy OpenAPI. Verify AC-01–AC-09, AD-01–AD-04, ID-08, and backend prerequisites reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Branch from current reviewed `HEAD`, never baseline, after reading reviewed changes. Stop on ancestry failure/unreviewed conflict/missing prerequisites/overlap. Preserve user work.

## Exact allowlist

Create only:

- `access-client/src/modules/modAdminReviewLab.bas`
- `access-client/src/forms/frmAdminReviewLab.txt`
- `access-client/tests/vba/TestAdminReviewLab.bas`
- `access-client/tests/fixtures/admin/review-lab-handoff.json`
- `access-client/tests/fixtures/errors/review-lab-handoff-invalid.json`
- `tests/access/test_admin_review_lab.py`
- `tests/access/test_admin_smoke.py`

Modify only:

- `access-client/src/modules/modApiRoutes.bas`
- `access-client/src/modules/modAdminAuth.bas`
- `access-client/src/modules/modNavigation.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/forms/frmAdminOverview.txt`
- `access-client/src/forms/frmShell.txt`
- `access-client/src/manifest.json`
- `access-client/build/InvokeAccessSmokeTests.ps1`
- `access-client/build/ScanAccessSource.ps1`
- `access-client/build/ValidateAccessBuild.ps1`
- `access-client/build/build-matrix.example.json`
- `access-client/tests/vba/TestRunner.bas`
- `access-client/tests/vba/classes/CFakeProcessLauncher.cls`
- `tests/unit/test_access_source_layout.py`
- `tests/unit/test_access_fixture_contracts.py`
- `tests/unit/test_access_route_parity.py`
- `tests/unit/test_access_vba_safety.py`
- `tests/access/conftest.py`
- `tests/access/fake_api.py`
- `tests/access/access_com.py`
- `tests/access/test_user_workflows.py`
- `access-client/README.md`
- `access-client/SLUT-Client.accdb`

Consume without modifying:

- `openapi/access-v1.yaml`
- `access-client/build/AccessBuild.Common.psm1`
- `access-client/build/ExportAccessSource.ps1`
- `access-client/build/ImportAccessSource.ps1`
- `access-client/build/BuildAccde.ps1`

No other paths.

## Locked handoff and acceptance rules

- Consume existing Admin grants/navigation, `TrustedReviewLabOrigin`, existing process launcher/fake and source/build/static/COM harnesses. Produce `OpenAdminReviewLab`, exact route, `Test_RunAdminSmokeWorkflow`, final evidence. Do not create a second launcher or test runner.
- Only Admin with active Center elevation plus fresh exact purpose `review_lab_handoff` may issue. One idempotency key per explicit action. Request body contains no PIN, Access/renewal token, actor, role, shared code, or fragment.
- Response is one HTTPS URL whose origin matches policy-approved `TrustedReviewLabOrigin()` exactly including port, followed by exactly `/access-handoff#` plus one nonempty fragment. Reject query, second `#`, user info, encoded authority delimiter, control/control-normalization, redirects, path normalization, different origin, unloaded policy. Never compare to API base or trust Host/form/registry/table.
- Handoff expiry is 60 seconds and one-time. Access calls `OpenUri` exactly once then immediately clears all URL/fragment references; URL must never appear in state/log/recovery. Second use requires new issue/step-up.
- Access never redeems fragment, sets browser cookies, sends Access credentials to browser, uses legacy shared Admin code, or displays/reimplements Review Lab content.
- Unit/COM uses fake launcher; never launch agency browser in tests or target production.
- Extend existing smoke with exact staged Admin User isolation/elevation/accounts/PIN/reports/revisions/transfer/exports/audit/health/handoff/expiry/restart checks. Safe JSON has stage/request metadata only.
- Each Windows row uses matching Access/PowerShell/Word bitness, isolated temp files, loopback fake API, no orphan process, source round-trip/static/VBA/COM/ACCDE/accessibility checks. Never infer unrun rows.
- All forms unbound/table schema empty; fictional data only; no sensitive values or generated artifacts committed.

## TDD and gates

1. Add exact failing handoff VBA/COM tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminReviewLab_Run
python -m pytest tests/access/test_admin_review_lab.py -q -m access_com
```

Expected: compile fails because `OpenAdminReviewLab`/route do not exist; COM fails because form absent.

3. Add failing Admin smoke test before extending harness:

```powershell
python -m pytest tests/access/test_admin_smoke.py -q -m access_com
```

Expected: FAIL because smoke has no `-IncludeAdmin` and `Test_RunAdminSmokeWorkflow` is undefined.

4. Execute every remaining checkbox exactly, including strict URL parsing/clear, no second runner, source/static/com rules.
5. Full gate:

```powershell
python -m pytest tests/unit/test_access_source_layout.py tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests Test_RunAll
python -m pytest tests/access/test_reconstruction.py -q -m access_com
python -m pytest tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py tests/access/test_admin_authorization.py tests/access/test_admin_accounts.py tests/access/test_admin_reports.py tests/access/test_admin_operations.py tests/access/test_admin_review_lab.py tests/access/test_admin_smoke.py -q -m access_com
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
python -m pytest -q
git diff --check
```

6. For each approved real inventory row, use matching bitness:

```powershell
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database $env:TEMP\SLUT-Admin-Matrix.accdb -Configuration Test
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database $env:TEMP\SLUT-Admin-Matrix.accdb -Source access-client/src -Platform x64
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database $env:TEMP\SLUT-Admin-Matrix.accdb -Output $env:TEMP\SLUT-Admin-Matrix.accde -Platform x64 -ClientVersion 0.1.0
powershell.exe -NoProfile -File access-client/build/InvokeAccessSmokeTests.ps1 -Database $env:TEMP\SLUT-Admin-Matrix.accde -FakeApiUrl http://127.0.0.1:8765 -Platform x64 -IncludeAdmin
```

Expected: full User/Admin/static/reconstruction suite passes; no sensitive state; each claimed row passes exact matrix/manual accessibility conditions. Failures/NOT RUN remain unsupported.

## Scope/commit/handoff

No browser Review Lab implementation, backend/OpenAPI edits, local tables, production host/data/browser, signing/installer/updater/deployment, new runner/launcher, or unrelated refactor. `git diff --name-only $taskBase` must be allowlisted; never stage `.superpowers/`, ACCDE, exports, URLs/fragments, secrets, machine identity.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modAdminReviewLab.bas',
  'access-client/src/forms/frmAdminReviewLab.txt',
  'access-client/tests/vba/TestAdminReviewLab.bas',
  'access-client/tests/fixtures/admin/review-lab-handoff.json',
  'access-client/tests/fixtures/errors/review-lab-handoff-invalid.json',
  'tests/access/test_admin_review_lab.py',
  'tests/access/test_admin_smoke.py',
  'access-client/src/modules/modApiRoutes.bas',
  'access-client/src/modules/modAdminAuth.bas',
  'access-client/src/modules/modNavigation.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/forms/frmAdminOverview.txt',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/manifest.json',
  'access-client/build/InvokeAccessSmokeTests.ps1',
  'access-client/build/ScanAccessSource.ps1',
  'access-client/build/ValidateAccessBuild.ps1',
  'access-client/build/build-matrix.example.json',
  'access-client/tests/vba/TestRunner.bas',
  'access-client/tests/vba/classes/CFakeProcessLauncher.cls',
  'tests/unit/test_access_source_layout.py',
  'tests/unit/test_access_fixture_contracts.py',
  'tests/unit/test_access_route_parity.py',
  'tests/unit/test_access_vba_safety.py',
  'tests/access/conftest.py',
  'tests/access/fake_api.py',
  'tests/access/access_com.py',
  'tests/access/test_user_workflows.py',
  'access-client/README.md',
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
git commit -m "test(access): complete admin handoff and Windows gates"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff branch/start/end/commit SHAs, files, red/final results, exact origin/fragment-clearing evidence without token, per-row versions/bitness/scaling/results/hashes without workstation identity, orphan check, unsupported rows, diff/parity, deviations.

Stop on invalid origin/path/fragment/expiry/one-time/purpose/audit behavior; expectation that Access redeem/cookie/reimplement; production target/real data/browser; COM/bitness/round-trip/reference/compile/ACCDE/static/fake/timeout/orphan/accessibility failure; dirty overlap/unreviewed prerequisite. Never push/merge/deploy/apply/sign/publish/install/access production/request secrets/change policy/reset/destroy work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `test(access): complete admin handoff and Windows gates`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
