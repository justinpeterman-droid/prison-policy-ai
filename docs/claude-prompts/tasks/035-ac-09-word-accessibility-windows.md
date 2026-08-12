# Claude Code Prompt 035 — AC-09: Saved-revision Word export, accessibility, static scans, COM smoke, and bitness acceptance

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **035**, task **AC-09**. Complete the User client with exact saved-revision DOCX export, the employee-approved update-grant/fake-launcher/named-pipe handoff, safe `ValidateRelease` hook, static security/accessibility scans, full COM smoke coverage, and honest per-Windows/Access-bitness acceptance evidence. Do not implement the .NET helper, sign, install, or publish an artifact.

Repository: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Branch: `claude/ac-09-user-acceptance`

## Reading/preflight

Read `AGENTS.md`; roadmap gates/wire contracts/sequence 035; Access User plan globals/completion gate and complete heading `### Task AC-09: Saved-revision Word export, accessibility, static scans, COM smoke, and bitness acceptance`; user/report/deployment specs; exact export and update-grant OpenAPI schema/headers. AC-01–AC-08 must be reviewed/merged.

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

Require correct root/ancestor/green baseline/clean task paths. Preserve user work. If main advanced, read reviewed plan/OpenAPI/template-test changes since baseline and verify AC-01–AC-08 reviews. Create the exact branch from current reviewed `HEAD`, never from the baseline SHA. Stop only for failed ancestry, unreviewed/conflicting changes, missing prerequisites, or overlapping allowed-path work.

## Exact allowlist

Create only:

- `access-client/src/modules/modWordExport.bas`
- `access-client/src/classes/IFileDialogService.cls`
- `access-client/src/classes/CAccessFileDialogService.cls`
- `access-client/src/classes/IProcessLauncher.cls`
- `access-client/src/classes/CWindowsProcessLauncher.cls`
- `access-client/src/forms/frmExport.txt`
- `access-client/tests/vba/TestWordExport.bas`
- `access-client/tests/vba/classes/CFakeFileDialogService.cls`
- `access-client/tests/vba/classes/CFakeProcessLauncher.cls`
- `access-client/tests/fixtures/word/fictional-report.docx`
- `access-client/tests/fixtures/word/fictional-report-metadata.json`
- `access-client/src/modules/modUpdater.bas`
- `access-client/src/classes/IUpdaterLauncher.cls`
- `access-client/src/classes/CWindowsUpdaterLauncher.cls`
- `access-client/tests/vba/TestUpdater.bas`
- `access-client/tests/vba/classes/CFakeUpdaterLauncher.cls`
- `access-client/tests/fixtures/policy/update-grant.json`
- `access-client/build/InvokeAccessSmokeTests.ps1`
- `access-client/build/ScanAccessSource.ps1`
- `tests/unit/test_access_vba_safety.py`

Modify only:

- `tests/access/conftest.py`
- `access-client/build/BuildAccde.ps1`
- `access-client/build/ValidateAccessBuild.ps1`
- `access-client/build/build-matrix.example.json`
- `access-client/src/modules/modWin32.bas`
- `access-client/src/modules/modApiClient.bas`
- `access-client/src/modules/modAppStartup.bas`
- `access-client/src/modules/modBuildInfo.bas`
- `access-client/src/modules/modClientPolicy.bas`
- `access-client/src/modules/modReportWorkflow.bas`
- `access-client/src/modules/modTestHooks.bas`
- `access-client/src/forms/frmReportEditor.txt`
- `access-client/src/forms/frmShell.txt`
- `access-client/src/forms/frmUpdateNotice.txt`
- `access-client/src/manifest.json`
- `access-client/tests/vba/TestRunner.bas`
- `tests/access/access_com.py`
- `tests/access/fake_api.py`
- `tests/access/test_user_workflows.py`
- `access-client/README.md`
- `access-client/SLUT-Client.accdb`

Consume without modifying:

- `openapi/access-v1.yaml`
- `templates/005_template_v3.docx`
- `tests/unit/test_filler_boxes.py`

No other paths.

## Locked interfaces, file, and Windows rules

- Consume `SaveNow`/revision/conflict behavior, byte responses, exact export endpoint, AC-01 harness. Produce `ExportSavedRevision`, dialog/process interfaces, `WriteBytesAtomically`, smoke/static scanners, matrix evidence.
- Consume the roadmap's locked update-grant and IPC contract. Produce `BeginApprovedUpdate(accessBitness, windowsArchitecture) As Boolean`, `IUpdaterLauncher.LaunchWithNamedPipe(pipeName, requestId) As Boolean`, and public COM-safe `ValidateRelease() As String` without modifying OpenAPI or implementing the server/helper.
- Only after employee acceptance, POST `/api/v1/client-updates/grants` with bearer, `X-Client-Version`, `X-Request-ID`, `Idempotency-Key`, and a body closed to exactly `access_bitness` plus `windows_architecture`. Release-one permitted combinations come only from OP-01: Access `x86|x64` on Windows `x64`, unless inventory explicitly approves another Windows architecture and schema/tests change together. Use `{"access_bitness":"x64","windows_architecture":"x64"}` as the exact fictional example, derive real values from the Access/Windows runtime, and reject unsupported combinations before launch. Require the closed first response fields `update_grant`, `expires_at`, `release_version`, `package_id`, `manifest_sha256`, `manifest_size_bytes`, `signer_thumbprint`, and `one_time_value_unavailable: false`. An identical replay has the same metadata, no grant, and `one_time_value_unavailable: true`; it must not launch.
- Keep the update grant in memory only. Launch the already installed trusted helper with only a cryptographically random pipe name and request ID as arguments. The helper owns a .NET `PipeOptions.CurrentUserOnly` pipe; Access sends one four-byte-length-prefixed UTF-8 closed `UpdateRequest` no larger than 64 KiB, then closes. Exact request keys are `schema_version`, `api_base_url`, `update_grant`, `expires_at`, `release_version`, `package_id`, `manifest_sha256`, `manifest_size_bytes`, `signer_thumbprint`, `access_bitness`, `windows_architecture`, `current_client_version`, `install_path`, and `request_id`.
- No bearer/update grant, endpoint, install path, person/report value, or sensitive data enters arguments, environment, registry, clipboard, disk, errors, diagnostics, or source-matched binaries. `signer_thumbprint` is descriptive metadata, never a trust anchor; trust follows only the approved signing/Windows publisher policy.
- `ValidateRelease` returns a closed bounded JSON object containing only `passed`, `client_version`, `source_commit`, `api_compatible`, `signature_valid`, `startup_valid`, and stable `failure_code`; no credentials, URL, storage/user/install paths, identity/report values, or raw exception.
- If dirty, save first and use returned explicit positive revision; stop on save/conflict. Export only a saved revision with one action idempotency key. Never regenerate AI text and never invoke legacy `/api/reports/download` or read the template locally.
- Validate DOCX MIME, nonzero exact bytes, safe filename, byte length, SHA-256, template version, request ID, report revision metadata. User chooses `.docx` path. Write same-directory temp then atomically replace only after full byte/hash checks. Word opens only after separate explicit consent.
- `ShellExecuteW` is pointer-safe in `modWin32`; file path must be absolute and URI HTTPS. Late-bind dialog/process; no Word reference.
- All forms remain unbound and table schema empty. Static scan must reject legacy/direct cloud endpoints, distributed/unsafe Win32 declarations, sensitive log parameters, unsafe `Kill`/`RmDir`, unauthorized absolute URLs/output paths, missing `Option Explicit`, and Admin objects.
- Keyboard/labels/focus/high contrast/non-color state/confirmations/long-operation behavior must pass at 1366×768 and 100/125/150%.
- Smoke covers full User journey listed in plan against loopback fake API only. Harness owns/closes its Access instance; no orphan or unrelated-process termination.
- Each matrix row is executed on matching Windows 11 Access/Word/PowerShell bitness. Never infer x86 from x64 or another version/channel. Generated ACCDE is unsigned/temp only; record hash, not artifact.
- Fictional data only. No sensitive content in source/log/recovery/fixtures except approved fictional fixture payloads.

## TDD and acceptance sequence

1. Add exact failing Word-export tests first.
2. Red run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestWordExport_Run
```

Expected: FAIL because `ExportSavedRevision` and `IFileDialogService` are undefined.

3. Before completing implementation, run smoke:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessSmokeTests.ps1 -Database access-client/SLUT-Client.accdb -FakeApiUrl http://127.0.0.1:8765 -Platform x64
```

Expected initial result: FAIL at Word export because `ExportSavedRevision` is undefined.

4. Before update implementation, run:

```powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestUpdater_Run
```

Expected: FAIL because `BeginApprovedUpdate` and `IUpdaterLauncher` are undefined.

5. Execute every task checkbox in order: export implementation/form; update fixture/fake launcher/named-pipe serialization/`ValidateRelease`; static tests; smoke; accessibility; matrix schema/runs; full automated/manual evidence; README.
6. Per actual inventory row, substituting matching bitness:

```powershell
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database $env:TEMP\SLUT-Client-Matrix.accdb -Configuration Test
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database $env:TEMP\SLUT-Client-Matrix.accdb -Source access-client/src -Platform x64
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database $env:TEMP\SLUT-Client-Matrix.accdb -Output $env:TEMP\SLUT-Client-Matrix.accde -Platform x64 -ClientVersion 0.1.0
powershell.exe -NoProfile -File access-client/build/InvokeAccessSmokeTests.ps1 -Database $env:TEMP\SLUT-Client-Matrix.accde -FakeApiUrl http://127.0.0.1:8765 -Platform x64
```

7. Complete automated regression gate:

```powershell
python -m pytest -q
python -m pytest tests/unit/test_access_source_layout.py tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb
python -m pytest tests/access -q -m access_com
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
git diff --check
```

Expected: all credential-free/static/VBA/COM tests pass; accepted-update tests use only `CFakeUpdaterLauncher`; `ValidateRelease` is safe; round-trip clean; no business table/sensitive value/legacy/direct-cloud route. Execute and record all twelve manual User scenarios from Step 11 on each claimed row; failed/not-run rows remain unsupported.

The fake API and static tests must also prove unsupported
bitness/architecture combinations are rejected before launch; no grant or bearer
appears in command line, environment, registry, clipboard, disk, test output, or
logs; and `ValidateRelease` returns only its seven safe keys.

## Scope, diff, commit, handoff

No Admin client, backend/OpenAPI/template changes, local tables, .NET updater implementation, signing/certificates, installer/deployment, real hostname/data, Office repair/policy change, or unrelated refactor. The Windows launcher is only the AC-09 IPC boundary and must be fake-tested; do not start a real helper. `git diff --name-only $taskBase` must be allowlisted; inspect all diffs and never stage `.superpowers/`, generated ACCDE, export docs, real inventory identity, or secrets.

Commit exactly:

```powershell
$allowed = @(
  'access-client/src/modules/modWordExport.bas',
  'access-client/src/classes/IFileDialogService.cls',
  'access-client/src/classes/CAccessFileDialogService.cls',
  'access-client/src/classes/IProcessLauncher.cls',
  'access-client/src/classes/CWindowsProcessLauncher.cls',
  'access-client/src/forms/frmExport.txt',
  'access-client/tests/vba/TestWordExport.bas',
  'access-client/tests/vba/classes/CFakeFileDialogService.cls',
  'access-client/tests/vba/classes/CFakeProcessLauncher.cls',
  'access-client/tests/fixtures/word/fictional-report.docx',
  'access-client/tests/fixtures/word/fictional-report-metadata.json',
  'access-client/src/modules/modUpdater.bas',
  'access-client/src/classes/IUpdaterLauncher.cls',
  'access-client/src/classes/CWindowsUpdaterLauncher.cls',
  'access-client/tests/vba/TestUpdater.bas',
  'access-client/tests/vba/classes/CFakeUpdaterLauncher.cls',
  'access-client/tests/fixtures/policy/update-grant.json',
  'access-client/build/InvokeAccessSmokeTests.ps1',
  'access-client/build/ScanAccessSource.ps1',
  'tests/unit/test_access_vba_safety.py',
  'tests/access/conftest.py',
  'access-client/build/BuildAccde.ps1',
  'access-client/build/ValidateAccessBuild.ps1',
  'access-client/build/build-matrix.example.json',
  'access-client/src/modules/modWin32.bas',
  'access-client/src/modules/modApiClient.bas',
  'access-client/src/modules/modAppStartup.bas',
  'access-client/src/modules/modBuildInfo.bas',
  'access-client/src/modules/modClientPolicy.bas',
  'access-client/src/modules/modReportWorkflow.bas',
  'access-client/src/modules/modTestHooks.bas',
  'access-client/src/forms/frmReportEditor.txt',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/forms/frmUpdateNotice.txt',
  'access-client/src/manifest.json',
  'access-client/tests/vba/TestRunner.bas',
  'tests/access/access_com.py',
  'tests/access/fake_api.py',
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
git commit -m "feat(access): complete user client acceptance"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push. Handoff task/branch/SHAs/files, both red/final commands, per-row Windows/Access/Word version/channel/bitness/scaling evidence without workstation identity, temporary artifact hashes, all twelve manual results, accepted-update fake-launcher and `ValidateRelease` results, sensitive-surface scan, unsupported/NOT RUN rows, diff/parity, commit, deviations.

Hard-stop any row on COM/bitness/import-export/reference/compile/ACCDE/reopen/fake-contract/DPAPI/Word/endpoint-protection/proxy-TLS/accessibility failure. Never push, merge, deploy, apply, sign, publish, install, access production, request/store secrets, modify agency/Trust Center policy, reset, or destroy user work.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `feat(access): complete user client acceptance`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
