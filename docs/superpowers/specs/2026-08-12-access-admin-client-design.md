# Access Admin Center Design

**Date:** 2026-08-12<br>
**Status:** Design approved; written specification awaiting final user review<br>
**Parent:** [Access + Cloud Run Master Design](2026-08-12-access-cloud-run-master-design.md)<br>
**Depends on:** [Cloud Identity Foundation](2026-08-12-cloud-identity-foundation-design.md),
[Report Storage and Access API](2026-08-12-report-storage-api-design.md),
[Access User Client](2026-08-12-access-user-client-design.md)

## Purpose

Add a role-aware Admin Center to the Access Guided Workspace. Administrators
retain normal employee report features and gain controlled access to all
reports, account and roster management, PIN reset, session revocation, audit
history, system health, Review Lab access, and operational exports.

Cloud Run enforces every administrator permission. The Access interface makes
the administrator context and attribution visible but is not the security
boundary.

## Scope

- Administrator navigation and overview dashboard.
- Persistent Admin account sessions with timed Admin Center locking.
- PIN step-up for sensitive actions.
- Search/view/edit/restore/export access to all reports.
- Account creation, activation/deactivation, role changes, unlock, PIN reset,
  and session revocation.
- Staff roster creation/correction/status and account linking.
- Read-only audit viewer.
- System/API/AI/database/backup status summary.
- Access entry point for the existing Review Lab during pilot/evaluation.
- Administrative usability, authorization, audit, and Windows acceptance tests.

## Non-goals

- Giving administrators a way to erase reports, revisions, accounts, or audits.
- Showing an existing PIN.
- Allowing an administrator to edit their own authorization locally.
- Treating hidden Access controls as authorization.
- A database administration console or raw SQL access.
- Displaying secrets, stack traces, service-account details, or sensitive Cloud
  Logging content.
- Bulk changing report narratives.

## Navigation and role behavior

An Admin sees the normal Reporting area:

- Home
- New Report
- My Reports
- Reports I Prepared
- Policy Expert
- Account

The shell also shows Administration:

- Overview
- All Reports
- Accounts & Staff
- Audit Log
- System Health
- Review Lab

The role comes only from `/api/v1/me`. A User receives no Admin navigation and
Cloud Run denies manually constructed administrator requests.

## Persistent Admin sessions and elevation

Admin accounts may select **Keep me signed in on this Windows account** using
the same DPAPI-protected rotating renewal-token design as Users.

Persistence restores the account and ordinary reporting area. The Admin Center
has a separate in-memory elevation state:

- Entering the Admin Center requires PIN confirmation when no elevation exists
  or after 15 minutes without Admin activity.
- Valid PIN confirmation returns a 15-minute Admin Center elevation.
- Browsing Admin pages refreshes local activity but not a sensitive-action
  step-up token.
- PIN reset, role change, account deactivation/reactivation, account unlock,
  session revocation, report ownership transfer, revision restoration, and bulk
  export require a server-issued step-up token no older than five minutes.
- After expiry, the form preserves selections but prompts for PIN before
  submitting the protected action.
- Closing Access discards elevation and step-up tokens, even when the account
  session persists.

## Administrator overview

`frmAdminOverview` shows bounded summaries rather than full sensitive content:

- Active/deactivated/locked account counts.
- Reports updated during selected periods.
- Account conditions requiring attention.
- API, database, AI, policy search, job queue, and latest-backup status.
- Recent audit actions.
- Quick links to All Reports and Accounts & Staff.

Health uses a protected, sanitized backend endpoint. It reports Operational,
Degraded, or Unavailable and a request/time reference, not infrastructure
credentials or internal error text.

## All Reports

`frmAdminAllReports` supports server-side, paginated structured filters:

- Report/incident ID.
- Reporting officer or preparer.
- Incident and creation date ranges.
- Structured inmate name or ADC number.
- Incident category.
- Facility, location, and shift.
- Status.
- Last editor and modified date.

Opening another employee's record displays a persistent banner:

> You are viewing/editing another employee's report. Your access and every
> saved revision are attributed to your administrator account.

Opening, saving, restoring, transferring, changing status, and exporting create
administrator-specific audit actions. Search-result display alone is recorded
as a bounded search audit rather than one view event per row; opening a report
creates the record-level view event.

### Editing and revisions

The Admin report editor reuses the User report controls and conflict handling.
It does not have a hidden overwrite path. Each save creates an `admin_edit`
revision. Restoration creates a new revision referencing the historical source.

Ownership correction/transfer requires a five-minute step-up token, a selected
active roster target, a required reason, and explicit confirmation. It updates
access relationships transactionally and creates a revision/audit event.

Reports remain editable after Completed. Archive is reversible; permanent
delete is unavailable.

### Export

An Admin may export any permitted report revision. One-record export is audited.
Bulk export requires:

- Fresh five-minute step-up.
- Explicit structured filters.
- Bounded maximum record count.
- Reason text.
- A generated manifest listing report/revision IDs, hashes, actor, filter, and
  time.

The first production release caps one bulk operation at 100 documents. Larger
requests require multiple explicit operations and are monitored.

## Accounts & Staff

The interface uses one staff identity screen with an optional linked account.

### Staff management

Administrators can:

- Search by name or employee number.
- Create an active/inactive staff record.
- Correct rank, name, employee number, and shift.
- Activate/deactivate roster selection independently from account sign-in.
- Link an account to the stable staff UUID.

Changing employee number never creates a new identity. Duplicate normalized
employee numbers are rejected. Staff with report history cannot be deleted.

### Account creation

The administrator chooses an eligible staff record and User/Admin role. Cloud
Run generates one 8-character temporary PIN and returns it once. The form:

- Displays a warning that the value cannot be retrieved again.
- Offers Copy only through explicit administrator action.
- Clears the value when the confirmation closes.
- Never writes it to local diagnostics or recovery files.

### PIN reset

A fresh step-up token is required. Reset revokes all target sessions, returns a
new temporary PIN once, requires first-use change, and records actor/target.

### Status and role

- Account deactivation revokes sessions immediately and preserves history.
- Reactivation does not restore old sessions.
- Role changes revoke sessions and require fresh sign-in/renewal.
- Unlock clears current lock state but not audit history.
- The last active Admin cannot be demoted or deactivated.
- An administrator cannot bypass these rules by modifying the form payload.

### Sessions

Admins can view bounded device/session summaries for an account and revoke one
or all. Raw token hashes and network secrets are never returned.

## Audit Log

`frmAdminAudit` is read-only. Filters include time range, actor, action family,
target type/ID, and result. Results show:

- UTC and localized display time.
- Actor display identity and stable ID.
- Action code and safe description.
- Target type/ID.
- Success/denied/failed result.
- Request ID and client version.
- Approved safe detail fields.

No Access action updates or deletes audit rows. Exporting audit summaries
requires step-up and is itself audited. Full report text, PINs, and tokens never
appear.

## System Health

`frmAdminHealth` shows:

- Access version and compatibility state.
- API release/source commit and Cloud Run revision.
- Cloud SQL reachability and migration version.
- AI classification/extraction/generation availability summary.
- Policy search availability.
- Queue depth and oldest pending AI job age.
- Latest automated backup time and latest successful restore exercise date.
- Current degraded-service notices.

Health is diagnostic summary only. It cannot modify cloud services.

## Review Lab

The first Access release opens the existing browser Review Lab through a
short-lived one-time handoff rather than reimplementing its large editable UI.
An elevated Admin requests
`POST /api/v1/admin/review-lab-handoffs`. Cloud Run returns a single-use URL of
the form `https://<managed-host>/access-handoff#<one-time-token>` that expires
after 60 seconds. The fragment is never sent in the initial HTTP URL or referrer.
The landing page posts it once, removes it from browser history, receives an
HttpOnly/Secure/SameSite=Lax session tied to the individual Admin account, and
redirects to `/review-lab` without exposing a PIN, Access bearer/renewal token,
or shared Admin code. Issuance and redemption are audited; the browser session
expires after 30 minutes of inactivity.

Moving Review Lab fully into Access is a later parity enhancement and does not
block production report workflows.

## Confirmation and safe actions

Protected forms show the exact target and effect before submission. Examples:

- Deactivate employee: blocks sign-in; preserves reports.
- Reset PIN: revokes every saved session; returns one temporary value.
- Change role: revokes sessions and changes authorization.
- Restore revision: creates a new current revision; preserves later history.
- Transfer ownership: changes who sees the canonical report; records reason.

Buttons disable after one submission. The idempotency key remains the server
authority against double-clicks.

## Error and conflict behavior

- Expired elevation preserves form state and prompts for PIN.
- Authorization denial never falls back to User mode and retry the mutation.
- A report conflict uses the same compare/recovery UI as the User client.
- Account concurrency conflicts reload current status before another attempt.
- A lost temporary-PIN response requires another reset; no retrieval endpoint
  exists.
- Partial bulk-export failure produces a manifest of successful/failed IDs and
  never marks failed documents as exported.
- Health dependency failures show Degraded/Unavailable with request IDs.

## Testing

### Authorization matrix

- User cannot discover or invoke any Admin endpoint.
- Admin without elevation cannot open protected Admin data.
- Elevated Admin can use read operations.
- Sensitive mutations require a fresh step-up token and reject expired/wrong
  purpose tokens.
- Persistent Admin session survives restart while elevation does not.

### Account and roster tests

- Create account/temporary PIN/first-use change.
- Reset, unlock, deactivate/reactivate, role change, and session revocation.
- Last-active-admin protection.
- Stable staff UUID through employee-number correction.
- Duplicate normalized employee-number rejection.
- Staff-with-history cannot be deleted.
- Temporary PIN never enters diagnostics/recovery.

### Report oversight tests

- Search bounds/filter combinations and concealed data.
- Admin open/view audit.
- Admin edit creates attributed revision.
- Restore/transfer requires step-up/reason and preserves history.
- Conflict cannot overwrite another employee's save.
- Single and bounded bulk export metadata/audit/manifest behavior.

### Audit and health tests

- Audit filters, immutable UI, bounded safe fields, and export attribution.
- Health contract and safe degradation messages.
- No secret or sensitive content in displayed/logged diagnostics.

### Manual acceptance

- Administrator can switch between normal report work and Admin Center without
  role confusion.
- Elevation timeout and re-confirmation are understandable and preserve work.
- High-impact confirmations clearly identify target and outcome.
- Every production Access version/bitness and supported display scale.

## Acceptance criteria

1. Only a server-authenticated Admin can discover and use the Admin Center.
2. Admin accounts may persist, while Admin Center elevation and sensitive
   step-up expire exactly as specified.
3. Administrators can search, view, edit, restore, and export any report without
   a silent-overwrite path.
4. Administrator report access and edits are visibly and durably attributed.
5. Administrators can manage staff/accounts/PINs/roles/status/sessions without
   ever viewing an existing PIN or deleting history.
6. Last-active-admin, stable staff identity, duplicate employee number, and
   session-revocation rules are enforced by Cloud Run.
7. Audit history is useful, bounded, read-only, and free of PINs/tokens/report
   text.
8. Health shows actionable safe summaries without becoming an infrastructure
   control surface.
9. Bulk export is bounded, step-up protected, manifested, and audited.
10. User/Admin authorization, persistence, Windows compatibility, and security
    acceptance tests pass before pilot use.
