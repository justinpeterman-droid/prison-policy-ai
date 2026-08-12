# Access User Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the source-controlled Microsoft Access Guided Workspace for ordinary employees, from employee-number/PIN sign-in through revision-safe report editing, Policy Expert citations, and saved-revision Word export.

**Architecture:** A compiled Access front end contains only unbound forms, focused VBA orchestration, and injected transport/storage abstractions. It communicates exclusively with the versioned Cloud Run /api/v1 contract over WinHTTP; Cloud Run remains authoritative for identity, authorization, reports, revisions, AI jobs, policy search, and Word generation. Reviewable SaveAsText/VBA exports reconstruct the editable SLUT-Client.accdb, while DPAPI-protected LocalAppData files are the only persistent client storage for renewal tokens and crash recovery.

**Tech Stack:** Microsoft Access ACCDB/ACCDE and VBA7; PowerShell 5.1 plus Access COM automation; WinHTTP 5.1 late binding; Windows DPAPI and narrow Win32 declarations; VBA-JSON v2.3.1; Python 3 and pytest for static/fixture/COM orchestration; the existing Flask /api/v1 OpenAPI contract and DOCX report engine.

## Global Constraints

- Target only agency-managed Windows 11 workstations with Microsoft Access installed or an explicitly approved Access Runtime.
- Development uses access-client/SLUT-Client.accdb. Production packaging consumes a compiled SLUT-Client.accde; this plan does not sign, publish, deploy, or install it.
- All Access forms and subforms are unbound: RecordSource is empty, no report content is cached in Access tables, and access-client/src/tables/schema.json contains an empty tables array.
- Do not create business, credential, profile, roster, report, job, audit, or recovery tables in Access.
- Access communicates only with /api/v1 over HTTPS. It never connects directly to Cloud SQL, Gemini, Vertex AI, Agent Builder, Cloud Storage, the Word template, or legacy shared-code browser endpoints.
- The authoritative contract is openapi/access-v1.yaml. Stop an API-consuming task if that file or the examples required by the task are absent or fail schema validation; do not infer response fields from HTML or legacy /api routes.
- Access tokens remain in memory. A rotating renewal token is persisted only when Keep me signed in on this Windows account is selected and DPAPI current-user encryption succeeds.
- Login, renewal, and client-policy calls are never eligible for bearer renewal. Only a request that actually carried the current `Authorization: Bearer` credential may attempt renewal, and it may do so once after the documented `401 authentication_required` expired-access response.
- `POST /api/v1/auth/change-pin`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/logout-all`, and `DELETE /api/v1/auth/sessions/{session_id}` each carry one `Idempotency-Key` per intended employee action. A single transport or post-renewal replay reuses that same key and byte-identical body.
- Never store or log a PIN, access token, renewal token, report content, employee name, or employee number. Safe diagnostics contain request IDs, stable error categories, client version, and timestamps only.
- Use the established term field notes. Preserve the trust-first promise: AI suggestions remain editable, charges are never applied automatically, and nothing files, emails, approves, or submits itself.
- Cloud Run supplies the authenticated employee profile and stable staff UUID. A local field never overrides signed-in identity.
- Form edits mark workflow state dirty. One save starts 60 seconds after the last change; a manual Save Now uses the same revision service.
- Before every cloud save, write a bounded DPAPI-encrypted recovery snapshot atomically under %LOCALAPPDATA%\StandardLogisticsUnitTools\Recovery. Remove it only after the matching revision succeeds.
- A stale base revision never overwrites server state. HTTP 409 preserves local controls and offers Open newest revision or Save local work as a recovery revision; automatic merging is excluded.
- AI submission uses one idempotency key per intended action. Poll at 2 seconds and back off to a maximum of 10 seconds. Closing Access does not cancel a cloud job.
- Blocking gaps disable generation in Access and the server remains authoritative through 422 blocking_information_required.
- Word export always references an explicit saved report revision. Unsaved changes save first; the employee chooses the path and separately chooses whether to open Word.
- Minimum tested viewport is 1366 by 768 at Windows scaling from 100% through 150%. Forms require keyboard navigation, logical tab order, visible focus, accessible labels, non-color-only state indicators, and high-contrast text.
- All Win32 declarations live in access-client/src/modules/modWin32.bas, use PtrSafe and LongPtr, and compile under #If VBA7 and #If Win64 branches.
- Late-bind WinHTTP, Scripting.Dictionary, stream helpers, Word launch, and browser launch. Do not add versioned Word, WinHTTP, Scripting Runtime, or VBIDE references to the production project.
- Use fictional fixtures only. Never place real employee names, employee numbers, PINs, tokens, field notes, or reports in source control.
- The browser application, frontend/forms, current Flask behavior, official DOCX template, report prompts, checklist rules, and admin workstream remain unchanged.
- Do not create Admin forms or Admin modules in this plan. frmShell exposes only the User navigation listed here.
- Do not create Claude prompts, an updater, deployment scripts, signing scripts, infrastructure, or backend implementation in this plan.
- Agents stop after local commits and handoff evidence. Agents never push, deploy, sign artifacts, request or handle secrets, alter agency machines, or modify Trust Center policy.

## Repository and Workstation Preconditions

1. Start each task from the repository root on its designated clean feature branch. Preserve all user-owned changes outside the task’s declared files.
2. Run credential-free Python tests before and after each task:

~~~powershell
python -m pytest -q
~~~

Expected baseline: the existing credential-free suite passes. If it does not, record the failing tests and stop before changing Access files.

3. AC-01 requires a controlled Windows 11 workstation with full Microsoft Access, not only Access Runtime. Determine the installed executable path, exact Access version, update channel, and x86/x64 bitness before COM automation.
4. Deterministic `.bas` and `.cls` round-tripping requires the controlled build workstation to permit programmatic access to the VBA project object model. This is a workstation prerequisite, not a setting changed by any script in this plan. If agency policy forbids it, stop AC-01; do not substitute a binary-only workflow or add a VBIDE project reference.
5. Run an Access task only from a PowerShell process matching Access bitness:

~~~powershell
[Environment]::Is64BitProcess
(New-Object -ComObject Access.Application).SysCmd(7)
~~~

Expected: the first value matches installed Access bitness and the second command returns the installed Access version. If COM activation fails or bitness differs, stop; do not repair Office or change machine policy.

6. AC-02 and every later API task require openapi/access-v1.yaml plus schema-valid fictional examples for the endpoints named in that task. That contract is produced by the backend workstream and is consumed read-only here.
7. The deployment/API workstream must supply the exact managed HTTPS API origin before a Release import. Do not infer it from the existing browser deployment and do not compile the legacy Cloud Run host into the Access client.
8. ACCDE creation is accepted only after BuildAccde.ps1 proves the Access SysCmd make-ACCDE operation on the selected Access version. If Access reports an unsupported database format, missing reference, compile error, or wrong bitness, stop that matrix row.
9. Signing is an external release gate. BuildAccde.ps1 creates an unsigned local verification artifact; no task invokes signtool, certificate stores, a signing service, Cloud Run, gcloud, gh push, or a package publisher.

## Locked File Structure

The final AC-09 source tree is:

~~~text
access-client/
  README.md
  VERSION
  SLUT-Client.accdb
  src/
    manifest.json
    project.json
    modules/
      modAppStartup.bas
      modAppState.bas
      modNavigation.bas
      modTheme.bas
      modBuildInfo.bas
      modApiRoutes.bas
      modApiClient.bas
      modJsonContracts.bas
      modIds.bas
      modUtf8.bas
      modAuth.bas
      modDpapi.bas
      modSessionStore.bas
      modRecovery.bas
      modReportWorkflow.bas
      modAutosave.bas
      modConflict.bas
      modJobs.bas
      modWordExport.bas
      modPolicyExpert.bas
      modErrors.bas
      modClientPolicy.bas
      modSafeLog.bas
      modWin32.bas
      modTestHooks.bas
    classes/
      IApiTransport.cls
      CWinHttpTransport.cls
      CApiRequest.cls
      CApiResponse.cls
      CApiError.cls
      ISecureStore.cls
      CDpapiFileStore.cls
      IRecoveryStore.cls
      CAtomicRecoveryStore.cls
      IClock.cls
      CSystemClock.cls
      IFileDialogService.cls
      CAccessFileDialogService.cls
      IProcessLauncher.cls
      CWindowsProcessLauncher.cls
      CUserProfile.cls
      CSessionState.cls
      CWorkflowState.cls
      CReportState.cls
      CJobState.cls
      CPagedResult.cls
    forms/
      frmShell.txt
      frmLogin.txt
      frmChangePin.txt
      frmDashboard.txt
      frmIncidentOfficers.txt
      frmFieldNotes.txt
      frmFactReview.txt
      frmGapReview.txt
      frmReportEditor.txt
      frmExport.txt
      frmReportHistory.txt
      frmRevisionHistory.txt
      frmRevisionCompare.txt
      frmRevisionConflict.txt
      frmRecoveryPrompt.txt
      frmJobProgress.txt
      frmPolicyExpert.txt
      frmAccount.txt
      frmSessionList.txt
      frmUpdateNotice.txt
      frmErrorDialog.txt
      frmConfirmAction.txt
      sfrmNavigation.txt
      sfrmStaffSearchResults.txt
      sfrmReportQueue.txt
      sfrmGapQuestions.txt
      sfrmReportTabs.txt
      sfrmRevisionList.txt
      sfrmPolicyCitations.txt
      sfrmSessionResults.txt
    reports/
      .gitkeep
    queries/
      .gitkeep
    tables/
      schema.json
    macros/
      AutoExec.txt
    assets/
      README.md
      shield-crystal-front.png
      seal.png
      app.ico
  vendor/
    json/
      JsonConverter.bas
      LICENSE.txt
      VERSION.txt
  build/
    AccessBuild.Common.psm1
    ExportAccessSource.ps1
    ImportAccessSource.ps1
    BuildAccde.ps1
    ValidateAccessBuild.ps1
    InvokeAccessUnitTests.ps1
    InvokeAccessSmokeTests.ps1
    ScanAccessSource.ps1
    build-matrix.example.json
  tests/
    vba/
      TestAssert.bas
      TestRunner.bas
      TestApiRoutes.bas
      TestJsonContracts.bas
      TestApiClient.bas
      TestAuth.bas
      TestDpapi.bas
      TestSessionStore.bas
      TestRecovery.bas
      TestReportWorkflow.bas
      TestAutosave.bas
      TestConflict.bas
      TestJobs.bas
      TestWordExport.bas
      TestPolicyExpert.bas
      TestErrors.bas
      TestClientPolicy.bas
      TestSafeLog.bas
      classes/
        CFakeApiTransport.cls
        CInMemorySecureStore.cls
        CInMemoryRecoveryStore.cls
        CFakeClock.cls
        CFakeFileDialogService.cls
        CFakeProcessLauncher.cls
    fixtures/
      auth/
        login-user.json
        login-temporary-pin.json
        renew-success.json
        sessions.json
      profile/
        me-user.json
      policy/
        client-current.json
        client-read-only.json
        answer-with-citations.json
      staff/
        search-results.json
      reports/
        incident-created-multi-officer.json
        owned-page.json
        prepared-page.json
        report-detail.json
        revision-page.json
        revision-conflict.json
        recovery-created.json
      jobs/
        queued.json
        running.json
        succeeded.json
        failed.json
      errors/
        authentication-required.json
        invalid-credentials.json
        session-reauthentication-required.json
        permission-denied.json
        validation-failed.json
        client-upgrade-required.json
        blocking-information-required.json
        dependency-unavailable.json
      word/
        fictional-report.docx
        fictional-report-metadata.json
      recovery/
        workflow-state-v1.json
tests/
  unit/
    test_access_source_layout.py
    test_access_vba_safety.py
    test_access_fixture_contracts.py
    test_access_route_parity.py
  access/
    conftest.py
    fake_api.py
    access_com.py
    test_reconstruction.py
    test_user_workflows.py
    test_recovery_after_termination.py
    requirements-windows.txt
~~~

access-client/src/manifest.json is the import/export order and SHA-256 inventory for Access objects. It lists only objects present in the current task’s binary and grows intentionally with each task. access-client/src/project.json contains startup form, built-in reference allowlist, database options, source schema version, and supported compilation constants. Form SaveAsText files contain their form modules; those modules are not exported a second time.

## Cross-Task VBA Contracts

These names and signatures are locked. A task may implement a signature assigned to it, but later tasks must consume it unchanged.

~~~vb
Public Sub AppStart()
Public Sub NavigateTo(ByVal destination As AppPage, Optional ByVal contextId As String = vbNullString)

Public Function NewApiRequest(ByVal method As String, ByVal relativePath As String, _
                              Optional ByVal bodyJson As String = vbNullString) As CApiRequest
Public Function ApiBaseUrl() As String
Public Function ApiSend(ByVal request As CApiRequest) As CApiResponse
Public Function ApiSendWithoutRenewal(ByVal request As CApiRequest) As CApiResponse
Public Sub ConfigureApiTransportForTest(ByVal transport As IApiTransport)

' IApiTransport
Public Function Send(ByVal request As CApiRequest) As CApiResponse

Public Function JsonParseObject(ByVal jsonText As String) As Object
Public Function JsonSerialize(ByVal value As Variant) As String
Public Function ParseSuccessEnvelope(ByVal response As CApiResponse) As Object
Public Function ParseErrorEnvelope(ByVal response As CApiResponse) As CApiError

Public Function Login(ByVal employeeNumber As String, ByVal pin As String, _
                      ByVal keepSignedIn As Boolean, ByVal deviceLabel As String) As CSessionState
Public Function RenewSession() As Boolean
Public Function LastRenewalError() As CApiError
Public Sub ChangePin(ByVal currentPin As String, ByVal newPin As String)
Public Sub LogoutCurrent()
Public Sub LogoutAll()
Public Sub RevokeSession(ByVal sessionId As String)
Public Function LoadCurrentProfile() As CUserProfile
Public Function ReviewLabOrigin() As String
Public Function RefreshClientPolicy() As ClientCompatibility
Public Function TrustedReviewLabOrigin() As String
Public Function FieldNotesMaxCharacters() As Long

' ISecureStore
Public Function ReadSecret(ByVal name As String) As String
Public Sub WriteSecret(ByVal name As String, ByVal plaintext As String)
Public Sub DeleteSecret(ByVal name As String)
Public Function Exists(ByVal name As String) As Boolean

Public Function SearchActiveStaff(ByVal query As String) As Collection
Public Function BeginNewIncident(ByVal reportingStaffIds As Collection) As CWorkflowState
Public Sub SetFieldNotes(ByVal state As CWorkflowState, ByVal fieldNotes As String)
Public Function SubmitJob(ByVal incidentId As String, ByVal jobType As String, _
                          ByVal payloadJson As String, ByVal idempotencyKey As String) As CJobState
Public Function PollJob(ByVal jobId As String) As CJobState
Public Function NextPollDelaySeconds(ByVal pollNumber As Long) As Long
Public Function ResumeKnownJobs(ByVal state As CWorkflowState) As Collection

Public Sub CopyReportControlsToState(ByVal editorForm As Access.Form, _
                                    ByVal state As CWorkflowState, ByVal reportId As String)
Public Sub LoadReportStateIntoControls(ByVal editorForm As Access.Form, _
                                      ByVal state As CWorkflowState, ByVal reportId As String)
Public Sub SwitchReportTab(ByVal editorForm As Access.Form, _
                           ByVal state As CWorkflowState, ByVal reportId As String)
Public Sub MarkDirty(ByVal state As CWorkflowState)
Public Function SaveNow(ByVal state As CWorkflowState, ByVal reason As String) As Long
Public Sub OnIdleTimer(ByVal state As CWorkflowState)

' IRecoveryStore
Public Sub WriteSnapshot(ByVal snapshotId As String, ByVal plaintextJson As String)
Public Function ReadSnapshot(ByVal snapshotId As String) As String
Public Function ListSnapshotIds() As Collection
Public Sub DeleteSnapshot(ByVal snapshotId As String)

' IClock
Public Function UtcNow() As Date
Public Function MonotonicMilliseconds() As Double

Public Function LoadReportPage(ByVal relationship As String, ByVal filtersJson As String, _
                               Optional ByVal cursor As String = vbNullString) As CPagedResult
Public Function AskPolicyQuestion(ByVal question As String, ByVal recentHistory As Collection) As Object
Public Function ExportSavedRevision(ByVal reportId As String, _
                                    ByVal revisionNumber As Long) As Boolean

' IFileDialogService
Public Function PromptSavePath(ByVal suggestedName As String, _
                               ByVal filterDescription As String, _
                               ByVal extension As String) As String

' IProcessLauncher
Public Sub OpenFile(ByVal absolutePath As String)
Public Sub OpenUri(ByVal absoluteUri As String)

Public Function Test_RunAll() As String
Public Sub Test_ResetApplication()
Public Sub Test_SetApiBaseUrl(ByVal baseUrl As String)
Public Sub Test_Navigate(ByVal destinationName As String, _
                         Optional ByVal contextId As String = vbNullString)
Public Function Test_GetStateJson() As String
Public Sub Test_TriggerAutosave()
Public Sub Test_ExitWithoutCleanup()
~~~

---

### Task AC-01: Source/build round-trip harness and editable Access master

**Files:**
- Create: access-client/README.md
- Create: access-client/VERSION
- Create: access-client/SLUT-Client.accdb
- Create: access-client/src/manifest.json
- Create: access-client/src/project.json
- Create: access-client/src/forms/frmShell.txt
- Create: access-client/src/forms/frmLogin.txt
- Create: access-client/src/forms/frmErrorDialog.txt
- Create: access-client/src/reports/.gitkeep
- Create: access-client/src/queries/.gitkeep
- Create: access-client/src/tables/schema.json
- Create: access-client/src/macros/AutoExec.txt
- Create: access-client/vendor/json/JsonConverter.bas
- Create: access-client/vendor/json/LICENSE.txt
- Create: access-client/vendor/json/VERSION.txt
- Create: access-client/build/AccessBuild.Common.psm1
- Create: access-client/build/ExportAccessSource.ps1
- Create: access-client/build/ImportAccessSource.ps1
- Create: access-client/build/BuildAccde.ps1
- Create: access-client/build/ValidateAccessBuild.ps1
- Create: access-client/build/InvokeAccessUnitTests.ps1
- Create: access-client/build/build-matrix.example.json
- Create: access-client/tests/vba/TestAssert.bas
- Create: access-client/tests/vba/TestRunner.bas
- Create: tests/unit/test_access_source_layout.py
- Create: tests/access/access_com.py
- Create: tests/access/test_reconstruction.py
- Create: tests/access/requirements-windows.txt

**Interfaces:**
- Consumes: Microsoft Access.Application COM, Application.SaveAsText, Application.LoadFromText, Application.NewCurrentDatabase, Application.SysCmd, and the official VBA-JSON v2.3.1 tag at commit 1e49ba826b979d1851029dc965ecb6a3ead2a32c.
- Produces: Export-AccessSource, Import-AccessSource, Build-AccessAccde, Test-AccessSourceRoundTrip in AccessBuild.Common.psm1; TestAssert.AreEqual, TestAssert.IsTrue, TestAssert.Fail; Test_RunAll() As String; the canonical object manifest and initial editable binary.

- [ ] **Step 1: Write the failing source-layout and vendor-integrity tests**

Create tests/unit/test_access_source_layout.py with exact repository invariants:

~~~python
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "access-client"

EXPECTED_VENDOR = {
    "JsonConverter.bas": (
        44164,
        "1c240aa3c7ef536c25bf44061b02b0fadeb39bfb449f67c419822650e23f6169",
    ),
    "LICENSE.txt": (
        1075,
        "f902104a3e36daea3a33f7adfcd25c5ac69791e9164b83a81b8d0b235728c9bd",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_access_master_and_source_manifest_exist():
    assert (CLIENT / "SLUT-Client.accdb").is_file()
    manifest = json.loads((CLIENT / "src" / "manifest.json").read_text("utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["database"] == "SLUT-Client.accdb"
    assert [item["name"] for item in manifest["objects"]] == [
        "AutoExec",
        "frmErrorDialog",
        "frmLogin",
        "frmShell",
        "JsonConverter",
        "TestAssert",
        "TestRunner",
    ]


def test_access_has_no_local_application_tables():
    schema = json.loads((CLIENT / "src" / "tables" / "schema.json").read_text("utf-8"))
    assert schema == {"schema_version": 1, "tables": []}


def test_vba_json_231_is_pinned_by_bytes_and_hash():
    vendor = CLIENT / "vendor" / "json"
    for name, expected in EXPECTED_VENDOR.items():
        path = vendor / name
        assert path.stat().st_size == expected[0]
        assert sha256(path) == expected[1]
    version = (vendor / "VERSION.txt").read_text("utf-8")
    assert "v2.3.1" in version
    assert "1e49ba826b979d1851029dc965ecb6a3ead2a32c" in version


def test_reports_and_queries_have_no_access_objects():
    assert list((CLIENT / "src" / "reports").glob("*.txt")) == []
    assert list((CLIENT / "src" / "queries").glob("*.sql")) == []
~~~

- [ ] **Step 2: Run the layout tests and verify the expected failure**

Run:

~~~powershell
python -m pytest tests/unit/test_access_source_layout.py -q
~~~

Expected: FAIL because access-client/SLUT-Client.accdb and access-client/src/manifest.json do not exist.

- [ ] **Step 3: Pin VBA-JSON v2.3.1 from immutable official URLs**

On a connected engineering workstation, download only these two immutable artifacts:

~~~powershell
$jsonUri = 'https://raw.githubusercontent.com/VBA-tools/VBA-JSON/1e49ba826b979d1851029dc965ecb6a3ead2a32c/JsonConverter.bas'
$licenseUri = 'https://raw.githubusercontent.com/VBA-tools/VBA-JSON/1e49ba826b979d1851029dc965ecb6a3ead2a32c/LICENSE'
Invoke-WebRequest -Uri $jsonUri -OutFile 'access-client/vendor/json/JsonConverter.bas'
Invoke-WebRequest -Uri $licenseUri -OutFile 'access-client/vendor/json/LICENSE.txt'
Get-FileHash -Algorithm SHA256 'access-client/vendor/json/JsonConverter.bas'
Get-FileHash -Algorithm SHA256 'access-client/vendor/json/LICENSE.txt'
~~~

Expected:

~~~text
JsonConverter.bas  1C240AA3C7EF536C25BF44061B02B0FADEB39BFB449F67C419822650E23F6169
LICENSE.txt         F902104A3E36DAEA3A33F7ADFCD25C5AC69791E9164B83A81B8D0B235728C9BD
~~~

Write VERSION.txt as:

~~~text
VBA-JSON v2.3.1
Tag commit: 1e49ba826b979d1851029dc965ecb6a3ead2a32c
JsonConverter.bas SHA-256: 1C240AA3C7EF536C25BF44061B02B0FADEB39BFB449F67C419822650E23F6169
LICENSE.txt SHA-256: F902104A3E36DAEA3A33F7ADFCD25C5AC69791E9164B83A81B8D0B235728C9BD
Upstream: https://github.com/VBA-tools/VBA-JSON/tree/v2.3.1
~~~

If either byte length or hash differs, delete the downloaded copy and stop AC-01. Do not bless a new hash.

- [ ] **Step 4: Create the source manifest, project policy, empty schema, and version**

Set access-client/VERSION to:

~~~text
0.1.0
~~~

Set access-client/src/tables/schema.json to:

~~~json
{
  "schema_version": 1,
  "tables": []
}
~~~

Set project.json to:

~~~json
{
  "schema_version": 1,
  "startup_form": "frmShell",
  "autoexec_macro": "AutoExec",
  "allow_bypass_key": false,
  "display_navigation_pane": false,
  "display_document_tabs": false,
  "use_access_special_keys": false,
  "references": [
    "Visual Basic For Applications",
    "Microsoft Access Object Library",
    "OLE Automation",
    "Microsoft Office Object Library",
    "Microsoft Office Access database engine Object Library"
  ],
  "forbidden_references": [
    "Microsoft Word Object Library",
    "Microsoft WinHTTP Services",
    "Microsoft Scripting Runtime",
    "Microsoft Visual Basic for Applications Extensibility"
  ]
}
~~~

The initial manifest entries use this exact shape and import order:

~~~json
{
  "schema_version": 1,
  "database": "SLUT-Client.accdb",
  "objects": [
    {"type": "macro", "name": "AutoExec", "path": "macros/AutoExec.txt", "order": 10},
    {"type": "form", "name": "frmErrorDialog", "path": "forms/frmErrorDialog.txt", "order": 20},
    {"type": "form", "name": "frmLogin", "path": "forms/frmLogin.txt", "order": 30},
    {"type": "form", "name": "frmShell", "path": "forms/frmShell.txt", "order": 40},
    {"type": "module", "name": "JsonConverter", "path": "../vendor/json/JsonConverter.bas", "order": 50, "vendor": true},
    {"type": "module", "name": "TestAssert", "path": "../tests/vba/TestAssert.bas", "order": 60, "test_only": true},
    {"type": "module", "name": "TestRunner", "path": "../tests/vba/TestRunner.bas", "order": 70, "test_only": true}
  ]
}
~~~

- [ ] **Step 5: Implement the PowerShell COM boundary**

AccessBuild.Common.psm1 must own COM creation, cleanup, bitness checks, Access object constants, manifest parsing, and canonical text comparison. Use the following public boundary:

~~~powershell
function New-AccessApplication {
    [CmdletBinding()]
    param()
    $app = New-Object -ComObject Access.Application
    $app.Visible = $false
    return $app
}

function Close-AccessApplication {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Application)
    try {
        $Application.CloseCurrentDatabase()
    } catch {
        if ($_.Exception.Message -notmatch 'database is not open') {
            throw
        }
    } finally {
        $Application.Quit()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Application)
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

function Assert-AccessBitness {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Application,
        [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$ExpectedPlatform
    )
    $processPlatform = if ([Environment]::Is64BitProcess) { 'x64' } else { 'x86' }
    if ($processPlatform -ne $ExpectedPlatform) {
        throw "PowerShell platform $processPlatform does not match requested Access platform $ExpectedPlatform."
    }
    $configuredPlatform = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration' -ErrorAction Stop).Platform
    if ($configuredPlatform -ne $ExpectedPlatform) {
        throw "Installed Access platform $configuredPlatform does not match requested platform $ExpectedPlatform."
    }
    [void]$Application.hWndAccessApp
}
~~~

For an inventory-approved MSI Office installation without the Click-to-Run registry value, implement the same check from that inventory row's recorded MSACCESS.EXE PE machine type and cover it with a Pester-free PowerShell assertion. Do not guess bitness or weaken the stop condition.

ExportAccessSource.ps1 must call SaveAsText for forms, reports, and macros, and late-bound Application.VBE.ActiveVBProject.VBComponents(name).Export for standard and class modules; choose `.bas` versus `.cls` from the component type; sort by object type and name; normalize CRLF and trailing whitespace; update per-object SHA-256 in manifest.json; and fail if an application table, query, report, or unmanifested object exists.

ImportAccessSource.ps1 must call NewCurrentDatabase for a new destination, apply project.json properties, use LoadFromText for forms, reports, and macros, use late-bound Application.VBE.ActiveVBProject.VBComponents.Import for `.bas` and `.cls` files including JsonConverter.bas, and include test_only objects only with -Configuration Test. The production project keeps the VBIDE reference absent.

BuildAccde.ps1 must compile and save every module, close the source database, call the Access make-ACCDE operation, and verify that the output exists and reopens read-only under the same Access bitness. Its public parameters are:

~~~powershell
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$Output,
    [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform,
    [Parameter(Mandatory)][string]$ClientVersion
)
~~~

No build script modifies the checked-in master unless -Database explicitly names access-client/SLUT-Client.accdb.

- [ ] **Step 6: Create the initial unbound forms, macro, and test runner in Access**

On the controlled Access workstation, use Application.NewCurrentDatabase to create access-client/SLUT-Client.accdb. Create frmShell, frmLogin, and frmErrorDialog with RecordSource empty, NavigationButtons false, RecordSelectors false, DividingLines false, and no bound ControlSource. Create AutoExec with one RunCode action calling Test_Bootstrap() during the test configuration and AppStart() after AC-04 introduces it.

The initial TestRunner.bas must compile before application modules exist:

~~~vb
Option Compare Database
Option Explicit

Public Function Test_RunAll() As String
    Test_RunAll = "{""passed"":0,""failed"":0,""tests"":[]}"
End Function

Public Function Test_Bootstrap() As Boolean
    Test_Bootstrap = True
End Function
~~~

Export the objects through ExportAccessSource.ps1. Never hand-author a SaveAsText form definition.

- [ ] **Step 7: Implement reconstruction and binary/source parity tests**

Create tests/access/test_reconstruction.py:

~~~python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from access_com import invoke_access_script


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "access-client"


@pytest.mark.access_com
def test_import_reexport_is_canonical(tmp_path: Path):
    rebuilt = tmp_path / "SLUT-Client.rebuilt.accdb"
    exported = tmp_path / "exported"
    invoke_access_script(
        CLIENT / "build" / "ImportAccessSource.ps1",
        Source=CLIENT / "src",
        Database=rebuilt,
        Configuration="Test",
    )
    invoke_access_script(
        CLIENT / "build" / "ExportAccessSource.ps1",
        Database=rebuilt,
        Output=exported,
        Check=True,
    )
    expected = json.loads((CLIENT / "src" / "manifest.json").read_text("utf-8"))
    actual = json.loads((exported / "manifest.json").read_text("utf-8"))
    assert actual["objects"] == expected["objects"]
~~~

tests/access/access_com.py must invoke Windows PowerShell with a bounded timeout and surface stdout/stderr:

~~~python
from __future__ import annotations

import subprocess
from pathlib import Path


def invoke_access_script(script: Path, timeout: int = 180, **parameters: object) -> str:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    for name, value in parameters.items():
        command.extend([f"-{name}", str(value)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{script.name} failed with {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout
~~~

Set tests/access/requirements-windows.txt to the repository dependency set; the Access COM bridge adds no Python COM package because it invokes matching-bitness Windows PowerShell:

~~~text
-r ../../requirements.txt
~~~

- [ ] **Step 8: Run source, reconstruction, compile, and ACCDE checks**

Run:

~~~powershell
python -m pytest tests/unit/test_access_source_layout.py -q
python -m pytest tests/access/test_reconstruction.py -q -m access_com
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database access-client/SLUT-Client.accdb -Output $env:TEMP\SLUT-Client-x64.accde -Platform x64 -ClientVersion 0.1.0
~~~

Expected: source tests PASS; reconstruction re-export has no diff; VBA compiles with no missing references; the local unsigned ACCDE opens with frmShell as startup form. Replace x64 with the actual current runner bitness. Do not claim the other bitness passed.

- [ ] **Step 9: Document the source workflow**

access-client/README.md must document: matching-bitness PowerShell, full Access requirement, export/import/validate/build commands, immutable VBA-JSON source and hashes, no local tables, unbound forms, test configuration versus release configuration, and the rule that signing/deployment is external.

- [ ] **Step 10: Commit AC-01**

~~~powershell
git add access-client tests/unit/test_access_source_layout.py tests/access/access_com.py tests/access/test_reconstruction.py tests/access/requirements-windows.txt
git commit -m "build(access): add deterministic source round-trip"
~~~

Expected: one commit containing only AC-01 files. Record Access version, PowerShell bitness, commands, results, and local ACCDE path in the handoff; do not commit the generated ACCDE.

---

### Task AC-02: API core, WinHTTP transport, JSON envelopes, errors, and fake contracts

**Files:**
- Create: access-client/src/modules/modAppState.bas
- Create: access-client/src/modules/modBuildInfo.bas
- Create: access-client/src/modules/modApiRoutes.bas
- Create: access-client/src/modules/modApiClient.bas
- Create: access-client/src/modules/modJsonContracts.bas
- Create: access-client/src/modules/modIds.bas
- Create: access-client/src/modules/modUtf8.bas
- Create: access-client/src/modules/modErrors.bas
- Create: access-client/src/modules/modSafeLog.bas
- Create: access-client/src/modules/modWin32.bas
- Create: access-client/src/modules/modTestHooks.bas
- Create: access-client/src/classes/IApiTransport.cls
- Create: access-client/src/classes/CWinHttpTransport.cls
- Create: access-client/src/classes/CApiRequest.cls
- Create: access-client/src/classes/CApiResponse.cls
- Create: access-client/src/classes/CApiError.cls
- Create: access-client/tests/vba/TestApiRoutes.bas
- Create: access-client/tests/vba/TestJsonContracts.bas
- Create: access-client/tests/vba/TestApiClient.bas
- Create: access-client/tests/vba/TestErrors.bas
- Create: access-client/tests/vba/TestSafeLog.bas
- Create: access-client/tests/vba/classes/CFakeApiTransport.cls
- Create: access-client/tests/fixtures/policy/client-current.json
- Create: access-client/tests/fixtures/errors/authentication-required.json
- Create: access-client/tests/fixtures/errors/invalid-credentials.json
- Create: access-client/tests/fixtures/errors/session-reauthentication-required.json
- Create: access-client/tests/fixtures/errors/permission-denied.json
- Create: access-client/tests/fixtures/errors/validation-failed.json
- Create: access-client/tests/fixtures/errors/client-upgrade-required.json
- Create: access-client/tests/fixtures/errors/blocking-information-required.json
- Create: access-client/tests/fixtures/errors/dependency-unavailable.json
- Create: tests/unit/test_access_fixture_contracts.py
- Create: tests/unit/test_access_route_parity.py
- Create: tests/access/conftest.py
- Create: tests/access/fake_api.py
- Modify: access-client/src/manifest.json
- Modify: access-client/SLUT-Client.accdb
- Modify: access-client/tests/vba/TestRunner.bas
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: AC-01 import/export/build functions; JsonConverter.ParseJson and JsonConverter.ConvertToJson; /api/v1 response envelope and header definitions from openapi/access-v1.yaml.
- Produces: NewApiRequest, ApiSend, ConfigureApiTransportForTest; IApiTransport.Send; JsonParseObject, JsonSerialize, ParseSuccessEnvelope, ParseErrorEnvelope; route functions; UserGuidanceFor; SafeLogEvent; Test_SetApiBaseUrl and Test_GetStateJson.

- [ ] **Step 1: Write failing Python OpenAPI/fixture/route tests**

Create tests/unit/test_access_fixture_contracts.py to load every AC-02 fixture and validate it against the exact response schema named by its x-openapi-fixture-schema field. The `policy/client-current.json` fixture must contain the closed public `ClientPolicy` data object with all nine required fields, including integer `field_notes_max_characters: 30000`; the fixture test asserts that exact value and rejects omission, string coercion, or additional public-policy fields. Create tests/unit/test_access_route_parity.py with:

~~~python
from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
OPENAPI = ROOT / "openapi" / "access-v1.yaml"
ROUTES = ROOT / "access-client" / "src" / "modules" / "modApiRoutes.bas"


def test_user_route_literals_exist_in_openapi():
    contract = yaml.safe_load(OPENAPI.read_text("utf-8"))
    paths = set(contract["paths"])
    source = ROUTES.read_text("utf-8")
    literals = set(re.findall(r'"/api/v1[^"]+"', source))
    normalized = {re.sub(r'&[^"]+', '{id}', item.strip('"')) for item in literals}
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/client-policy" in paths
    assert "/api/v1/me" in paths
    assert "/api/v1/staff" in paths
    assert all(path.startswith("/api/v1/") for path in normalized)


def test_access_routes_never_target_legacy_api():
    source = ROUTES.read_text("utf-8")
    assert '"/api/chat"' not in source
    assert '"/api/reports/' not in source
    assert '"/api/roster' not in source
~~~

- [ ] **Step 2: Run the Python tests and verify the expected failure**

~~~powershell
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py -q
~~~

Expected: FAIL because modApiRoutes.bas and the fictional fixture files do not exist. If openapi/access-v1.yaml is missing or invalid, stop AC-02 and hand the exact failure to the backend contract task.

- [ ] **Step 3: Write failing VBA route, JSON, envelope, error, and log tests**

TestApiRoutes.bas must assert exact documented paths:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestApiRoutes_Run()
    TestAssert.AreEqual "/api/v1/auth/login", RouteAuthLogin(), "login route"
    TestAssert.AreEqual "/api/v1/auth/renew", RouteAuthRenew(), "renew route"
    TestAssert.AreEqual "/api/v1/client-policy", RouteClientPolicy(), "client policy route"
    TestAssert.AreEqual "/api/v1/me", RouteMe(), "profile route"
    TestAssert.AreEqual "/api/v1/staff?query=Smith%20123", RouteStaffSearch("Smith 123"), "staff route"
    TestAssert.AreEqual "/api/v1/incidents/abc", RouteIncident("abc"), "incident route"
    TestAssert.AreEqual "/api/v1/reports/r1/revisions/4", RouteReportRevision("r1", 4), "revision route"
    TestAssert.AreEqual "/api/v1/jobs/j1", RouteJob("j1"), "job route"
    TestAssert.AreEqual "/api/v1/policy/questions", RoutePolicyQuestions(), "policy route"
End Sub
~~~

TestJsonContracts.bas must cover Unicode, null, arrays, missing required members, success envelopes, and safe error envelopes. TestSafeLog.bas must pass strings named pin, access_token, renewal_token, field_notes, name, and employee_number and assert none appears in the resulting diagnostic line.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestApiRoutes_Run,TestJsonContracts_Run,TestErrors_Run,TestSafeLog_Run
~~~

Expected: FAIL at compile time because RouteAuthLogin and JsonParseObject are undefined.

- [ ] **Step 4: Implement request, response, and error value classes**

CApiRequest exposes Method, RelativePath, BodyJson, Headers, ConnectTimeoutMs, SendTimeoutMs, ReceiveTimeoutMs, CanRetry, ModifiesState, OperationName, RetryCount, UsesBearerAuthentication, and AuthenticationReplayCount. Initialize Headers with CreateObject("Scripting.Dictionary"). `UsesBearerAuthentication` defaults false and becomes true only in `AttachCurrentBearer` when that routine adds the current `Authorization: Bearer` header; tests cannot set it true without also supplying that header. `RetryCount` owns the one transport retry, while `AuthenticationReplayCount` independently owns the one post-renewal replay.

CApiResponse exposes StatusCode, BodyText, BodyBytes, ContentType, Headers, and RequestId. Its BodyBytes property must preserve arbitrary DOCX bytes without text conversion.

CApiError exposes Code, Message, Retryable, DetailsJson, RequestId, and HttpStatus. It never stores raw HTML or an exception stack.

IApiTransport contains only:

~~~vb
Option Compare Database
Option Explicit

Public Function Send(ByVal request As CApiRequest) As CApiResponse
End Function
~~~

CFakeApiTransport implements IApiTransport, queues CApiResponse instances, records deep copies of received CApiRequest instances, and raises an explicit test failure if Send is called with an empty queue.

- [ ] **Step 5: Implement centralized routes from the OpenAPI contract**

modApiRoutes.bas defines one function per User endpoint and percent-encodes each path/query component through modUtf8:

~~~vb
Option Compare Database
Option Explicit

Private Const API_PREFIX As String = "/api/v1"

Public Function RouteAuthLogin() As String
    RouteAuthLogin = API_PREFIX & "/auth/login"
End Function

Public Function RouteStaffSearch(ByVal query As String) As String
    RouteStaffSearch = API_PREFIX & "/staff?query=" & UrlEncodeComponent(query)
End Function

Public Function RouteReportRevision(ByVal reportId As String, ByVal revisionNumber As Long) As String
    RouteReportRevision = API_PREFIX & "/reports/" & UrlEncodeComponent(reportId) & _
                          "/revisions/" & CStr(revisionNumber)
End Function

Public Function RouteReportExport(ByVal reportId As String, _
                                  ByVal revisionNumber As Long) As String
    If revisionNumber < 1 Then
        Err.Raise vbObjectError + 2120, "RouteReportExport", _
                  "A saved report revision is required."
    End If
    RouteReportExport = API_PREFIX & "/reports/" & UrlEncodeComponent(reportId) & _
                        "/export-docx?revision=" & CStr(revisionNumber)
End Function
~~~

Also implement RouteAuthRenew, RouteAuthLogout, RouteAuthLogoutAll, RouteAuthChangePin, RouteAuthSessions, RouteAuthSession, RouteMe, RouteClientPolicy, RouteIncidentCreate, RouteIncident, RouteIncidentRevisions, RouteIncidentRevision, RouteIncidentRestore, RouteReports, RouteReport, RouteReportRevisions, RouteReportRestore, RouteReportRecovery, RouteReportExport, RouteIncidentJob, RouteJob, and RoutePolicyQuestions. No route function accepts a complete URL.

- [ ] **Step 6: Implement strict JSON and response-envelope validation**

modJsonContracts.bas wraps the pinned parser:

~~~vb
Public Function JsonParseObject(ByVal jsonText As String) As Object
    Dim parsed As Object
    Set parsed = JsonConverter.ParseJson(jsonText)
    If parsed Is Nothing Then
        Err.Raise vbObjectError + 2101, "JsonParseObject", "Expected a JSON object."
    End If
    Set JsonParseObject = parsed
End Function

Public Function RequireString(ByVal source As Object, ByVal memberName As String) As String
    If Not source.Exists(memberName) Then
        Err.Raise vbObjectError + 2102, "RequireString", "Missing response member: " & memberName
    End If
    If VarType(source(memberName)) <> vbString Then
        Err.Raise vbObjectError + 2103, "RequireString", "Invalid response member: " & memberName
    End If
    RequireString = CStr(source(memberName))
End Function
~~~

ParseSuccessEnvelope requires data, request_id, server_time, and api_version before returning data. ParseErrorEnvelope requires error.code, error.message, error.retryable, request_id, and server_time and rejects raw HTML content types before any form state changes.

- [ ] **Step 7: Implement WinHTTP transport and one bounded safe-read retry**

modBuildInfo.bas contains non-secret version constants and a release database-property boundary. A Test build accepts only an explicit loopback origin; a Release build accepts only the `ApiBaseUrl` custom database property injected by ImportAccessSource.ps1:

~~~vb
Option Compare Database
Option Explicit

Public Const CLIENT_VERSION As String = "0.1.0"
Public Const API_VERSION As String = "v1"

Private mTestApiBaseUrl As String

Public Function ApiBaseUrl() As String
#If TEST_BUILD Then
    If Len(mTestApiBaseUrl) = 0 Then
        Err.Raise vbObjectError + 7100, "ApiBaseUrl", "Test API base URL is not configured."
    End If
    ApiBaseUrl = mTestApiBaseUrl
#Else
    Dim configured As String
    configured = CStr(CurrentDb.Properties("ApiBaseUrl").Value)
    If LCase$(Left$(configured, 8)) <> "https://" Then
        Err.Raise vbObjectError + 7101, "ApiBaseUrl", "Release API base URL must use HTTPS."
    End If
    ApiBaseUrl = configured
#End If
End Function

#If TEST_BUILD Then
Public Sub SetTestApiBaseUrl(ByVal baseUrl As String)
    If LCase$(Left$(baseUrl, 17)) <> "http://127.0.0.1:" Then
        Err.Raise vbObjectError + 7102, "SetTestApiBaseUrl", "Test API must use explicit IPv4 loopback and port."
    End If
    mTestApiBaseUrl = baseUrl
End Sub
#End If
~~~

CWinHttpTransport.Initialize validates that the Release base URI is HTTPS and that every base URI has no user info, query, fragment, or trailing route suffix. Test configuration additionally requires `http://127.0.0.1:{port}`. Send late-binds WinHttp.WinHttpRequest.5.1, calls SetTimeouts, sets Content-Type, Accept, X-Client-Version, X-Request-ID, Authorization, Idempotency-Key, and If-Match only when present on CApiRequest, and returns bytes plus safe headers.

Extend ImportAccessSource.ps1 with `[string]$ApiBaseUrl`. `-Configuration Release` requires that value, validates an exact HTTPS origin, and writes the `ApiBaseUrl` custom database property before compilation; `-Configuration Test` rejects any non-loopback value. A missing or malformed Release origin is a hard stop, not a fallback to the browser application's legacy Cloud Run URL.

ApiSend retries once only when all conditions are true: transport failure or retryable 503; request.CanRetry is true; and request.RetryCount is zero. It never recursively calls itself. Authentication renewal is added in AC-03.

Use these timeout profiles:

~~~vb
Public Sub ApplyFocusedTimeouts(ByVal request As CApiRequest)
    request.ConnectTimeoutMs = 5000
    request.SendTimeoutMs = 10000
    request.ReceiveTimeoutMs = 30000
End Sub

Public Sub ApplyPolicyTimeouts(ByVal request As CApiRequest)
    request.ConnectTimeoutMs = 5000
    request.SendTimeoutMs = 10000
    request.ReceiveTimeoutMs = 90000
End Sub
~~~

AI generation is not assigned a long receive timeout because it uses job submission and polling.

- [ ] **Step 8: Implement stable user guidance and redacted diagnostics**

modErrors.UserGuidanceFor maps at least authentication_required, invalid_credentials, session_reauthentication_required, dependency_unavailable, permission_denied, validation_failed, revision_conflict, idempotency_conflict, request_in_progress, idempotent_response_unavailable, job_result_conflict, blocking_information_required, rate_limited, client_upgrade_required, payload_too_large, and unknown_error. `invalid_credentials` tells the employee that the employee number or PIN was not accepted without distinguishing which value failed. `session_reauthentication_required` says the session ended and sign-in is required. `dependency_unavailable` preserves local work and offers Retry. The default message is:

~~~text
The request could not be completed. Your work is still on this screen. Reference request ID: {request_id}
~~~

SafeLogEvent accepts category, request ID, HTTP status, and client version only. Its parameter list must make sensitive values impossible to pass:

~~~vb
Public Sub SafeLogEvent(ByVal category As String, ByVal requestId As String, _
                        ByVal httpStatus As Long, ByVal clientVersion As String)
End Sub
~~~

Write under %LOCALAPPDATA%\StandardLogisticsUnitTools\Logs with one UTF-8 line per event. Do not log request or response bodies.

- [ ] **Step 9: Implement the local fictional fake API**

tests/access/fake_api.py reads fixture files, never imports Google clients, and serves only loopback:

~~~python
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify


def create_fake_api(fixtures: Path) -> Flask:
    app = Flask(__name__)

    def fixture(relative: str):
        return json.loads((fixtures / relative).read_text("utf-8"))

    @app.get("/api/v1/client-policy")
    def client_policy():
        return jsonify(fixture("policy/client-current.json"))

    @app.get("/api/v1/me")
    def me():
        return jsonify(fixture("profile/me-user.json"))

    return app
~~~

conftest additions in later tasks register further endpoint fixtures against the same create_fake_api function.

- [ ] **Step 10: Import, run tests, and verify source parity**

~~~powershell
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database $env:TEMP\SLUT-Client-AC02.accdb -Configuration Test
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database $env:TEMP\SLUT-Client-AC02.accdb -Tests TestApiRoutes_Run,TestJsonContracts_Run,TestApiClient_Run,TestErrors_Run,TestSafeLog_Run
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py -q
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database $env:TEMP\SLUT-Client-AC02.accdb -Source access-client/src -Platform x64
~~~

Expected: every VBA and Python test passes; no request targets a legacy endpoint; malformed/HTML responses leave state unchanged; logs contain no supplied sensitive strings; source round-trip is clean.

- [ ] **Step 11: Commit AC-02**

~~~powershell
git add access-client/src access-client/tests tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/access/fake_api.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add versioned API client core"
~~~

Expected: one commit limited to AC-02 files and the source-matched Access binary.

---

### Task AC-03: DPAPI secure stores, device/session lifecycle, and employee authentication

**Files:**
- Create: access-client/src/modules/modAuth.bas
- Create: access-client/src/modules/modDpapi.bas
- Create: access-client/src/modules/modSessionStore.bas
- Create: access-client/src/classes/ISecureStore.cls
- Create: access-client/src/classes/CDpapiFileStore.cls
- Create: access-client/src/classes/CUserProfile.cls
- Create: access-client/src/classes/CSessionState.cls
- Create: access-client/tests/vba/TestAuth.bas
- Create: access-client/tests/vba/TestDpapi.bas
- Create: access-client/tests/vba/TestSessionStore.bas
- Create: access-client/tests/vba/classes/CInMemorySecureStore.cls
- Create: access-client/tests/fixtures/auth/login-user.json
- Create: access-client/tests/fixtures/auth/login-temporary-pin.json
- Create: access-client/tests/fixtures/auth/renew-success.json
- Create: access-client/tests/fixtures/auth/sessions.json
- Create: access-client/tests/fixtures/profile/me-user.json
- Modify: access-client/src/modules/modWin32.bas
- Modify: access-client/src/modules/modApiClient.bas
- Modify: access-client/src/modules/modAppState.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/forms/frmLogin.txt
- Modify: access-client/src/forms/frmChangePin.txt
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/fake_api.py
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: AC-02 NewApiRequest, ApiSend, ParseSuccessEnvelope, ParseErrorEnvelope, CApiRequest, CApiResponse, CApiError, and CFakeApiTransport.
- Produces: Login, RenewSession, ChangePin, LogoutCurrent, LogoutAll, LoadCurrentProfile; ProtectForCurrentUser, UnprotectForCurrentUser; GetOrCreateDeviceId; SavePersistentRenewalToken, LoadPersistentRenewalToken, DeletePersistentRenewalToken; ISecureStore methods; CSessionState and CUserProfile validated initializers.

- [ ] **Step 1: Write failing DPAPI and secure-store tests**

Create TestDpapi.bas:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestDpapi_Run()
    Dim plaintext As String
    Dim protectedText As String

    plaintext = "fictional-renewal-token-α"
    protectedText = ProtectForCurrentUser(plaintext)

    TestAssert.IsTrue Len(protectedText) > 0, "DPAPI returns ciphertext"
    TestAssert.AreEqual 0, InStr(1, protectedText, plaintext, vbBinaryCompare), "ciphertext hides plaintext"
    TestAssert.AreEqual plaintext, UnprotectForCurrentUser(protectedText), "DPAPI round trip"
End Sub
~~~

Create TestSessionStore.bas to use a temporary test root, save a fictional renewal token, inspect every byte on disk, load it, corrupt it, and assert corruption deletes the unusable token and returns an empty string. It must also assert that GetOrCreateDeviceId returns the same UUID twice and that no file contains a name, employee number, or PIN.

- [ ] **Step 2: Write failing auth/session contract tests**

TestAuth.bas queues login-user.json, login-temporary-pin.json, renew-success.json, and sessions.json through CFakeApiTransport. It must assert:

- employee number and PIN are present only in the login request body;
- PIN is absent from CSessionState, CUserProfile, ISecureStore, and safe logs;
- keepSignedIn false never calls ISecureStore.WriteSecret;
- keepSignedIn true writes only the renewal token through ISecureStore;
- a temporary-PIN response sets RequiresPinChange true;
- /me profile fields replace any local identity;
- logout-current deletes the local renewal token and access token;
- logout-all also clears all in-memory session state;
- change PIN, logout-current, logout-all, and single-session DELETE each send a nonempty `Idempotency-Key`; a replay retains the original key and byte-identical body;
- login maps `invalid_credentials`, renewal maps `session_reauthentication_required`, and either operation maps `dependency_unavailable` without displaying backend detail;
- a documented `401 authentication_required` on a request that carried the current bearer causes exactly one renewal and one replay, with no recursive renewal;
- login, renewal, and client-policy requests never trigger renewal, and a bearer request's second `401` is returned without another renewal;
- a `503 dependency_unavailable` renewal response retains the in-memory session, embedded profile, and DPAPI credential and surfaces Retry;
- only a definitive renewal rejection (`invalid_credentials` or `session_reauthentication_required`) deletes the persistent credential and clears authenticated state;
- successful renewal atomically replaces both session and the embedded profile, so no observer can see a rotated token paired with the old profile.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestDpapi_Run,TestSessionStore_Run,TestAuth_Run
~~~

Expected: FAIL at compile time because ProtectForCurrentUser, Login, and ISecureStore are undefined.

- [ ] **Step 3: Add pointer-safe DPAPI and file-operation declarations**

Keep all declarations in modWin32.bas. Use this type shape and conditional declarations:

~~~vb
Option Compare Database
Option Explicit

#If VBA7 Then
    Public Type DATA_BLOB
        cbData As Long
        pbData As LongPtr
    End Type

    Public Declare PtrSafe Function CryptProtectData Lib "Crypt32.dll" ( _
        ByRef pDataIn As DATA_BLOB, ByVal szDataDescr As LongPtr, _
        ByVal pOptionalEntropy As LongPtr, ByVal pvReserved As LongPtr, _
        ByVal pPromptStruct As LongPtr, ByVal dwFlags As Long, _
        ByRef pDataOut As DATA_BLOB) As Long

    Public Declare PtrSafe Function CryptUnprotectData Lib "Crypt32.dll" ( _
        ByRef pDataIn As DATA_BLOB, ByVal ppszDataDescr As LongPtr, _
        ByVal pOptionalEntropy As LongPtr, ByVal pvReserved As LongPtr, _
        ByVal pPromptStruct As LongPtr, ByVal dwFlags As Long, _
        ByRef pDataOut As DATA_BLOB) As Long

    Public Declare PtrSafe Function LocalFree Lib "Kernel32.dll" ( _
        ByVal hMem As LongPtr) As LongPtr

    Public Declare PtrSafe Sub CopyMemory Lib "Kernel32.dll" Alias "RtlMoveMemory" ( _
        ByRef destination As Any, ByRef source As Any, ByVal length As LongPtr)
#End If

Public Const CRYPTPROTECT_UI_FORBIDDEN As Long = &H1
~~~

DATA_BLOB.cbData remains Long because the Windows API defines it as DWORD. Pointers and allocated-memory handles use LongPtr. Any failed Windows call raises a stable VBA error without including input text.

- [ ] **Step 4: Implement DPAPI UTF-8/base64 conversion**

modUtf8 owns StringToUtf8Bytes, Utf8BytesToString, BytesToBase64, and Base64ToBytes. modDpapi owns:

~~~vb
Public Function ProtectForCurrentUser(ByVal plaintext As String) As String
End Function

Public Function UnprotectForCurrentUser(ByVal protectedText As String) As String
End Function
~~~

ProtectForCurrentUser converts plaintext to UTF-8 bytes, pins the input array while CryptProtectData runs with current-user scope and CRYPTPROTECT_UI_FORBIDDEN, copies the returned bytes, always calls LocalFree, zeroes the input/output byte arrays, and returns base64. UnprotectForCurrentUser performs the reverse and rejects empty, malformed, or non-DPAPI input.

Do not use machine scope and do not supply a prompt window.

- [ ] **Step 5: Implement injectable secure stores and device identity**

ISecureStore contains the four locked methods. CDpapiFileStore.Initialize accepts an absolute LocalAppData directory and rejects a root, profile root, Documents, Downloads, network path, or path outside %LOCALAPPDATA%\StandardLogisticsUnitTools.

Write a secret through a same-directory temporary file, close it, and atomically replace the final file. Use filenames containing only the allowlisted logical names persistent-renewal-token and device-id. The device ID is non-secret but remains under the same directory with a random UUID; no Windows username or workstation name appears in the filename.

CInMemorySecureStore stores values in a late-bound dictionary and records call counts for tests.

modSessionStore exposes:

~~~vb
Public Function GetOrCreateDeviceId() As String
Public Sub SavePersistentRenewalToken(ByVal renewalToken As String)
Public Function LoadPersistentRenewalToken() As String
Public Sub DeletePersistentRenewalToken()
Public Sub ConfigureSecureStoreForTest(ByVal store As ISecureStore)
~~~

If DPAPI persistence fails, SavePersistentRenewalToken deletes any partial file, clears the persistent flag, and returns control to modAuth so the session remains nonpersistent.

- [ ] **Step 6: Implement validated session/profile classes and app state**

CSessionState.Initialize accepts only the exact OpenAPI login/renew data object and requires access_token, access_expires_at, renewal_token, renewal_expires_at, session_id, persistent, requires_pin_change, and profile. It validates that profile is an object, constructs a `CUserProfile` through `CUserProfile.Initialize`, and exposes that validated object only through `Public Property Get EmbeddedProfile() As CUserProfile`. It holds tokens in private fields and exposes access only to modAuth/modApiClient through narrow Property Get members. It has ClearSensitive to overwrite token strings before releasing them.

Its narrow renewal boundary is `Public Property Get RenewalToken() As String`, `Public Property Get IsPersistent() As Boolean`, and `Public Property Get EmbeddedProfile() As CUserProfile`. No session-only replacement operation is exposed.

CUserProfile.Initialize requires staff_id, employee_number, display_name, rank, shift, role, and status. frmLogin controls never populate these fields directly.

modAppState owns one current CSessionState and CUserProfile and provides:

~~~vb
Public Sub SetAuthenticatedState(ByVal session As CSessionState, ByVal profile As CUserProfile)
Public Function CurrentSession() As CSessionState
Public Function CurrentProfile() As CUserProfile
Public Sub ClearAuthenticatedState()
Public Function CurrentAccessToken() As String
~~~

`SetAuthenticatedState` validates both non-Nothing inputs, places them into local object variables, swaps both module references without calling event/UI code between assignments, then clears/releases the previous session. Callers therefore cannot publish a new session without its response-embedded profile.

- [ ] **Step 7: Implement login, temporary-PIN routing, renewal rotation, and logout**

modAuth.Login normalizes employee number exactly as the OpenAPI contract specifies, accepts a 4–8-character PIN/passcode, builds a device-bound login request, parses both `CSessionState` and the server-owned `CUserProfile` from the same response, writes a renewal token only after DPAPI succeeds, calls `SetAuthenticatedState`, and returns CSessionState. `RenewSession` validates the rotated response's embedded profile and replaces both session and profile atomically; `LoadCurrentProfile` remains the explicit `/me` refresh used during startup and account-screen refresh.

Use one guarded renewal. The error object contains only the safe envelope fields parsed by `CApiError`:

~~~vb
Private mRenewing As Boolean
Private mLastRenewalError As CApiError

Public Function LastRenewalError() As CApiError
    Set LastRenewalError = mLastRenewalError
End Function

Private Function IsDefinitiveRenewalError(ByVal errorCode As String) As Boolean
    IsDefinitiveRenewalError = (errorCode = "invalid_credentials") Or _
                               (errorCode = "session_reauthentication_required")
End Function

Public Function RenewSession() As Boolean
    Dim current As CSessionState
    Dim rotated As CSessionState
    Dim rotatedProfile As CUserProfile
    Dim payload As Object
    Dim request As CApiRequest
    Dim response As CApiResponse
    Dim data As Object
    Dim renewalError As CApiError
    Dim renewalToken As String

    If mRenewing Then
        RenewSession = False
        Exit Function
    End If

    mRenewing = True
    Set mLastRenewalError = Nothing
    On Error GoTo RenewalUnexpected

    Set current = CurrentSession()
    If Not current Is Nothing Then renewalToken = current.RenewalToken
    If Len(renewalToken) = 0 Then renewalToken = LoadPersistentRenewalToken()
    If Len(renewalToken) = 0 Then
        ClearAuthenticatedState
        mRenewing = False
        Err.Raise vbObjectError + 2301, "RenewSession", _
                  "session_reauthentication_required"
    End If

    Set payload = CreateObject("Scripting.Dictionary")
    payload.Add "renewal_token", renewalToken
    payload.Add "device_id", GetOrCreateDeviceId()

    Set request = NewApiRequest("POST", RouteAuthRenew(), JsonSerialize(payload))
    request.CanRetry = False
    request.UsesBearerAuthentication = False
    Set response = ApiSendWithoutRenewal(request)
    If response.StatusCode < 200 Or response.StatusCode > 299 Then
        Set renewalError = ParseErrorEnvelope(response)
        Set mLastRenewalError = renewalError
        If IsDefinitiveRenewalError(renewalError.Code) Then
            DeletePersistentRenewalToken
            ClearAuthenticatedState
        End If
        RenewSession = False
        GoTo RenewalDone
    End If

    Set data = ParseSuccessEnvelope(response)
    Set rotated = New CSessionState
    rotated.Initialize data
    Set rotatedProfile = rotated.EmbeddedProfile
    SetAuthenticatedState rotated, rotatedProfile
    If rotated.IsPersistent Then SavePersistentRenewalToken rotated.RenewalToken

    RenewSession = True
RenewalDone:
    mRenewing = False
    Exit Function

RenewalUnexpected:
    ' A transport, 429/503, or malformed-response failure is not proof that the
    ' server rejected the credential. Keep the session, profile, and DPAPI value.
    RenewSession = False
    Resume RenewalDone
End Function
~~~

`SavePersistentRenewalToken` atomically replaces the stored rotation value. If DPAPI persistence fails after the in-memory swap, it deletes the stale on-disk value and marks the current session nonpersistent without rolling back the valid in-memory session/profile pair.

Modify `ApiSend` with this exact boundary. `AttachCurrentBearer` is the only routine that sets both the header and `UsesBearerAuthentication = True`; login, renewal, and client-policy requests bypass it. `ApiSendWithoutRenewal` retains AC-02's separate one-retry transport rule.

~~~vb
Private Sub RaiseRenewalFailure(ByVal renewalError As CApiError)
    If renewalError Is Nothing Then
        Err.Raise vbObjectError + 2302, "ApiSend", "dependency_unavailable"
    End If
    Err.Raise vbObjectError + 2303, "ApiSend", renewalError.Code
End Sub

Public Function ApiSend(ByVal request As CApiRequest) As CApiResponse
    Dim response As CApiResponse
    Dim apiError As CApiError

    Set response = ApiSendWithoutRenewal(request)
    If response.StatusCode = 401 And request.UsesBearerAuthentication _
       And request.AuthenticationReplayCount = 0 Then
        Set apiError = ParseErrorEnvelope(response)
        If apiError.Code = "authentication_required" Then
            If Not RenewSession() Then RaiseRenewalFailure LastRenewalError()
            request.AuthenticationReplayCount = 1
            request.Headers("Authorization") = "Bearer " & CurrentAccessToken()
            Set response = ApiSendWithoutRenewal(request)
        End If
    End If
    Set ApiSend = response
End Function
~~~

The replay mutates only `AuthenticationReplayCount` and the bearer header. Method, relative path, body bytes, `Idempotency-Key`, `If-Match`, and transport `RetryCount` remain unchanged. A second `401` is returned to normal error handling. A transient renewal failure such as `503 dependency_unavailable` preserves credentials/profile and surfaces Retry; only `invalid_credentials` or `session_reauthentication_required` from renewal clears them.

ChangePin sends current and new PIN once with a new `Idempotency-Key`, parses the response's embedded profile, atomically replaces session/profile through `SetAuthenticatedState`, revokes other sessions as directed by the server, clears form controls immediately, and returns to the shell only after success.

LogoutCurrent and LogoutAll each create one `Idempotency-Key` before the first send and call their server endpoints when reachable; local token/state clearing occurs in a Finally-style cleanup even during network failure. `RevokeSession` sends `DELETE /api/v1/auth/sessions/{session_id}` with its own action key. Any allowed replay reuses the original request object so the key and body are unchanged.

- [ ] **Step 8: Build unbound login and forced-change forms**

frmLogin controls:

- txtEmployeeNumber
- txtPin with InputMask or PasswordChar behavior that never exposes the value
- chkKeepSignedIn with caption Keep me signed in on this Windows account
- cmdSignIn
- lblLoginGuidance
- lblRequestId

frmChangePin controls:

- txtCurrentPin
- txtNewPin
- txtConfirmPin
- cmdChangePin
- lblPinRules
- lblChangeGuidance

Both forms have RecordSource empty and clear PIN controls on success, failure, deactivate, unload, and unexpected error. A session with RequiresPinChange true can navigate only to frmChangePin or logout; modNavigation rejects every other destination.

- [ ] **Step 9: Extend the fake API and run auth/security tests**

Add exact fixture-backed handlers for login, renew, change-pin, logout, logout-all, sessions, session delete, and /me. Record requests in memory so Python/COM tests can assert call counts without logging bodies.

Run:

~~~powershell
python -m pytest tests/unit/test_access_fixture_contracts.py -q
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestDpapi_Run,TestSessionStore_Run,TestAuth_Run,TestApiClient_Run,TestSafeLog_Run
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: all tests PASS; persistent renewal survives reopen under the same Windows account; corrupt DPAPI content is rejected/deleted; temporary PIN cannot navigate past frmChangePin; a 401 yields one renewal and one replay; no test PIN/token/profile string is found in logs or source exports.

Cross-identity DPAPI rejection is recorded as NOT RUN unless the controlled runner supplies a second test identity. It is never reported as passed by inference.

- [ ] **Step 10: Commit AC-03**

~~~powershell
git add access-client/src access-client/tests tests/access/fake_api.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add secure employee sessions"
~~~

Expected: one commit limited to AC-03 files and the source-matched binary.

---

### Task AC-04: Startup, Guided Workspace shell, navigation, dashboard, and client policy

**Files:**
- Create: access-client/src/modules/modAppStartup.bas
- Create: access-client/src/modules/modNavigation.bas
- Create: access-client/src/modules/modTheme.bas
- Create: access-client/src/modules/modClientPolicy.bas
- Create: access-client/src/forms/frmDashboard.txt
- Create: access-client/src/forms/frmUpdateNotice.txt
- Create: access-client/src/forms/sfrmNavigation.txt
- Create: access-client/src/assets/README.md
- Create: access-client/src/assets/shield-crystal-front.png
- Create: access-client/src/assets/seal.png
- Create: access-client/src/assets/app.ico
- Create: access-client/tests/vba/TestClientPolicy.bas
- Create: access-client/tests/fixtures/policy/client-read-only.json
- Create: tests/access/test_user_workflows.py
- Modify: access-client/src/forms/frmShell.txt
- Modify: access-client/src/forms/frmErrorDialog.txt
- Modify: access-client/src/macros/AutoExec.txt
- Modify: access-client/src/modules/modAppState.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/fake_api.py
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: backend/webapp/static/tokens.css
- Consume without modifying: backend/webapp/static/shield-crystal-front.png
- Consume without modifying: backend/webapp/static/seal.svg
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: AC-03 session restoration, renewal, profile, app state, API client, and DPAPI store.
- Produces: AppStart; NavigateTo; ApplyTheme; RefreshClientPolicy() As ClientCompatibility; `TrustedReviewLabOrigin() As String`; `FieldNotesMaxCharacters() As Long`; RefreshDashboard; Test_Navigate and expanded Test_GetStateJson.

- [ ] **Step 1: Write failing startup, navigation, policy, and unbound-form tests**

TestClientPolicy.bas must queue client-current.json and client-read-only.json and assert:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestClientPolicy_Run()
    TestAssert.AreEqual CompatibilityCurrent, RefreshClientPolicy(), "current client"
    TestAssert.AreEqual "https://review.example.gov", TrustedReviewLabOrigin(), _
                        "policy owns the trusted Review Lab origin"
    TestAssert.AreEqual 30000, FieldNotesMaxCharacters(), _
                        "policy owns the release-one field notes maximum"
    TestAssert.AreEqual CompatibilityReadOnly, RefreshClientPolicy(), "minimum client"
    TestAssert.AreEqual 30000, FieldNotesMaxCharacters(), _
                        "read-only policy keeps the same field notes maximum"
    TestAssert.IsTrue ApplicationWritesAllowed() = False, "old client is read only"
    TestAssert.IsTrue ExportsAllowed() = True, "saved export remains allowed"
End Sub
~~~

Both `client-current.json` (produced by AC-02) and the new
`client-read-only.json` fixture contain the same required integer
`field_notes_max_characters: 30000`. Add malformed-policy cases for a missing
value, a JSON string value, zero/negative values, and any value other than
`30000`; each fails closed without replacing the last validated in-memory
policy.

Add COM tests to tests/access/test_user_workflows.py that start Access with no token, assert frmLogin is active, seed a fictional persistent token and assert frmDashboard is active after renewal, assert User navigation contains exactly Home, New Report, My Reports, Reports I Prepared, Policy Expert, Account, and assert every loaded form/subform has an empty RecordSource.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestClientPolicy_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com
~~~

Expected: FAIL because RefreshClientPolicy, frmDashboard, and NavigateTo are undefined.

- [ ] **Step 2: Lock theme tokens and prepare Access-compatible image assets**

modTheme.bas defines:

~~~vb
Public Function ThemeNavy() As Long: ThemeNavy = RGB(14, 26, 43): End Function
Public Function ThemeNavy2() As Long: ThemeNavy2 = RGB(18, 35, 60): End Function
Public Function ThemeGold() As Long: ThemeGold = RGB(201, 151, 28): End Function
Public Function ThemeGoldBright() As Long: ThemeGoldBright = RGB(221, 176, 65): End Function
Public Function ThemeBackground() As Long: ThemeBackground = RGB(247, 245, 240): End Function
Public Function ThemeSurface() As Long: ThemeSurface = RGB(255, 255, 255): End Function
Public Function ThemeText() As Long: ThemeText = RGB(15, 22, 38): End Function
Public Function ThemeSuccess() As Long: ThemeSuccess = RGB(15, 157, 88): End Function
Public Function ThemeDanger() As Long: ThemeDanger = RGB(212, 60, 48): End Function
~~~

Use Segoe UI for every form. Copy shield-crystal-front.png from the approved source bytes. Render seal.svg once to a transparent PNG and app.ico at approved desktop icon sizes; assets/README.md records source path, rendering command, dimensions, and SHA-256. Do not import WebP, video, claw, or animated layers.

- [ ] **Step 3: Implement application/page state and navigation**

modAppState adds:

~~~vb
Public Enum AppPage
    PageLogin = 1
    PageChangePin = 2
    PageHome = 10
    PageNewReport = 20
    PageMyReports = 30
    PagePreparedReports = 40
    PagePolicyExpert = 50
    PageAccount = 60
End Enum

Public Enum ClientCompatibility
    CompatibilityUnknown = 0
    CompatibilityCurrent = 1
    CompatibilityUpdateAvailable = 2
    CompatibilityReadOnly = 3
End Enum
~~~

modNavigation.NavigateTo validates authentication, RequiresPinChange, and ApplicationWritesAllowed before changing frmShell.subMain.SourceObject. It never treats hidden navigation as authorization. PageNewReport is blocked in read-only mode; report viewing, account, and saved-revision export remain available.

sfrmNavigation contains exactly the six User destinations plus Home, using text labels and focus rectangles. No Admin destination or role mutation appears.

- [ ] **Step 4: Implement startup sequencing**

AutoExec calls AppStart. modAppStartup executes this exact order:

1. Load modBuildInfo constants and reject malformed HTTPS base metadata.
2. Get or create the device ID.
3. Load the DPAPI renewal token.
4. If a token exists, call RenewSession.
5. On rejection/revocation, delete it and open frmLogin.
6. After authentication, call LoadCurrentProfile.
7. Call RefreshClientPolicy.
8. Open frmChangePin when required; otherwise open frmShell and PageHome.
9. Refresh the dashboard only after profile and client policy succeed.

AC-06 adds unfinished-job checks and AC-07 adds recovery checks after step 7. Startup catches errors into frmErrorDialog using UserGuidanceFor and request ID; it never shows VBA error text, HTML, or a stack.

- [ ] **Step 5: Implement client compatibility and update notice**

RefreshClientPolicy validates exactly `release_version`, `latest_client_version`, `minimum_client_version`, `minimum_server_version`, `api_version`, `release_notes`, `read_only_required`, `review_lab_origin`, and `field_notes_max_characters` from the closed OpenAPI example for every caller. It rejects package selection, expected hash, signer, URL, bucket, or other extra policy fields; OP-09's authenticated update-grant response owns update package metadata. `field_notes_max_characters` must be a JSON integer exactly equal to `30000` in release one and is stored with the current policy in module memory; `FieldNotesMaxCharacters()` returns it for AC-05. It is never read from modBuildInfo, an environment value, a registry/local table/file, or `release/version.json`. Refresh compares semantic versions numerically, not lexically. `review_lab_origin` must be an HTTPS origin containing scheme, host, and optional port only—no user info, path other than `/`, query, or fragment—and is stored in memory with the current policy. `TrustedReviewLabOrigin()` returns that validated origin for AD-05; it is never sourced from `ApiBaseUrl`, a redirect, the `Host` header, a form, registry, or local table.

frmUpdateNotice displays:

- Update available or Update required
- current and latest versions
- release notes
- Continue for an optional update
- Close application for a required update

This plan does not download or invoke an updater. Required-update state sets ApplicationWritesAllowed false while preserving authentication, reads, recovery viewing, and saved-revision export.

- [ ] **Step 6: Build the unbound shell and dashboard**

frmShell owns:

- imgBrandMark
- lblBrandName with Standard Logistics & Unit Tools and highlighted S-L-U-T initials
- subNavigation
- subMain
- lblEmployeeIdentity
- lblConnectionState
- lblSaveState
- lblClientVersion
- lblUpdateState

frmDashboard owns:

- cmdStartNewReport
- lblOwnedCount
- lblPreparedCount
- lstRecentOwned
- lstRecentPrepared
- lblApiStatus
- lblAiStatus
- lblLastSuccessfulSync
- lstResumableWork

Populate bounded summary controls from authorized /reports pages and the exact service-status contract. Do not fetch complete report content for dashboard rows. If the OpenAPI contract does not supply the required AI/API status or bounded counts, stop this step and request the missing backend contract; do not derive health from an unrelated legacy endpoint.

All state labels include text: Connected, Reconnecting, Update available, Update required, Saved, Saving, Unsaved changes, and Save failed—work preserved. Color reinforces but never replaces text.

- [ ] **Step 7: Add COM-visible test hooks**

modTestHooks implements:

~~~vb
Public Sub Test_Navigate(ByVal destinationName As String, Optional ByVal contextId As String = vbNullString)
    NavigateTo PageFromName(destinationName), contextId
End Sub

Public Function Test_GetStateJson() As String
    Dim state As Object
    Set state = CreateObject("Scripting.Dictionary")
    state.Add "active_form", Screen.ActiveForm.Name
    state.Add "authenticated", Not CurrentSession() Is Nothing
    state.Add "writes_allowed", ApplicationWritesAllowed()
    state.Add "client_version", CLIENT_VERSION
    Test_GetStateJson = JsonSerialize(state)
End Function
~~~

PageFromName accepts only Login, ChangePin, Home, NewReport, MyReports, PreparedReports, PolicyExpert, and Account. Production builds retain hooks but each hook first verifies the compiled TEST_BUILD constant; release builds raise a stable disabled error.

- [ ] **Step 8: Run startup, shell, policy, and display smoke tests**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestClientPolicy_Run,TestAuth_Run,TestErrors_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "startup or navigation or client_policy or unbound"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: no-token startup opens frmLogin; valid renewal opens PageHome; temporary PIN opens frmChangePin; User navigation is exact; required update blocks writes but not reads/export; all forms are unbound; no raw error appears.

Manually inspect frmShell and frmDashboard at 1366 by 768 under 100%, 125%, and 150% scaling before accepting the task. Stop if any required control is clipped or cannot receive keyboard focus.

- [ ] **Step 9: Commit AC-04**

~~~powershell
git add access-client/src access-client/tests/vba/TestClientPolicy.bas access-client/tests/fixtures/policy tests/access/fake_api.py tests/access/test_user_workflows.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add guided workspace shell"
~~~

Expected: one commit limited to AC-04 files and the source-matched binary.

---

### Task AC-05: Six-step workflow foundation, officer selection, and field notes

**Files:**
- Create: access-client/src/modules/modReportWorkflow.bas
- Create: access-client/src/classes/CWorkflowState.cls
- Create: access-client/src/forms/frmIncidentOfficers.txt
- Create: access-client/src/forms/frmFieldNotes.txt
- Create: access-client/src/forms/sfrmStaffSearchResults.txt
- Create: access-client/tests/vba/TestReportWorkflow.bas
- Create: access-client/tests/fixtures/staff/search-results.json
- Create: access-client/tests/fixtures/reports/incident-created-multi-officer.json
- Modify: access-client/src/forms/frmShell.txt
- Modify: access-client/src/forms/frmDashboard.txt
- Modify: access-client/src/modules/modNavigation.bas
- Modify: access-client/src/modules/modApiRoutes.bas
- Modify: access-client/src/modules/modAppState.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/fake_api.py
- Modify: tests/access/test_user_workflows.py
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: CurrentProfile, NewApiRequest, ApiSend, route helpers, JsonSerialize, ParseSuccessEnvelope, NavigateTo, ApplicationWritesAllowed, and AC-04 `FieldNotesMaxCharacters() As Long` from the validated in-memory client policy.
- Produces: SearchActiveStaff, BeginNewIncident, SetFieldNotes; CWorkflowState; StartNewReport, ShowWorkflowStep, CurrentWorkflow; Step 1 and Step 2 test hooks.

- [ ] **Step 1: Write failing workflow-domain tests**

TestReportWorkflow.bas must assert that the authenticated staff UUID is the initial reporting officer, server staff search returns only active stable UUID records, duplicates are rejected by UUID, multiple officers preserve selection order, and field-note mutation does not call an AI route.

Include:

~~~vb
Public Sub TestReportWorkflow_Run()
    Dim selected As New Collection
    Dim state As CWorkflowState

    selected.Add "staff-user-001"
    selected.Add "staff-owner-002"
    Set state = BeginNewIncident(selected)

    TestAssert.AreEqual "incident-001", state.IncidentId, "server incident id"
    TestAssert.AreEqual 2, state.ReportingStaffIds.Count, "two reporting officers"
    TestAssert.AreEqual "staff-user-001", state.ReportingStaffIds(1), "signed in default"

    SetFieldNotes state, "Fictional field notes."
    TestAssert.AreEqual "Fictional field notes.", state.FieldNotes, "field notes retained"
    SetFieldNotes state, String$(FieldNotesMaxCharacters(), "F")
    TestAssert.AreEqual 30000, Len(state.FieldNotes), "maximum accepted"
    On Error Resume Next
    SetFieldNotes state, String$(FieldNotesMaxCharacters() + 1, "F")
    TestAssert.IsTrue Err.Number <> 0, "maximum plus one rejected"
    Err.Clear
    On Error GoTo 0
End Sub
~~~

Preserve the exact 30,000-accepted/30,001-rejected assertions. The rejected
call must not replace the already accepted value or invoke an API/AI route.

- [ ] **Step 2: Write failing COM workflow tests**

Add tests that sign in as the fictional User, click Start a new incident report, assert the User is preselected, search by fictional name and employee number, select a second officer, continue, enter Unicode field notes, and confirm the fake API has received one incident creation but zero job submissions.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportWorkflow_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "officer or field_notes"
~~~

Expected: FAIL because CWorkflowState and frmIncidentOfficers do not exist.

- [ ] **Step 3: Implement workflow state as the only mutable report workspace**

CWorkflowState has private members and typed Property Get/Let boundaries for:

- IncidentId
- IncidentBaseRevisionNumber
- ReportingStaffIds
- ReportingStaffSummaries
- FieldNotes
- Classification
- ExtractedFacts
- GapAnswers
- Charges
- ReportsById
- CurrentReportId
- JobIdsByType
- Dirty
- LastChangedUtc
- SaveStateText

Initialize every collection/dictionary in Class_Initialize. Expose ToRecoveryJson and LoadRecoveryJson only in AC-07. No form owns canonical field data.

modAppState stores one current CWorkflowState through SetCurrentWorkflow, CurrentWorkflow, and ClearCurrentWorkflow.

- [ ] **Step 4: Implement active-staff search and officer selection**

SearchActiveStaff trims the query, requires at least two characters unless the query is a complete employee number allowed by the OpenAPI schema, calls GET /api/v1/staff?query=, validates staff_id, employee_number, display_name, rank, shift, and active status, and returns a Collection of dictionaries. It never caches roster rows to disk.

frmIncidentOfficers is unbound and contains:

- txtStaffSearch
- cmdSearchStaff
- subStaffSearchResults
- lstSelectedOfficers
- cmdAddOfficer
- cmdRemoveOfficer
- lblOwnershipExplanation
- cmdContinueToFieldNotes

Set lblOwnershipExplanation to:

~~~text
The named officer owns their report. If you prepare it for someone else, you are recorded as the preparer. You both use the same canonical report, and every revision identifies its actual editor.
~~~

Preselect CurrentProfile.StaffId. Prevent removal when it would leave zero reporting officers. The server remains authoritative for active status and duplicate selection.

- [ ] **Step 5: Implement incident creation and six-step navigation foundation**

modReportWorkflow defines:

~~~vb
Public Enum WorkflowStep
    WorkflowOfficers = 1
    WorkflowFieldNotes = 2
    WorkflowFacts = 3
    WorkflowGaps = 4
    WorkflowReports = 5
    WorkflowExport = 6
End Enum
~~~

BeginNewIncident posts the selected stable UUIDs with a new idempotency key, validates incident ID/current revision and returned report ownership summaries, creates CWorkflowState, and stores it in modAppState. It ignores client-supplied owner/preparer identity fields because those fields are not sent.

ShowWorkflowStep loads the matching unbound form into frmShell.subMain and rejects skipping ahead when required state is absent. AC-05 permits only Steps 1 and 2.

- [ ] **Step 6: Implement bounded field-note editing without AI submission**

frmFieldNotes controls:

- txtFieldNotes
- lblCharacterCount
- lblCharacterBounds
- lblIncidentId
- lblCreatedBy
- lblConnectionState
- lblSaveState
- cmdBackToOfficers
- cmdContinueToReviewFacts

`SetFieldNotes(state, value)` calls AC-04 `FieldNotesMaxCharacters()` and uses a surrogate-pair-aware VBA counter matching Pydantic's decoded-Unicode-code-point `max_length`: one valid high/low UTF-16 pair counts as one, while an unpaired high or low surrogate is invalid. It performs no Unicode normalization. It rejects invalid/over-limit text locally without changing the last accepted value and does not accept a caller-supplied maximum or duplicate the literal in AC-05. Because AC-04 already validates and stores the required release-one policy value, AC-05 has no undefined maximum/source stop. It updates `CWorkflowState` and marks it dirty in memory only after validation. The VBA and fake/COM tests prove a non-BMP fictional character counts as one, exactly 30,000 code points are accepted, 30,001 are rejected before an API or AI call, and the visible bounds label uses the same counter and `30000` in-memory policy value.

The form’s Change event updates state and character count but makes no classify, extract, generate, or policy call. Continue is the first point that AC-06 may submit classification.

- [ ] **Step 7: Add fake staff/incident endpoints and verify request ownership**

Serve fixture-backed staff search and incident creation. The fake API must reject a request containing prepared_by_staff_member_id, owner_account_id, employee_number as identity authority, or reporting officer data without staff UUIDs.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportWorkflow_Run,TestApiRoutes_Run,TestApiClient_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "officer or field_notes"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: signed-in User is selected by server UUID; second officer can be added; one canonical incident is returned; field notes remain editable; no AI route is called before Continue; all forms remain unbound.

- [ ] **Step 8: Commit AC-05**

~~~powershell
git add access-client/src access-client/tests/vba/TestReportWorkflow.bas access-client/tests/fixtures/staff access-client/tests/fixtures/reports/incident-created-multi-officer.json tests/access/fake_api.py tests/access/test_user_workflows.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add incident workflow foundation"
~~~

Expected: one commit limited to AC-05 files and the source-matched binary.

---

### Task AC-06: AI jobs, classification/extraction, fact review, gaps, and resume

**Files:**
- Create: access-client/src/modules/modJobs.bas
- Create: access-client/src/classes/CJobState.cls
- Create: access-client/src/forms/frmFactReview.txt
- Create: access-client/src/forms/frmGapReview.txt
- Create: access-client/src/forms/frmJobProgress.txt
- Create: access-client/src/forms/sfrmGapQuestions.txt
- Create: access-client/tests/vba/TestJobs.bas
- Create: access-client/tests/fixtures/jobs/queued.json
- Create: access-client/tests/fixtures/jobs/running.json
- Create: access-client/tests/fixtures/jobs/succeeded.json
- Create: access-client/tests/fixtures/jobs/failed.json
- Create: access-client/tests/fixtures/errors/blocking-information-required.json
- Modify: access-client/src/modules/modReportWorkflow.bas
- Modify: access-client/src/modules/modAppStartup.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/classes/CWorkflowState.cls
- Modify: access-client/src/forms/frmFieldNotes.txt
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestReportWorkflow.bas
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/fake_api.py
- Modify: tests/access/test_user_workflows.py
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: AC-05 workflow state/steps, AC-02 API core, documented classify/extract/generate/disciplinary job routes, and server-defined gap schemas.
- Produces: SubmitJob, PollJob, NextPollDelaySeconds, ResumeKnownJobs; CJobState; ApplyClassificationResult, ApplyExtractionResult, ConfirmFactReview, CollectGapAnswers, CanSubmitGeneration.

- [ ] **Step 1: Write failing job-state/idempotency/backoff tests**

TestJobs.bas:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestJobs_Run()
    TestAssert.AreEqual 2, NextPollDelaySeconds(1), "first poll"
    TestAssert.AreEqual 4, NextPollDelaySeconds(2), "second poll"
    TestAssert.AreEqual 6, NextPollDelaySeconds(3), "third poll"
    TestAssert.AreEqual 8, NextPollDelaySeconds(4), "fourth poll"
    TestAssert.AreEqual 10, NextPollDelaySeconds(5), "fifth poll"
    TestAssert.AreEqual 10, NextPollDelaySeconds(50), "bounded poll"

    Dim job As CJobState
    Set job = SubmitJob("incident-001", "classify", "{""field_notes"":""fictional""}", "idem-classify-001")
    TestAssert.AreEqual "job-001", job.JobId, "job id"
    TestAssert.AreEqual "queued", job.State, "queued state"
End Sub
~~~

Add assertions that the same intended UI action reuses one idempotency key until the submission response arrives; a new explicit action gets a new key; buttons remain disabled while submission is outstanding.

- [ ] **Step 2: Write failing fact/gap/COM tests**

Add COM scenarios:

1. Continue submits classification, closes/reopens frmJobProgress, and polls queued → running → succeeded.
2. Classification displays incident type and suggested charges; employee changes the type and unchecks a charge.
3. Extraction displays persons, dates/times, locations, roster resolution, and provenance.
4. Employee edits a suggested fact and explicitly confirms.
5. A blocking unanswered gap disables generation.
6. Unknown is available only when the server gap object allows it.
7. Closing and reopening the job form resumes by job ID without a second POST.
8. A failed AI job preserves field notes and previously saved work.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestJobs_Run,TestReportWorkflow_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "classification or extraction or gap or job"
~~~

Expected: FAIL because NextPollDelaySeconds, CJobState, frmFactReview, and frmGapReview are undefined.

- [ ] **Step 3: Implement durable job value/state handling**

CJobState.Initialize validates job_id, incident_id, job_type, state, stage, created_at, and optional result/error fields. Allowed state values are queued, running, succeeded, failed, and cancelled. Allowed visible stages are queued, classifying, extracting, validating, generating, disciplinary, completed, and failed.

modJobs:

~~~vb
Public Function NextPollDelaySeconds(ByVal pollNumber As Long) As Long
    If pollNumber < 1 Then pollNumber = 1
    NextPollDelaySeconds = pollNumber * 2
    If NextPollDelaySeconds > 10 Then NextPollDelaySeconds = 10
End Function
~~~

SubmitJob sets Idempotency-Key, disables the initiating control before sending, validates the returned durable job, and stores JobId under state.JobIdsByType(jobType). PollJob is always a safe GET. No code issues a provider request directly.

- [ ] **Step 4: Build nonblocking job progress and resume**

frmJobProgress uses Form_Timer. It starts with TimerInterval 2000, calls PollJob once per tick, updates stage text, and sets the next interval to NextPollDelaySeconds(pollNumber) multiplied by 1000. It sets TimerInterval 0 before each network call to prevent reentry, then restores it after the call.

Closing frmJobProgress stops local polling only. ResumeKnownJobs iterates CWorkflowState.JobIdsByType, polls unfinished IDs, and returns a Collection of current CJobState objects. modAppStartup invokes ResumeKnownJobs after profile/client-policy load when a current or recovered workflow supplies known IDs.

- [ ] **Step 5: Implement classification review and charge confirmation**

ApplyClassificationResult validates incident_type, display label, suggested charges, and provenance metadata from the succeeded job result. frmFactReview shows:

- cboIncidentType
- lstSuggestedCharges with checked/unchecked state
- lstPersons
- lstDatesTimes
- lstLocations
- lstRosterResolutions
- lstProvenance
- chkFactsConfirmed
- cmdBackToFieldNotes
- cmdContinueToGaps

Charges are labeled suggestions. Unchecking removes them from state; adding requires a server-recognized charge code from the response catalog. chkFactsConfirmed is required before leaving Step 3.

- [ ] **Step 6: Implement extraction result edits and server-defined gap controls**

ApplyExtractionResult stores only validated, editable structured facts and server provenance in CWorkflowState. It never converts missing values into invented defaults.

frmGapReview and sfrmGapQuestions render each server gap from question, slot, answer_type, options, blocking, allow_unknown, and default. Supported answer types are text, choice, and yes_no. The control writes to state.GapAnswers by slot.

CanSubmitGeneration returns False when any blocking gap lacks a nonempty answer or an explicitly allowed UNKNOWN:

~~~vb
Public Function CanSubmitGeneration(ByVal gaps As Collection, ByVal answers As Object) As Boolean
    Dim gap As Variant
    For Each gap In gaps
        If CBool(gap("blocking")) Then
            If Not answers.Exists(CStr(gap("slot"))) Then Exit Function
            If Len(Trim$(CStr(answers(CStr(gap("slot")))))) = 0 Then Exit Function
            If CStr(answers(CStr(gap("slot")))) = "UNKNOWN" And Not CBool(gap("allow_unknown")) Then Exit Function
        End If
    Next gap
    CanSubmitGeneration = True
End Function
~~~

The Continue to Reports button follows CanSubmitGeneration, but a server 422 remains authoritative and maps field guidance back into the visible gap controls without clearing answers.

- [ ] **Step 7: Implement generate and disciplinary job orchestration**

The Generate action submits one generate job with confirmed facts, answers, charges, selected reporters, base incident revision, and a new action idempotency key. If the result indicates a required disciplinary stage, submit one disciplinary job after the primary reports complete, retaining already completed reports on failure.

On success, apply results through CWorkflowState, store returned report IDs/revisions by reporting officer, and navigate to Step 5. Do not generate narrative in VBA and do not send raw notes to any endpoint not defined by the OpenAPI job request schema.

- [ ] **Step 8: Expand fake API and run AI workflow tests**

The fake API keeps per-job state counters so GET /jobs/{job_id} returns queued, running, then succeeded. It validates that one POST exists per idempotency key and returns 409 when a key is reused with changed input.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestJobs_Run,TestReportWorkflow_Run,TestErrors_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "classification or extraction or gap or job"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: polling is 2/4/6/8/10 seconds; no duplicate job submission occurs; fact edits and charge choices survive navigation; blocking gaps stop generation; allowed UNKNOWN works; failures preserve visible work; resume uses GET only.

- [ ] **Step 9: Commit AC-06**

~~~powershell
git add access-client/src access-client/tests/vba/TestJobs.bas access-client/tests/fixtures/jobs access-client/tests/fixtures/errors/blocking-information-required.json tests/access/fake_api.py tests/access/test_user_workflows.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add resumable AI review workflow"
~~~

Expected: one commit limited to AC-06 files and the source-matched binary.

---

### Task AC-07: Report editor, immutable revisions, autosave, encrypted recovery, and conflicts

**Files:**
- Create: access-client/src/modules/modAutosave.bas
- Create: access-client/src/modules/modRecovery.bas
- Create: access-client/src/modules/modConflict.bas
- Create: access-client/src/classes/IRecoveryStore.cls
- Create: access-client/src/classes/CAtomicRecoveryStore.cls
- Create: access-client/src/classes/IClock.cls
- Create: access-client/src/classes/CSystemClock.cls
- Create: access-client/src/classes/CReportState.cls
- Create: access-client/src/forms/frmReportEditor.txt
- Create: access-client/src/forms/frmRevisionHistory.txt
- Create: access-client/src/forms/frmRevisionCompare.txt
- Create: access-client/src/forms/frmRevisionConflict.txt
- Create: access-client/src/forms/frmRecoveryPrompt.txt
- Create: access-client/src/forms/sfrmReportTabs.txt
- Create: access-client/src/forms/sfrmRevisionList.txt
- Create: access-client/tests/vba/TestAutosave.bas
- Create: access-client/tests/vba/TestRecovery.bas
- Create: access-client/tests/vba/TestConflict.bas
- Create: access-client/tests/vba/classes/CInMemoryRecoveryStore.cls
- Create: access-client/tests/vba/classes/CFakeClock.cls
- Create: access-client/tests/fixtures/reports/report-detail.json
- Create: access-client/tests/fixtures/reports/revision-page.json
- Create: access-client/tests/fixtures/reports/revision-conflict.json
- Create: access-client/tests/fixtures/reports/recovery-created.json
- Create: access-client/tests/fixtures/recovery/workflow-state-v1.json
- Create: tests/access/test_recovery_after_termination.py
- Modify: access-client/src/modules/modWin32.bas
- Modify: access-client/src/modules/modReportWorkflow.bas
- Modify: access-client/src/modules/modAppStartup.bas
- Modify: access-client/src/modules/modAppState.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/classes/CWorkflowState.cls
- Modify: access-client/src/forms/frmShell.txt
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestReportWorkflow.bas
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/fake_api.py
- Modify: tests/access/test_user_workflows.py
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: AC-06 generated report IDs/content, AC-03 DPAPI, AC-02 API/errors, report/incident revision endpoints, and CWorkflowState.
- Produces: CopyReportControlsToState, LoadReportStateIntoControls, SwitchReportTab, MarkDirty, SaveNow, OnIdleTimer; IRecoveryStore methods; IClock methods; SerializeRecoverySnapshot, DetectRecoverySnapshots, HandleRevisionConflict, CreateRecoveryRevision; CReportState.

- [ ] **Step 1: Write failing report-tab and revision tests**

Extend TestReportWorkflow.bas to create two CReportState instances, load the first tab, edit narrative and a header control, switch to the second tab, switch back, and assert the first edits remain in CWorkflowState. Assert every successful manual save updates BaseRevisionNumber and LastEditor metadata from the server response.

Use:

~~~vb
Public Sub TestReportTabSwitch_Run()
    Dim state As CWorkflowState
    Set state = BuildTwoReportWorkflowFixture()

    LoadReportStateIntoControls Forms!frmReportEditor, state, "report-001"
    Forms!frmReportEditor!txtNarrative.Value = "Edited fictional narrative one."
    SwitchReportTab Forms!frmReportEditor, state, "report-002"
    SwitchReportTab Forms!frmReportEditor, state, "report-001"

    TestAssert.AreEqual "Edited fictional narrative one.", _
        Forms!frmReportEditor!txtNarrative.Value, "tab edit survives switch"
End Sub
~~~

BuildTwoReportWorkflowFixture is a test helper in TestReportWorkflow.bas that constructs both reports explicitly from fictional dictionaries.

- [ ] **Step 2: Write failing autosave, recovery, and conflict tests**

TestAutosave.bas injects CFakeClock and CInMemoryRecoveryStore:

~~~vb
Public Sub TestAutosave_Run()
    Dim state As CWorkflowState
    Set state = BuildTwoReportWorkflowFixture()

    ConfigureAutosaveForTest NewFakeClockAtZero(), NewInMemoryRecoveryStore()
    MarkDirty state
    AdvanceFakeClockMilliseconds 59000
    OnIdleTimer state
    TestAssert.AreEqual 0, FakeTransportSendCount(), "no early save"

    AdvanceFakeClockMilliseconds 1000
    OnIdleTimer state
    TestAssert.AreEqual 1, FakeTransportSendCount(), "one idle save"
End Sub
~~~

TestRecovery.bas asserts:

- plaintext fixture serializes to the versioned bounded shape;
- encrypted file bytes contain none of its fictional narrative;
- atomic write leaves no .tmp after success;
- failed cloud save leaves the encrypted snapshot;
- successful matching revision removes it;
- a corrupt snapshot is reported safely and not opened;
- a snapshot older than seven days is listed for explicit discard, not silently overwritten.

TestConflict.bas queues revision-conflict.json and asserts local controls are unchanged, no automatic PATCH follows, Open newest revision performs a GET, and Save local work as a recovery revision performs one dedicated POST.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportTabSwitch_Run,TestAutosave_Run,TestRecovery_Run,TestConflict_Run
~~~

Expected: FAIL because CReportState, MarkDirty, and IRecoveryStore are undefined.

- [ ] **Step 3: Implement report state and unbound multi-report editor**

CReportState validates and stores:

- ReportId
- IncidentId
- ReportType
- ReportingStaffId
- ReportingOfficerDisplay
- PreparedByStaffId
- Status
- BaseRevisionNumber
- EditableContent
- LastEditorDisplay
- LastEditedAt
- ValidationFlags
- AiWarnings
- Dirty

frmReportEditor controls:

- subReportTabs
- txtNarrative
- txtUnitDivision
- txtOfficerLast
- txtOfficerFirst
- txtEmployeeNumber
- txtRank
- txtShiftAssignment
- txtIncidentDate
- txtIncidentTime
- txtLocation
- txtInmatesInvolved
- txtEmployeesInvolved
- txtInmatesPresent
- txtEmployeesPresent
- txtOthersPresent
- txtInmateInjuries
- txtInmateTreatment
- txtOfficerInjuries
- txtOfficerTreatment
- txtRecommendation
- chk005
- chk409
- lblRevision
- lblLastEditor
- lblLastEditedAt
- lblSaveState
- lstValidationFlags
- lstAiWarnings
- cmdSaveNow
- cmdRevisionHistory
- cmdContinueToExport

Every editable control has no ControlSource. Its Change/AfterUpdate event copies into the active CReportState and calls MarkDirty. SwitchReportTab always calls CopyReportControlsToState before changing CurrentReportId.

- [ ] **Step 4: Implement a monotonic 60-second idle autosave**

IClock contains UtcNow and MonotonicMilliseconds. CSystemClock uses UTC conversion plus GetTickCount64 through modWin32; the Win64 and VBA7 declaration returns a 64-bit-compatible value converted to Double. CFakeClock allows explicit advancement.

modAutosave holds injected/default clock and recovery store:

~~~vb
Private Const IDLE_SAVE_MILLISECONDS As Double = 60000#
Private mClock As IClock
Private mRecoveryStore As IRecoveryStore
Private mSaveInProgress As Boolean

Public Sub MarkDirty(ByVal state As CWorkflowState)
    state.Dirty = True
    state.LastChangedMonotonicMs = CurrentClock().MonotonicMilliseconds()
    state.SaveStateText = "Unsaved changes"
End Sub

Public Sub OnIdleTimer(ByVal state As CWorkflowState)
    If state Is Nothing Then Exit Sub
    If Not state.Dirty Then Exit Sub
    If mSaveInProgress Then Exit Sub
    If CurrentClock().MonotonicMilliseconds() - state.LastChangedMonotonicMs < IDLE_SAVE_MILLISECONDS Then Exit Sub
    Call SaveNow(state, "autosave")
End Sub
~~~

frmShell uses a 1000 ms TimerInterval only to evaluate idle state; it does not save per tick or per keystroke.

- [ ] **Step 5: Implement bounded recovery serialization and atomic encrypted files**

CWorkflowState.ToRecoveryJson emits exactly:

~~~json
{
  "schema_version": 1,
  "snapshot_id": "incident-001",
  "incident_id": "incident-001",
  "incident_base_revision_number": 4,
  "captured_at": "2026-08-12T12:00:00Z",
  "reporting_staff_ids": ["staff-user-001", "staff-owner-002"],
  "field_notes": "Fictional field notes.",
  "classification": {},
  "extracted_facts": {},
  "gap_answers": {},
  "charges": [],
  "reports": {},
  "job_ids_by_type": {}
}
~~~

It excludes profile display fields, employee number, PINs, tokens, diagnostics, and API base URL. Enforce OpenAPI collection/string/depth bounds before serialization.

CAtomicRecoveryStore.Initialize receives the fixed Recovery directory and uses ProtectForCurrentUser. WriteSnapshot writes ciphertext to snapshotId.tmp, closes/flushed data, then calls MoveFileExW with MOVEFILE_REPLACE_EXISTING and MOVEFILE_WRITE_THROUGH. The final filename is incident UUID plus .recovery. A failure removes only the matching temporary file and preserves any prior valid final file.

Add pointer-safe MoveFileExW and DeleteFileW declarations to modWin32. Validate the resolved path remains directly under the Recovery directory before replacing/deleting.

- [ ] **Step 6: Implement SaveNow transaction sequencing and visible save states**

SaveNow:

1. Copies active controls into CWorkflowState.
2. Serializes and writes the encrypted recovery snapshot.
3. Sets Saving and mSaveInProgress.
4. PATCHes dirty incident state with base_revision_number and one idempotency key.
5. PATCHes each dirty report with its own base revision and idempotency key.
6. Applies only server-returned next revision numbers/editor timestamps.
7. Clears dirty flags and removes the matching snapshot only after every required save succeeds.
8. Sets Saved and records LastSuccessfulSync.

On network/API failure it sets Save failed—work preserved, keeps controls and the snapshot, and returns the existing incident revision. It never reports success for a partial save.

- [ ] **Step 7: Implement revision history, comparison, restoration, and 409 choices**

frmRevisionHistory and sfrmRevisionList show revision number, reason, editor, created time, changed-field summary, and source AI job when present. Opening one revision GETs its complete snapshot on demand.

frmRevisionCompare shows a field-by-field local/server comparison with Local value, Server value, server editor/time, and changed-field list. No field is automatically selected for merge.

frmRevisionConflict buttons:

- cmdOpenNewestRevision
- cmdSaveRecoveryRevision
- cmdCancel

HandleRevisionConflict receives CApiError and the current state, leaves controls untouched, retrieves safe current revision metadata, and opens frmRevisionConflict. CreateRecoveryRevision posts local state to /reports/{report_id}/recovery-revisions with a new idempotency key. Restoration posts the chosen source revision and creates a new current revision; it never changes historical rows.

- [ ] **Step 8: Integrate startup recovery decisions**

After authentication/profile/client-policy load, AppStart calls DetectRecoverySnapshots. frmRecoveryPrompt lists bounded snapshot IDs and capture times and offers Recover, Compare, or Discard.

- Recover with the same cloud base opens the recovered state and saves only after employee confirmation.
- Recover against a newer server revision creates a separate recovery revision.
- Compare opens frmRevisionCompare.
- Discard deletes only the selected encrypted file after confirmation.
- Files older than seven days are labeled Expired recovery—discard required and remain until explicit discard.

- [ ] **Step 9: Add forced-termination COM recovery test**

tests/access/test_recovery_after_termination.py:

~~~python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from access_com import AccessSession


@pytest.mark.access_com
def test_forced_termination_offers_encrypted_recovery(fake_api_url: str, access_database: Path):
    session = AccessSession(access_database, fake_api_url)
    session.start()
    session.run("Test_Navigate", "NewReport")
    session.run("Test_SeedDirtyWorkflow")
    session.run("Test_TriggerAutosave")
    recovery_path = Path(session.run("Test_GetRecoveryPath"))
    assert recovery_path.is_file()
    assert b"Fictional field notes" not in recovery_path.read_bytes()
    session.run("Test_ExitWithoutCleanup")

    reopened = AccessSession(access_database, fake_api_url)
    reopened.start()
    state = json.loads(reopened.run("Test_GetStateJson"))
    assert state["active_form"] == "frmRecoveryPrompt"
    reopened.close()
~~~

AccessSession is implemented in tests/access/access_com.py using the PowerShell COM bridge; it never kills an unrelated Access process. Test_ExitWithoutCleanup closes only the test Application instance after persisting the snapshot and skipping normal cleanup.

- [ ] **Step 10: Run editor/revision/recovery tests**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportTabSwitch_Run,TestAutosave_Run,TestRecovery_Run,TestConflict_Run
python -m pytest tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py -q -m access_com -k "report or revision or autosave or recovery or conflict"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: tab edits survive switches; one idle save begins at 60 seconds; snapshots are ciphertext; failure preserves work; success removes the matching snapshot; 409 never writes automatically; recovery against newer state creates a separate revision; forced termination offers recovery.

- [ ] **Step 11: Commit AC-07**

~~~powershell
git add access-client/src access-client/tests/vba/TestAutosave.bas access-client/tests/vba/TestRecovery.bas access-client/tests/vba/TestConflict.bas access-client/tests/vba/classes access-client/tests/fixtures/reports access-client/tests/fixtures/recovery tests/access/fake_api.py tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add revision-safe recovery editing"
~~~

Expected: one commit limited to AC-07 files and the source-matched binary.

---

### Task AC-08: Owned/prepared history, Policy Expert citations, and account/session screens

**Files:**
- Create: access-client/src/modules/modPolicyExpert.bas
- Create: access-client/src/classes/CPagedResult.cls
- Create: access-client/src/forms/frmReportHistory.txt
- Create: access-client/src/forms/frmPolicyExpert.txt
- Create: access-client/src/forms/frmAccount.txt
- Create: access-client/src/forms/frmSessionList.txt
- Create: access-client/src/forms/frmConfirmAction.txt
- Create: access-client/src/forms/sfrmReportQueue.txt
- Create: access-client/src/forms/sfrmPolicyCitations.txt
- Create: access-client/src/forms/sfrmSessionResults.txt
- Create: access-client/tests/vba/TestPolicyExpert.bas
- Create: access-client/tests/fixtures/reports/owned-page.json
- Create: access-client/tests/fixtures/reports/prepared-page.json
- Create: access-client/tests/fixtures/policy/answer-with-citations.json
- Modify: access-client/src/modules/modReportWorkflow.bas
- Modify: access-client/src/modules/modAuth.bas
- Modify: access-client/src/modules/modAppStartup.bas
- Modify: access-client/src/modules/modNavigation.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/forms/frmDashboard.txt
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestAuth.bas
- Modify: access-client/tests/vba/TestReportWorkflow.bas
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/fake_api.py
- Modify: tests/access/test_user_workflows.py
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: openapi/access-v1.yaml

**Interfaces:**
- Consumes: authenticated profile/session, report list/detail/revision APIs, AC-07 editor, /api/v1/policy/questions, and current-user session endpoints.
- Produces: LoadReportPage, AskPolicyQuestion; CPagedResult; LoadAccountSessions, RevokeSession; bounded dashboard/history/account view behavior.

- [ ] **Step 1: Write failing paginated owned/prepared queue tests**

Extend TestReportWorkflow.bas:

~~~vb
Public Sub TestReportHistory_Run()
    Dim owned As CPagedResult
    Dim prepared As CPagedResult

    Set owned = LoadReportPage("owned", "{""status"":""in_progress""}")
    Set prepared = LoadReportPage("prepared", "{}")

    TestAssert.AreEqual 2, owned.Items.Count, "owned rows"
    TestAssert.AreEqual 1, prepared.Items.Count, "prepared rows"
    TestAssert.AreEqual "cursor-owned-next", owned.NextCursor, "owned cursor"
    TestAssert.AreEqual "report-shared-001", prepared.Items(1)("report_id"), "canonical report"
End Sub
~~~

Assert list rows contain only bounded summary fields and never narrative, field_notes, extracted_facts, or tokens.

- [ ] **Step 2: Write failing Policy Expert and account tests**

TestPolicyExpert.bas:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestPolicyExpert_Run()
    Dim history As New Collection
    Dim answer As Object

    history.Add PolicyTurn("Question one", "Answer one")
    history.Add PolicyTurn("Question two", "Answer two")
    history.Add PolicyTurn("Question three", "Answer three")
    history.Add PolicyTurn("Question four", "Answer four")
    history.Add PolicyTurn("Question five", "Answer five")

    Set answer = AskPolicyQuestion("What does the fictional policy require?", history)
    TestAssert.AreEqual 2, answer("citations").Count, "two citations"
    TestAssert.AreEqual 4, LastPolicyRequestHistoryCount(), "bounded history"
    TestAssert.IsTrue Len(LastPolicyIdempotencyKey()) >= 8, "policy request has idempotency key"
End Sub
~~~

Extend TestAuth.bas to assert Account is server-profile read-only, session list contains bounded device labels/times only, revoking one session calls DELETE once, Sign out of this computer clears the current token, and Sign out everywhere clears every local session value.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportHistory_Run,TestPolicyExpert_Run,TestAuth_Run
~~~

Expected: FAIL because CPagedResult, LoadReportPage, and AskPolicyQuestion are undefined.

- [ ] **Step 3: Implement bounded cursor pagination**

CPagedResult.Initialize validates items as a Collection, optional next_cursor as String, and bounded total/count metadata from the exact OpenAPI response.

LoadReportPage accepts only relationship owned or prepared, constructs explicit filters for status, incident date, category, and updated date, and requests one bounded page. It never sends wildcard narrative search or a client identity.

frmReportHistory controls:

- cboRelationship fixed to My Reports or Reports I Prepared
- cboStatus fixed to All, In Progress, Completed, Archived
- txtIncidentDateFrom
- txtIncidentDateTo
- cboCategory
- txtUpdatedFrom
- txtUpdatedTo
- subReportQueue
- cmdPreviousPage
- cmdNextPage
- lblPageStatus

sfrmReportQueue displays report/incident ID, reporting officer, preparer relationship, category, incident date, status, updated time, and revision number. Selecting a row loads one authorized report on demand into frmReportEditor. Completed and Archived remain editable; Archive is reversible through the server-supported status change.

- [ ] **Step 4: Complete dashboard summaries**

frmDashboard uses the first bounded owned and prepared pages to display counts/recent rows. It does not request full report content. Resumable drafts come from AC-07 recovery metadata and unfinished AI jobs from AC-06 known IDs. Last successful synchronization updates only after a successful API operation.

- [ ] **Step 5: Implement session-only Policy Expert history and citations**

modPolicyExpert keeps a Collection of question/answer turns in memory only. AskPolicyQuestion takes the last four complete turns, applies the 90-second policy timeout profile, creates one `NewUuid()` idempotency key for the explicit Ask click, posts one question with that key, validates answer, citations, source titles, and safe errors, and returns the data object. Transport retry for this request reuses the same key; a new click creates a new key. `request_in_progress` keeps the form in a waiting state, while `idempotent_response_unavailable` explains that the prior sensitive answer was not stored and requires an explicit Ask again. It never adds policy text to report facts.

frmPolicyExpert controls:

- txtPolicyQuestion
- cmdAskPolicy
- cmdClearConversation
- lstConversation
- subPolicyCitations
- lblPolicyDisclaimer
- lblPolicyStatus

Set lblPolicyDisclaimer to:

~~~text
Policy Expert provides cited policy guidance. It does not make an official decision and does not add anything to an incident report.
~~~

sfrmPolicyCitations shows citation number, source title, and exact returned passage. Clear removes all in-memory turns and visible citations. Closing Access discards the collection.

- [ ] **Step 6: Implement read-only account identity and session controls**

frmAccount displays server profile fields and contains:

- lblDisplayName
- lblEmployeeNumber
- lblRank
- lblShift
- lblRole
- lblStatus
- lblPersistenceState
- cmdChangePin
- cmdViewSessions
- cmdSignOutComputer
- cmdSignOutEverywhere

No profile field is editable. The form states that an Admin must correct roster identity.

frmSessionList and sfrmSessionResults display session ID, bounded device label, created time, last-used time, expiry, persistent flag, and current-device flag. They never display raw tokens, token hashes, IP details, or employee identity. Revoking a noncurrent session calls DELETE /auth/sessions/{session_id}. Revoking current invokes LogoutCurrent cleanup.

frmConfirmAction uses explicit target/effect text:

- Sign out of this computer: Ends this saved session on this Windows account.
- Sign out everywhere: Ends every session for your account on all devices.

- [ ] **Step 7: Extend fake API and COM user journeys**

Serve owned/prepared cursor pages, report detail, policy answer with citations, sessions, and session deletion. Add COM assertions for keyboard-opening a queue row, canonical report ID shared between owner/preparer fixtures, citation order/title/text, Policy history clearing, read-only account controls, single-session revoke, and logout scopes.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestReportHistory_Run,TestPolicyExpert_Run,TestAuth_Run
python -m pytest tests/access/test_user_workflows.py -q -m access_com -k "history or policy or account or session or dashboard"
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: owned/prepared lists are authorization-scoped summaries; one canonical report ID appears in the correct relationship fixtures; Policy sends at most four turns and displays two ordered citations; account identity is uneditable; revoke/logout behavior clears only the intended sessions.

- [ ] **Step 8: Commit AC-08**

~~~powershell
git add access-client/src access-client/tests/vba/TestPolicyExpert.bas access-client/tests/fixtures/reports/owned-page.json access-client/tests/fixtures/reports/prepared-page.json access-client/tests/fixtures/policy/answer-with-citations.json tests/access/fake_api.py tests/access/test_user_workflows.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add report history and policy expert"
~~~

Expected: one commit limited to AC-08 files and the source-matched binary.

---

### Task AC-09: Saved-revision Word export, accessibility, static scans, COM smoke, and bitness acceptance

**Files:**
- Create: access-client/src/modules/modWordExport.bas
- Create: access-client/src/classes/IFileDialogService.cls
- Create: access-client/src/classes/CAccessFileDialogService.cls
- Create: access-client/src/classes/IProcessLauncher.cls
- Create: access-client/src/classes/CWindowsProcessLauncher.cls
- Create: access-client/src/forms/frmExport.txt
- Create: access-client/tests/vba/TestWordExport.bas
- Create: access-client/tests/vba/classes/CFakeFileDialogService.cls
- Create: access-client/tests/vba/classes/CFakeProcessLauncher.cls
- Create: access-client/tests/fixtures/word/fictional-report.docx
- Create: access-client/tests/fixtures/word/fictional-report-metadata.json
- Create: access-client/src/modules/modUpdater.bas
- Create: access-client/src/classes/IUpdaterLauncher.cls
- Create: access-client/src/classes/CWindowsUpdaterLauncher.cls
- Create: access-client/tests/vba/TestUpdater.bas
- Create: access-client/tests/vba/classes/CFakeUpdaterLauncher.cls
- Create: access-client/tests/fixtures/policy/update-grant.json
- Create: access-client/build/InvokeAccessSmokeTests.ps1
- Create: access-client/build/ScanAccessSource.ps1
- Create: tests/unit/test_access_vba_safety.py
- Modify: tests/access/conftest.py
- Modify: access-client/build/BuildAccde.ps1
- Modify: access-client/build/ValidateAccessBuild.ps1
- Modify: access-client/build/build-matrix.example.json
- Modify: access-client/src/modules/modWin32.bas
- Modify: access-client/src/modules/modApiClient.bas
- Modify: access-client/src/modules/modAppStartup.bas
- Modify: access-client/src/modules/modBuildInfo.bas
- Modify: access-client/src/modules/modClientPolicy.bas
- Modify: access-client/src/modules/modReportWorkflow.bas
- Modify: access-client/src/modules/modTestHooks.bas
- Modify: access-client/src/forms/frmReportEditor.txt
- Modify: access-client/src/forms/frmShell.txt
- Modify: access-client/src/forms/frmUpdateNotice.txt
- Modify: access-client/src/manifest.json
- Modify: access-client/tests/vba/TestRunner.bas
- Modify: tests/access/access_com.py
- Modify: tests/access/fake_api.py
- Modify: tests/access/test_user_workflows.py
- Modify: access-client/README.md
- Modify: access-client/SLUT-Client.accdb
- Consume without modifying: openapi/access-v1.yaml
- Consume without modifying: templates/005_template_v3.docx
- Consume without modifying: tests/unit/test_filler_boxes.py

**Interfaces:**
- Consumes: AC-07 SaveNow/report revisions/conflict behavior; AC-02 byte/JSON responses; `/reports/{report_id}/export-docx`; the roadmap's locked update-grant/API/IPC contract; file dialog/process adapters; AC-01 build/validate harness.
- Produces: ExportSavedRevision; IFileDialogService.PromptSavePath; IProcessLauncher.OpenFile/OpenUri; WriteBytesAtomically; `BeginApprovedUpdate(accessBitness, windowsArchitecture) As Boolean`; `IUpdaterLauncher.LaunchWithNamedPipe(pipeName, requestId) As Boolean`; public COM-safe `ValidateRelease() As String`; one-message current-user-only named-pipe client; InvokeAccessSmokeTests; ScanAccessSource; per-supported-version/bitness acceptance evidence.

- [ ] **Step 1: Write failing Word-export unit tests**

TestWordExport.bas must inject fake file dialog/process launcher and assert:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestWordExport_Run()
    Dim savePath As String
    savePath = Environ$("TEMP") & "\SLUT-Access-" & NewUuid() & ".docx"

    ConfigureWordExportForTest NewFakeFileDialog(savePath), _
                               NewFakeProcessLauncher()

    TestAssert.IsTrue ExportSavedRevision("report-001", 7), "saved export succeeds"
    TestAssert.AreEqual savePath, LastWrittenExportPath(), "chosen path"
    TestAssert.AreEqual 0, FakeOpenedFileCount(), "Word does not open without choice"
End Sub
~~~

Additional cases:

- dirty report invokes SaveNow before export;
- save conflict prevents export until employee chooses a resolution;
- cancelled Save dialog sends no export request;
- response bytes exactly match fictional-report.docx;
- filename, SHA-256, byte length, MIME type, template version, request ID, and revision are displayed;
- Open in Word calls IProcessLauncher.OpenFile only after explicit choice;
- failed export leaves report dirty/saved state exactly as it was before export and never regenerates AI text.

- [ ] **Step 2: Run Word tests and verify the expected failure**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestWordExport_Run
~~~

Expected: FAIL because ExportSavedRevision and IFileDialogService are undefined.

- [ ] **Step 3: Implement employee-chosen binary export**

IFileDialogService and IProcessLauncher contain only the locked signatures. CAccessFileDialogService uses Access.Application.FileDialog with the Save As dialog, restricts the extension to .docx, suggests the server-provided safe filename, and returns an empty string on Cancel.

CWindowsProcessLauncher.OpenFile uses pointer-safe ShellExecuteW with the open verb and rejects a nonabsolute path. OpenUri accepts HTTPS only. Add ShellExecuteW to modWin32 with LongPtr return type.

modWordExport.ExportSavedRevision:

1. Requires reportId and revisionNumber greater than zero.
2. If current state is dirty, calls SaveNow and updates revisionNumber from the successful server response.
3. Stops on any save failure or conflict.
4. POSTs /api/v1/reports/{report_id}/export-docx with the explicit saved revision and one idempotency key.
5. Validates application/vnd.openxmlformats-officedocument.wordprocessingml.document, nonzero bytes, safe filename, exact byte length, SHA-256 metadata, template version, request ID, and report revision metadata from the documented response headers/envelope.
6. Prompts for a path.
7. Writes bytes to a same-directory temporary file and atomically replaces the chosen destination only after the complete byte count matches.
8. Displays hash/size/template/revision metadata.
9. Asks Open the saved document in Word? and invokes OpenFile only for Yes.

It never reads templates/005_template_v3.docx and never invokes legacy /api/reports/download.

- [ ] **Step 4: Build the unbound export step**

frmExport controls:

- cboSavedReportRevision
- lblReportOwner
- lblRevision
- lblTemplateVersion
- lblSha256
- lblByteLength
- lblRequestId
- cmdSaveWordDocument
- chkOpenAfterSave
- cmdBackToReports

Only server-authorized saved revisions are selectable. Unsaved local values are not offered. Export failure displays safe guidance and does not alter report SaveStateText.

- [ ] **Step 5: Implement and fake-test the accepted-update handoff and release validation hook**

Write `TestUpdater.bas` before implementation and run it through the AC-01 unit
harness. `update-grant.json` is a closed fictional first-response fixture with
exactly:

~~~json
{
  "update_grant": "fixture-update-grant-not-a-secret",
  "expires_at": "2026-08-12T18:35:00Z",
  "release_version": "0.0.0-test",
  "package_id": "access-x64-win-x64-fixture",
  "manifest_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "manifest_size_bytes": 1024,
  "signer_thumbprint": "0000000000000000000000000000000000000000000000000000000000000000",
  "one_time_value_unavailable": false
}
~~~

Tests must prove:

- `BeginApprovedUpdate("x64", "x64")` does nothing until the employee accepts;
- acceptance sends `POST /api/v1/client-updates/grants` with bearer,
  `X-Client-Version`, `X-Request-ID`, `Idempotency-Key`, and a closed body with
  exactly `access_bitness` plus `windows_architecture`; test both approved Access
  values `x86|x64` on Windows `x64`, use
  `{"access_bitness":"x64","windows_architecture":"x64"}` as the exact
  fictional example, and reject any combination outside the OP-01 matrix before
  launch;
- a first closed response requires every fixture field, keeps `update_grant` in
  memory only, and rejects unknown/missing fields, bad hashes, nonpositive size,
  expired grants, or mismatched package metadata;
- an idempotent replay with `one_time_value_unavailable: true` and no
  `update_grant` never launches and shows safe retry guidance;
- `CFakeUpdaterLauncher` receives only a random pipe name and request ID, never a
  grant, bearer, endpoint, person/report value, install path, or other secret;
- the pipe payload is exactly one length-prefixed UTF-8 JSON object no larger
  than 64 KiB and the connection is closed after the message;
- no update grant or bearer reaches arguments, environment variables, registry,
  clipboard, disk, diagnostics, errors, or source-matched binary artifacts; and
- `ValidateRelease()` returns bounded valid JSON with only version, source,
  API-compatibility, signature, and startup results and fails closed on each
  injected mismatch without returning a credential, URL, path, identity, report
  value, or raw exception.

Run the red test first:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestUpdater_Run
~~~

Expected: FAIL because `BeginApprovedUpdate` and `IUpdaterLauncher` are undefined.

Implement `modUpdater` with the exact grant request/closed-response rules above.
The response's `signer_thumbprint` is descriptive grant-bound metadata, never a
trust anchor; Access and the helper rely only on the preapproved managed-signing
and Windows trust policy and expected publisher identity.

`CWindowsUpdaterLauncher` launches the already installed trusted helper with only
the cryptographically random pipe name and request ID as command-line arguments.
The helper owns the named-pipe server and must create it with .NET
`PipeOptions.CurrentUserOnly`; Access connects through pointer-safe declarations
centralized in `modWin32`, sends one closed length-prefixed request, and closes.
The exact `UpdateRequest` keys are `schema_version`, `api_base_url`,
`update_grant`, `expires_at`, `release_version`, `package_id`,
`manifest_sha256`, `manifest_size_bytes`, `signer_thumbprint`,
`access_bitness`, `windows_architecture`, `current_client_version`,
`install_path`, and `request_id`. It contains no employee/report data. No
credential or sensitive value may leave memory through arguments, environment,
registry, clipboard, file, or log surfaces.

Expose public COM-safe `ValidateRelease()` from a standard module. It returns a
closed JSON result containing only `passed`, `client_version`, `source_commit`,
`api_compatible`, `signature_valid`, `startup_valid`, and bounded stable
`failure_code`. It performs no update, download, install, signing, or publication.

- [ ] **Step 6: Write static source/security/accessibility tests**

Create tests/unit/test_access_vba_safety.py:

~~~python
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "access-client"
MODULES = CLIENT / "src" / "modules"
FORMS = CLIENT / "src" / "forms"


def all_vba_text() -> str:
    paths = list(MODULES.glob("*.bas")) + list((CLIENT / "src" / "classes").glob("*.cls"))
    return "\n".join(path.read_text("utf-8", errors="replace") for path in paths)


def test_all_forms_are_unbound():
    for path in FORMS.glob("*.txt"):
        text = path.read_text("utf-8", errors="replace")
        assert not re.search(r"RecordSource\s*=\s*\"[^\"]+\"", text), path
        assert not re.search(r"ControlSource\s*=\s*\"[^\"]+\"", text), path


def test_no_local_application_tables():
    schema = json.loads((CLIENT / "src" / "tables" / "schema.json").read_text("utf-8"))
    assert schema["tables"] == []


def test_win32_declarations_are_central_and_ptrsafe():
    for path in MODULES.glob("*.bas"):
        text = path.read_text("utf-8", errors="replace")
        if path.name != "modWin32.bas":
            assert " Declare " not in text, path
    win32 = (MODULES / "modWin32.bas").read_text("utf-8")
    for line in win32.splitlines():
        if " Declare " in line:
            assert "PtrSafe" in line


def test_no_legacy_or_direct_cloud_endpoints():
    source = all_vba_text()
    forbidden = [
        "/api/chat",
        "/api/reports/",
        "/api/roster",
        "cloudsql",
        "googleapis.com",
        "generativelanguage",
        "vertexai",
        "ACCESS_CODE",
        "ADMIN_CODE",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ]
    for value in forbidden:
        assert value not in source


def test_no_admin_client_objects():
    names = {path.stem.lower() for path in FORMS.glob("*.txt")}
    names.update(path.stem.lower() for path in MODULES.glob("*.bas"))
    assert not any(name.startswith("frmadmin") for name in names)
    assert not any(name.startswith("modadmin") for name in names)
~~~

Expand ScanAccessSource.ps1 to enforce the same rules plus forbidden sensitive log parameter names, unapproved absolute URLs, missing Option Explicit, unsafe Kill/RmDir calls, and output paths outside LocalAppData or an employee-chosen export path.

- [ ] **Step 7: Write and run the failing full COM smoke workflow**

InvokeAccessSmokeTests.ps1 launches only the specified database and calls public test hooks through Access.Application.Run. It returns JSON and always closes its own Application instance:

~~~powershell
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$FakeApiUrl,
    [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform
)

$app = New-Object -ComObject Access.Application
try {
    $app.Visible = $false
    $app.OpenCurrentDatabase((Resolve-Path -LiteralPath $Database).Path)
    $app.Run('Test_SetApiBaseUrl', $FakeApiUrl)
    $result = $app.Run('Test_RunSmokeWorkflow')
    $parsed = $result | ConvertFrom-Json
    if (-not $parsed.passed) {
        throw ($result)
    }
    $result
} finally {
    try { $app.CloseCurrentDatabase() } catch {}
    $app.Quit()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)
}
~~~

The smoke hook performs temporary-PIN sign-in, persistent renewal, profile/client policy, own-plus-other officer incident, field notes, classification, extraction, fact/gap confirmation, report tabs, manual save, autosave, owned/prepared history, revision conflict/recovery, Policy Expert citations, saved-revision Word bytes, session revoke, logout, required-update read-only behavior, employee-accepted update through `CFakeUpdaterLauncher`, and safe `ValidateRelease` success/failure results. It never starts a real updater or connects to a non-loopback endpoint.

Run before finishing implementation:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessSmokeTests.ps1 -Database access-client/SLUT-Client.accdb -FakeApiUrl http://127.0.0.1:8765 -Platform x64
~~~

Expected initial result: FAIL at the Word-export stage because ExportSavedRevision is undefined.

- [ ] **Step 8: Complete keyboard, high-contrast, and scaling behavior**

For every form:

- set a logical TabIndex sequence;
- set TabStop false on decorative controls;
- give every input an associated visible label;
- provide an accessible text name for icons/buttons;
- show focus through border/font changes visible in high contrast;
- pair color status with exact text;
- bind Enter only to the safe primary action and Escape only to non-destructive cancel;
- require explicit confirmation for discard/logout/revoke;
- prevent long operations from freezing by disabling one initiating button, showing stage text, and using job/timer state;
- anchor shell/subform/list controls so required content fits at 1366 by 768 at 150%.

Run keyboard-only manual traversal from startup through all six workflow steps, histories, Policy Expert, Account, and export. Stop acceptance on a focus trap, clipped required control, color-only state, or unlabeled input.

- [ ] **Step 9: Build matrix artifacts without signing or publishing**

build-matrix.example.json defines the evidence schema, not claimed workstation support:

~~~json
{
  "schema_version": 1,
  "required_fields": [
    "windows_build",
    "access_version",
    "access_channel",
    "access_bitness",
    "word_version",
    "word_bitness",
    "display_scale",
    "resolution"
  ],
  "rows": []
}
~~~

For each real inventory row, run on its matching controlled runner:

~~~powershell
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database $env:TEMP\SLUT-Client-Matrix.accdb -Configuration Test
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database $env:TEMP\SLUT-Client-Matrix.accdb -Source access-client/src -Platform x64
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database $env:TEMP\SLUT-Client-Matrix.accdb -Output $env:TEMP\SLUT-Client-Matrix.accde -Platform x64 -ClientVersion 0.1.0
powershell.exe -NoProfile -File access-client/build/InvokeAccessSmokeTests.ps1 -Database $env:TEMP\SLUT-Client-Matrix.accde -FakeApiUrl http://127.0.0.1:8765 -Platform x64
~~~

Use x86 on a matching 32-bit Access runner. Never claim x86 from an x64 run or the reverse. Keep unsigned artifacts in the runner’s temporary directory and provide hashes in handoff evidence only.

Hard stop a row for:

- Access COM activation failure;
- PowerShell/Access bitness mismatch;
- source import/re-export drift;
- any VBA compile error or missing reference;
- make-ACCDE failure;
- ACCDE reopen failure;
- fake API contract failure;
- DPAPI failure under the current user;
- Word save/open failure under agency policy;
- clipping or focus failure at a required scale;
- endpoint protection quarantine;
- proxy/TLS failure against the real fictional test environment.

Signing, trusted-location deployment, update packaging, and rollout remain external tasks.

- [ ] **Step 10: Run the complete automated verification**

~~~powershell
python -m pytest -q
python -m pytest tests/unit/test_access_source_layout.py tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb
python -m pytest tests/access -q -m access_com
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: complete credential-free Python suite PASS; static scan PASS; every VBA test PASS; all COM workflows PASS; source round-trip clean; no Access business tables; no sensitive fixture value in source/log/recovery bytes; no legacy/direct-cloud route.

- [ ] **Step 11: Run manual Windows acceptance on every supported inventory row**

Use fictional scenarios only and record exact observed results for:

1. first-use temporary PIN and forced change;
2. persistent and nonpersistent restart behavior;
3. own report and report prepared for another officer;
4. multiple reporting officers and tab edit retention;
5. field notes, fact confirmation, blocking gaps, and AI progress/resume;
6. autosave, network interruption, recovery after forced termination, and revision conflict;
7. owned/prepared history and editable Completed/Archived status;
8. Policy answer citations and session-only clearing;
9. saved-revision DOCX save, optional Word open, and print under agency policy;
10. token revocation and logout scopes;
11. optional update, minimum-client read-only behavior, accepted-update fake
    launcher handoff, and safe `ValidateRelease` output;
12. keyboard-only, high contrast, 1366 by 768, and 100%/125%/150% scaling.

Expected: each supported matrix row passes all twelve. Any failed row remains unsupported until fixed and rerun; it is not averaged with passing rows.

- [ ] **Step 12: Update Access documentation and commit AC-09**

Update access-client/README.md with final source commands, fake API test commands, supported evidence procedure, LocalAppData paths, safe troubleshooting/request IDs, and explicit signing/deployment exclusions.

~~~powershell
git add access-client tests/unit/test_access_vba_safety.py tests/access
git commit -m "feat(access): complete user client acceptance"
~~~

Expected: one commit limited to AC-09 files, the source-matched binary, and test/documentation updates. Do not add generated ACCDE files, matrix secrets, real workstation identity, certificates, or export documents.

---

## Implementation Completion Gate

Before declaring the User client complete:

1. Re-read docs/superpowers/specs/2026-08-12-access-user-client-design.md and map each acceptance criterion to AC-03 through AC-09 evidence.
2. Confirm access-client/src/manifest.json matches a fresh export of SLUT-Client.accdb.
3. Confirm access-client/src/tables/schema.json still has an empty tables array and every form/subform is unbound.
4. Confirm the official Word template and existing backend regression tests are unchanged.
5. Confirm no Admin form/module, updater, signing/deployment code, prompt, secret, real staff data, or direct cloud credential exists in the diff.
6. Confirm each supported Access version/bitness has its own compile, ACCDE, COM smoke, scaling, keyboard, Word, network, revocation, update, and rollback-adjacent validation evidence.
7. Report unrun matrix rows and externally blocked gates explicitly; never convert a missing run into a pass.

The implementation is ready for the separate release/signing workstream only after all seven checks pass.
