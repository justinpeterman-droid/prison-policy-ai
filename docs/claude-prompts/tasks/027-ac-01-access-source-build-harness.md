# Claude Code Prompt 027 — AC-01: Source/build round-trip harness and editable Access master

Copy everything below this line into a fresh Claude Code session.

## Mission

Implement sequence **027**, task **AC-01**, exactly as specified in the approved implementation plan. The outcome is a deterministic, source-controlled Microsoft Access build/reconstruction harness, an editable `SLUT-Client.accdb`, an empty local-table schema, pinned VBA-JSON bytes, and credible Windows/Access build evidence. This foundation exists so later Access work is reviewable from text exports instead of an opaque binary.

Work only in this repository root:

`C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`

The approved planning baseline is exactly:

`6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`

Use branch:

`claude/ac-01-source-build`

## Mandatory reading

Before changing a file, read:

1. `AGENTS.md`.
2. `docs/superpowers/plans/2026-08-12-access-cloud-run-program-roadmap.md`, especially global gates and sequence 027 / AC-01.
3. `docs/superpowers/plans/2026-08-12-access-user-client-implementation.md` from the beginning through the locked file structure, then the complete exact heading `### Task AC-01: Source/build round-trip harness and editable Access master` through the next task divider.
4. `docs/superpowers/specs/2026-08-12-access-user-client-design.md` for accepted client boundaries.

The plan task is executable and authoritative. Perform every checkbox in order; this prompt does not replace any detail in it.

## Preflight and branch safety

Run and record:

```powershell
git rev-parse --show-toplevel
git status --short
if ((git branch --show-current) -ne 'main') { throw 'Start from current reviewed main.' }
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
$taskBase = git rev-parse HEAD
python -m pytest -q
```

The root must be the path above, the ancestor command must succeed, and the credential-free baseline must pass. Do not reset, clean, stash, overwrite, or discard user work. If reviewed main advanced, continue only when the baseline remains an ancestor; read intervening reviewed plan/spec changes with `git diff 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD -- docs/superpowers` and follow them. Create the exact branch from current reviewed `HEAD`, never from the planning baseline SHA. Stop only when ancestry fails, intervening changes are unreviewed/conflicting, prerequisites are missing, or an allowed path overlaps unexplained work.

## Exact file allowlist

Create only:

- `access-client/README.md`
- `access-client/VERSION`
- `access-client/SLUT-Client.accdb`
- `access-client/src/manifest.json`
- `access-client/src/project.json`
- `access-client/src/forms/frmShell.txt`
- `access-client/src/forms/frmLogin.txt`
- `access-client/src/forms/frmErrorDialog.txt`
- `access-client/src/reports/.gitkeep`
- `access-client/src/queries/.gitkeep`
- `access-client/src/tables/schema.json`
- `access-client/src/macros/AutoExec.txt`
- `access-client/vendor/json/JsonConverter.bas`
- `access-client/vendor/json/LICENSE.txt`
- `access-client/vendor/json/VERSION.txt`
- `access-client/build/AccessBuild.Common.psm1`
- `access-client/build/ExportAccessSource.ps1`
- `access-client/build/ImportAccessSource.ps1`
- `access-client/build/BuildAccde.ps1`
- `access-client/build/ValidateAccessBuild.ps1`
- `access-client/build/InvokeAccessUnitTests.ps1`
- `access-client/build/build-matrix.example.json`
- `access-client/tests/vba/TestAssert.bas`
- `access-client/tests/vba/TestRunner.bas`
- `tests/unit/test_access_source_layout.py`
- `tests/access/access_com.py`
- `tests/access/test_reconstruction.py`
- `tests/access/requirements-windows.txt`

There are no consume-only repository files in AC-01 beyond the plans/specs/instructions. Do not edit those documents or any file not listed above.

## Locked interfaces and implementation rules

- Consume Access COM `Access.Application`, `SaveAsText`, `LoadFromText`, `NewCurrentDatabase`, and `SysCmd`.
- Produce `Export-AccessSource`, `Import-AccessSource`, `Build-AccessAccde`, and `Test-AccessSourceRoundTrip` in `AccessBuild.Common.psm1`; `TestAssert.AreEqual`, `IsTrue`, and `Fail`; `Test_RunAll() As String`; the canonical manifest and editable binary.
- Pin official VBA-JSON v2.3.1 commit `1e49ba826b979d1851029dc965ecb6a3ead2a32c` to the exact byte lengths and SHA-256 values in the plan. A mismatch is a hard stop; never bless different bytes.
- All forms are unbound. `access-client/src/tables/schema.json` must remain exactly an empty application-table array. Do not introduce queries, reports, business data, credentials, or local cache tables.
- SaveAsText form files must be exported from Access, never hand-authored. The manifest import order, project references, forbidden references, CRLF normalization, hash handling, and test-only object rules must match the task exactly.
- Production must not gain versioned Word, WinHTTP, Scripting Runtime, or VBIDE references. The build workflow may late-bind VBIDE only where the approved plan allows it.
- Build scripts may create unsigned temporary ACCDE output only. They must not sign, publish, install, or change Trust Center policy.

## Test-first execution

1. Add the exact failing source-layout/vendor-integrity tests from Step 1.
2. Run the red test:

```powershell
python -m pytest tests/unit/test_access_source_layout.py -q
```

Expected red result: failure because `access-client/SLUT-Client.accdb` and `access-client/src/manifest.json` do not exist. If it passes for an unexplained reason, stop and inspect the starting tree.

3. Complete Steps 3–7 exactly, including immutable vendor verification, project/manifest policy, COM cleanup and bitness checks, controlled Access creation, export rather than hand-authoring, and reconstruction tests.
4. On a controlled Windows 11 workstation with full Access, use a PowerShell process matching Access bitness. Verify `[Environment]::Is64BitProcess` against Access/Office inventory and `(New-Object -ComObject Access.Application).SysCmd(7)`. Stop on COM activation, inventory, bitness, Trust Center, compile, reference, or database-format failure; do not repair Office or weaken policy.
5. Run focused verification, replacing `x64` only with the actual runner bitness:

```powershell
python -m pytest tests/unit/test_access_source_layout.py -q
python -m pytest tests/access/test_reconstruction.py -q -m access_com
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database access-client/SLUT-Client.accdb -Output $env:TEMP\SLUT-Client-x64.accde -Platform x64 -ClientVersion 0.1.0
```

Expected: layout tests pass; import/re-export is canonical with no diff; VBA compiles without missing references; an unsigned temporary ACCDE exists and opens with `frmShell`. Claim only the bitness actually tested.

6. Run the full credential-free regression again:

```powershell
python -m pytest -q
git diff --check
```

## Security, privacy, and non-goals

Use fictional values only. Never add real employee identity, PINs, tokens, reports, workstation identity, certificates, or secrets. No local application tables. No backend, OpenAPI, browser app, deployment, updater, prompt, template, AI behavior, or Admin-client work. Do not refactor unrelated code.

## Acceptance and diff gate

- Every AC-01 checkbox is complete and its expected result observed.
- The source tree reconstructs the checked-in editable binary and re-exports canonically.
- The empty-table and unbound-form invariants hold.
- Vendor bytes/hashes are exact.
- Windows/Access version, channel, bitness, commands, results, and temporary ACCDE path/hash are recorded without machine identity or secrets.
- `git diff --name-only $taskBase` contains only the allowlisted paths above; inspect `git diff --stat`, `git diff --check`, and every text diff. Do not stage `.superpowers/` or unrelated files.

Commit exactly:

```powershell
$allowed = @(
  'access-client/README.md',
  'access-client/VERSION',
  'access-client/SLUT-Client.accdb',
  'access-client/src/manifest.json',
  'access-client/src/project.json',
  'access-client/src/forms/frmShell.txt',
  'access-client/src/forms/frmLogin.txt',
  'access-client/src/forms/frmErrorDialog.txt',
  'access-client/src/reports/.gitkeep',
  'access-client/src/queries/.gitkeep',
  'access-client/src/tables/schema.json',
  'access-client/src/macros/AutoExec.txt',
  'access-client/vendor/json/JsonConverter.bas',
  'access-client/vendor/json/LICENSE.txt',
  'access-client/vendor/json/VERSION.txt',
  'access-client/build/AccessBuild.Common.psm1',
  'access-client/build/ExportAccessSource.ps1',
  'access-client/build/ImportAccessSource.ps1',
  'access-client/build/BuildAccde.ps1',
  'access-client/build/ValidateAccessBuild.ps1',
  'access-client/build/InvokeAccessUnitTests.ps1',
  'access-client/build/build-matrix.example.json',
  'access-client/tests/vba/TestAssert.bas',
  'access-client/tests/vba/TestRunner.bas',
  'tests/unit/test_access_source_layout.py',
  'tests/access/access_com.py',
  'tests/access/test_reconstruction.py',
  'tests/access/requirements-windows.txt'
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
git commit -m "build(access): add deterministic source round-trip"
$taskFinal = (git rev-parse HEAD).Trim()
git status --short
git show --stat --oneline HEAD
```

Do not push.

## Handoff

Return: task/sequence; branch; starting and ending SHA; files created; red test and exact failure; focused/full commands and results; Access/Word version/channel/bitness and display context without workstation identity; temporary ACCDE path/hash (not committed); `git diff --check`; commit SHA; deviations; and any NOT RUN matrix rows with reasons.

## Hard prohibitions and stop conditions

Never push, merge, deploy, apply infrastructure, sign, publish, install, access production, request/store secrets, alter agency machines or Trust Center, run destructive Git/filesystem commands, or reset user work. Stop on a missing prerequisite, dirty allowed path, baseline ancestry failure, unreviewed contract change, vendor hash mismatch, unsupported Access/PowerShell bitness, COM/compile/reference failure, or any need to leave the allowlist.

## Required handoff template

Return: `Sequence/task`; `Branch`; `Starting SHA`; `Final HEAD and commit SHA`; exact commit message `build(access): add deterministic source round-trip`; exact changed/deleted files; red, focused, and regression commands with results; unstaged+staged+untracked allowlist result; both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and source-parity results; Windows/Access/Word/PowerShell evidence or `NOT RUN`; assumptions, risks, deviations, blockers, and remaining external gates; generated temporary artifacts and hashes (not committed); and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, no secrets were changed, and production was not accessed.
