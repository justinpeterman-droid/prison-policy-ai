# Access Client Screens and Workflow Design

## Goal

Turn the Microsoft Access client from a buildable shell into a usable employee
application backed by the existing Google Cloud Run API and Cloud SQL service.
Every officer has an individual account and a private report history. Authorized
administrators can manage accounts and view or edit every report with an
attributable revision history.

## Scope

This design covers the employee and administrator Access experiences:

- employee-number and PIN sign-in;
- first-use PIN change, sign-out, and account-aware navigation;
- a home dashboard;
- report draft, generation, review, submission, and personal history;
- session-only policy chat;
- administrator roster/account management;
- administrator-wide report review and revisioned editing.

It does not move authoritative data into Access, create a local report store,
or replace server-side authorization. The existing Cloud Run API remains the
only authority for accounts, permissions, drafts, reports, revisions, and
policy retrieval.

## Architecture

```text
Microsoft Access ACCDE
  -> HTTPS API requests with a signed-in session
Google HTTPS load balancer and Cloud Armor
  -> Cloud Run API
Cloud Run API
  -> Cloud SQL accounts, sessions, incidents, reports, revisions, and audit
  -> approved policy search and AI/report services
```

Access holds only the current in-memory session state and temporary screen
state. It does not persist readable PINs, policy-chat history, or report
records locally. Cloud Run derives the actor from the session for every request;
an Access control being hidden is never an authorization boundary.

## Roles

### Officer

- Signs in with employee number and PIN.
- Changes a temporary PIN on first use.
- Creates, saves, resumes, generates, reviews, and submits only their own
  reports.
- Sees only their own report history.
- Uses policy chat for the active sign-in session only.

### Administrator

An Administrator has all Officer capabilities plus:

- creates Officer and Administrator accounts;
- assigns employee number, role, and a temporary PIN;
- resets a PIN and deactivates an account without deleting its history;
- views and opens every report;
- edits any report through revisioned server-side save operations.

Administrator edits retain the original report and record the editor, time, and
resulting revision. A report is never silently overwritten.

## Screen Map

### Sign In

The opening screen contains employee number and PIN fields. A successful first
sign-in routes to Change PIN; a normal successful sign-in routes to Home. A
failed or expired session returns to Sign In with a clear, non-sensitive error.

### Home

The home dashboard shows the signed-in employee and provides:

- Start New Report;
- My Reports;
- Policy Chat;
- Account and Sign Out;
- Staff Roster and All Reports for Administrators only.

### Report Workspace

An Officer creates a report, writes field notes, saves a draft, requests report
generation, reviews the result, and submits it. Drafts and reports are centrally
stored under the signed-in account. A later sign-in on another approved work
computer can resume the draft.

### My Reports

Shows only reports the signed-in Officer is authorized to access, including
draft/submitted status and revision information.

### Policy Chat

Sends questions to the approved policy endpoint. Its conversation exists only
for the active Access session and clears on sign-out. It does not show or retain
another employee's chat history.

### Administrator Roster

Shows staff identity and account status. It supports account creation, role
selection, temporary-PIN issue/reset, and deactivation. It never exposes stored
PIN values after their one-time issuance.

### Administrator All Reports

Provides server-authorized report search and report opening across all staff.
Editing saves a new revision and displays a clear attribution/audit notice.

## Report and Session Flow

1. An employee signs in through Cloud Run using employee number and PIN.
2. Access obtains the current profile and role, then renders role-appropriate
   navigation.
3. A report draft is saved to Cloud SQL under the server-derived account.
4. Generation/review/submission calls retain the report's revision and reject a
   conflicting concurrent edit rather than overwriting it.
5. An Administrator can open and revise any report through the same server-side
   revision rules.
6. Sign out revokes or clears the current local session and clears policy-chat
   history.

## Failure Handling

- A network, Cloud Run, or authorization failure is shown clearly and does not
  claim that a draft/report was saved.
- An expired session returns the user to Sign In rather than retrying modifying
  actions without consent.
- An unavailable policy service shows an unavailable result without inventing an
  answer.
- A revision conflict reloads the latest server version and asks the user to
  review it before making another edit.

## Acceptance Criteria

1. Separate fictional Officer and Administrator accounts can sign in to the
   Access test client through the Cloud Run test environment.
2. An Officer can create, save, resume, generate, and submit a fictional report
   and sees it only in My Reports.
3. An Administrator can create both Officer and Administrator accounts, reset a
   PIN, deactivate an account, and view/edit the fictional report.
4. The server records a new attributed revision for the Administrator edit.
5. Policy chat works only while signed in and clears after sign-out.
6. A disconnected or rejected request cannot be mistaken for a successful save.
7. No real employee, inmate, incident, or policy-sensitive data is required for
   the implementation or acceptance tests.
