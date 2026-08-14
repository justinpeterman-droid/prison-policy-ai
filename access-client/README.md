# SLUT Access Client — source/build harness

Deterministic, source-controlled build for the Microsoft Access employee client.
The editable master `SLUT-Client.accdb` is reconstructible from the text sources in
`src/`, so every later change is reviewable as text instead of an opaque binary.

## Requirements

- **Windows with full Microsoft Access.** The Access Runtime cannot run this
  harness: it has no design surface, no VBE, and cannot create objects.
- **PowerShell bitness must match Access bitness.** Every entry-point script
  asserts this via `Assert-AccessBitness` and stops on mismatch. Verified target
  for this repository is **x64**.
- **Trust access to the VBA project object model** must be enabled
  (Trust Center → Macro Settings). `VBComponents` import/export fails without it.
- The database being built must be in a **Trusted Location** (or a trusted
  document). Access opens untrusted databases in disabled mode, where
  `CurrentDb()` is unavailable and the build cannot inspect objects.

## Commands

Run from the repository root, in a PowerShell process matching Access bitness.

~~~powershell
# Export the master's objects back to text sources
powershell.exe -NoProfile -File access-client/build/ExportAccessSource.ps1 `
    -Database access-client/SLUT-Client.accdb -Output <dir> -SourceRoot access-client/src

# Rebuild a database from text sources (Test includes test-only modules)
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 `
    -Source access-client/src -Database <path.accdb> -Configuration Test

# Validate bitness, invariants, vendor hashes, references, and VBA compilation
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 `
    -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64

# Build an unsigned local ACCDE for verification only
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 `
    -Database access-client/SLUT-Client.accdb -Output $env:TEMP\SLUT-Client-x64.accde `
    -Platform x64 -ClientVersion 0.1.0

# The command opens Access for the native **File → Save As → Make ACCDE** workflow.
# Save to the exact -Output path printed by the script; cancelling or choosing another
# path fails the subsequent artifact check after five minutes.

# Run the in-database VBA test entry point
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 `
    -Database access-client/SLUT-Client.accdb -Platform x64
~~~

Python-side checks:

~~~powershell
python -m pytest tests/unit/test_access_source_layout.py -q
python -m pytest tests/access/test_reconstruction.py -q -m access_com
~~~

## Invariants

- **No local application tables.** `src/tables/schema.json` is permanently
  `{"schema_version": 1, "tables": []}`. `Assert-NoUnmanagedObjects` fails the
  build if any non-system table, stored query, or report appears.
- **All forms are unbound** — empty `RecordSource`, no bound `ControlSource`,
  navigation buttons, record selectors, and dividing lines off.
- **Every object is manifested.** `src/manifest.json` is the canonical list; an
  object present in the database but absent from the manifest fails the build.
- **Production carries no versioned Word, WinHTTP, Scripting Runtime, or VBIDE
  reference.** `project.json` lists these as `forbidden_references` and
  `ValidateAccessBuild.ps1` enforces it. VBIDE is used late-bound by the build
  workflow only.
- **Test-only objects** (`TestAssert`, `TestRunner`) are imported only with
  `-Configuration Test`.

## Vendor dependencies

The importer creates a transient, exact two-line late-bound Access adaptation of
VBA-JSON at build time. The hash-pinned vendor source remains untouched; this avoids
the compile-time **Microsoft Scripting Runtime** reference while preserving the
production reference invariant.

VBA-JSON v2.3.1, pinned to commit `1e49ba826b979d1851029dc965ecb6a3ead2a32c`:

| File | Bytes | SHA-256 |
|---|---|---|
| `vendor/json/JsonConverter.bas` | 44164 | `1c240aa3c7ef536c25bf44061b02b0fadeb39bfb449f67c419822650e23f6169` |
| `vendor/json/LICENSE.txt` | 1075 | `f902104a3e36daea3a33f7adfcd25c5ac69791e9164b83a81b8d0b235728c9bd` |

These bytes are **immutable**. A mismatch is a hard stop — never re-bless a new
hash. `Export-AccessSource` deliberately skips objects marked `vendor: true` and
records the pinned hash rather than re-exporting: Access re-exports
`JsonConverter.bas` at 45,287 bytes, which would silently break the pin.

## Signing and deployment are external

`BuildAccde.ps1` produces an **unsigned, local, temporary** artifact for
verification only. No script in this directory invokes `signtool`, touches a
certificate store, changes Trust Center policy, or publishes anything. Signing,
distribution, and the updater are handled by OP-09.

## Deliberate deviations from the AC-01 plan snippets

Each of these was required to make headless automation work; none weakens a
security control.

1. **`Close-AccessApplication` does not call `CloseCurrentDatabase()`.** That call
   raises a modal "Save As" against a database created in the same automation
   session, which blocks headless Access indefinitely. It uses
   `Quit(1 = acQuitSaveAll)` instead. `acQuitSaveNone` is *not* usable — it
   discards imported VBA modules, leaving a database whose `VBComponents` lookup
   fails with "Subscript out of range".
2. **Forms are created with Close-then-Rename**, never `DoCmd.Save` on a new
   form, which also raises a modal "Save As".
3. **`RunCommand(126)` after every module import.** `VBComponents.Import` only
   stages modules in memory; without an explicit compile-and-save they are lost
   silently on close.
4. **ACCDE creation uses the native Access File → Save As → Make ACCDE workflow.**
   Access refuses conversion when it is invoked from a macro or VBA/automation.
   The build compiles, opens the database visibly, waits for an approved operator
   to select the exact `-Output` path, then verifies the artifact. No UI automation
   is used.
5. **`-Check` is a `[string]` parameter.** `powershell.exe -File` passes every
   argument as a string, so the Python COM bridge's `-Check True` cannot bind to a
   switch or a bool.
6. **Manifest JSON is written UTF-8 without BOM.** `Set-Content -Encoding UTF8`
   emits a BOM in Windows PowerShell, which breaks Python's `read_text("utf-8")`.

## Known open items

- **ACCDE creation requires one controlled interactive matrix pass.** The build
  opens Access's native dialog and then verifies the exact output path and a
  read-only reopen. Record the Access version/channel/bitness and artifact hash;
  do not use UI automation, signing, or a Trust Center change.
- **Reconstruction uses a trusted, ignored child of the existing project Trusted
  Location.** It does not use pytest's untrusted temporary directory and does not
  change Trust Center policy.
- **`pytest.mark.access_com` is unregistered**, producing
  `PytestUnknownMarkWarning`. Registering it means editing `pytest.ini`, which is
  outside the AC-01 file allowlist.
