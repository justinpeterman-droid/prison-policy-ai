# Access Client Screens and Cloud Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a role-aware Microsoft Access client that signs individual staff into the existing Google Cloud Run Access API, supports report work and policy questions, and gives authorized administrators roster and all-report capabilities.

**Architecture:** The rebuilt `SLUT-Client.accdb` remains an unbound Access front end. New VBA modules provide one bounded HTTPS transport, current session state, API routes, and screen services; forms call those services and contain no authorization logic. Cloud Run and Cloud SQL remain authoritative for identity, report access, drafts, revisions, AI jobs, policy answers, and audits.

**Tech Stack:** Microsoft Access x64/VBA, existing hash-pinned VBA-JSON source, late-bound WinHTTP over Windows TLS, DPAPI current-user protection, Flask `/api/v1` contract in `openapi/access-v1.yaml`, Cloud Run, and Cloud SQL.

## Global Constraints

- Implement only after the AC-01 source/build harness range is merged and its Access COM/release gates are approved; do not fork a second Access database.
- The managed HTTPS API origin comes from the approved client-policy/deployment interface; never compile the legacy browser host into Access.
- Keep `SLUT-Client.accdb` unbound: no application tables, stored queries, reports, plaintext PINs, bearer tokens, report contents, or local report history.
- Use bearer tokens only in memory. DPAPI may protect a rotating renewal token for the current Windows user only after an explicit Keep Me Signed In choice.
- Every modifying call supplies a UUID idempotency key. Every incident/report save supplies the current revision and displays a conflict instead of overwriting.
- Never rely on hidden controls for access control. Cloud Run derives the actor from the bearer session and enforces Officer/Admin permissions.
- Use fictional accounts and reports in all tests. Do not query, create, or alter production staff or reports during development.
- The policy conversation exists only in memory and is cleared on logout.
- Form source remains exportable text under `access-client/src`, manifest-hashed, and rebuilt into `access-client/SLUT-Client.accdb` with the existing import/validation scripts.

---

## File Structure

- `access-client/src/modules/modApiRoutes.bas` — exact URL construction for the documented `/api/v1` operations.
- `access-client/src/classes/CApiRequest.cls`, `CApiResponse.cls`, `CApiError.cls`, `CSessionState.cls`, `CWorkflowState.cls` — typed request/response/session/workflow boundaries.
- `access-client/src/modules/modHttp.bas`, `modJson.bas`, `modAuth.bas`, `modAppState.bas`, `modAppStartup.bas`, `modNavigation.bas`, `modReports.bas`, `modPolicy.bas`, `modAdmin.bas` — focused services; forms call these modules rather than constructing HTTP requests.
- `access-client/src/forms/*.txt` — unbound Sign In, Change PIN, Home, Report Workspace, My Reports, Policy Chat, Account, Admin Roster, and Admin All Reports forms.
- `access-client/src/macros/AutoExec.txt` — invokes only `AppStart()` in Release; it never invokes test-only VBA.
- `tests/unit/test_access_*.py` — static source/manifest/fixture contracts.
- `tests/access/test_access_client_workflow.py` — Windows Access COM integration against a fictional fake API, never Google credentials.
- `access-client/tests/fixtures/access-api/*.json` — schema-valid fictional OpenAPI examples used by the fake transport.

### Task 1: Lock the Access API boundary and fictional fixture server

**Files:**
- Create: `access-client/src/modules/modApiRoutes.bas`
- Create: `access-client/src/classes/CApiRequest.cls`
- Create: `access-client/src/classes/CApiResponse.cls`
- Create: `access-client/src/classes/CApiError.cls`
- Create: `access-client/src/modules/modHttp.bas`
- Create: `access-client/tests/fixtures/access-api/auth-login.json`
- Create: `access-client/tests/fixtures/access-api/me-officer.json`
- Create: `access-client/tests/fixtures/access-api/me-admin.json`
- Create: `tests/unit/test_access_route_parity.py`
- Create: `tests/unit/test_access_fixture_contracts.py`

**Consumes:** `openapi/access-v1.yaml` operations `loginAccessClient`, `renewAccessSession`, `getCurrentActorProfile`, `logoutCurrentSession`, `getClientPolicy`, `createIncident`, `listEmployeeReports`, `askPolicyQuestion`, `listAdminStaff`, and `searchAdminReports`.

**Produces:** `NewApiRequest(method As String, path As String) As CApiRequest`, `ApiSend(request As CApiRequest) As CApiResponse`, and route functions returning only documented relative paths.

- [ ] **Step 1: Write the failing route/fixture contracts**

```python
def test_access_routes_match_openapi_operations():
    routes = read_module("modApiRoutes.bas")
    assert '"/api/v1/auth/login"' in routes
    assert '"/api/v1/reports"' in routes
    assert '"/api/v1/policy/questions"' in routes
    assert '"/api/v1/admin/staff"' in routes


def test_login_fixture_is_a_closed_fictional_contract():
    data = json.loads(fixture("auth-login.json").read_text())
    assert data["data"]["profile"]["employee_number"] == "FICT-1001"
    assert "access_token" in data["data"]
    assert "real" not in json.dumps(data).lower()
```

- [ ] **Step 2: Run the route/fixture contracts**

Run: `python -m pytest tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py -q`

Expected: FAIL because the Access route modules and fictional fixtures do not exist.

- [ ] **Step 3: Implement the transport boundary**

```vb
Public Function NewApiRequest(ByVal method As String, ByVal path As String) As CApiRequest
    Dim request As New CApiRequest
    request.Method = UCase$(method)
    request.Path = path
    request.RequestId = NewUuid()
    Set NewApiRequest = request
End Function

Public Function ApiSend(ByVal request As CApiRequest) As CApiResponse
    'CreateObject("WinHttp.WinHttpRequest.5.1") only; no compile-time WinHTTP reference.
    'Apply bounded timeouts, request ID, client version, and optional bearer header.
    'Return a parsed success/error envelope; never expose HTML or VBA errors to a form.
End Function
```

- [ ] **Step 4: Re-run contracts and compile the rebuilt Access database**

Run: `python -m pytest tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py -q; powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database tests/output/access-api-core.accdb -Configuration Test; powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database tests/output/access-api-core.accdb -Source access-client/src -Platform x64`

Expected: PASS; no static WinHTTP reference and no credential in fixtures.

- [ ] **Step 5: Commit**

```bash
git add access-client/src access-client/tests/fixtures/access-api tests/unit/test_access_route_parity.py tests/unit/test_access_fixture_contracts.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add API transport contracts"
```

### Task 2: Add individual login, first-use PIN change, and session state

**Files:**
- Create: `access-client/src/classes/CSessionState.cls`
- Create: `access-client/src/modules/modAuth.bas`
- Create: `access-client/src/modules/modAppState.bas`
- Create: `access-client/src/modules/modDpapi.bas`
- Modify: `access-client/src/forms/frmLogin.txt`
- Create: `access-client/src/forms/frmChangePin.txt`
- Create: `tests/unit/test_access_auth_contract.py`
- Create: `tests/access/test_access_client_workflow.py`

**Consumes:** Task 1 `ApiSend`, `/api/v1/auth/login`, `/api/v1/auth/renew`, `/api/v1/me`, `/api/v1/auth/change-pin`, `/api/v1/auth/logout`, and `/api/v1/auth/logout-all`.

**Produces:** `CurrentSession() As CSessionState`, `Login(employeeNumber As String, pin As String, persist As Boolean)`, `ChangeCurrentPin(oldPin As String, newPin As String)`, and `SignOutCurrentComputer()`.

- [ ] **Step 1: Write failing login/state tests**

```python
def test_login_source_never_persists_pin_or_access_token():
    source = read_module("modAuth.bas") + read_module("modDpapi.bas")
    assert "ProtectRenewalTokenForCurrentUser" in source
    assert "SavePin" not in source
    assert "access_token" not in read_recovery_files(source)


def test_fake_access_login_routes_officer_and_admin_by_server_profile():
    result = drive_access_fake_api("FICT-1001", "temporary-pin")
    assert result.screen == "frmChangePin"
    assert result.role == "Officer"
```

- [ ] **Step 2: Run the focused auth tests**

Run: `python -m pytest tests/unit/test_access_auth_contract.py tests/access/test_access_client_workflow.py -q`

Expected: FAIL because session state and sign-in behavior do not exist.

- [ ] **Step 3: Implement session and form behavior**

```vb
Public Sub Login(ByVal employeeNumber As String, ByVal pin As String, ByVal persist As Boolean)
    Dim response As CApiResponse
    Set response = ApiSend(LoginRequest(employeeNumber, pin, persist))
    LoadSessionFromLogin response
    ClearTextBoxValue Forms!frmLogin!txtPin
    If CurrentSession.RequiresPinChange Then
        NavigateTo "frmChangePin"
    Else
        NavigateTo "frmHome"
    End If
End Sub
```

Implement DPAPI only for the rotating renewal token after an explicit persist choice. Access token remains memory-only. Login errors use safe API error codes; a form never shows a PIN, token, HTTP HTML body, or VBA exception.

- [ ] **Step 4: Run fake-API and Access COM tests**

Run: `python -m pytest tests/unit/test_access_auth_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: fictional Officer reaches Change PIN/Home, fictional Admin gets Admin role, and Sign Out clears policy/session state.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_auth_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add individual account sign-in"
```

### Task 3: Build the role-aware Home shell and navigation

**Files:**
- Create: `access-client/src/modules/modAppStartup.bas`
- Create: `access-client/src/modules/modNavigation.bas`
- Modify: `access-client/src/forms/frmShell.txt`
- Create: `access-client/src/forms/frmHome.txt`
- Create: `access-client/src/forms/frmAccount.txt`
- Modify: `access-client/src/macros/AutoExec.txt`
- Create: `tests/unit/test_access_shell_contract.py`

**Consumes:** Task 2 `CurrentSession`, `Login`, `SignOutCurrentComputer`, and `/api/v1/client-policy`.

**Produces:** `AppStart()`, `NavigateTo(screenName As String)`, `CanUseAdminCenter() As Boolean`, and `SignOutAndReturnToLogin()`.

- [ ] **Step 1: Write a failing role-navigation test**

```python
def test_home_exposes_admin_routes_only_through_role_aware_navigation():
    home = read_form("frmHome")
    nav = read_module("modNavigation")
    assert "cmdNewReport" in home
    assert "cmdMyReports" in home
    assert "cmdPolicyChat" in home
    assert "CanUseAdminCenter" in nav
    assert "frmAdminRoster" in nav
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/unit/test_access_shell_contract.py -q`

Expected: FAIL because the existing shell is blank.

- [ ] **Step 3: Implement the guided Home screen**

```vb
Public Sub AppStart()
    If RestoreOrRenewSession() Then
        NavigateTo "frmHome"
    Else
        NavigateTo "frmLogin"
    End If
End Sub

Public Function CanUseAdminCenter() As Boolean
    CanUseAdminCenter = (CurrentSession.Role = "Admin")
End Function
```

The Home form has Start New Report, My Reports, Policy Chat, Account, and Sign Out. It displays Staff Roster and All Reports only when `CanUseAdminCenter()` is true. `AutoExec` calls only `AppStart()` in Release.

- [ ] **Step 4: Verify the navigation with fictional roles**

Run: `python -m pytest tests/unit/test_access_shell_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: Officer sees no Admin route; Admin sees roster and all-report routes; manually opening an Admin form still receives a Cloud Run authorization error if the server denies it.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_shell_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add role-aware home screen"
```

### Task 4: Implement new-report drafts and private report history

**Files:**
- Create: `access-client/src/classes/CWorkflowState.cls`
- Create: `access-client/src/modules/modReports.bas`
- Create: `access-client/src/forms/frmReportWorkspace.txt`
- Create: `access-client/src/forms/frmMyReports.txt`
- Create: `tests/unit/test_access_report_workflow_contract.py`
- Modify: `tests/access/test_access_client_workflow.py`

**Consumes:** Task 1 incident/report routes and Task 2 server-derived profile.

**Produces:** `StartNewIncident()`, `SaveDraft()`, `LoadMyReports()`, and `OpenReport(reportId As String)`.

- [ ] **Step 1: Write failing private-history and save tests**

```python
def test_report_save_uses_server_revision_and_idempotency():
    source = read_module("modReports")
    assert "IfMatchRevision" in source
    assert "IdempotencyKey" in source


def test_officer_history_fake_api_never_returns_another_officers_report():
    page = fake_api_reports("FICT-1001")
    assert {row["owner"] for row in page["data"]["items"]} == {"FICT-1001"}
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/unit/test_access_report_workflow_contract.py tests/access/test_access_client_workflow.py -q`

Expected: FAIL because the workspace and report services do not exist.

- [ ] **Step 3: Implement the draft flow**

```vb
Public Sub SaveDraft()
    Dim request As CApiRequest
    Set request = SaveIncidentRequest(CurrentWorkflow)
    request.IdempotencyKey = NewUuid()
    request.IfMatchRevision = CurrentWorkflow.IncidentRevision
    ApplySavedIncident ApiSend(request)
End Sub
```

The workspace is unbound and contains incident metadata plus field notes. It has Save Draft and Continue actions; a failed save stays visibly unsaved. My Reports calls only `/api/v1/reports`, does not use a local table, and opens only server-returned report IDs.

- [ ] **Step 4: Verify against the fictional API**

Run: `python -m pytest tests/unit/test_access_report_workflow_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: draft can be saved/resumed by the same fictional Officer, and another Officer’s report cannot be loaded.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_report_workflow_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add private report drafts and history"
```

### Task 5: Add AI report processing, review, and revision-safe editing

**Files:**
- Create: `access-client/src/modules/modAiJobs.bas`
- Create: `access-client/src/forms/frmReportReview.txt`
- Create: `access-client/src/forms/frmConflict.txt`
- Modify: `access-client/src/modules/modReports.bas`
- Create: `tests/unit/test_access_ai_job_contract.py`
- Modify: `tests/access/test_access_client_workflow.py`

**Consumes:** `/api/v1/incidents/{incident_id}/jobs/classify`, `extract`, `generate`, `/api/v1/jobs/{job_id}`, and Task 4 workflow state.

**Produces:** `SubmitGenerationJob()`, `PollJob(jobId As String)`, `SaveReportRevision()`, and `ShowRevisionConflict()`.

- [ ] **Step 1: Write failing job/conflict tests**

```python
def test_generation_uses_a_job_and_never_blocks_on_ai_response():
    source = read_module("modAiJobs")
    assert "/jobs/generate" in source
    assert "PollJob" in source


def test_revision_conflict_does_not_overwrite_server_report():
    result = fake_save_with_stale_revision()
    assert result.screen == "frmConflict"
    assert result.report_was_not_overwritten is True
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/unit/test_access_ai_job_contract.py tests/access/test_access_client_workflow.py -q`

Expected: FAIL because job submission and conflict display are absent.

- [ ] **Step 3: Implement asynchronous processing and revision saves**

```vb
Public Sub SubmitGenerationJob()
    Dim request As CApiRequest
    Set request = NewApiRequest("POST", GenerateJobPath(CurrentWorkflow.IncidentId))
    request.IdempotencyKey = NewUuid()
    BeginJobPolling ApiSend(request).JobId
End Sub
```

Poll at a bounded interval, show progress, and resume known unfinished jobs after reopening Access. Report saves include the report revision. A `409` conflict preserves editor text, fetches the current server revision, and opens `frmConflict`; it never retries a modifying request automatically.

- [ ] **Step 4: Run job and conflict tests**

Run: `python -m pytest tests/unit/test_access_ai_job_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: fictional job completes once, report review opens, and stale save displays a conflict without changing the server record.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_ai_job_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add report generation and revision safety"
```

### Task 6: Add session-only Policy Chat and account controls

**Files:**
- Create: `access-client/src/modules/modPolicy.bas`
- Create: `access-client/src/forms/frmPolicyChat.txt`
- Modify: `access-client/src/forms/frmAccount.txt`
- Modify: `access-client/src/modules/modAuth.bas`
- Create: `tests/unit/test_access_policy_contract.py`

**Consumes:** `/api/v1/policy/questions`, Task 2 session state, and Task 3 navigation.

**Produces:** `AskPolicy(question As String)`, `ClearPolicyConversation()`, and account change-PIN/logout actions.

- [ ] **Step 1: Write failing policy-session tests**

```python
def test_policy_history_is_memory_only_and_cleared_on_logout():
    source = read_module("modPolicy") + read_module("modAuth")
    assert "ClearPolicyConversation" in source
    assert "WriteAllText" not in source


def test_policy_answer_shows_citations_without_becoming_report_facts():
    result = fake_policy_question("What does policy say?")
    assert result.citations_visible is True
    assert result.report_state_changed is False
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/unit/test_access_policy_contract.py tests/access/test_access_client_workflow.py -q`

Expected: FAIL because the Policy Chat form/service do not exist.

- [ ] **Step 3: Implement session-only chat**

```vb
Public Sub AskPolicy(ByVal question As String)
    Dim response As CApiResponse
    Set response = ApiSend(PolicyQuestionRequest(question, CurrentConversation))
    CurrentConversation.Add response.Data
    Forms!frmPolicyChat!txtAnswer = response.Data("answer")
End Sub

Public Sub ClearPolicyConversation()
    Set CurrentConversation = New Collection
End Sub
```

Clear the in-memory conversation during Sign Out, Login failure, and application shutdown. Display answer/citations/source titles and a guidance notice; never append it to report notes automatically.

- [ ] **Step 4: Verify logout behavior**

Run: `python -m pytest tests/unit/test_access_policy_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: citations display for a fictional answer and reopening after Sign Out has no previous conversation.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_policy_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add session-only policy chat"
```

### Task 7: Build the Administrator Roster and account workflow

**Files:**
- Create: `access-client/src/modules/modAdmin.bas`
- Create: `access-client/src/forms/frmAdminRoster.txt`
- Create: `access-client/src/forms/frmAdminAccount.txt`
- Create: `access-client/src/forms/frmConfirmAction.txt`
- Create: `tests/unit/test_access_admin_roster_contract.py`
- Modify: `tests/access/test_access_client_workflow.py`

**Consumes:** `/api/v1/admin/staff`, `/api/v1/admin/accounts`, account update/reset/unlock/session routes, Task 3 `CanUseAdminCenter`, and Task 2 Admin profile.

**Produces:** `LoadAdminRoster()`, `CreateStaffAndAccount()`, `ResetAccountPin(accountId As String)`, `DeactivateAccount(accountId As String)`, and `RequireAdminStepUp()`.

- [ ] **Step 1: Write failing roster/admin authorization tests**

```python
def test_roster_form_has_no_existing_pin_display_control():
    form = read_form("frmAdminRoster")
    assert "txtExistingPin" not in form
    assert "txtTemporaryPinOnce" in form


def test_admin_account_actions_use_server_role_and_step_up():
    source = read_module("modAdmin")
    assert "/api/v1/admin/accounts" in source
    assert "RequireAdminStepUp" in source
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/unit/test_access_admin_roster_contract.py tests/access/test_access_client_workflow.py -q`

Expected: FAIL because the Admin Roster forms and service do not exist.

- [ ] **Step 3: Implement account administration**

```vb
Public Sub ResetAccountPin(ByVal accountId As String)
    Dim response As CApiResponse
    RequireAdminStepUp "reset_pin"
    Set response = ApiSend(AdminResetPinRequest(accountId))
    ShowTemporaryPinOnce response.Data("temporary_pin")
End Sub
```

The Admin chooses Officer or Admin only through the documented role field. Reset/deactivate/role change uses fresh server step-up where required. The one-time temporary PIN is cleared from the form after confirmation and never written to logs, recovery files, clipboard, or a local table.

- [ ] **Step 4: Verify fictional Admin and Officer behavior**

Run: `python -m pytest tests/unit/test_access_admin_roster_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: fictional Admin creates both roles and deactivates a fictional account; fictional Officer receives no Admin navigation and the fake API rejects manually attempted Admin requests.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_admin_roster_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add administrator roster management"
```

### Task 8: Build Administrator All Reports with attributable edits

**Files:**
- Create: `access-client/src/forms/frmAdminAllReports.txt`
- Create: `access-client/src/forms/frmAdminReportEditor.txt`
- Modify: `access-client/src/modules/modAdmin.bas`
- Create: `tests/unit/test_access_admin_reports_contract.py`
- Modify: `tests/access/test_access_client_workflow.py`

**Consumes:** `/api/v1/admin/reports`, `/api/v1/admin/reports/{report_id}`, `/revisions`, `/restore`, `/transfer`, Task 5 report editor services, and Task 7 Admin step-up.

**Produces:** `SearchAllReports()`, `OpenAdminReport(reportId As String)`, `SaveAdminReportRevision()`, and `ShowAdminAttributionBanner()`.

- [ ] **Step 1: Write failing report-oversight tests**

```python
def test_admin_editor_warns_that_the_report_belongs_to_another_employee():
    form = read_form("frmAdminReportEditor")
    assert "You are viewing/editing another employee's report" in form


def test_admin_save_uses_admin_endpoint_and_current_revision():
    source = read_module("modAdmin")
    assert '"/api/v1/admin/reports/"' in source
    assert "IfMatchRevision" in source
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/unit/test_access_admin_reports_contract.py tests/access/test_access_client_workflow.py -q`

Expected: FAIL because all-report search/editor forms do not exist.

- [ ] **Step 3: Implement search and revisioned admin edit**

```vb
Public Sub SaveAdminReportRevision()
    Dim request As CApiRequest
    ShowAdminAttributionBanner
    Set request = AdminSaveReportRequest(CurrentAdminReport)
    request.IdempotencyKey = NewUuid()
    request.IfMatchRevision = CurrentAdminReport.Revision
    ApplyAdminSavedReport ApiSend(request)
End Sub
```

Search uses server-side bounded filters only. Opening/saving goes through Admin routes; the form shows the persistent attribution banner and handles `409` with the same no-overwrite conflict path as Officer editing.

- [ ] **Step 4: Run fictional report attribution tests**

Run: `python -m pytest tests/unit/test_access_admin_reports_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: Admin sees two fictional Officers’ reports, admin save creates a new attributed revision in the fake API, and Officer history remains private.

- [ ] **Step 5: Commit**

```bash
git add access-client/src tests/unit/test_access_admin_reports_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "feat(access): add administrator report oversight"
```

### Task 9: Rebuild, accessibility-check, and verify Cloud Run test integration

**Files:**
- Modify: `access-client/src/manifest.json`
- Modify: `access-client/src/project.json`
- Modify: `access-client/README.md`
- Modify: `tests/access/test_access_client_workflow.py`
- Create: `tests/unit/test_access_accessibility_contract.py`

**Consumes:** Tasks 1 through 8 and existing `ImportAccessSource.ps1`, `ValidateAccessBuild.ps1`, and `BuildAccde.ps1`.

**Produces:** a source-matched test ACCDB, an unsigned test ACCDE, and evidence that fictional end-to-end Access workflow reaches the approved Cloud Run test environment.

- [ ] **Step 1: Write failing end-to-end/accessibility checks**

```python
def test_every_interactive_form_has_named_labels_and_logical_tab_order():
    for form in interactive_forms():
        assert "TabIndex" in form.text
        assert "AccessibleName" in form.text


def test_cloud_run_test_flow_uses_only_fictional_staff():
    result = run_access_cloud_test("FICT-1001", "fictional-pin")
    assert result.officer_report_visible is True
    assert result.admin_revision_visible is True
```

- [ ] **Step 2: Run tests and build validation**

Run: `python -m pytest tests/unit/test_access_accessibility_contract.py tests/access/test_access_client_workflow.py -q -m access_com`

Expected: FAIL until every new form has accessible labels, tab order, and fake/test-environment execution.

- [ ] **Step 3: Complete form metadata and acceptance harness**

Every interactive control gets an accessible label, visible keyboard focus, and a logical TabIndex. The test harness must reject a non-test API origin and must never use a production officer number, PIN, report, or policy question.

- [ ] **Step 4: Execute full client verification**

Run: `python -m pytest tests/unit/test_access_*.py tests/access/test_access_client_workflow.py -q; powershell.exe -NoProfile -File access-client/build/ImportAccessSource.ps1 -Source access-client/src -Database tests/output/access-client-final.accdb -Configuration Test; powershell.exe -NoProfile -File access-client/build/ValidateAccessBuild.ps1 -Database tests/output/access-client-final.accdb -Source access-client/src -Platform x64`

Expected: PASS with no local application tables, no forbidden VBA reference, no unmanifested Access object, and no secret/real-data fixture.

- [ ] **Step 5: Perform controlled manual test-ACCDE acceptance**

Run: `powershell.exe -NoProfile -File access-client/build/BuildAccde.ps1 -Database tests/output/access-client-final.accdb -Output tests/output/SLUT-Client-test-x64.accde -Platform x64 -ClientVersion 0.1.0-test`

Expected: native File → Save As → Make ACCDE creates the exact test artifact; reopen it read-only, sign in to the test API with fictional credentials, complete Officer and Admin workflows, and record only artifact hash/version/Access bitness.

- [ ] **Step 6: Commit**

```bash
git add access-client/src access-client/README.md tests/unit/test_access_accessibility_contract.py tests/access/test_access_client_workflow.py access-client/SLUT-Client.accdb
git commit -m "test(access): verify role-aware client workflow"
```

## Plan Self-Review

- The plan maps approved Sign In, Home, New Report, My Reports, Policy Chat, Roster, and All Reports screens to Tasks 2 through 8.
- Individual officer history, administrator-wide revisioned editing, temporary PIN behavior, and policy-chat clearance are tested explicitly.
- Every user-visible capability is backed by an existing `/api/v1` contract; the plan introduces no browser-login fallback or local Access data store.
- Task 9 blocks manual Cloud Run validation on a test-only origin and fictional credentials, preventing accidental production use.
- The task order preserves dependency flow: API transport, identity, navigation, employee reports, jobs/editor, policy, roster, admin reports, acceptance.
