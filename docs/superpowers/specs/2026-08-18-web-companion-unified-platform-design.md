# Web Companion + Unified Identity Design

## Goal

Make the web application a full-featured companion to the Microsoft Access client. Both clients use the same Cloud Run `/api/v1` platform, PostgreSQL data, individual employee accounts, authorization rules, report history, revisions, AI jobs, policy service, exports, and audit trail.

The finished web product replaces the current Flask browser UI. The old shared `ACCESS_CODE` and `ADMIN_CODE` paths remain only as a restricted, explicitly legacy fallback during a staged migration and are removed after the new web application passes full Officer and Administrator acceptance.

## Product decisions

These decisions are approved for this design:

- Web and Access use the same employee-number + PIN accounts.
- Administrators create accounts from the approved staff roster; there is no public self-registration.
- Shared-code retirement uses a staged cutover.
- The replacement web application ships full Officer and Administrator parity as one coordinated release.
- The web UI is independently web-native rather than a visual copy of Access.
- The frontend is React + TypeScript in `web-client/`.
- Flask/Cloud Run initially serves the compiled React application and remains the API host.
- Browser authentication uses a server-side browser-session adapter with Secure, HttpOnly, SameSite cookies and CSRF protection; React does not store bearer or renewal tokens.
- The web application may be used from any internet-connected device with valid credentials.
- Initial web authentication is employee number + PIN only; MFA is not part of this release.
- Preserve the current 4-8 character alphanumeric PIN contract.
- Administrators may view and edit every report; every edit is attributable and revisioned.
- Each report has one primary Officer owner. Other Officers cannot access it. Administrators can access it under server-side authorization.
- At cutover, the React application replaces the current Flask browser UI rather than keeping two permanent web applications.

## Architecture

```text
                          One authoritative platform
                                   |
                    Google HTTPS edge / Cloud Run
                                   |
                  +----------------+----------------+
                  |                                 |
           Microsoft Access                   React Web App
          employee # + PIN                   employee # + PIN
          bearer/device session              HttpOnly browser session
                  |                                 |
                  +----------------+----------------+
                                   |
                              /api/v1
                                   |
       +---------------------------+----------------------------+
       |              |              |             |            |
    Identity       Reports        AI jobs       Policy       Admin/Audit
       |              |              |             |            |
       +---------------------------+----------------------------+
                                   |
                              PostgreSQL
```

Cloud Run remains the only authority for authentication, authorization, account state, report ownership, report revisions, staff data, AI jobs, policy access, export eligibility, and administrative operations. Neither Access nor React may create a separate authorization model or authoritative report store.

## Identity and browser sessions

The existing identity service remains the source of truth. Employee-number/PIN validation, account lockout, roles, PIN changes, device sessions, renewal, revocation, logout-all, audit, and Admin step-up continue to use the existing identity domain code.

The web client does not receive long-lived identity credentials directly. A browser-auth adapter in Flask translates between browser-safe cookie sessions and the existing identity/session service:

1. React posts employee number, PIN, browser/device identifier, device label, and persistence choice to a same-origin browser-auth login route.
2. Flask invokes the existing identity login service.
3. Flask stores the resulting access and renewal credentials only in Secure, HttpOnly, SameSite cookies.
4. React receives the safe profile/session state but never receives the renewal credential.
5. Browser-auth middleware validates/renews credentials and establishes the same server-side actor used by `/api/v1` authorization.
6. State-changing browser requests require CSRF protection.
7. Logout, logout-all, account deactivation, PIN reset, and explicit session revocation invalidate the corresponding server-side session rather than merely deleting a browser cookie.

No report, roster, policy passage, audit record, PIN, access token, or renewal token is persisted in `localStorage`, IndexedDB, a service-worker cache, or another offline browser store. Ordinary browser HTTP caching of sensitive authenticated responses is disabled.

## Internet-access security model

The web application is intentionally usable from personal and remote devices. Facility-network location is therefore not an authorization boundary.

The initial release deliberately does not require MFA and retains the existing 4-8 alphanumeric PIN contract. Compensating controls are mandatory:

- existing employee/device/network login throttling and account lockout remain enabled;
- authentication and sensitive failures do not disclose whether an employee number exists;
- browser access and renewal credentials use HttpOnly cookies;
- modifying requests require CSRF validation;
- authenticated sensitive responses use no-store caching rules;
- sessions are named by device/browser and visible to the account owner;
- users can revoke individual sessions and sign out all sessions;
- account deactivation and Admin reset/revocation take effect across clients;
- sensitive Admin actions continue to require purpose-specific PIN step-up where the API requires it;
- audit attribution always comes from the server-derived actor;
- shared/public-device guidance is displayed at sign-in and account/session surfaces.

## Roles and authorization

### Officer

An Officer can:

- sign in, satisfy required first-login PIN change, change their PIN, sign out, and manage their sessions;
- create and save a report draft;
- resume their own draft from either Access or web;
- request AI generation and observe job state;
- review and revise their own report under revision/concurrency rules;
- submit/finalize their own report according to the existing API state machine;
- view/search their own report history;
- export their authorized reports;
- use the Policy Expert with citations.

An Officer cannot list, read, revise, export, or search another Officer's reports merely because the browser UI knows an identifier.

### Administrator

An Administrator has Officer capabilities plus server-authorized access to:

- staff roster and account management;
- create Officer or Administrator accounts from approved staff identities;
- issue/reset a temporary PIN and deactivate accounts;
- revoke user sessions where supported;
- search and open all reports;
- edit/reopen/restore/transfer reports through existing revisioned operations;
- bulk export where authorized;
- audit and operational health views;
- Review Lab/administrative review capabilities that remain approved for production.

Administrator report edits never overwrite history. The original owner remains attributable and every Admin change records the acting Administrator and resulting revision.

## Web application information architecture

The React UI is web-native and responsive. It does not mirror Access forms visually.

### Public/authentication

- Sign In
- Required PIN Change
- Authentication/error recovery

### Officer workspace

- Home dashboard: active drafts, recent reports, AI job status, quick Policy Expert entry
- New Report / Report Workspace
- My Reports
- Report Detail / Revision History
- Policy Expert
- Account & Sessions

### Administrator workspace

- Admin Overview
- Staff & Accounts
- All Reports
- Report Oversight / Revision Detail
- Audit
- System Health
- Review Lab entry where enabled

Responsive behavior must support desktop, tablet, and phone browsers. Mobile support is functional, not merely a squeezed desktop layout.

## Report workflow and cross-client continuity

The web application consumes the centralized report APIs rather than calling the old `/api/reports/classify`, `/extract`, `/generate`, or `/download` legacy endpoints.

A report created in Access is visible on the web to its owning Officer and Administrators. A report created on the web is visible in Access under the same rules. Both clients operate on the same report ID, current revision, provenance, AI job state, and audit history.

Revision conflicts fail closed. The web client presents the latest server revision and requires the user to review before attempting another edit; it never silently overwrites a newer Access or Admin change.

## Policy Expert

The React Policy Expert uses the authenticated `/api/v1` policy surface and preserves citation/grounding behavior. Conversation state may be maintained in browser memory for the active signed-in experience but is cleared on sign-out and is not used as policy evidence. It is not persisted as a separate long-term chat-history product in this release.

## Error handling

The UI must distinguish:

- validation errors;
- expired/revoked sessions;
- required PIN change;
- permission denial;
- revision conflicts;
- AI job pending/retry/failure states;
- policy-service unavailability;
- network/dependency failures.

A failed network or server request must never be rendered as a successful save, submission, account mutation, or Admin action. Retriable operations use the API's idempotency contract where required.

## Legacy staged cutover

### Stage 1 - coexistence

The existing Flask browser UI remains available only as a clearly labeled legacy fallback. Shared codes do not grant access to `/api/v1`, centralized report history, account administration, audit, health, or other identity-backed features.

### Stage 2 - full parity acceptance

Before cutover, fictional Officer and Administrator accounts must pass the complete web acceptance suite against a test environment, including cross-client Access/web report continuity.

### Stage 3 - cutover

React becomes the primary `/` application. Individual employee login is the only normal web authentication path. The old Flask pages, shared-code cookie gate, `ACCESS_CODE`, and `ADMIN_CODE` deployment secrets/configuration are removed rather than retained as a permanent backdoor.

Emergency recovery is handled through documented administrative/bootstrap procedures, not a universal shared credential.

## Repository cleanup and documentation

The release work must also resolve repository drift:

- treat `integration/access-cloud-run-rp02` as the current release-candidate line until its reviewed work is consolidated to `main`;
- protect `main` with PR/review/status-check rules through GitHub repository settings before production rollout;
- resolve valid open reliability/deployment issues before cutover, including root-source deployment, feedback request timeout, and temporary DOCX cleanup;
- close or supersede stale planning issues after their remaining requirements are captured in the current roadmap;
- rewrite `README.md` around the unified Access + web + `/api/v1` architecture;
- replace stale `HANDOFF.md` instructions with current external gates and rollout actions;
- keep the 42-task implementation ledger accurate and add a web-companion workstream rather than pretending the web parity work is already complete.

## Testing strategy

Testing is layered:

1. React unit/component tests for auth state, role navigation, report state, errors, and Admin workflows.
2. Browser-auth Flask tests for cookie flags, CSRF, renewal, revocation, no-store behavior, and safe failure responses.
3. Existing `/api/v1` unit/contract/PostgreSQL integration tests remain authoritative for backend authorization and persistence.
4. End-to-end browser tests cover Officer and Administrator workflows against fictional data.
5. Cross-client acceptance proves a report created/edited in one client is correctly visible in the other.
6. Security regression tests verify Officers cannot access another Officer's report by changing IDs and shared codes cannot reach identity-backed APIs during migration.
7. Cutover tests verify the old shared-code authentication path is absent after retirement.

## Acceptance criteria

The coordinated release is ready for cutover only when all of the following are true:

1. A fictional Officer can sign in to the web app with the same employee number and PIN used by Access and complete a required first-login PIN change.
2. The Officer can create, save, resume, generate, review, submit, search, and export their own fictional report from the web.
3. That report is visible in Access to the same Officer and preserves the same report/revision identity.
4. Another fictional Officer cannot access that report.
5. A fictional Administrator can create an account from the approved test roster, assign Officer/Admin role, issue/reset a temporary PIN, deactivate an account, and perform supported session controls.
6. The Administrator can search, open, edit, reopen/restore/transfer where supported, and export authorized reports; edits create attributable revisions.
7. Policy Expert works in the web app with citations and safe unavailable behavior.
8. Browser credentials are HttpOnly and no sensitive application data is intentionally persisted to browser offline storage.
9. CSRF, lockout/rate limits, session revocation, no-store caching, and Admin step-up tests pass.
10. The React UI is usable on supported desktop, tablet, and phone viewport classes.
11. The full backend unit, contract, PostgreSQL 17 integration, migration, security, container, and release gates pass on the consolidated candidate.
12. Shared-code access is restricted during the pilot and completely removed at final cutover.
13. `README.md`, `HANDOFF.md`, architecture/operations documentation, and the implementation ledger describe the system that is actually shipped.

## Explicit non-goals for this release

- MFA/passkeys/SMS authentication.
- Self-service public employee registration.
- Collaborative multi-Officer ownership of a report.
- Permanent legacy Flask UI.
- Separate web-only report or identity database.
- Offline report storage or offline editing.
- A native mobile application.
- Automatic submission into an external corrections records system.
