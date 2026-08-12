# Access Admin Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the source-controlled Access Guided Workspace with a role-aware, server-authorized Admin Center for account, staff, report, audit, health, and Review Lab operations while preserving every ordinary User workflow.

**Architecture:** The Admin Center is part of the same `SLUT-Client.accdb`/compiled ACCDE and reuses the AC transport, authentication, revision, recovery, export, accessibility, and Windows test harness. `/api/v1/me` is the only source of role; Cloud Run remains the authorization boundary. Fifteen-minute Admin elevation and five-minute purpose-scoped step-up credentials live only in memory, while every Admin form remains unbound and every protected action is idempotent, attributed, confirmed, and server-enforced.

**Tech Stack:** Microsoft Access ACCDB/ACCDE and VBA7; existing AC modules/classes/forms; WinHTTP 5.1 late binding; VBA-JSON v2.3.1; Windows DPAPI and pointer-safe Win32 declarations; PowerShell 5.1 plus Access COM; Python 3 and pytest; the merged `openapi/access-v1.yaml` produced by ID-07, ID-08, RP-05, RP-09, and RP-10.

## Global Constraints

- AD-01 starts only after reviewed AC-01 through AC-09, ID-01 through ID-08, and RP-01 through RP-10 deliver the exact merged OpenAPI operations and fictional examples consumed below.
- The Admin Center extends `access-client/SLUT-Client.accdb`; it does not create a second Access client, backend implementation, browser replacement, updater, installer, deployment script, signing script, or Claude prompt.
- Administrators retain Home, New Report, My Reports, Reports I Prepared, Policy Expert, and Account. Administration adds Overview, All Reports, Accounts & Staff, Audit Log, System Health, and Review Lab.
- Role comes only from `CurrentProfile().Role`, populated by `/api/v1/me`. Hidden controls, test hooks, local flags, employee number, or request JSON never grant authorization.
- Cloud Run denies every unauthorized request. The client does not retry a denied Admin mutation in User mode and does not conceal denial by changing the requested operation.
- All new forms and subforms are unbound. Their `RecordSource` and bound `ControlSource` values remain empty. `access-client/src/tables/schema.json` remains exactly `{"schema_version": 1, "tables": []}`.
- Do not create local account, staff, session, report, revision, audit, health, handoff, credential, role, elevation, step-up, or temporary-PIN tables.
- Persistent Admin sign-in reuses the AC-03 DPAPI-protected rotating renewal token. Closing Access always clears Admin elevation and step-up state, even when the account session persists.
- Admin elevation expires after 15 minutes without Admin activity. Ordinary reporting work does not refresh it. A protected Admin read refreshes server and local Admin activity; it never refreshes a sensitive step-up grant.
- A sensitive step-up token expires after five minutes, is bound to the current Admin Access session and one exact purpose, and is consumed once by the matching server transaction.
- The executable step-up header is `X-Admin-Step-Up`, as defined by ID-07/RP-05/RP-09/RP-10. Do not add `X-Admin-Elevation` or `X-Step-Up-Token`. If the merged OpenAPI uses a different name, stop and reconcile the backend plans and roadmap before editing VBA.
- Elevation expiry, step-up token, temporary PIN, submitted PIN, Access token, renewal token, and Review Lab handoff fragment never enter DPAPI files, recovery snapshots, logs, error text, test-state JSON, form tags, Access tables, or manifest metadata.
- PIN text exists only in the active unbound PIN control and synchronous request body. Clear the control on submit, success, failure, deactivate, unload, and unexpected error.
- Account creation and reset show one generated 8-character temporary PIN once. There is no existing-PIN field or retrieval request. Copy occurs only after the Admin clicks Copy, and closing the dialog overwrites and clears its unbound control.
- Staff identity is the stable server UUID. Employee-number correction never creates a new identity. Duplicate normalized employee numbers and deletion of staff with history are server rejections, not client workarounds.
- Account deactivation, role change, reset, unlock, and session revocation use only server APIs. The last active Admin rule is never estimated or overridden locally.
- Admin report search is server-side, paginated, and structured. Search results contain bounded summaries; opening a record obtains detail and creates the server-side record view audit.
- The existing `frmReportEditor`, revision forms, autosave, recovery snapshots, and conflict UI remain the only report editing path. Admin mode adds attribution and Admin routes; it never adds an overwrite path.
- Every Admin save creates an `admin_edit` revision. Restore creates a new revision referencing the source. Transfer requires an active staff UUID, nonblank reason no longer than 500 characters, explicit confirmation, and purpose `report_transfer`.
- Completed reports remain editable. Archive is reversible. No Admin form exposes permanent report, revision, account, staff-history, or audit deletion.
- Single export references one saved revision. Bulk export requires explicit structured filters, reason text, purpose `bulk_export`, and at most 100 documents. Bulk report narrative editing is excluded.
- Audit UI is read-only and bounded to safe fields. Audit export requires purpose `audit_export` and is itself audited. No full report text, PIN, token, or raw service detail is displayed.
- Health is a sanitized diagnostic summary only. It cannot restart, configure, scale, migrate, back up, restore, or otherwise control cloud infrastructure.
- Review Lab remains in the browser. Access requests one 60-second, single-use handoff URL after purpose `review_lab_handoff`, opens it once through `IProcessLauncher.OpenUri`, and immediately clears the URL and fragment from local variables.
- Review Lab never receives an Access bearer token, renewal token, PIN, shared Admin code, or persistent browser cookie from Access. The server owns fragment redemption and the 30-minute-idle individual browser session.
- All modifying calls carry one idempotency key per intended action. Buttons disable after one submission. A retry reuses that key only when the OpenAPI operation explicitly allows replay.
- All revision writes carry the current base revision and preserve local work on `409 revision_conflict`. Account concurrency conflicts reload current server status before another explicit attempt.
- New forms meet the AC-09 keyboard, focus, accessible-label, non-color-only state, 1366-by-768, 100/125/150-percent scaling, and high-contrast requirements.
- Every automated fixture is fictional. No real employee, PIN, token, account, inmate, report, audit event, hostname secret, or agency health detail enters source control.
- Agents may edit and test local/test-scope files named by one task. Agents never push, merge, deploy, sign, publish, access production data, handle secrets, alter Trust Center policy, or act on an agency workstation outside the approved test matrix.

## Preconditions and Contract Gate

1. Begin each AD task from the reviewed AC-09 source-matched binary and exported manifest. Run:

~~~powershell
python -m pytest -q
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests Test_RunAll
python -m pytest tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py -q -m access_com
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: the credential-free suite, all existing VBA tests, User COM journeys, source parity, reference scan, and compilation pass. Use `x86` only on a matching 32-bit Access runner. Stop on a pre-existing failure or source/binary drift.

2. Validate `openapi/access-v1.yaml` and require schema-valid fictional examples before each task. The merged contract must define these exact relative paths:

~~~text
POST /api/v1/auth/admin-step-up
GET  /api/v1/admin/overview
GET  /api/v1/admin/staff
POST /api/v1/admin/staff
PATCH /api/v1/admin/staff/{staff_id}
GET  /api/v1/admin/accounts
POST /api/v1/admin/accounts
PATCH /api/v1/admin/accounts/{account_id}
POST /api/v1/admin/accounts/{account_id}/reset-pin
POST /api/v1/admin/accounts/{account_id}/unlock
GET  /api/v1/admin/accounts/{account_id}/sessions
POST /api/v1/admin/accounts/{account_id}/revoke-sessions
GET  /api/v1/admin/reports
GET  /api/v1/admin/reports/{report_id}
PATCH /api/v1/admin/reports/{report_id}
GET  /api/v1/admin/reports/{report_id}/revisions
GET  /api/v1/admin/reports/{report_id}/revisions/{revision_number}
POST /api/v1/admin/reports/{report_id}/restore
POST /api/v1/admin/reports/{report_id}/transfer
POST /api/v1/admin/reports/{report_id}/export-docx
POST /api/v1/admin/reports/bulk-export
GET  /api/v1/admin/audit-events
POST /api/v1/admin/audit-events/export
GET  /api/v1/admin/health
POST /api/v1/admin/review-lab-handoffs
~~~

The account-session list and exact Admin report/audit export route spellings must be settled in the OpenAPI bundle before their consuming task starts. If the backend uses a different reviewed path, update `modApiRoutes.bas`, fixture metadata, route-parity tests, and this plan together in a separate plan-review change; do not guess inside an implementation task.

3. The merged contract must expose purposes `admin_center`, `staff_write`, `account_create`, `account_role_status`, `account_reset_pin`, `account_unlock`, `account_revoke_sessions`, `report_restore`, `report_transfer`, `bulk_export`, `audit_export`, and `review_lab_handoff`. It must document five-minute expiry, exact-purpose binding, single use, and `X-Admin-Step-Up`.
4. Protected Admin GET/list operations rely on server-side elevation tied to the Access session and carry no elevation credential. `POST /auth/admin-step-up` with purpose `admin_center` returns `elevation_expires_at` and no action token. Sensitive purposes return `step_up_token`, `step_up_expires_at`, and `purpose` once.
5. Stop if the merged contract can replay a readable temporary PIN, returns raw token/session hashes, omits last-active-admin behavior, permits deletion, permits more than 100 bulk documents, lacks safe request IDs, or exposes infrastructure secrets.
6. All form SaveAsText exports are produced through `ExportAccessSource.ps1`; never hand-author a form text export. Every task updates `SLUT-Client.accdb`, exports the named objects, and proves manifest/source parity before committing.

## Locked Admin Additions

Only these new production Access objects may be introduced by AD-01 through AD-05:

~~~text
access-client/src/modules/
  modAdminAuth.bas
  modAdminOverview.bas
  modAdminAccounts.bas
  modAdminReports.bas
  modAdminAudit.bas
  modAdminHealth.bas
  modAdminReviewLab.bas
access-client/src/classes/
  CAdminGrantState.cls
  CAdminReportFilter.cls
  CAdminAuditFilter.cls
  IClipboardService.cls
  CWindowsClipboardService.cls
access-client/src/forms/
  frmAdminElevation.txt
  frmAdminStepUp.txt
  frmAdminOverview.txt
  frmAdminAccountsStaff.txt
  frmAdminStaffEditor.txt
  frmAdminAccountAction.txt
  frmAdminTemporaryPin.txt
  frmAdminSessions.txt
  frmAdminAllReports.txt
  frmAdminTransferReport.txt
  frmAdminBulkExport.txt
  frmAdminAudit.txt
  frmAdminHealth.txt
  frmAdminReviewLab.txt
  sfrmAdminStaffResults.txt
  sfrmAdminSessionResults.txt
  sfrmAdminReportResults.txt
  sfrmAdminAuditResults.txt
  sfrmAdminHealthResults.txt
~~~

Do not create Admin reports, queries, macros, tables, a second shell, a second report editor, or a second confirmation dialog. Reuse `AutoExec`, `frmShell`, `sfrmNavigation`, `frmReportEditor`, `frmRevisionHistory`, `frmRevisionCompare`, `frmRevisionConflict`, `frmConfirmAction`, `frmExport`, `CWorkflowState`, `CReportState`, `CPagedResult`, `IClock`, `IFileDialogService`, and `IProcessLauncher`.

New Admin test objects are:

~~~text
access-client/tests/vba/
  TestAdminAuthorization.bas
  TestAdminAccounts.bas
  TestAdminReports.bas
  TestAdminAudit.bas
  TestAdminHealth.bas
  TestAdminReviewLab.bas
access-client/tests/vba/classes/
  CFakeClipboardService.cls
~~~

Existing shared harness files remain authoritative and are modified, not replaced: `access-client/src/manifest.json`, `access-client/src/project.json`, `access-client/build/AccessBuild.Common.psm1`, `ExportAccessSource.ps1`, `ImportAccessSource.ps1`, `BuildAccde.ps1`, `ValidateAccessBuild.ps1`, `InvokeAccessUnitTests.ps1`, `InvokeAccessSmokeTests.ps1`, `ScanAccessSource.ps1`, `build-matrix.example.json`, `access-client/tests/vba/TestAssert.bas`, `TestRunner.bas`, `tests/access/conftest.py`, `fake_api.py`, `access_com.py`, and the four existing `tests/unit/test_access_*.py` files.

## Locked Admin VBA Contracts

These signatures are exact. Existing AC signatures remain unchanged.

~~~vb
Public Enum AdminStepUpPurpose
    AdminPurposeStaffWrite = 1
    AdminPurposeAccountCreate = 2
    AdminPurposeAccountRoleStatus = 3
    AdminPurposeAccountResetPin = 4
    AdminPurposeAccountUnlock = 5
    AdminPurposeAccountRevokeSessions = 6
    AdminPurposeReportRestore = 7
    AdminPurposeReportTransfer = 8
    AdminPurposeBulkExport = 9
    AdminPurposeAuditExport = 10
    AdminPurposeReviewLabHandoff = 11
End Enum

Public Function IsCurrentUserAdmin() As Boolean
Public Function ConfirmAdminPin(ByVal pin As String, _
                                ByVal purpose As String) As CAdminGrantState
Public Function CurrentAdminGrant() As CAdminGrantState
Public Function AdminCenterIsElevated() As Boolean
Public Sub RequireAdminElevation()
Public Sub TouchAdminActivity()
Public Sub ClearAdminGrants()
Public Function AdminPurposeName(ByVal purpose As AdminStepUpPurpose) As String
Public Function SendWithAdminStepUp(ByVal request As CApiRequest, _
                                    ByVal purpose As AdminStepUpPurpose) As CApiResponse
Public Sub ConfigureAdminClockForTest(ByVal clock As IClock)

Public Function LoadAdminOverview() As Object

Public Function LoadAdminStaffPage(ByVal query As String, _
                                   Optional ByVal cursor As String = vbNullString) As CPagedResult
Public Function CreateAdminStaff(ByVal employeeNumber As String, _
                                 ByVal firstName As String, ByVal lastName As String, _
                                 ByVal rank As String, _
                                 ByVal shift As String, ByVal isActive As Boolean, _
                                 ByVal idempotencyKey As String) As Object
Public Function UpdateAdminStaff(ByVal staffId As String, _
                                 ByVal employeeNumber As String, _
                                 ByVal firstName As String, ByVal lastName As String, _
                                 ByVal rank As String, _
                                 ByVal shift As String, ByVal isActive As Boolean, _
                                 ByVal idempotencyKey As String) As Object
Public Function LoadAdminAccountPage(ByVal query As String, _
                                     Optional ByVal cursor As String = vbNullString) As CPagedResult
Public Function CreateAdminAccount(ByVal staffId As String, ByVal role As String, _
                                   ByVal idempotencyKey As String) As CTemporaryPinResult
Public Function ResetAdminPin(ByVal accountId As String, _
                              ByVal idempotencyKey As String) As CTemporaryPinResult
Public Sub ChangeAdminAccountRoleOrStatus(ByVal accountId As String, _
                                          ByVal role As String, ByVal status As String, _
                                          ByVal idempotencyKey As String)
Public Sub UnlockAdminAccount(ByVal accountId As String, _
                              ByVal idempotencyKey As String)
Public Function LoadAdminAccountSessions(ByVal accountId As String, _
                                         Optional ByVal cursor As String = vbNullString) As CPagedResult
Public Sub RevokeAdminAccountSession(ByVal accountId As String, _
                                     ByVal sessionId As String, ByVal revokeAll As Boolean, _
                                     ByVal idempotencyKey As String)
Public Sub ConfigureAdminClipboardForTest(ByVal clipboard As IClipboardService)
Public Function AdminClipboard() As IClipboardService

' IClipboardService
Public Sub CopyText(ByVal plaintext As String)

Public Function LoadAdminReportPage(ByVal filters As CAdminReportFilter, _
                                    Optional ByVal cursor As String = vbNullString) As CPagedResult
Public Function OpenAdminReport(ByVal reportId As String) As CWorkflowState
Public Function SaveAdminReport(ByVal state As CWorkflowState) As Long
Public Function RestoreAdminReportRevision(ByVal reportId As String, _
                                           ByVal revisionNumber As Long, _
                                           ByVal idempotencyKey As String) As Long
Public Function TransferAdminReport(ByVal reportId As String, _
                                    ByVal newOwnerStaffId As String, _
                                    ByVal reason As String, _
                                    ByVal idempotencyKey As String) As Long
Public Function ExportAdminSavedRevision(ByVal reportId As String, _
                                         ByVal revisionNumber As Long) As Boolean
Public Function ExportAdminReportBatch(ByVal filters As CAdminReportFilter, _
                                       ByVal reason As String) As Boolean

Public Function LoadAdminAuditPage(ByVal filters As CAdminAuditFilter, _
                                   Optional ByVal cursor As String = vbNullString) As CPagedResult
Public Function ExportAdminAuditSummary(ByVal filters As CAdminAuditFilter) As Boolean
Public Function LoadAdminHealth() As Object

Public Function OpenAdminReviewLab() As Boolean
Public Sub ConfigureAdminProcessLauncherForTest(ByVal launcher As IProcessLauncher)
Public Function AdminProcessLauncher() As IProcessLauncher

Public Sub WriteBytesAtomically(ByVal absolutePath As String, ByRef bytes() As Byte)
Public Function Test_GetAdminStateJson() As String
Public Function Test_RunAdminSmokeWorkflow() As String
~~~

---


### Task AD-01: Role-aware navigation, elevation, and overview

**Files:**
- Create: `access-client/src/modules/modAdminAuth.bas`
- Create: `access-client/src/modules/modAdminOverview.bas`
- Create: `access-client/src/classes/CAdminGrantState.cls`
- Create: `access-client/src/forms/frmAdminElevation.txt`
- Create: `access-client/src/forms/frmAdminStepUp.txt`
- Create: `access-client/src/forms/frmAdminOverview.txt`
- Create: `access-client/tests/vba/TestAdminAuthorization.bas`
- Create: `access-client/tests/fixtures/profile/me-admin.json`
- Create: `access-client/tests/fixtures/admin/elevation-admin-center.json`
- Create: `access-client/tests/fixtures/admin/elevation-step-up.json`
- Create: `access-client/tests/fixtures/admin/overview.json`
- Create: `access-client/tests/fixtures/errors/admin-elevation-required.json`
- Create: `access-client/tests/fixtures/errors/step-up-required.json`
- Create: `tests/access/test_admin_authorization.py`
- Modify: `access-client/src/modules/modApiRoutes.bas`
- Modify: `access-client/src/modules/modAppStartup.bas`
- Modify: `access-client/src/modules/modAppState.bas`
- Modify: `access-client/src/modules/modNavigation.bas`
- Modify: `access-client/src/modules/modErrors.bas`
- Modify: `access-client/src/modules/modTestHooks.bas`
- Modify: `access-client/src/classes/CUserProfile.cls`
- Modify: `access-client/src/forms/frmShell.txt`
- Modify: `access-client/src/forms/sfrmNavigation.txt`
- Modify: `access-client/src/manifest.json`
- Modify: `access-client/tests/vba/TestRunner.bas`
- Modify: `access-client/tests/fixtures/policy/client-current.json`
- Modify: `tests/unit/test_access_fixture_contracts.py`
- Modify: `tests/unit/test_access_route_parity.py`
- Modify: `tests/access/fake_api.py`
- Modify: `access-client/SLUT-Client.accdb`
- Consume without modifying: `openapi/access-v1.yaml`

**Interfaces:**
- Consumes: AC `CurrentProfile() As CUserProfile`, `CurrentSession() As CSessionState`, `NewApiRequest`, `ApiSend`, `ParseSuccessEnvelope`, `JsonSerialize`, `NavigateTo`, `IClock`, `CSystemClock`, `CFakeClock`, `UserGuidanceFor`, `Test_GetStateJson`, and `/api/v1/me` role.
- Produces: `CAdminGrantState`; `IsCurrentUserAdmin`, `ConfirmAdminPin`, `CurrentAdminGrant`, `AdminCenterIsElevated`, `RequireAdminElevation`, `TouchAdminActivity`, `ClearAdminGrants`, `AdminPurposeName`, `SendWithAdminStepUp`, `ConfigureAdminClockForTest`, `LoadAdminOverview`; route helpers `RouteAdminStepUp` and `RouteAdminOverview`; `PageAdminOverview`, `PageAdminAllReports`, `PageAdminAccountsStaff`, `PageAdminAudit`, `PageAdminHealth`, and `PageAdminReviewLab` values added to the existing `AppPage` enum.

**Stop conditions:**
- Stop before editing if `/me`, Admin step-up, or Admin overview examples are absent, fail schema validation, or omit role/elevation expiry.
- Stop if `admin_center` returns a readable step-up token, if protected reads require a client-created elevation header, or if an ordinary User can obtain Admin overview data.
- Stop if the reviewed AC manifest, `SLUT-Client.accdb`, or existing User navigation differs from AC-09 source.

- [ ] **Step 1: Write failing role, navigation, elevation, and expiry tests**

Create `TestAdminAuthorization.bas` with these concrete cases:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestAdminAuthorization_Run()
    Test_ResetApplication
    Test_SeedProfileFromFixture "profile/me-user.json"
    TestAssert.IsTrue IsCurrentUserAdmin() = False, "User role is not Admin"
    TestAssert.AreEqual "Home|New Report|My Reports|Reports I Prepared|Policy Expert|Account", _
                        Test_NavigationCaptions(), "User navigation remains exact"

    Test_SeedProfileFromFixture "profile/me-admin.json"
    TestAssert.IsTrue IsCurrentUserAdmin(), "Admin role comes from profile"
    TestAssert.AreEqual _
        "Home|New Report|My Reports|Reports I Prepared|Policy Expert|Account|Overview|All Reports|Accounts & Staff|Audit Log|System Health|Review Lab", _
        Test_NavigationCaptions(), "Admin receives both navigation groups"

    Test_QueueFixtureResponse "admin/elevation-admin-center.json"
    TestAssert.IsTrue ConfirmAdminPin("A7B902", "admin_center") Is CurrentAdminGrant(), _
                      "PIN confirmation sets current grant"
    TestAssert.IsTrue AdminCenterIsElevated(), "elevation is active"
    Test_AdvanceAdminClockMilliseconds 900001#
    TestAssert.IsTrue AdminCenterIsElevated() = False, "idle elevation expires"
    TestAssert.IsTrue InStr(1, Test_GetAdminStateJson(), "A7B902", vbBinaryCompare) = 0, _
                      "PIN is absent from state JSON"
End Sub
~~~

Add test-only hooks to `modTestHooks.bas`: `Test_SeedProfileFromFixture`, `Test_NavigationCaptions`, and `Test_AdvanceAdminClockMilliseconds`. Each hook must first enforce `TEST_BUILD`; release calls raise the existing disabled-test-hook error.

Create `tests/access/test_admin_authorization.py` with tests that start the fake API and Access COM instance, then assert:

- User startup exposes the six Reporting destinations and no Administration heading or destination;
- manually calling `Test_Navigate("AdminOverview")` as User produces safe `permission_denied` and no Admin GET;
- Admin startup still opens the normal dashboard until Overview is selected;
- selecting Overview without elevation opens `frmAdminElevation` without losing the intended destination;
- successful confirmation opens `frmAdminOverview`;
- 15 minutes plus one millisecond of Admin inactivity relocks the Center while the Access session remains authenticated;
- closing and reopening a persistent Admin session restores the profile but not elevation;
- every new form has empty `RecordSource`.

- [ ] **Step 2: Run the focused tests and observe the expected failures**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAuthorization_Run
python -m pytest tests/access/test_admin_authorization.py -q -m access_com
~~~

Expected: VBA compilation fails because `CAdminGrantState`, `IsCurrentUserAdmin`, and `PageAdminOverview` do not exist; COM tests fail because Admin forms and navigation are absent.

- [ ] **Step 3: Add exact Admin route helpers and route-parity assertions**

Append to `modApiRoutes.bas`:

~~~vb
Public Function RouteAdminStepUp() As String
    RouteAdminStepUp = API_PREFIX & "/auth/admin-step-up"
End Function

Public Function RouteAdminOverview() As String
    RouteAdminOverview = API_PREFIX & "/admin/overview"
End Function
~~~

Extend `tests/unit/test_access_route_parity.py` so both literals exist in `openapi/access-v1.yaml`. Extend `tests/unit/test_access_fixture_contracts.py` so each new fixture names and validates against its exact `x-openapi-fixture-schema` response schema.

Run:

~~~powershell
python -m pytest tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py -q
~~~

Expected: PASS only when the Access literals and fixture schemas match the reviewed OpenAPI bundle.

- [ ] **Step 4: Implement in-memory Admin grant state and exact purpose mapping**

`CAdminGrantState` stores only elevation timestamps/activity and one pending action token. Use this boundary:

~~~vb
Option Compare Database
Option Explicit

Private mElevationExpiresAt As Date
Private mLastAdminActivityMs As Double
Private mStepUpToken As String
Private mStepUpPurpose As String
Private mStepUpExpiresAt As Date

Public Sub SetElevation(ByVal expiresAtUtc As Date, ByVal monotonicMs As Double)
    mElevationExpiresAt = expiresAtUtc
    mLastAdminActivityMs = monotonicMs
End Sub

Public Sub Touch(ByVal expiresAtUtc As Date, ByVal monotonicMs As Double)
    mElevationExpiresAt = expiresAtUtc
    mLastAdminActivityMs = monotonicMs
End Sub

Public Function IsElevated(ByVal nowUtc As Date, ByVal monotonicMs As Double) As Boolean
    IsElevated = mElevationExpiresAt > nowUtc _
        And monotonicMs - mLastAdminActivityMs < 900000#
End Function

Public Sub StoreStepUp(ByVal token As String, ByVal purpose As String, _
                       ByVal expiresAtUtc As Date)
    ClearStepUp
    mStepUpToken = token
    mStepUpPurpose = purpose
    mStepUpExpiresAt = expiresAtUtc
End Sub

Public Function TakeStepUp(ByVal expectedPurpose As String, ByVal nowUtc As Date) As String
    If Len(mStepUpToken) = 0 Or mStepUpPurpose <> expectedPurpose _
       Or mStepUpExpiresAt <= nowUtc Then
        ClearStepUp
        Err.Raise vbObjectError + 7301, "CAdminGrantState.TakeStepUp", _
                  "Administrator PIN confirmation is required."
    End If
    TakeStepUp = mStepUpToken
    ClearStepUp
End Function

Public Sub ClearStepUp()
    If Len(mStepUpToken) > 0 Then mStepUpToken = String$(Len(mStepUpToken), Chr$(0))
    mStepUpToken = vbNullString
    mStepUpPurpose = vbNullString
    mStepUpExpiresAt = 0
End Sub

Public Sub ClearAll()
    ClearStepUp
    mElevationExpiresAt = 0
    mLastAdminActivityMs = 0
End Sub
~~~

`AdminPurposeName` must use one closed `Select Case` mapping:

~~~vb
Public Function AdminPurposeName(ByVal purpose As AdminStepUpPurpose) As String
    Select Case purpose
        Case AdminPurposeStaffWrite: AdminPurposeName = "staff_write"
        Case AdminPurposeAccountCreate: AdminPurposeName = "account_create"
        Case AdminPurposeAccountRoleStatus: AdminPurposeName = "account_role_status"
        Case AdminPurposeAccountResetPin: AdminPurposeName = "account_reset_pin"
        Case AdminPurposeAccountUnlock: AdminPurposeName = "account_unlock"
        Case AdminPurposeAccountRevokeSessions: AdminPurposeName = "account_revoke_sessions"
        Case AdminPurposeReportRestore: AdminPurposeName = "report_restore"
        Case AdminPurposeReportTransfer: AdminPurposeName = "report_transfer"
        Case AdminPurposeBulkExport: AdminPurposeName = "bulk_export"
        Case AdminPurposeAuditExport: AdminPurposeName = "audit_export"
        Case AdminPurposeReviewLabHandoff: AdminPurposeName = "review_lab_handoff"
        Case Else
            Err.Raise vbObjectError + 7302, "AdminPurposeName", "Unknown Admin purpose."
    End Select
End Function
~~~

No Property Get exposes the pending token. `Test_GetAdminStateJson` may expose booleans and expiry timestamps only.

- [ ] **Step 5: Implement PIN confirmation and single-use protected send**

`ConfirmAdminPin` accepts only `admin_center` or an exact `AdminPurposeName` result, disables retry, and validates the matching response shape:

~~~vb
Public Function ConfirmAdminPin(ByVal pin As String, _
                                ByVal purpose As String) As CAdminGrantState
    Dim payload As Object
    Dim request As CApiRequest
    Dim response As CApiResponse
    Dim data As Object

    If Len(pin) < 4 Or Len(pin) > 8 Then
        Err.Raise vbObjectError + 7303, "ConfirmAdminPin", "Enter your PIN."
    End If
    If Not IsAllowedAdminPurpose(purpose) Then
        Err.Raise vbObjectError + 7304, "ConfirmAdminPin", "Unknown Admin purpose."
    End If

    Set payload = CreateObject("Scripting.Dictionary")
    payload.Add "pin", pin
    payload.Add "purpose", purpose
    Set request = NewApiRequest("POST", RouteAdminStepUp(), JsonSerialize(payload))
    request.Headers("Idempotency-Key") = NewUuid()
    request.CanRetry = False
    Set response = ApiSend(request)
    Set data = ParseSuccessEnvelope(response)

    EnsureAdminGrantState
    mAdminGrant.SetElevation ParseAdminUtc(CStr(data("elevation_expires_at"))), _
                             AdminClock().MonotonicMilliseconds
    If purpose <> "admin_center" Then
        If CStr(data("purpose")) <> purpose Then
            Err.Raise vbObjectError + 7305, "ConfirmAdminPin", "Step-up purpose mismatch."
        End If
        mAdminGrant.StoreStepUp CStr(data("step_up_token")), purpose, _
                                ParseAdminUtc(CStr(data("step_up_expires_at")))
    End If
    pin = String$(Len(pin), Chr$(0))
    pin = vbNullString
    Set ConfirmAdminPin = mAdminGrant
End Function
~~~

`SendWithAdminStepUp` removes the header and overwrites its local token on both success and error:

~~~vb
Public Function SendWithAdminStepUp(ByVal request As CApiRequest, _
                                    ByVal purpose As AdminStepUpPurpose) As CApiResponse
    Dim token As String
    Dim response As CApiResponse
    Dim savedNumber As Long
    Dim savedSource As String
    Dim savedDescription As String

    RequireAdminElevation
    token = CurrentAdminGrant().TakeStepUp(AdminPurposeName(purpose), AdminClock().UtcNow)
    request.Headers("X-Admin-Step-Up") = token
    On Error GoTo SendFailed
    Set response = ApiSend(request)
    GoTo SendDone

SendFailed:
    savedNumber = Err.Number
    savedSource = Err.Source
    savedDescription = Err.Description
SendDone:
    If request.Headers.Exists("X-Admin-Step-Up") Then request.Headers.Remove "X-Admin-Step-Up"
    If Len(token) > 0 Then token = String$(Len(token), Chr$(0))
    token = vbNullString
    If savedNumber <> 0 Then Err.Raise savedNumber, savedSource, savedDescription
    Set SendWithAdminStepUp = response
End Function
~~~

`AppStart`, `LogoutCurrent`, `LogoutAll`, and `ClearAuthenticatedState` call `ClearAdminGrants`. `ConfigureAdminClockForTest` accepts the existing `IClock`; release builds use `CSystemClock`.

- [ ] **Step 6: Add role-aware navigation and elevation-preserving routing**

Extend the existing `AppPage` enum with the six Admin values. `sfrmNavigation` renders exactly two headings only for role `admin`. Before opening an Admin destination, `NavigateTo` executes this guard:

~~~vb
Private Sub RequireAdminDestinationAccess(ByVal destination As AppPage)
    If Not IsAdminPage(destination) Then Exit Sub
    If Not IsCurrentUserAdmin() Then
        Err.Raise vbObjectError + 7306, "NavigateTo", _
                  "You do not have permission to open the Admin Center."
    End If
    If Not AdminCenterIsElevated() Then
        SetPendingAdminDestination destination
        DoCmd.OpenForm "frmAdminElevation", WindowMode:=acDialog
        If Not AdminCenterIsElevated() Then
            Err.Raise vbObjectError + 7307, "NavigateTo", _
                      "Administrator PIN confirmation is required."
        End If
    End If
End Sub
~~~

`frmAdminElevation` submits purpose `admin_center`, clears `txtPin` in a single cleanup handler, and resumes the saved destination. `frmAdminStepUp` receives one closed purpose enum plus target/effect copy, preserves the calling form's selections, and returns only success/cancel; it never returns the token.

- [ ] **Step 7: Build the unbound overview and bounded summary loader**

`LoadAdminOverview` sends a GET with no client elevation header, parses account/report/attention/health/recent-audit summaries, and calls `TouchAdminActivity` using the server response's refreshed `elevation_expires_at`. On `admin_elevation_required`, clear local grants and reopen `frmAdminElevation` without retrying automatically.

`frmAdminOverview` contains:

- `txtActiveAccounts`, `txtDeactivatedAccounts`, and `txtLockedAccounts` read-only summary controls;
- `cboReportPeriod` restricted to Today, 7 days, and 30 days;
- `txtReportsUpdated`, `lstAttention`, `lstRecentAudit` bounded summaries;
- `lblApiHealth`, `lblDatabaseHealth`, `lblAiHealth`, `lblPolicyHealth`, `lblQueueHealth`, and `lblBackupHealth`, each with text plus icon, not color alone;
- `cmdAllReports` and `cmdAccountsStaff` quick links;
- `lblAdminContext` showing signed-in Admin display name and `Admin Center`;
- no narrative, field notes, credentials, internal errors, or infrastructure controls.

All list population uses `.RowSourceType = "Value List"` or explicit unbound controls and caps recent items to the response limit.

- [ ] **Step 8: Extend fake API behavior and run authorization regressions**

`tests/access/fake_api.py` must:

- return User/Admin profiles from distinct fictional fixtures;
- require Admin bearer role for every `/api/v1/admin/*` route;
- track server elevation by fictional session ID;
- expire elevation after 15 minutes of fake-clock inactivity;
- return a fictional one-time step-up only for an exact allowed purpose;
- reject wrong role, absent/expired elevation, wrong purpose, expiry, and replay with stable safe errors;
- record request method/path/body/header names while redacting PIN and credential values.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAuthorization_Run,TestAuth_Run,TestClientPolicy_Run,TestSafeLog_Run
python -m pytest tests/access/test_admin_authorization.py tests/access/test_user_workflows.py -q -m access_com -k "navigation or elevation or startup or persistent or unbound"
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py -q
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: User navigation is unchanged; User Admin calls are denied; Admin retains ordinary pages; elevation expires after 15 minutes of Admin inactivity; restart clears elevation; overview is bounded/safe; every new form is unbound; all User tests remain green.

- [ ] **Step 9: Commit AD-01**

~~~powershell
git add access-client/src/modules/modAdminAuth.bas access-client/src/modules/modAdminOverview.bas access-client/src/classes/CAdminGrantState.cls access-client/src/forms/frmAdminElevation.txt access-client/src/forms/frmAdminStepUp.txt access-client/src/forms/frmAdminOverview.txt access-client/src/modules/modApiRoutes.bas access-client/src/modules/modAppStartup.bas access-client/src/modules/modAppState.bas access-client/src/modules/modNavigation.bas access-client/src/modules/modErrors.bas access-client/src/modules/modTestHooks.bas access-client/src/classes/CUserProfile.cls access-client/src/forms/frmShell.txt access-client/src/forms/sfrmNavigation.txt access-client/src/manifest.json access-client/tests/vba/TestAdminAuthorization.bas access-client/tests/vba/TestRunner.bas access-client/tests/fixtures/profile/me-admin.json access-client/tests/fixtures/admin access-client/tests/fixtures/errors/admin-elevation-required.json access-client/tests/fixtures/errors/step-up-required.json tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/access/fake_api.py tests/access/test_admin_authorization.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add role-aware admin center"
~~~

Expected: one focused commit containing only AD-01 files and the source-matched editable binary. Do not push or build a signed artifact.

---

### Task AD-02: Accounts & Staff and session management

**Files:**
- Create: `access-client/src/modules/modAdminAccounts.bas`
- Create: `access-client/src/classes/CTemporaryPinResult.cls`
- Create: `access-client/src/classes/IClipboardService.cls`
- Create: `access-client/src/classes/CWindowsClipboardService.cls`
- Create: `access-client/src/forms/frmAdminAccountsStaff.txt`
- Create: `access-client/src/forms/frmAdminStaffEditor.txt`
- Create: `access-client/src/forms/frmAdminAccountAction.txt`
- Create: `access-client/src/forms/frmAdminTemporaryPin.txt`
- Create: `access-client/src/forms/frmAdminSessions.txt`
- Create: `access-client/src/forms/sfrmAdminStaffResults.txt`
- Create: `access-client/src/forms/sfrmAdminSessionResults.txt`
- Create: `access-client/tests/vba/TestAdminAccounts.bas`
- Create: `access-client/tests/vba/classes/CFakeClipboardService.cls`
- Create: `access-client/tests/fixtures/admin/staff-page.json`
- Create: `access-client/tests/fixtures/admin/staff-created.json`
- Create: `access-client/tests/fixtures/admin/staff-updated.json`
- Create: `access-client/tests/fixtures/admin/account-page.json`
- Create: `access-client/tests/fixtures/admin/account-created.json`
- Create: `access-client/tests/fixtures/admin/account-pin-reset.json`
- Create: `access-client/tests/fixtures/admin/account-pin-replay.json`
- Create: `access-client/tests/fixtures/admin/account-updated.json`
- Create: `access-client/tests/fixtures/admin/account-unlocked.json`
- Create: `access-client/tests/fixtures/admin/account-sessions-page.json`
- Create: `access-client/tests/fixtures/admin/account-sessions-revoked.json`
- Create: `access-client/tests/fixtures/errors/duplicate-employee-number.json`
- Create: `access-client/tests/fixtures/errors/last-active-admin.json`
- Create: `access-client/tests/fixtures/errors/staff-has-history.json`
- Create: `tests/access/test_admin_accounts.py`
- Modify: `access-client/src/modules/modApiRoutes.bas`
- Modify: `access-client/src/modules/modAdminAuth.bas`
- Modify: `access-client/src/modules/modErrors.bas`
- Modify: `access-client/src/modules/modTestHooks.bas`
- Modify: `access-client/src/modules/modWin32.bas`
- Modify: `access-client/src/forms/frmAdminOverview.txt`
- Modify: `access-client/src/forms/frmConfirmAction.txt`
- Modify: `access-client/src/manifest.json`
- Modify: `access-client/tests/vba/TestAdminAuthorization.bas`
- Modify: `access-client/tests/vba/TestRunner.bas`
- Modify: `tests/unit/test_access_fixture_contracts.py`
- Modify: `tests/unit/test_access_route_parity.py`
- Modify: `tests/unit/test_access_vba_safety.py`
- Modify: `tests/access/fake_api.py`
- Modify: `access-client/SLUT-Client.accdb`
- Consume without modifying: `openapi/access-v1.yaml`

**Interfaces:**
- Consumes: AD-01 role/elevation/grant functions; AC `CPagedResult`, `NewUuid`, `NewApiRequest`, `ApiSend`, `JsonSerialize`, `ParseSuccessEnvelope`, `UserGuidanceFor`, `frmConfirmAction`; Admin staff/account/session OpenAPI schemas and exact step-up purposes from ID-07.
- Produces: all locked `LoadAdminStaffPage`, staff create/update, account list/create/reset/change/unlock, session list/revoke, and clipboard signatures; `IClipboardService.CopyText`; route helpers `RouteAdminStaff`, `RouteAdminStaffMember`, `RouteAdminAccounts`, `RouteAdminAccount`, `RouteAdminAccountResetPin`, `RouteAdminAccountUnlock`, `RouteAdminAccountSessions`, and `RouteAdminAccountRevokeSessions`.

**Stop conditions:**
- Stop if the OpenAPI account/session operations omit stable staff/account/session UUIDs, pagination, one/all revocation scope, or one-time temporary-PIN semantics.
- Stop if a create/reset retry can replay the readable temporary PIN, if unlock changes the PIN, or if role/status changes fail to revoke sessions and increment authorization version.
- Stop if the only active Admin can be demoted/deactivated or if staff/account deletion is exposed.
- Stop if a production clipboard implementation would require a new Office/Forms reference instead of existing late-bound/Win32 boundaries.

- [ ] **Step 1: Write failing account, roster, temporary-PIN, and session tests**

Create `TestAdminAccounts.bas`:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestAdminAccounts_Run()
    Dim staffPage As CPagedResult
    Dim sessionsPage As CPagedResult
    Dim pinResult As CTemporaryPinResult
    Dim temporaryPin As String

    Test_ResetApplication
    Test_SeedProfileFromFixture "profile/me-admin.json"
    Test_EnterAdminCenterFromFixture

    Test_QueueFixtureResponse "admin/staff-page.json"
    Set staffPage = LoadAdminStaffPage("FICTIONAL")
    TestAssert.AreEqual 2, staffPage.Items.Count, "staff page is bounded"
    TestAssert.AreEqual "staff-00000000-0000-0000-0000-000000000001", _
                        CStr(staffPage.Items(1)("id")), "stable staff UUID"

    Test_QueueAdminStepUpFixture "account_create"
    Test_QueueFixtureResponse "admin/account-created.json"
    Set pinResult = CreateAdminAccount( _
        "staff-00000000-0000-0000-0000-000000000001", "user", NewUuid())
    temporaryPin = pinResult.TakeTemporaryPin()
    TestAssert.AreEqual 8, Len(temporaryPin), "temporary PIN is eight characters"
    TestAssert.IsTrue Len(pinResult.OperationReferenceId) > 0, "durable operation reference"
    TestAssert.IsFalse pinResult.OneTimeValueUnavailable, "first response contains PIN"
    TestAssert.AreEqual 0, Test_AdminClipboardCopyCount(), "PIN is not copied implicitly"
    Test_ShowTemporaryPin temporaryPin, "Create account"
    Test_ClickTemporaryPinCopy
    TestAssert.AreEqual 1, Test_AdminClipboardCopyCount(), "explicit Copy writes once"
    Test_CloseTemporaryPin
    TestAssert.IsTrue InStr(1, Test_GetAdminStateJson(), temporaryPin, vbBinaryCompare) = 0, _
                      "temporary PIN is absent from state"

    Test_QueueFixtureResponse "admin/account-sessions-page.json"
    Set sessionsPage = LoadAdminAccountSessions( _
        "account-00000000-0000-0000-0000-000000000001")
    TestAssert.AreEqual 2, sessionsPage.Items.Count, "bounded session summaries"

    Test_QueueAdminStepUpFixture "account_reset_pin"
    Test_QueueFixtureResponse "admin/account-pin-replay.json"
    Set pinResult = ResetAdminPin( _
        "account-00000000-0000-0000-0000-000000000001", NewUuid())
    TestAssert.IsTrue pinResult.OneTimeValueUnavailable, "replay flag is explicit"
    TestAssert.AreEqual vbNullString, pinResult.TakeTemporaryPin(), "PIN is never replayed"
End Sub
~~~

Create `tests/access/test_admin_accounts.py` to cover:

- search by fictional name and employee number;
- create active/inactive staff with first name, last name, rank, employee number, shift, and stable UUID;
- correct employee number without changing UUID;
- duplicate normalized employee number safe rejection;
- staff roster activation independent from account status;
- staff with report history has no Delete control and a constructed delete route is absent;
- link one account to one eligible staff record as User or Admin;
- one-time account-create PIN, reset PIN, first-use-change marker, and no retrieval route;
- explicit Copy only, form close clearing, and marker absence from logs/recovery/test-state JSON;
- reset revokes all target sessions;
- deactivate/reactivate, role change, unlock, and last-active-admin conflict;
- one/all session revocation with bounded device labels, creation/last-use/expiry times, and no raw token hashes;
- double-click sends one request/idempotency key;
- every new form/subform has empty `RecordSource`.

- [ ] **Step 2: Run tests and verify their expected failures**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAccounts_Run
python -m pytest tests/access/test_admin_accounts.py -q -m access_com
~~~

Expected: compilation fails because `LoadAdminStaffPage` and `IClipboardService` do not exist; COM tests fail because `frmAdminAccountsStaff` is absent.

- [ ] **Step 3: Add exact account/staff/session route helpers and fixture validation**

Add these helpers to `modApiRoutes.bas`; every path component passes through existing `UrlEncodePathComponent`:

~~~vb
Public Function RouteAdminStaff() As String
    RouteAdminStaff = API_PREFIX & "/admin/staff"
End Function

Public Function RouteAdminStaffMember(ByVal staffId As String) As String
    RouteAdminStaffMember = RouteAdminStaff() & "/" & UrlEncodePathComponent(staffId)
End Function

Public Function RouteAdminAccounts() As String
    RouteAdminAccounts = API_PREFIX & "/admin/accounts"
End Function

Public Function RouteAdminAccount(ByVal accountId As String) As String
    RouteAdminAccount = RouteAdminAccounts() & "/" & UrlEncodePathComponent(accountId)
End Function

Public Function RouteAdminAccountResetPin(ByVal accountId As String) As String
    RouteAdminAccountResetPin = RouteAdminAccount(accountId) & "/reset-pin"
End Function

Public Function RouteAdminAccountUnlock(ByVal accountId As String) As String
    RouteAdminAccountUnlock = RouteAdminAccount(accountId) & "/unlock"
End Function

Public Function RouteAdminAccountSessions(ByVal accountId As String) As String
    RouteAdminAccountSessions = RouteAdminAccount(accountId) & "/sessions"
End Function

Public Function RouteAdminAccountRevokeSessions(ByVal accountId As String) As String
    RouteAdminAccountRevokeSessions = RouteAdminAccount(accountId) & "/revoke-sessions"
End Function
~~~

Extend route-parity and fixture-schema tests and run:

~~~powershell
python -m pytest tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py -q
~~~

Expected: PASS; every new literal and fictional response validates against the merged Admin schemas.

- [ ] **Step 4: Implement bounded list, staff mutation, and account mutation services**

`LoadAdminStaffPage` and `LoadAdminAccountPage` trim query to the OpenAPI maximum, URL-encode it, request at most 50 records, return `CPagedResult`, and call `TouchAdminActivity` after success. They never request report text or token material.

Build staff payloads with exact fields only:

~~~vb
Private Function AdminStaffPayload(ByVal employeeNumber As String, _
                                   ByVal firstName As String, ByVal lastName As String, _
                                   ByVal rank As String, ByVal shift As String, _
                                   ByVal isActive As Boolean) As Object
    Dim payload As Object
    Set payload = CreateObject("Scripting.Dictionary")
    payload.Add "employee_number", Trim$(employeeNumber)
    payload.Add "first_name", Trim$(firstName)
    payload.Add "last_name", Trim$(lastName)
    payload.Add "rank", Trim$(rank)
    payload.Add "shift", Trim$(shift)
    payload.Add "is_active", isActive
    Set AdminStaffPayload = payload
End Function
~~~

`CreateAdminStaff` and `UpdateAdminStaff` create POST/PATCH requests, set `Idempotency-Key`, disable the clicked button, and call `SendWithAdminStepUp(request, AdminPurposeStaffWrite)`. Payloads contain no actor, role, account owner, authorization flag, or delete request.

Account creation sends only `staff_id` and role `user|admin` with purpose `account_create`. Role/status changes accept only role `user|admin` and status `active|deactivated`, show exact target/effect in `frmConfirmAction`, and use purpose `account_role_status`. Unlock uses purpose `account_unlock`. The client displays server conflicts and reloads the current account record before enabling another explicit attempt.

- [ ] **Step 5: Implement one-time temporary-PIN display and explicit clipboard copy**

`IClipboardService.cls` contains only:

~~~vb
Option Compare Database
Option Explicit

Public Sub CopyText(ByVal plaintext As String)
End Sub
~~~

`CWindowsClipboardService` delegates to a pointer-safe `CopyUnicodeTextToClipboard` wrapper added to `modWin32`. The wrapper uses `OpenClipboard`, `EmptyClipboard`, `GlobalAlloc`, `GlobalLock`, `RtlMoveMemory`, `GlobalUnlock`, `SetClipboardData(CF_UNICODETEXT)`, and `CloseClipboard`; it transfers ownership only after `SetClipboardData` succeeds and calls `GlobalFree` on failure. Declarations use `PtrSafe`/`LongPtr` under `#If VBA7` and width-correct `Long` under the existing compatibility branch. No Forms or VBIDE reference is added.

`frmAdminTemporaryPin` has `txtTemporaryPin` read-only, `cmdCopy`, `cmdClose`, `lblOneTimeWarning`, and `lblAction`. Copy is the only event that calls the injected service:

~~~vb
Private Sub cmdCopy_Click()
    If Len(Nz(Me.txtTemporaryPin.Value, vbNullString)) = 0 Then Exit Sub
    AdminClipboard().CopyText CStr(Me.txtTemporaryPin.Value)
    Me.lblOneTimeWarning.Caption = "Copied. This temporary PIN cannot be retrieved again."
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Dim value As String
    value = Nz(Me.txtTemporaryPin.Value, vbNullString)
    If Len(value) > 0 Then value = String$(Len(value), Chr$(0))
    Me.txtTemporaryPin.Value = Null
    value = vbNullString
End Sub
~~~

`CTemporaryPinResult.Initialize` parses exactly `operation_reference_id`, `account_id`, optional `temporary_pin`, and `one_time_value_unavailable`. It rejects a missing durable ID, rejects `temporary_pin` when the flag is true, and rejects a first-success shape whose flag is false but PIN is absent. `TakeTemporaryPin()` returns the private string once, overwrites it, and returns an empty string thereafter; no property exposes it. The durable reference and account ID are safe for retry/result correlation but not written to a local table.

`CreateAdminAccount` and `ResetAdminPin` return `CTemporaryPinResult`. On first success, pass `TakeTemporaryPin()` directly to the dialog and overwrite the local variable. On a same-key replay, `one_time_value_unavailable=true` is handled explicitly: show `The earlier operation succeeded, but its temporary PIN cannot be shown again. Reset the PIN with a new action to issue another one.` and never call a retrieval route. A malformed/missing readable value without the replay flag is a contract error, not a generic success.

- [ ] **Step 6: Implement bounded account-session management**

`LoadAdminAccountSessions` calls exactly `GET /api/v1/admin/accounts/{account_id}/sessions?limit=50` plus the opaque encoded cursor when present. It parses top-level `account_id`, `items`, and nullable `next_cursor`; each item requires exactly `session_id`, `device_label`, `persistent`, `created_at`, `last_used_at`, `idle_expires_at`, nullable `revoked_at`, and `current`. `frmAdminSessions` and `sfrmAdminSessionResults` show session ID suffix, safe device label, persistence, created/last-used/idle-expiry timestamps, and current/revoked state. They never display IP address, token/hash, raw device ID, family ID, user agent, network value, or revoke reason.

Revoke uses one exact body:

~~~vb
Private Function RevokeSessionPayload(ByVal sessionId As String, _
                                      ByVal revokeAll As Boolean) As Object
    Dim payload As Object
    Set payload = CreateObject("Scripting.Dictionary")
    If revokeAll Then
        payload.Add "scope", "all"
    Else
        If Len(sessionId) = 0 Then
            Err.Raise vbObjectError + 7401, "RevokeSessionPayload", _
                      "Select a session to revoke."
        End If
        payload.Add "scope", "one"
        payload.Add "session_id", sessionId
    End If
    Set RevokeSessionPayload = payload
End Function
~~~

`RevokeAdminAccountSession` requires purpose `account_revoke_sessions`, disables the button after confirmation, sends one idempotent POST, and parses exactly `account_id`, `scope`, `revoked_session_ids`, and `revoked_count` before reloading the session page. It never revokes the current Admin implicitly unless the selected target/scope returned by the confirmation says so. `not_found` does not disclose that a session belongs to another account; `account_conflict` reloads without automatic resubmission.

- [ ] **Step 7: Build the unbound Accounts & Staff forms**

`frmAdminAccountsStaff` is one stable staff identity screen with optional linked account. Controls are:

- `txtSearch`, `cmdSearch`, `cmdNextPage`, `sfrmAdminStaffResults`;
- read-only `txtStaffId`, editable-action launchers for employee number, first/last name, rank, shift, and roster active state;
- linked account summary `txtAccountId`, `txtRole`, `txtAccountStatus`, `txtRequiresPinChange`, and `txtLockedUntil`;
- `cmdCreateStaff`, `cmdEditStaff`, `cmdCreateAccount`, `cmdResetPin`, `cmdChangeRoleStatus`, `cmdUnlock`, and `cmdSessions`;
- no Delete, Existing PIN, Raw Token, Change Actor, or Edit Authorization control.

`frmAdminStaffEditor` performs create/correct only. `frmAdminAccountAction` shows selected stable IDs, current state, exact target state, and effect copy. `frmConfirmAction` is reused for deactivate/reactivate, role, reset, unlock, and session actions. Closing any dialog preserves the parent search and selection.

- [ ] **Step 8: Extend safe error mapping and static sensitive-data checks**

Map `duplicate_employee_number`, `staff_has_history`, `account_already_exists`, `last_active_admin`, `account_conflict`, `admin_elevation_required`, and `step_up_required` to stable action-oriented messages. `admin_step_up_required` is forbidden and must fail route/fixture parity as an unknown contract code. Never display backend detail containing a PIN or internal row state.

Extend `tests/unit/test_access_vba_safety.py` and `ScanAccessSource.ps1` to assert:

- no production source contains `temporary_pin` in a log/recovery/test-state serializer;
- no local table or delete route exists;
- every clipboard call originates from `frmAdminTemporaryPin.cmdCopy_Click` through `IClipboardService`;
- all new Win32 declarations are centralized and pointer-safe;
- all new forms/subforms are unbound.

- [ ] **Step 9: Run account/staff/session and User regressions**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAccounts_Run,TestAdminAuthorization_Run,TestAuth_Run,TestSessionStore_Run,TestSafeLog_Run
python -m pytest tests/access/test_admin_accounts.py tests/access/test_admin_authorization.py tests/access/test_user_workflows.py -q -m access_com -k "staff or account or pin or role or session or user_navigation or unbound"
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: staff UUID survives employee-number correction; one-time PIN handling is explicit and absent from persistence/logs; account lifecycle/session rules are server-driven; last Admin is protected; all new UI remains unbound; User account/session behavior stays green.

- [ ] **Step 10: Commit AD-02**

~~~powershell
git add access-client/src/modules/modAdminAccounts.bas access-client/src/classes/CTemporaryPinResult.cls access-client/src/classes/IClipboardService.cls access-client/src/classes/CWindowsClipboardService.cls access-client/src/forms/frmAdminAccountsStaff.txt access-client/src/forms/frmAdminStaffEditor.txt access-client/src/forms/frmAdminAccountAction.txt access-client/src/forms/frmAdminTemporaryPin.txt access-client/src/forms/frmAdminSessions.txt access-client/src/forms/sfrmAdminStaffResults.txt access-client/src/forms/sfrmAdminSessionResults.txt access-client/src/modules/modApiRoutes.bas access-client/src/modules/modAdminAuth.bas access-client/src/modules/modErrors.bas access-client/src/modules/modTestHooks.bas access-client/src/modules/modWin32.bas access-client/src/forms/frmAdminOverview.txt access-client/src/forms/frmConfirmAction.txt access-client/src/manifest.json access-client/tests/vba/TestAdminAccounts.bas access-client/tests/vba/TestAdminAuthorization.bas access-client/tests/vba/TestRunner.bas access-client/tests/vba/classes/CFakeClipboardService.cls access-client/tests/fixtures/admin access-client/tests/fixtures/errors tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py tests/access/fake_api.py tests/access/test_admin_accounts.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add admin account and staff management"
~~~

Expected: one focused AD-02 commit with no backend, prompt, deployment, signing, or production-data file.

---

### Task AD-03: All-report search, edit, revision restore, transfer, and single/bulk export

**Files:**
- Create: `access-client/src/modules/modAdminReports.bas`
- Create: `access-client/src/classes/CAdminReportFilter.cls`
- Create: `access-client/src/forms/frmAdminAllReports.txt`
- Create: `access-client/src/forms/frmAdminTransferReport.txt`
- Create: `access-client/src/forms/frmAdminBulkExport.txt`
- Create: `access-client/src/forms/sfrmAdminReportResults.txt`
- Create: `access-client/tests/vba/TestAdminReports.bas`
- Create: `access-client/tests/fixtures/admin/report-page.json`
- Create: `access-client/tests/fixtures/admin/report-detail.json`
- Create: `access-client/tests/fixtures/admin/report-revisions-page.json`
- Create: `access-client/tests/fixtures/admin/report-revision-detail.json`
- Create: `access-client/tests/fixtures/admin/report-restored.json`
- Create: `access-client/tests/fixtures/admin/report-transferred.json`
- Create: `access-client/tests/fixtures/admin/report-saved.json`
- Create: `access-client/tests/fixtures/admin/bulk-export.zip`
- Create: `access-client/tests/fixtures/admin/bulk-export-metadata.json`
- Create: `tests/access/test_admin_reports.py`
- Modify: `access-client/src/modules/modApiRoutes.bas`
- Modify: `access-client/src/modules/modAdminAuth.bas`
- Modify: `access-client/src/modules/modReportWorkflow.bas`
- Modify: `access-client/src/modules/modAutosave.bas`
- Modify: `access-client/src/modules/modConflict.bas`
- Modify: `access-client/src/modules/modRecovery.bas`
- Modify: `access-client/src/modules/modWordExport.bas`
- Modify: `access-client/src/modules/modErrors.bas`
- Modify: `access-client/src/modules/modTestHooks.bas`
- Modify: `access-client/src/classes/CWorkflowState.cls`
- Modify: `access-client/src/forms/frmAdminOverview.txt`
- Modify: `access-client/src/forms/frmReportEditor.txt`
- Modify: `access-client/src/forms/frmRevisionHistory.txt`
- Modify: `access-client/src/forms/frmRevisionCompare.txt`
- Modify: `access-client/src/forms/frmRevisionConflict.txt`
- Modify: `access-client/src/forms/frmExport.txt`
- Modify: `access-client/src/forms/frmConfirmAction.txt`
- Modify: `access-client/src/manifest.json`
- Modify: `access-client/tests/vba/TestReportWorkflow.bas`
- Modify: `access-client/tests/vba/TestConflict.bas`
- Modify: `access-client/tests/vba/TestWordExport.bas`
- Modify: `access-client/tests/vba/TestRunner.bas`
- Modify: `tests/unit/test_access_fixture_contracts.py`
- Modify: `tests/unit/test_access_route_parity.py`
- Modify: `tests/unit/test_access_vba_safety.py`
- Modify: `tests/access/fake_api.py`
- Modify: `access-client/SLUT-Client.accdb`
- Consume without modifying: `openapi/access-v1.yaml`
- Consume without modifying: `access-client/tests/fixtures/word/fictional-report.docx`

**Interfaces:**
- Consumes: AD-01 grants; AD-02 active-staff search; AC `CWorkflowState`, `CReportState`, `CPagedResult`, report-control copy/load/tab functions, `MarkDirty`, `SaveNow`, `OnIdleTimer`, recovery/conflict services, `IFileDialogService`, `IProcessLauncher`, `WriteBytesAtomically`, `CApiResponse.BodyBytes`, and Word-export fakes.
- Produces: `CAdminReportFilter`; all locked Admin report search/open/save/restore/transfer/single/bulk export functions; `CWorkflowState.AdminMode As Boolean` and `CWorkflowState.AdminViewedOwnerDisplay As String`; all Admin report route helpers.

**Stop conditions:**
- Stop if Admin search is not authorization-first, server-side, cursor-paginated, default 50/cap 100, or omits any approved structured filter.
- Stop if Admin save/restore/transfer can overwrite a stale revision, omit actor attribution, avoid an immutable revision, or delete history.
- Stop if transfer lacks active staff target, reason, confirmation, transactional relationship update, and purpose `report_transfer`.
- Stop if bulk export lacks explicit filters, reason, purpose `bulk_export`, deterministic manifest, partial-failure accounting, or the 100-document cap.
- Stop if the binary response lacks reviewed filename/MIME/hash/revision/manifest metadata needed for safe display.

- [ ] **Step 1: Write failing Admin report-domain tests**

Create `TestAdminReports.bas`:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestAdminReports_Run()
    Dim filters As New CAdminReportFilter
    Dim page As CPagedResult
    Dim state As CWorkflowState
    Dim restoredRevision As Long

    Test_ResetApplication
    Test_SeedProfileFromFixture "profile/me-admin.json"
    Test_EnterAdminCenterFromFixture

    filters.InmateAdcNumber = "ADC900001"
    filters.Status = "completed"
    Test_QueueFixtureResponse "admin/report-page.json"
    Set page = LoadAdminReportPage(filters)
    TestAssert.AreEqual 2, page.Items.Count, "Admin report page is bounded"

    Test_QueueFixtureResponse "admin/report-detail.json"
    Set state = OpenAdminReport("report-00000000-0000-0000-0000-000000000001")
    TestAssert.IsTrue state.AdminMode, "workflow is in Admin mode"
    TestAssert.AreEqual 7, state.IncidentBaseRevisionNumber, "base revision is loaded"

    Test_QueueAdminStepUpFixture "report_restore"
    Test_QueueFixtureResponse "admin/report-restored.json"
    restoredRevision = RestoreAdminReportRevision( _
        "report-00000000-0000-0000-0000-000000000001", 3, NewUuid())
    TestAssert.AreEqual 8, restoredRevision, "restore appends a new revision"
End Sub
~~~

Add cases for stale Admin save preserving controls, same conflict UI as User, completed/archived editability, transfer purpose/reason, single saved-revision export, explicit-filter enforcement, 100-document cap, ZIP byte equality, and no bulk narrative mutation.

- [ ] **Step 2: Write failing COM report-oversight journeys**

Create `tests/access/test_admin_reports.py` with these exact journeys:

1. Search each approved filter alone, then a combined filter, and verify fake API query parameters contain structured values only.
2. Result rows show summaries, not narrative/field notes; one search audit is recorded by fake server, while opening one row records one report-view audit.
3. Opening another employee's report shows the exact attribution banner and reuses `frmReportEditor`.
4. Edit a header and narrative, autosave once, and assert Admin route, base revision, idempotency key, `admin_edit` attribution, and returned editor metadata.
5. Force `409 revision_conflict` and assert no overwrite, local controls preserved, existing compare/recovery choices retained.
6. Restore revision 3 after fresh purpose `report_restore`; assert current becomes revision 8 and revisions 4–7 remain listed.
7. Transfer after fresh purpose `report_transfer`, active staff UUID, reason, and confirmation; assert canonical report ID unchanged and relationship summary updated.
8. Single export uses a saved revision and existing employee-chosen DOCX path behavior.
9. Bulk export refuses empty filters, refuses a server count above 100, requires reason and fresh step-up, writes exact ZIP bytes, and reports partial failures from safe response metadata/manifest.
10. No form exposes overwrite, delete, bulk narrative edit, or direct owner/account identity fields.

Run after creating the failing tests:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminReports_Run
python -m pytest tests/access/test_admin_reports.py -q -m access_com
~~~

Expected: compilation fails because `CAdminReportFilter` and `LoadAdminReportPage` are undefined; COM tests fail because `frmAdminAllReports` is absent.

- [ ] **Step 3: Add exact Admin report route helpers and contract checks**

Append to `modApiRoutes.bas`:

~~~vb
Public Function RouteAdminReports() As String
    RouteAdminReports = API_PREFIX & "/admin/reports"
End Function

Public Function RouteAdminReport(ByVal reportId As String) As String
    RouteAdminReport = RouteAdminReports() & "/" & UrlEncodePathComponent(reportId)
End Function

Public Function RouteAdminReportRevisions(ByVal reportId As String) As String
    RouteAdminReportRevisions = RouteAdminReport(reportId) & "/revisions"
End Function

Public Function RouteAdminReportRevision(ByVal reportId As String, _
                                         ByVal revisionNumber As Long) As String
    RouteAdminReportRevision = RouteAdminReportRevisions(reportId) & "/" & CStr(revisionNumber)
End Function

Public Function RouteAdminReportRestore(ByVal reportId As String) As String
    RouteAdminReportRestore = RouteAdminReport(reportId) & "/restore"
End Function

Public Function RouteAdminReportTransfer(ByVal reportId As String) As String
    RouteAdminReportTransfer = RouteAdminReport(reportId) & "/transfer"
End Function

Public Function RouteAdminReportExport(ByVal reportId As String, _
                                       ByVal revisionNumber As Long) As String
    If revisionNumber < 1 Then Err.Raise vbObjectError + 7500, _
        "RouteAdminReportExport", "Select a saved revision."
    RouteAdminReportExport = RouteAdminReport(reportId) & _
        "/export-docx?revision=" & CStr(revisionNumber)
End Function

Public Function RouteAdminReportBulkExport() As String
    RouteAdminReportBulkExport = RouteAdminReports() & "/bulk-export"
End Function
~~~

Update route and fixture tests. Expected route-parity result is exact equality with OpenAPI, not substring matching.

- [ ] **Step 4: Implement the typed structured filter and bounded pagination**

`CAdminReportFilter` has typed properties that map one-to-one to the closed backend schema: `ReportId`, `IncidentId`, `ReportingStaffId`, `PreparerStaffId`, `IncidentDateFrom`, `IncidentDateTo`, `CreatedAtFrom`, `CreatedAtTo`, `InmateFirstName`, `InmateMiddleName`, `InmateLastName`, `InmateAdcNumber`, `Category`, `Facility`, `Location`, `Shift`, `Status`, `LastEditorStaffId`, `ModifiedAtFrom`, and `ModifiedAtTo`. Officer/preparer/last-editor controls display names but submit only a selected stable staff UUID.

It exposes:

~~~vb
Public Function HasExplicitFilter() As Boolean
    HasExplicitFilter = Len(mReportId) > 0 Or Len(mIncidentId) > 0 _
        Or Len(mReportingStaffId) > 0 Or Len(mPreparerStaffId) > 0 _
        Or mIncidentDateFrom <> 0 Or mIncidentDateTo <> 0 _
        Or mCreatedAtFrom <> 0 Or mCreatedAtTo <> 0 _
        Or Len(mInmateFirstName) > 0 Or Len(mInmateMiddleName) > 0 _
        Or Len(mInmateLastName) > 0 Or Len(mInmateAdcNumber) > 0 _
        Or Len(mCategory) > 0 Or Len(mFacility) > 0 _
        Or Len(mLocation) > 0 Or Len(mShift) > 0 Or Len(mStatus) > 0 _
        Or Len(mLastEditorStaffId) > 0 Or mModifiedAtFrom <> 0 Or mModifiedAtTo <> 0
End Function

Public Sub ValidateForBulk()
    If Not HasExplicitFilter() Then
        Err.Raise vbObjectError + 7501, "CAdminReportFilter.ValidateForBulk", _
                  "Choose at least one structured filter for bulk export."
    End If
    ValidateDateRange mIncidentDateFrom, mIncidentDateTo, "incident date"
    ValidateDateRange mCreatedAtFrom, mCreatedAtTo, "creation date"
    ValidateDateRange mModifiedAtFrom, mModifiedAtTo, "modified date"
End Sub
~~~

`ToQueryString` emits only the exact snake-case keys `report_id`, `incident_id`, `reporting_staff_id`, `preparer_staff_id`, `incident_date_from`, `incident_date_to`, `created_at_from`, `created_at_to`, `inmate_first_name`, `inmate_middle_name`, `inmate_last_name`, `inmate_adc_number`, `category`, `facility`, `location`, `shift`, `status`, `last_editor_staff_id`, `modified_at_from`, and `modified_at_to` in that order. It formats dates as `yyyy-mm-dd`, uses `UrlEncodeQueryComponent`, appends `limit=50`, and adds the opaque cursor only when supplied. `ToJsonObject` emits the same nonempty fields without cursor/limit for bulk selection. Neither method builds SQL, accepts a raw query fragment, combines inmate names into a hidden field, or sends narrative search.

- [ ] **Step 5: Reuse the User editor with explicit Admin context and attribution**

Add `AdminMode As Boolean` and `AdminViewedOwnerDisplay As String` properties to `CWorkflowState`; neither stores role, actor ID, or authorization. `OpenAdminReport` uses the Admin detail route, constructs the same `CReportState` objects as User mode, and sets only these presentation/routing fields.

`frmReportEditor` shows this persistent banner when `AdminMode` is true:

~~~text
You are viewing/editing another employee's report. Your access and every saved revision are attributed to your administrator account.
~~~

The banner is visible while editing, history, compare, conflict, restore, transfer, status, and export dialogs are open. It cannot be dismissed.

Modify `SaveNow` to delegate Admin mode to the exact `SaveAdminReport` function. `SaveAdminReport` sends current content plus base revision through `PATCH RouteAdminReport`, sets one idempotency key, and consumes no step-up. It accepts only the server response's new revision/editor/time. `409` calls the existing `HandleRevisionConflict`; no branch changes `If-Match`, base revision, or content to force a write.

Recovery snapshots add `"admin_mode": true` and report ID only; they do not contain role, actor, elevation, step-up, temporary PIN, or handoff data. Recovery reopens through the Admin route only after a fresh role/elevation check.

- [ ] **Step 6: Implement protected restore and transfer without history loss**

Restore sends the closed body `{"revision_number": selectedRevision}` plus idempotency key to `POST RouteAdminReportRestore(reportId)` through purpose `report_restore`. It never embeds the revision in the path or sends an empty body. It confirms:

~~~text
Restore revision {revision}. This creates a new current revision and preserves every later revision.
~~~

Transfer validates its payload exactly:

~~~vb
Private Function TransferPayload(ByVal newOwnerStaffId As String, _
                                 ByVal reason As String) As Object
    Dim payload As Object
    reason = Trim$(reason)
    If Len(newOwnerStaffId) = 0 Then
        Err.Raise vbObjectError + 7502, "TransferPayload", "Select an active staff member."
    End If
    If Len(reason) = 0 Or Len(reason) > 500 Then
        Err.Raise vbObjectError + 7503, "TransferPayload", _
                  "Enter a transfer reason of 500 characters or fewer."
    End If
    Set payload = CreateObject("Scripting.Dictionary")
    payload.Add "new_owner_staff_id", newOwnerStaffId
    payload.Add "reason", reason
    Set TransferPayload = payload
End Function
~~~

`frmAdminTransferReport` searches active staff through the existing staff provider, shows current/new stable staff summaries, requires reason, and uses `frmConfirmAction`. `TransferAdminReport` calls purpose `report_transfer`, replaces no local identity, and reloads the server detail/revision/access summaries after success.

- [ ] **Step 7: Implement revision-exact single and bounded ZIP export**

`ExportAdminSavedRevision` mirrors AC-09 `ExportSavedRevision` but calls `RouteAdminReportExport(reportId, revisionNumber)`, placing the explicit positive revision only in the `?revision=` query parameter. It sends no revision body, receives DOCX bytes, displays filename/hash/size/MIME/template/revision/request ID, writes through the existing employee-chosen dialog and `WriteBytesAtomically`, and opens Word only after a separate explicit choice. It does not require step-up unless the reviewed OpenAPI adds a purpose through a separately reviewed design change.

`ExportAdminReportBatch` executes this fixed sequence:

1. `filters.ValidateForBulk`.
2. Trim reason and require 1–500 characters.
3. Show filter summary, maximum 100 documents, destination ZIP, and attribution in `frmConfirmAction`.
4. Obtain fresh purpose `bulk_export` through `frmAdminStepUp` without clearing filter selections.
5. Build the exact closed body `{"selection":{"mode":"filters","filters":filters.ToJsonObject()},"revision_selection":"current_at_request","reason":reason}`; POST it with one idempotency key through `SendWithAdminStepUp`. Do not send a client limit, a floating `latest` value, or display names in staff-ID fields.
6. Reject non-ZIP MIME, absent safe filename, absent `Digest`, absent manifest hash/count metadata, or a server count above 100.
7. Prompt for `.zip`, write bytes atomically, and display succeeded/failed counts plus request ID. Never mark a failed manifest item exported locally.

The Python fixture test opens `bulk-export.zip`, requires sorted DOCX entries and `manifest.json`, and verifies each manifest report/revision/export ID, hash, actor ID, normalized filter names, timestamp, reason, and failure entry against `bulk-export-metadata.json`.

- [ ] **Step 8: Build the unbound All Reports, transfer, and bulk-export forms**

`frmAdminAllReports` contains one explicitly labeled control for every filter, Search/Clear/Next, `sfrmAdminReportResults`, and bounded summary columns. Row Open loads detail and attribution. Search result display never calls detail per row.

`frmAdminBulkExport` shows a read-only normalized filter summary, reason, maximum `100`, chosen ZIP path, result counts, request ID, and `cmdExport`; no narrative controls exist. `frmAdminTransferReport` and all reused revision forms show report ID, owner, selected source/target revision, action effect, and Admin attribution.

All forms disable submit after one click and re-enable only for a safe validation error before a request or a server response that explicitly permits another new action.

- [ ] **Step 9: Extend fake API attribution, conflict, and export behavior**

The fake API must:

- enforce Admin role/elevation before search/detail and exact step-up purpose before restore/transfer/bulk export;
- audit one bounded search, one opened record, every save/restore/transfer/status/export, and no per-row view during search;
- return `admin_edit` revisions attributed to the fictional Admin actor from bearer context, ignoring actor fields in JSON;
- preserve all revisions and return 409 on stale base revision;
- reject inactive transfer targets, empty reason, wrong/replayed step-up, empty bulk filters, selections above 100 as `bulk_export_limit_exceeded`, and any bulk body that omits `current_at_request`;
- return deterministic single DOCX and bulk ZIP bytes with reviewed safe headers;
- never accept delete or bulk narrative mutation routes.

- [ ] **Step 10: Run Admin report and full User editor/export regressions**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminReports_Run,TestReportTabSwitch_Run,TestAutosave_Run,TestRecovery_Run,TestConflict_Run,TestWordExport_Run
python -m pytest tests/access/test_admin_reports.py tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py -q -m access_com -k "report or revision or restore or transfer or conflict or recovery or export"
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py tests/unit/test_filler_boxes.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: structured search/pagination, visible Admin attribution, immutable save/restore/transfer, conflict preservation, revision-exact single export, bounded manifested bulk export, and all User report/recovery/export behaviors pass.

- [ ] **Step 11: Commit AD-03**

~~~powershell
git add access-client/src/modules/modAdminReports.bas access-client/src/classes/CAdminReportFilter.cls access-client/src/forms/frmAdminAllReports.txt access-client/src/forms/frmAdminTransferReport.txt access-client/src/forms/frmAdminBulkExport.txt access-client/src/forms/sfrmAdminReportResults.txt access-client/src/modules/modApiRoutes.bas access-client/src/modules/modAdminAuth.bas access-client/src/modules/modReportWorkflow.bas access-client/src/modules/modAutosave.bas access-client/src/modules/modConflict.bas access-client/src/modules/modRecovery.bas access-client/src/modules/modWordExport.bas access-client/src/modules/modErrors.bas access-client/src/modules/modTestHooks.bas access-client/src/classes/CWorkflowState.cls access-client/src/forms/frmAdminOverview.txt access-client/src/forms/frmReportEditor.txt access-client/src/forms/frmRevisionHistory.txt access-client/src/forms/frmRevisionCompare.txt access-client/src/forms/frmRevisionConflict.txt access-client/src/forms/frmExport.txt access-client/src/forms/frmConfirmAction.txt access-client/src/manifest.json access-client/tests/vba/TestAdminReports.bas access-client/tests/vba/TestReportWorkflow.bas access-client/tests/vba/TestConflict.bas access-client/tests/vba/TestWordExport.bas access-client/tests/vba/TestRunner.bas access-client/tests/fixtures/admin tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py tests/access/fake_api.py tests/access/test_admin_reports.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add attributed admin report oversight"
~~~

Expected: one focused AD-03 commit. Generated DOCX/ZIP files outside fictional fixtures remain in the test runner's temporary directory and are not committed.

---

### Task AD-04: Read-only audit and sanitized system health

**Files:**
- Create: `access-client/src/modules/modAdminAudit.bas`
- Create: `access-client/src/modules/modAdminHealth.bas`
- Create: `access-client/src/classes/CAdminAuditFilter.cls`
- Create: `access-client/src/forms/frmAdminAudit.txt`
- Create: `access-client/src/forms/frmAdminHealth.txt`
- Create: `access-client/src/forms/sfrmAdminAuditResults.txt`
- Create: `access-client/src/forms/sfrmAdminHealthResults.txt`
- Create: `access-client/tests/vba/TestAdminAudit.bas`
- Create: `access-client/tests/vba/TestAdminHealth.bas`
- Create: `access-client/tests/fixtures/admin/audit-page.json`
- Create: `access-client/tests/fixtures/admin/audit-export.csv`
- Create: `access-client/tests/fixtures/admin/audit-export-metadata.json`
- Create: `access-client/tests/fixtures/admin/health-operational.json`
- Create: `access-client/tests/fixtures/admin/health-degraded.json`
- Create: `access-client/tests/fixtures/admin/health-unavailable.json`
- Create: `tests/access/test_admin_operations.py`
- Modify: `access-client/src/modules/modApiRoutes.bas`
- Modify: `access-client/src/modules/modAdminAuth.bas`
- Modify: `access-client/src/modules/modErrors.bas`
- Modify: `access-client/src/modules/modTestHooks.bas`
- Modify: `access-client/src/forms/frmAdminOverview.txt`
- Modify: `access-client/src/forms/frmExport.txt`
- Modify: `access-client/src/manifest.json`
- Modify: `access-client/tests/vba/TestRunner.bas`
- Modify: `tests/unit/test_access_fixture_contracts.py`
- Modify: `tests/unit/test_access_route_parity.py`
- Modify: `tests/unit/test_access_vba_safety.py`
- Modify: `tests/access/fake_api.py`
- Modify: `access-client/SLUT-Client.accdb`
- Consume without modifying: `openapi/access-v1.yaml`

**Interfaces:**
- Consumes: AD-01 grants/activity; AC `CPagedResult`, `IFileDialogService`, `WriteBytesAtomically`, `CApiResponse.BodyBytes`, safe error/logging, theme/accessibility helpers; RP-10 overview/audit/health schemas.
- Produces: `CAdminAuditFilter`; locked `LoadAdminAuditPage`, `ExportAdminAuditSummary`, and `LoadAdminHealth`; route helpers `RouteAdminAuditEvents`, `RouteAdminAuditExport`, and `RouteAdminHealth`.

**Stop conditions:**
- Stop if audit responses can contain report content, field notes, PIN/token fields, unrestricted detail JSON, unbounded pages, or an update/delete operation.
- Stop if audit export is not purpose `audit_export`, idempotent, bounded, and audited.
- Stop if health exposes credentials, service-account details, connection strings, raw stack/error text, sensitive Cloud Logging content, or a mutation/control route.
- Stop if backup/restore-exercise fields are missing from the reviewed health schema; do not infer them from developer machine or cloud tooling.

- [ ] **Step 1: Write failing audit and health VBA tests**

Create `TestAdminAudit.bas`:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestAdminAudit_Run()
    Dim filters As New CAdminAuditFilter
    Dim page As CPagedResult

    filters.ActionFamily = "account"
    filters.Result = "success"
    Test_QueueFixtureResponse "admin/audit-page.json"
    Set page = LoadAdminAuditPage(filters)

    TestAssert.AreEqual 2, page.Items.Count, "audit page is bounded"
    TestAssert.AreEqual "admin.account_pin_reset", _
                        CStr(page.Items(1)("action_code")), "safe action code"
    TestAssert.IsTrue page.Items(1).Exists("report_content") = False, _
                      "report content is absent"
    TestAssert.IsTrue page.Items(1).Exists("token") = False, "token is absent"
End Sub
~~~

Create `TestAdminHealth.bas`:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestAdminHealth_Run()
    Dim health As Object

    Test_QueueFixtureResponse "admin/health-degraded.json"
    Set health = LoadAdminHealth()
    TestAssert.AreEqual "Degraded", CStr(health("overall_status")), _
                        "degraded status remains visible"
    TestAssert.IsTrue health.Exists("request_id"), "health includes request reference"
    TestAssert.IsTrue health.Exists("connection_string") = False, _
                      "connection string is absent"
    TestAssert.IsTrue health.Exists("service_account") = False, _
                      "service account is absent"
End Sub
~~~

- [ ] **Step 2: Write failing COM operational tests and run the red phase**

Create `tests/access/test_admin_operations.py` to assert:

- each audit filter and a combined filter is server-side and cursor-paginated;
- displayed audit row has UTC/local time, actor display/stable ID, action code/safe description, target type/ID, result, request ID, client version, and allowlisted safe details only;
- no Add/Edit/Delete/SQL/detail-JSON controls exist;
- CSV export preserves filters, requires a new `audit_export` step-up, writes exact fixture bytes, and is recorded by the fake audit stream;
- health shows Access version/compatibility, API version/source commit/Cloud Run revision, database reachability/migration, AI classify/extract/generate, policy search, queue depth/oldest age, latest backup, latest successful restore exercise, and notices;
- dependency failures render Operational/Degraded/Unavailable plus request/time reference and never raw error text;
- no control invokes a health mutation, browser cloud console, SQL client, gcloud, or service URL containing credentials;
- forms/subforms are unbound.

Run:

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAudit_Run,TestAdminHealth_Run
python -m pytest tests/access/test_admin_operations.py -q -m access_com
~~~

Expected: compilation fails because `CAdminAuditFilter`, `LoadAdminAuditPage`, and `LoadAdminHealth` do not exist; COM tests fail because `frmAdminAudit` and `frmAdminHealth` are absent.

- [ ] **Step 3: Add exact operational route helpers and fixture contract checks**

~~~vb
Public Function RouteAdminAuditEvents() As String
    RouteAdminAuditEvents = API_PREFIX & "/admin/audit-events"
End Function

Public Function RouteAdminAuditExport() As String
    RouteAdminAuditExport = RouteAdminAuditEvents() & "/export"
End Function

Public Function RouteAdminHealth() As String
    RouteAdminHealth = API_PREFIX & "/admin/health"
End Function
~~~

Update route parity and fixture validation. `audit-export.csv` is checked by bytes/hash/line count through its metadata fixture; it is not parsed into or stored in Access.

- [ ] **Step 4: Implement closed audit filters and safe row projection**

`CAdminAuditFilter` exposes `OccurredAtFromUtc`, `OccurredAtToUtc`, `ActorAccountId`, `ActorStaffMemberId`, `ActionFamily`, `TargetType`, `TargetId`, and `Result`. It validates time ordering, UUID fields, and restricts `Result` to empty, `success`, `denied`, or `failed`. `ToQueryString` emits exactly `occurred_at_from`, `occurred_at_to`, `actor_account_id`, `actor_staff_member_id`, `action_family`, `target_type`, `target_id`, and `result`, followed by `limit=50` and an opaque cursor only. `ToJsonObject` emits the same nonempty filter fields without cursor/limit for export.

`LoadAdminAuditPage` parses each item through one allowlist:

~~~vb
Private Function SafeAuditRow(ByVal source As Object) As Object
    Dim row As Object
    Set row = CreateObject("Scripting.Dictionary")
    row.Add "occurred_at_utc", RequireString(source, "occurred_at_utc")
    row.Add "actor_display", RequireString(source, "actor_display")
    row.Add "actor_id", RequireString(source, "actor_id")
    row.Add "action_code", RequireString(source, "action_code")
    row.Add "safe_description", RequireString(source, "safe_description")
    row.Add "target_type", RequireString(source, "target_type")
    row.Add "target_id", RequireString(source, "target_id")
    row.Add "result", RequireString(source, "result")
    row.Add "request_id", RequireString(source, "request_id")
    row.Add "client_version", RequireString(source, "client_version")
    If source.Exists("safe_details") Then row.Add "safe_details", SafeAuditDetails(source("safe_details"))
    Set SafeAuditRow = row
End Function
~~~

`SafeAuditDetails` copies only exact keys present in the OpenAPI allowlist. Unknown keys are discarded, not rendered generically. The form converts UTC to local display for presentation while retaining the UTC column.

- [ ] **Step 5: Implement protected audit CSV export**

`ExportAdminAuditSummary` requires a valid bounded filter, shows filter/time/actor/action/result scope in `frmConfirmAction`, obtains purpose `audit_export`, and sends one idempotent POST with the exact closed body `{"filters":filters.ToJsonObject(),"format":"csv","reason":reason}`. Reason is trimmed and must contain 1–500 characters. It validates `text/csv`, filename, byte length, SHA-256/Digest, export ID, request ID, and row count at or below 10,000 before prompting for `.csv` and calling `WriteBytesAtomically`. `audit_export_limit_exceeded` preserves the filters/reason and asks the Admin to narrow the selection; it is never automatically resubmitted.

It never opens Excel automatically. After success, it shows `The audit summary export was recorded in the audit log.` A cancellation before send makes no API call; cancellation after generation is still a server-audited export and is shown as such.

- [ ] **Step 6: Implement sanitized health parsing and non-control UI**

`LoadAdminHealth` GETs the protected endpoint, touches Admin activity, and copies only reviewed keys into a new dictionary. Required values include:

~~~text
overall_status
observed_at
request_id
access_client_version
compatibility_state
api_release_version
api_source_commit
cloud_run_revision
database_status
migration_version
ai_classification_status
ai_extraction_status
ai_generation_status
policy_search_status
queue_depth
oldest_pending_job_age_seconds
latest_backup_at
latest_restore_exercise_at
notices
~~~

Each status accepts only Operational, Degraded, or Unavailable. Unknown/missing required status becomes `Unavailable` with the current request ID, never the raw value.

`frmAdminHealth` and `sfrmAdminHealthResults` contain Refresh only. They show local Access version plus the sanitized service values and accessible text/icon status. There are no Open Console, Restart, Retry Job, Run Backup, Restore, Migrate, Scale, Configure, Edit, Delete, or raw endpoint controls.

- [ ] **Step 7: Extend fake API safe-detail and degradation enforcement**

The fake API validates role/elevation, serves bounded audit pages, records audit export as another event, and emits operational/degraded/unavailable health fixtures. It rejects audit update/delete and health mutation verbs with 405. Inject marker strings resembling passwords, report content, tokens, stack traces, and connection URLs into fake internal dependency exceptions and assert none appear in responses, safe logs, form state, or COM test JSON.

- [ ] **Step 8: Run operational and regression suites**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminAudit_Run,TestAdminHealth_Run,TestAdminAuthorization_Run,TestSafeLog_Run
python -m pytest tests/access/test_admin_operations.py tests/access/test_admin_authorization.py -q -m access_com
python -m pytest tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
~~~

Expected: audit filtering/viewing/export is bounded, immutable, safe, step-up protected, and attributed; health is actionable but sanitized/read-only; injected sensitive markers are absent; User and prior Admin suites remain compilable.

- [ ] **Step 9: Commit AD-04**

~~~powershell
git add access-client/src/modules/modAdminAudit.bas access-client/src/modules/modAdminHealth.bas access-client/src/classes/CAdminAuditFilter.cls access-client/src/forms/frmAdminAudit.txt access-client/src/forms/frmAdminHealth.txt access-client/src/forms/sfrmAdminAuditResults.txt access-client/src/forms/sfrmAdminHealthResults.txt access-client/src/modules/modApiRoutes.bas access-client/src/modules/modAdminAuth.bas access-client/src/modules/modErrors.bas access-client/src/modules/modTestHooks.bas access-client/src/forms/frmAdminOverview.txt access-client/src/forms/frmExport.txt access-client/src/manifest.json access-client/tests/vba/TestAdminAudit.bas access-client/tests/vba/TestAdminHealth.bas access-client/tests/vba/TestRunner.bas access-client/tests/fixtures/admin tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py tests/access/fake_api.py tests/access/test_admin_operations.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add admin audit and health views"
~~~

Expected: one focused AD-04 commit with no infrastructure-control code or exported operational data.

---

### Task AD-05: One-time Review Lab handoff and full Admin/Windows regression

**Files:**
- Create: `access-client/src/modules/modAdminReviewLab.bas`
- Create: `access-client/src/forms/frmAdminReviewLab.txt`
- Create: `access-client/tests/vba/TestAdminReviewLab.bas`
- Create: `access-client/tests/fixtures/admin/review-lab-handoff.json`
- Create: `access-client/tests/fixtures/errors/review-lab-handoff-invalid.json`
- Create: `tests/access/test_admin_review_lab.py`
- Create: `tests/access/test_admin_smoke.py`
- Modify: `access-client/src/modules/modApiRoutes.bas`
- Modify: `access-client/src/modules/modAdminAuth.bas`
- Modify: `access-client/src/modules/modNavigation.bas`
- Modify: `access-client/src/modules/modTestHooks.bas`
- Modify: `access-client/src/forms/frmAdminOverview.txt`
- Modify: `access-client/src/forms/frmShell.txt`
- Modify: `access-client/src/manifest.json`
- Modify: `access-client/build/InvokeAccessSmokeTests.ps1`
- Modify: `access-client/build/ScanAccessSource.ps1`
- Modify: `access-client/build/ValidateAccessBuild.ps1`
- Modify: `access-client/build/build-matrix.example.json`
- Modify: `access-client/tests/vba/TestRunner.bas`
- Modify: `access-client/tests/vba/classes/CFakeProcessLauncher.cls`
- Modify: `tests/unit/test_access_source_layout.py`
- Modify: `tests/unit/test_access_fixture_contracts.py`
- Modify: `tests/unit/test_access_route_parity.py`
- Modify: `tests/unit/test_access_vba_safety.py`
- Modify: `tests/access/conftest.py`
- Modify: `tests/access/fake_api.py`
- Modify: `tests/access/access_com.py`
- Modify: `tests/access/test_user_workflows.py`
- Modify: `access-client/README.md`
- Modify: `access-client/SLUT-Client.accdb`
- Consume without modifying: `openapi/access-v1.yaml`
- Consume without modifying: `access-client/build/AccessBuild.Common.psm1`
- Consume without modifying: `access-client/build/ExportAccessSource.ps1`
- Consume without modifying: `access-client/build/ImportAccessSource.ps1`
- Consume without modifying: `access-client/build/BuildAccde.ps1`

**Interfaces:**
- Consumes: AD-01 purpose/grant and navigation; AC `IProcessLauncher.OpenUri`, `CWindowsProcessLauncher`, `CFakeProcessLauncher`, source/build/static/COM harnesses; ID-08 one-time handoff contract.
- Produces: `OpenAdminReviewLab`; route helper `RouteAdminReviewLabHandoffs`; `Test_RunAdminSmokeWorkflow`; final Admin source/build/authorization/Windows evidence.

**Stop conditions:**
- Stop if the handoff URL is not the policy-approved HTTPS origin followed by exactly `/access-handoff#` and one nonempty fragment token, or if it lacks 60-second expiry, one-time semantics, purpose `review_lab_handoff`, and safe audit behavior.
- Stop if Access is expected to redeem the fragment, set a browser cookie, send an Access credential to the browser, use the legacy shared Admin code, or reimplement Review Lab.
- Stop a Windows row on Access COM activation failure, PowerShell/Access bitness mismatch, import/export drift, missing reference, compile/ACCDE failure, static-scan failure, fake-API failure, COM timeout, orphaned test Access process, or unsupported display/scaling behavior.
- Stop before any test that targets a production hostname, uses real data, launches the agency browser outside the fake launcher/unit boundary, signs, deploys, pushes, or installs an artifact.

- [ ] **Step 1: Write failing one-time handoff tests**

Create `TestAdminReviewLab.bas`:

~~~vb
Option Compare Database
Option Explicit

Public Sub TestAdminReviewLab_Run()
    Dim launcher As CFakeProcessLauncher
    Dim expectedPrefix As String
    Set launcher = New CFakeProcessLauncher

    Test_ResetApplication
    Test_SeedProfileFromFixture "profile/me-admin.json"
    Test_SeedClientPolicyFromFixture "policy/client-current.json"
    Test_EnterAdminCenterFromFixture
    ConfigureAdminProcessLauncherForTest launcher
    Test_QueueAdminStepUpFixture "review_lab_handoff"
    Test_QueueFixtureResponse "admin/review-lab-handoff.json"

    TestAssert.IsTrue OpenAdminReviewLab(), "handoff opens"
    TestAssert.AreEqual 1, launcher.OpenUriCount, "one browser launch"
    expectedPrefix = TrustedReviewLabOrigin() & "/access-handoff#"
    TestAssert.AreEqual expectedPrefix, _
                        Left$(launcher.LastOpenedUri, Len(expectedPrefix)), _
                        "policy-approved fragment URL"
    TestAssert.IsTrue InStr(1, Test_GetAdminStateJson(), _
                      Mid$(launcher.LastOpenedUri, Len(expectedPrefix) + 1), _
                      vbBinaryCompare) = 0, _
                      "handoff fragment is absent from state"
End Sub
~~~

`CFakeProcessLauncher` is the existing AC-09 fake and gains read-only `OpenUriCount` and `LastOpenedUri` test properties; no new launcher class is created. `ConfigureAdminProcessLauncherForTest` accepts that existing interface only in `TEST_BUILD`; release uses the existing `CWindowsProcessLauncher` through `AdminProcessLauncher`.

Create `tests/access/test_admin_review_lab.py` to assert:

- User cannot discover Review Lab navigation or call issue endpoint;
- Admin without elevation cannot open it;
- expired elevation preserves the form and prompts again;
- wrong/replayed/expired step-up is denied;
- the issue request has no PIN, Access/renewal token in body, actor, role, shared Admin code, or handoff fragment;
- exactly one HTTPS fragment URL is passed to the fake process launcher;
- the URL is absent from state JSON/log/recovery after the call;
- second use requires a newly issued handoff;
- cancellation before PIN makes no issue call;
- no Access form attempts to display/redeem browser Review Lab content.

- [ ] **Step 2: Run the handoff tests and verify expected failures**

~~~powershell
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests TestAdminReviewLab_Run
python -m pytest tests/access/test_admin_review_lab.py -q -m access_com
~~~

Expected: compilation fails because `OpenAdminReviewLab` and `RouteAdminReviewLabHandoffs` do not exist; COM tests fail because `frmAdminReviewLab` is absent.

- [ ] **Step 3: Add the exact handoff route and strict URL validator**

~~~vb
Public Function RouteAdminReviewLabHandoffs() As String
    RouteAdminReviewLabHandoffs = API_PREFIX & "/admin/review-lab-handoffs"
End Function
~~~

`IsValidReviewLabHandoffUrl` requires:

~~~vb
Private Function IsValidReviewLabHandoffUrl(ByVal handoffUrl As String) As Boolean
    Dim marker As String
    Dim fragmentAt As Long
    marker = "/access-handoff#"
    fragmentAt = InStr(1, handoffUrl, marker, vbBinaryCompare)
    IsValidReviewLabHandoffUrl = LCase$(Left$(handoffUrl, 8)) = "https://" _
        And fragmentAt > 12 _
        And fragmentAt + Len(marker) <= Len(handoffUrl) _
        And InStr(fragmentAt + Len(marker), handoffUrl, "#", vbBinaryCompare) = 0 _
        And InStr(1, Left$(handoffUrl, fragmentAt - 1), "?", vbBinaryCompare) = 0 _
        And InStr(1, Left$(handoffUrl, fragmentAt - 1), "@", vbBinaryCompare) = 0
End Function
~~~

Parse the candidate origin without following a redirect and compare it exactly, including port, to AC-04 `TrustedReviewLabOrigin()`. Require the remaining path/fragment shape to be exactly `/access-handoff#` plus one nonempty fragment token; reject a query, second `#`, user info, encoded authority delimiter, control character, or any path normalization. Stop if policy has not been loaded or the origin differs. Do not compare to `ApiBaseUrl()`: the API and browser origins may legitimately differ. Do not use redirects, the `Host` header, a form value, registry entry, or a second configurable handoff host.

- [ ] **Step 4: Implement one-time issue/open/clear behavior**

~~~vb
Public Function OpenAdminReviewLab() As Boolean
    Dim request As CApiRequest
    Dim response As CApiResponse
    Dim data As Object
    Dim handoffUrl As String

    RequireAdminElevation
    Set request = NewApiRequest("POST", RouteAdminReviewLabHandoffs(), "{}")
    request.Headers("Idempotency-Key") = NewUuid()
    request.CanRetry = False
    Set response = SendWithAdminStepUp(request, AdminPurposeReviewLabHandoff)
    Set data = ParseSuccessEnvelope(response)
    handoffUrl = RequireString(data, "handoff_url")

    If Not IsValidReviewLabHandoffUrl(handoffUrl) Then
        Err.Raise vbObjectError + 7701, "OpenAdminReviewLab", _
                  "The Review Lab handoff could not be opened safely."
    End If
    AdminProcessLauncher().OpenUri handoffUrl
    If Len(handoffUrl) > 0 Then handoffUrl = String$(Len(handoffUrl), Chr$(0))
    handoffUrl = vbNullString
    OpenAdminReviewLab = True
End Function
~~~

Use one cleanup/error path that overwrites `handoffUrl` even if validation or `OpenUri` fails. Never retry the POST automatically: a new explicit attempt obtains a new step-up and handoff.

`frmAdminReviewLab` explains: the link expires in 60 seconds, opens the managed browser Review Lab, signs the individual Admin browser session in, and expires after 30 minutes without browser activity. It contains `cmdOpenReviewLab`, `cmdCancel`, and no browser control, token field, shared-code field, URL display, or history.

- [ ] **Step 5: Extend static source, manifest, and route/fixture tests**

Add the route and fixtures to parity/contract tests. Extend source-layout expectations with exactly the seven Admin modules, five Admin classes/interfaces, fourteen Admin forms, five Admin subforms, six Admin VBA tests, and one fake clipboard class locked above.

Extend `ScanAccessSource.ps1` and `test_access_vba_safety.py` to reject:

- WebBrowser/EdgeBrowser controls on Admin forms;
- `ADMIN_CODE`, `ACCESS_CODE`, bearer/renewal credential concatenation into a URL, or `/review-lab` opened directly;
- handoff URL/fragment fields in logs, recovery, app-state/test JSON, tables, or form tags;
- any Admin delete route, raw SQL/ADO/DAO cloud connection, or infrastructure command;
- production hostname literals outside the approved injected `ApiBaseUrl` property;
- a new process launcher rather than existing `IProcessLauncher`.

- [ ] **Step 6: Write the failing full Admin smoke workflow**

Create `tests/access/test_admin_smoke.py` that starts the local fake API, calls `InvokeAccessSmokeTests.ps1 -IncludeAdmin`, parses JSON, and requires these named stages:

~~~python
EXPECTED_ADMIN_STAGES = [
    "user_denied_admin",
    "admin_persistent_restart_without_elevation",
    "admin_elevation",
    "admin_overview",
    "staff_create_correct",
    "account_create_temporary_pin",
    "account_reset_role_status_unlock",
    "account_session_revoke",
    "admin_report_search_open",
    "admin_report_edit_conflict",
    "admin_report_restore_transfer",
    "admin_single_bulk_export",
    "admin_audit_export",
    "admin_health_degraded",
    "review_lab_handoff",
    "admin_logout_clears_grants",
]


def test_admin_smoke_reports_every_stage(admin_smoke_result):
    assert admin_smoke_result["failed"] == 0
    assert [item["name"] for item in admin_smoke_result["stages"]] == EXPECTED_ADMIN_STAGES
    assert all(item["status"] == "passed" for item in admin_smoke_result["stages"])
~~~

Run before extending the smoke hook:

~~~powershell
python -m pytest tests/access/test_admin_smoke.py -q -m access_com
~~~

Expected: FAIL because `InvokeAccessSmokeTests.ps1` has no `-IncludeAdmin` switch and `Test_RunAdminSmokeWorkflow` is undefined.

- [ ] **Step 7: Extend the existing smoke harness without creating a second runner**

Add to `InvokeAccessSmokeTests.ps1`:

~~~powershell
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$FakeApiUrl,
    [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform,
    [switch]$IncludeAdmin
)
~~~

Preserve the existing User smoke call. When `-IncludeAdmin` is present, call `Application.Run("Test_RunAdminSmokeWorkflow")`, parse both JSON results, and return one result with separate `user` and `admin` keys. The script starts/closes only its own Access application, uses the existing bounded timeout/orphan checks, and never launches a real browser because `Test_RunAdminSmokeWorkflow` injects `CFakeProcessLauncher`.

`Test_RunAdminSmokeWorkflow` performs all 16 stages in order and resets the fake API/state between destructive fictional actions. It returns only stage name/status/request-count metadata; no PIN, token, report content, employee number, handoff URL, or temporary export path.

- [ ] **Step 8: Run full static, User/Admin, and reconstruction gates**

~~~powershell
python -m pytest tests/unit/test_access_source_layout.py tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py -q
powershell.exe -NoProfile -File access-client/build/InvokeAccessUnitTests.ps1 -Database access-client/SLUT-Client.accdb -Tests Test_RunAll
python -m pytest tests/access/test_reconstruction.py -q -m access_com
python -m pytest tests/access/test_user_workflows.py tests/access/test_recovery_after_termination.py tests/access/test_admin_authorization.py tests/access/test_admin_accounts.py tests/access/test_admin_reports.py tests/access/test_admin_operations.py tests/access/test_admin_review_lab.py tests/access/test_admin_smoke.py -q -m access_com
powershell.exe -NoProfile -File access-client/build/ScanAccessSource.ps1 -Source access-client/src -Tests access-client/tests/vba
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database access-client/SLUT-Client.accdb -Source access-client/src -Platform x64
git diff --check
~~~

Expected: all static/VBA/COM tests pass, reconstruction re-exports with no diff, the empty-table invariant holds, no sensitive/source-safety finding exists, User behavior is unchanged, and the current Access row compiles. Do not claim the other bitness from this run.

- [ ] **Step 9: Execute each supported Windows/Access matrix row locally**

For each approved row in `build-matrix.example.json`, use a matching-bitness runner and isolated temporary directory:

~~~powershell
powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database $env:TEMP\SLUT-Admin-Matrix.accdb -Configuration Test
powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database $env:TEMP\SLUT-Admin-Matrix.accdb -Source access-client/src -Platform x64
powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database $env:TEMP\SLUT-Admin-Matrix.accdb -Output $env:TEMP\SLUT-Admin-Matrix.accde -Platform x64 -ClientVersion 0.1.0
powershell.exe -NoProfile -File access-client/build/InvokeAccessSmokeTests.ps1 -Database $env:TEMP\SLUT-Admin-Matrix.accde -FakeApiUrl http://127.0.0.1:8765 -Platform x64 -IncludeAdmin
~~~

Repeat with `x86` only on a matching 32-bit Access runner. Record Windows build, Access full/runtime product, Access version/update channel, bitness, display scale, commands, exit codes, unsigned artifact SHA-256, and User/Admin stage results. Do not commit generated ACCDEs or test output.

Manual acceptance for each inventoried full-Access display row covers 1366 by 768 at 100%, 125%, and 150% scaling, keyboard-only navigation, visible focus, screen-reader-accessible names, high contrast, exact target/effect confirmations, understandable elevation expiry, preserved form selections, Admin attribution, and switching between Reporting/Administration without role confusion. Runtime rows run the automated smoke and applicable display checks but do not attempt source import/compile.

- [ ] **Step 10: Document final Admin source and test workflow**

Update `access-client/README.md` with:

- one binary and shared User/Admin navigation model;
- Admin role/elevation/step-up lifecycle and memory-only rule;
- new Admin object inventory;
- fixture, unit, COM smoke, static scan, rebuild, compile, and matrix commands;
- temporary-PIN, audit, health, bulk-export, and handoff safety boundaries;
- no local tables/direct cloud connections/delete paths;
- agents never deploy, push, sign, handle secrets, or target production;
- signing, packaging, installation, pilot, and deployment remain external rollout gates.

- [ ] **Step 11: Commit AD-05**

~~~powershell
git add access-client/src/modules/modAdminReviewLab.bas access-client/src/forms/frmAdminReviewLab.txt access-client/src/modules/modApiRoutes.bas access-client/src/modules/modAdminAuth.bas access-client/src/modules/modNavigation.bas access-client/src/modules/modTestHooks.bas access-client/src/forms/frmAdminOverview.txt access-client/src/forms/frmShell.txt access-client/src/manifest.json access-client/build/InvokeAccessSmokeTests.ps1 access-client/build/ScanAccessSource.ps1 access-client/build/ValidateAccessBuild.ps1 access-client/build/build-matrix.example.json access-client/tests/vba/TestAdminReviewLab.bas access-client/tests/vba/TestRunner.bas access-client/tests/vba/classes/CFakeProcessLauncher.cls access-client/tests/fixtures/admin/review-lab-handoff.json access-client/tests/fixtures/errors/review-lab-handoff-invalid.json tests/unit/test_access_source_layout.py tests/unit/test_access_fixture_contracts.py tests/unit/test_access_route_parity.py tests/unit/test_access_vba_safety.py tests/access/conftest.py tests/access/fake_api.py tests/access/access_com.py tests/access/test_user_workflows.py tests/access/test_admin_review_lab.py tests/access/test_admin_smoke.py access-client/README.md access-client/SLUT-Client.accdb
git commit -m "test(access): complete admin handoff and Windows gates"
~~~

Expected: one focused AD-05 commit containing source, fictional fixtures, harness changes, documentation, and the source-matched editable binary only. No signed/package/deployed artifact, prompt, secret, production evidence, or generated test export is committed.

## Admin Implementation Completion Gate

Before declaring AD-01 through AD-05 complete:

1. `git status --short` contains only reviewed task files; each task is one independently reviewed commit.
2. `ExportAccessSource.ps1 -Check`, reconstruction, VBA compile, static scans, User/Admin unit tests, fake-API COM journeys, and full smoke pass.
3. User cannot discover or invoke Admin operations; Admin ordinary reporting remains unchanged; persistent restart never restores elevation or step-up.
4. Elevation is 15-minute idle, sensitive grants are five-minute exact-purpose single-use, and no sensitive credential appears in any client persistence/log/test-state surface.
5. Staff/account/session/report/audit/health/handoff operations satisfy the approved spec, visible attribution, immutable history, no-silent-overwrite, no-delete, bounded-page/export, and safe diagnostic requirements.
6. Every approved Access version/bitness row is actually executed on matching inventory hardware and every required display/accessibility row is manually accepted. Unsupported or unexecuted rows remain explicitly unaccepted.
7. No agent has pushed, merged, deployed, signed, installed, published, handled secrets, accessed production data, changed Trust Center policy, or created Claude prompts/updater/backend/infrastructure work.
