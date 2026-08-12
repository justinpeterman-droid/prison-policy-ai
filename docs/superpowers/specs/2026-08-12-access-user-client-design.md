# Access User Client Design

**Date:** 2026-08-12<br>
**Status:** Approved for implementation planning<br>
**Parent:** [Access + Cloud Run Master Design](2026-08-12-access-cloud-run-master-design.md)<br>
**Depends on:** [Cloud Identity Foundation](2026-08-12-cloud-identity-foundation-design.md),
[Report Storage and Access API](2026-08-12-report-storage-api-design.md)

## Purpose

Build the Microsoft Access Guided Workspace used by employees on agency-managed
Windows 11 workstations. The client provides secure sign-in, report creation,
multi-officer preparation, autosave/recovery, AI fact review, generated-report
editing, report history, revision recovery, Policy Expert access, and on-demand
Word export through the Cloud Run `/api/v1` contract.

## Scope

- Source-controlled Access/VBA project and repeatable `.accde` build.
- Guided Workspace shell and User navigation.
- Employee-number/PIN login and optional persistent session.
- Current-account profile and automatic reporting-officer selection.
- Six-step report workflow.
- My Reports and Reports I Prepared work queues.
- Report/revision viewer, comparison, restoration, and conflict recovery.
- Policy Expert with citations and bounded history.
- On-demand Word export.
- DPAPI renewal-token storage and encrypted crash-recovery snapshots.
- API compatibility/update notices and safe error presentation.
- Keyboard, display-scaling, and Windows 11 acceptance behavior.

## Non-goals

- Admin Center forms and administrator-only actions.
- Direct database, Gemini, Vertex AI, Cloud Storage, or Word-template access.
- General offline report creation or synchronization.
- Storing readable credentials in Access tables, VBA, registry, or files.
- Automatically filing, emailing, or approving a report.
- Reproducing the existing browser HTML/CSS inside an embedded browser control.
- Supporting non-Windows platforms.

## Distribution and source layout

Development uses `access-client/SLUT-Client.accdb`. Production receives only a
compiled, signed `SLUT-Client.accde`.

Source control includes a text representation:

```text
access-client/
  SLUT-Client.accdb
  src/
    modules/       exported .bas modules
    classes/       exported .cls classes
    forms/         Access SaveAsText form definitions
    reports/       Access SaveAsText report definitions, if any
    queries/       query definitions / SQL
    tables/        local schema manifest
    assets/        icons and approved static resources
  vendor/
    json/          pinned JSON parser source and license
  build/
    ExportAccessSource.ps1
    ImportAccessSource.ps1
    BuildAccde.ps1
    ValidateAccessBuild.ps1
  tests/
    vba/           VBA unit/contract test modules
    fixtures/      fictional JSON requests/responses
```

The binary `.accdb` is the editable master, while exported text enables review,
diffing, and deterministic reconstruction checks. Build scripts use Access COM
automation on a controlled Windows build workstation with Access installed.

All Win32 declarations use `PtrSafe` and `LongPtr` with `#If VBA7` / `#If
Win64` branches. The build produces and tests separate artifacts when the
production inventory contains both 32-bit and 64-bit Access.

## Client architecture

### Shell and navigation

`frmShell` is the startup form. It owns the navy/gold Guided Workspace frame,
role-aware left navigation, employee identity display, connection state, save
state, application version, and a main subform region.

User navigation:

- Home
- New Report
- My Reports
- Reports I Prepared
- Policy Expert
- Account

Admin navigation is added by the separate Admin Center workstream. The shell
does not treat hidden navigation as authorization.

### Focused VBA modules

- `modAppStartup`: startup sequencing, version check, and session restoration.
- `modAppState`: current immutable profile/session/navigation state.
- `modApiRoutes`: centralized `/api/v1` paths.
- `modApiClient`: HTTPS transport, headers, timeout, JSON, renewal, and safe
  retry behavior.
- `modAuth`: login, PIN change, logout, session renewal, and current profile.
- `modDpapi`: Windows-user-bound encryption/decryption.
- `modSessionStore`: encrypted renewal token and device ID lifecycle.
- `modRecovery`: encrypted draft snapshots, expiry, and recovery detection.
- `modReportWorkflow`: six-step state machine and API orchestration.
- `modAutosave`: dirty tracking, 60-second idle save, and save-state events.
- `modConflict`: 409 comparison/recovery behavior.
- `modJobs`: AI job submission, polling, resumption, and display stages.
- `modWordExport`: revision save requirement, download, hash metadata display,
  file choice, and optional Word launch.
- `modPolicyExpert`: bounded conversation state and citation presentation.
- `modErrors`: stable API error-code to user guidance mapping.
- `modClientPolicy`: latest/minimum version and read-only enforcement.
- `modSafeLog`: local diagnostics containing request IDs and categories but no
  report content, PINs, tokens, names, or employee numbers.

Transport and storage are accessed behind class interfaces so tests can inject
fake responses and in-memory stores.

### JSON handling

A pinned, reviewed, 64-bit-compatible VBA JSON parser is vendored with its
license. The application wraps it behind focused serializer functions and does
not let forms construct arbitrary JSON strings. Every response shape is
validated before form state changes.

## Startup and sign-in

1. Validate local build metadata and load the non-secret API base URL.
2. Load/create a random Access installation/device identifier.
3. Check for a DPAPI-encrypted renewal token for the current Windows user.
4. If present, call `/auth/renew` and open the dashboard on success.
5. If renewal is rejected/revoked, delete the local token and show login.
6. If no persistent token exists, show `frmLogin`.
7. After authentication, call `/me` and `/client-policy` before enabling work.
8. Check for encrypted recovery snapshots and unfinished cloud AI jobs.

`frmLogin` accepts employee number, 4–8-character PIN/passcode, and **Keep me
signed in on this Windows account** for either role. It never saves the PIN.
Temporary-PIN users are routed immediately to `frmChangePin` and cannot open
other screens until change succeeds.

The profile returned by `/me` supplies staff UUID, employee number for display,
name, rank, shift, role, and status. A local field cannot override that identity.

### Accepted client update handoff

Client policy remains the exact nine-field public safe response. It contains no
package selection, hash, signer, bucket credential, storage object path, signed
URL, or reusable download credential. Package selection occurs only after the
employee accepts the update.

When an employee explicitly accepts an available update, Access:

1. sends `POST /api/v1/client-updates/grants` with the live bearer session,
   `X-Client-Version`, `X-Request-ID`, `Idempotency-Key`, and a closed body with
   exactly `access_bitness` and `windows_architecture`; the fictional x64 example
   is `{"access_bitness":"x64","windows_architecture":"x64"}`;
2. retains the returned five-minute update grant in memory only;
3. creates a cryptographically random named-pipe name and launches the installed,
   trusted .NET updater with only that pipe name and the request ID as command-line
   arguments; and
4. sends one closed, length-prefixed UTF-8 JSON `UpdateRequest` of at most 64 KiB
   over the pipe after the helper creates it with .NET
   `PipeOptions.CurrentUserOnly`.

The first grant response is a closed object containing `update_grant`,
`expires_at`, `release_version`, `package_id`, `manifest_sha256`,
`manifest_size_bytes`, `signer_thumbprint`, and
`one_time_value_unavailable: false`. An identical idempotent replay returns the
same expiry and selected non-secret metadata with
`one_time_value_unavailable: true` and omits `update_grant`. The returned signer
thumbprint is descriptive grant-bound metadata, never a trust anchor; the helper
accepts a signature only under the preapproved managed-signing and Windows trust
policy and expected publisher identity.

Release-one `access_bitness` permits `x86` or `x64`; release-one
`windows_architecture` permits `x64` unless the OP-01 inventory explicitly
approves another architecture and the schema/tests are reviewed together.
Access derives these values from its real build/runtime, and the server rejects
every combination outside the approved support matrix before issuing a grant.

The update grant, bearer credential, report/person data, install paths, and other
sensitive values never enter command-line arguments, environment variables, the
registry, clipboard, disk, or logs. The helper accepts one connection and the
request is closed to exactly `schema_version`, `api_base_url`, `update_grant`,
`expires_at`, `release_version`, `package_id`, `manifest_sha256`,
`manifest_size_bytes`, `signer_thumbprint`, `access_bitness`,
`windows_architecture`, `current_client_version`, `install_path`, and
`request_id`. The helper derives only the fixed protected relative routes from
the validated HTTPS API origin; the request contains no person/report data.

Access also exposes a public COM-safe `ValidateRelease` test/validation hook. It
returns bounded JSON containing only version, source-commit, API-compatibility,
signature, and startup checks. It never returns a credential, URL query, bucket
or object path, user/profile path, employee identity, report content, or raw
exception.

## User dashboard

`frmDashboard` shows:

- Prominent **Start a new incident report** action.
- Owned report counts and recent records.
- Reports prepared for other officers.
- Current connection/API/AI status.
- Last successful synchronization time.
- Resumable drafts and unfinished AI jobs.
- Required/available application update notice.

The dashboard never downloads complete report content for all rows. It uses
bounded summaries and opens one authorized record on demand.

## Six-step report workflow

### Step 1: Officers

`frmIncidentOfficers` defaults the signed-in staff member as reporting officer.
The employee may search the active roster by name or employee number and add
one or more other reporting officers. The screen explains:

- The named officer owns their report.
- The signed-in employee is recorded as preparer when different.
- Both access the same canonical report.
- Every revision identifies its actual editor.

The server returns stable staff UUIDs and is authoritative for active status.

### Step 2: Field Notes

`frmFieldNotes` provides a large plain-text editor using the established term
**field notes**. It shows character bounds, connection/save state, incident ID,
and created-by identity. It does not run AI until the employee explicitly
continues. Startup validates the required integer
`field_notes_max_characters` from client policy, which is exactly `30000` in
release one, and stores it only in memory. `SetFieldNotes` consumes that
validated policy value, counts Unicode code points with valid UTF-16 surrogate
pairs counting as one and rejects unpaired surrogates, accepts 30,000, and
rejects 30,001 locally; the server repeats the same authoritative validation.

### Step 3: Review Facts

Access submits or resumes classification/extraction jobs and presents incident
type, suggested charges, persons, dates/times, locations, roster resolutions,
and provenance. AI suggestions are editable and require employee confirmation.
Charges are suggestions and are not applied automatically.

### Step 4: Missing Information

`frmGapReview` renders server-defined gap questions and acceptable answer
controls. The employee enters a fact, explicitly marks Unknown where allowed,
or returns to field notes. Blocking gaps prevent generation. The client cannot
hide or bypass a server blocking result.

### Step 5: Reports

`frmReportEditor` uses tabs for each reporting officer/report type. Text fields
remain editable. Switching tabs first copies control values into workflow state
and marks dirtiness so no tab loses edits.

The screen shows current revision, last editor/time, save state, validation
flags, and AI warnings. **Save Now**, Revision History, and Continue to Export
are available. Nothing files itself.

### Step 6: Export

The employee selects a saved report/revision and requests the official Word
document. Unsaved changes must save first. Access opens a Windows Save dialog,
writes the returned DOCX, and may open it in Word only after employee choice.
Export errors never mark the report unsaved or regenerate AI text.

## Owned and prepared work queues

`frmReportHistory` supports two fixed relationships:

- **My Reports**: current employee is owner/reporting officer.
- **Reports I Prepared**: current employee is preparer for another owner.

Filters include status, incident date, category, and updated date. Results are
paginated summaries. The same report ID can appear in one employee's owned list
and another's prepared list; it is one canonical record.

Statuses are In Progress, Completed, and Archived and never disable editing.

## Autosave and local recovery

- Form changes mark the workflow dirty but do not create a revision per
  keystroke.
- Sixty seconds after the last change, `modAutosave` initiates one save.
- Before sending, `modRecovery` serializes the bounded unsaved workflow state,
  DPAPI-encrypts it for the Windows user, and writes it atomically under
  `%LOCALAPPDATA%\StandardLogisticsUnitTools\Recovery`.
- After Cloud Run confirms the revision, the matching recovery file is removed.
- A failed save keeps controls and the encrypted recovery snapshot intact.
- Startup detects snapshots, fetches current cloud revision, and offers Recover,
  Compare, or Discard.
- A recovery against a newer server revision creates a separate recovery
  revision; it never silently overwrites.
- Orphaned snapshots older than seven days are listed once for explicit discard
  and then removed. No plaintext recovery file is written.

Visible states are Saved, Saving, Unsaved changes, Reconnecting, and Save
failed—work preserved.

## Simultaneous-edit conflict behavior

Every open report remembers its server revision. HTTP 409 leaves local controls
untouched and opens `frmRevisionConflict`, which shows:

- Local unsaved value.
- Current server value and editor/time.
- Changed field list.
- Open newest revision.
- Save local work as a recovery revision.

Automatic merging is excluded. The employee makes the choice explicitly.

## AI jobs

Access submits one idempotency key per intended action and stores the returned
job ID in workflow state/recovery. `frmJobProgress` displays queued, classifying,
extracting, validating, generating, disciplinary, completed, or failed stages.

Polling starts at two seconds and backs off to a maximum of ten seconds. Closing
Access does not cancel the cloud job. Startup queries known unfinished jobs and
offers to resume their incident workspace.

Buttons disable after submission until the server responds, but idempotency is
the authoritative duplicate protection.

## Policy Expert

`frmPolicyExpert` sends one question and at most the server-supported recent
history. It displays the answer, citations, source titles, and safe errors. It
clearly distinguishes policy guidance from an official decision and does not
save policy questions as report facts automatically.

Conversation history exists for the current session only in the first release
and is not part of employee report history.

## Account screen

`frmAccount` shows the signed-in profile, session persistence state, active
sessions/device labels, Change PIN, Sign out of this computer, and Sign out
everywhere. Employees cannot edit roster identity fields; an Admin must correct
them through the Admin Center.

## API and network behavior

- Use WinHTTP with modern TLS through Windows defaults and bounded timeouts.
- Login/save/list calls use focused timeouts; AI work uses jobs rather than one
  blocking HTTP request.
- On 401, the client performs one synchronized renewal and one request retry.
- It never recursively retries authentication or modifying requests.
- Retryable network/503 failures use bounded backoff for safe reads and
  idempotent operations.
- All requests include bearer token, client version, request ID correlation,
  and idempotency/revision headers where required.
- Access never displays raw stack traces or HTML gateway errors.

## Display and accessibility

- Guided Workspace uses corrections-professional navy/gold visuals and the
  established S-L-U-T brand.
- Minimum tested viewport is 1366×768 at Windows scaling from 100% through
  150%.
- Forms support keyboard navigation, logical tab order, visible focus,
  accessible labels, non-color-only state indicators, and high-contrast text.
- Destructive-looking actions use explicit confirmation and plain language.
- Long operations never freeze Access without feedback.

## Local security

- Renewal tokens and recovery snapshots use DPAPI current-user scope.
- Access tokens remain in memory.
- No PIN, token, report content, name, or employee number enters local
  diagnostics.
- Clipboard use is not automated.
- Local export is always employee-initiated and uses a chosen path.
- The application clears sensitive form state on logout.
- A compiled `.accde` and code signature deter modification; Cloud Run remains
  the real authorization boundary.

## Testing

### VBA unit and contract tests

- URL/header construction and response envelope validation.
- JSON serialization/parsing, Unicode, nulls, arrays, and bounds.
- Login, renewal, change PIN, logout, and profile state using fake transport.
- DPAPI round trip and rejection under a different test identity where the test
  environment supports it.
- Session-store corruption/revocation handling.
- Autosave timing, atomic recovery writes, expiry, and successful cleanup.
- Revision conflict and recovery-decision state machine.
- AI idempotency key/job polling/backoff/resume behavior.
- Stable error-code mapping and sensitive-log redaction.
- Update-grant request validation, one-time in-memory retention, employee cancel,
  fake-launcher behavior, random pipe naming, exact closed `UpdateRequest`
  serialization, 64 KiB rejection, and zero secret command-line/disk/log output.
- `ValidateRelease` returns only the approved safe JSON fields and fails closed on
  version, source, API, signature, or startup mismatch.

### Automated Access integration tests

A local fictional fake API implements the OpenAPI examples. Access COM
automation launches the `.accdb`/`.accde`, drives named public test hooks, and
verifies navigation and state transitions without Google credentials.

Tests cover temporary-PIN sign-in, persistent renewal, new incident, multiple
officers, field notes, fact/gap review, report tabs, autosave, history,
revisions, conflicts, Policy Expert display, Word download, logout, update
policy, accepted-update fake-launcher handoff, `ValidateRelease`, and recovery
after forced termination.

### Manual Windows acceptance

- Every Access version/bitness in the production inventory.
- Windows 11 at supported scaling and resolution.
- Keyboard-only use and high contrast.
- Real Cloud Run test environment with fictional scenarios.
- Word document opening/printing under agency policy.
- Network interruption, token revocation, app update, and rollback.

## Acceptance criteria

1. The signed-in employee is obtained from Cloud Run and auto-selected as the
   default reporting officer.
2. Either role can choose a DPAPI-protected persistent session without storing
   a PIN or readable token.
3. The approved Guided Workspace and six-step workflow function on every
   production Access build/bitness.
4. Preparing another officer's report creates and opens the canonical shared
   record and displays the ownership/preparer explanation.
5. Autosave creates cloud revisions; a failure preserves visible and encrypted
   recoverable work.
6. Simultaneous edits never silently overwrite and offer explicit recovery.
7. AI jobs show progress, survive closing Access, and resume without duplicate
   submissions.
8. Owned and prepared history show only server-authorized records.
9. Policy answers retain citations and never become report facts automatically.
10. Word output is requested from a saved revision and written only to an
    employee-chosen location.
11. No Google/database credential, PIN, bearer token, or plaintext recovery
    payload is stored in the Access project.
12. Exported text sources reconstruct and validate the `.accdb`, and the signed
    `.accde` passes automated and manual acceptance tests.
13. An accepted update obtains a five-minute server grant, keeps all credentials
    in memory, and hands one bounded request to the current-user-only updater pipe
    without exposing secrets through process or local persistence surfaces.
14. `ValidateRelease` is COM-safe, deterministic, and returns only the approved
    non-sensitive validation result.
