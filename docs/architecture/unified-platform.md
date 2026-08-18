# Unified Access and Web Platform Architecture

Last updated: 2026-08-18

## Purpose and status

Prison Policy AI is becoming **one authoritative platform** used through two clients:

1. a Microsoft Access employee/Administrator client; and
2. a web-native React + TypeScript companion.

The backend, PostgreSQL model, Access source/build foundation, and cloud release-candidate work already exist. The React application and browser-session adapter are approved designs but are not yet shipped. This document distinguishes the shared platform boundary from the temporary legacy Flask browser pilot.

The approved web design is recorded in `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`; its staged implementation plans live under `docs/superpowers/plans/`. The persistent delivery state is recorded in `docs/access-cloud-run-implementation-checklist.md`.

## System boundary

```text
                              Internet / approved HTTPS edge
                                           |
                      +--------------------+--------------------+
                      |                                         |
            Microsoft Access client                 React web companion
           employee number + PIN                    employee number + PIN
              device bearer session                HttpOnly browser session
                      |                                         |
                      +--------------------+--------------------+
                                           |
                                     Cloud Run /api/v1
                                           |
        +------------------+---------------+---------------+------------------+
        |                  |                               |                  |
     Identity           Reporting                      AI jobs          Policy Expert
        |                  |                               |                  |
        +------------------+---------------+---------------+------------------+
                                           |
                                      PostgreSQL 17
                                           |
                            audit, revisions, jobs, sessions
```

Supporting Google Cloud services provide policy search/model calls, private task dispatch, secrets, storage, monitoring, backup, and edge controls. Terraform and reviewed delivery workflows define those resources; a client does not configure them.

## Authority model

Cloud Run and PostgreSQL are the only authority for:

- accounts, roles, PIN state, lockout, and session revocation;
- Officer/Admin authorization;
- report ownership and access;
- incidents, report drafts, revisions, provenance, and concurrency;
- AI job and outbox state;
- exports and export metadata;
- audit events and operational health;
- policy-query authorization and bounded request handling.

Every operation is protected by **server-side authorization**. An Access form, React route, disabled button, hidden navigation item, URL identifier, cookie, or client-side role value is never an authorization boundary.

Neither client maintains an independent identity database, report database, or durable permission model. A report has the same identifier, owner, revision history, and audit record regardless of which client opened it.

## Components

### `/api/v1`

The versioned Flask API is the common interface for Access and React. It contains:

- authentication, PIN change, renewal, logout, session listing, and revocation;
- Officer incidents and reports;
- durable AI-job submission and status;
- Policy Expert questions with citations;
- deterministic report export;
- Admin staff/accounts, report oversight, audit, and health;
- idempotency, request IDs, role checks, Admin elevation, and purpose-specific step-up.

`openapi/access-v1.yaml` is the contract. Client convenience behavior must not silently redefine it.

### PostgreSQL 17

PostgreSQL 17 stores identity, sessions, security records, staff, incidents, reports, revisions, jobs, outbox rows, exports, and audit data. PostgreSQL 17 is a hard floor because database constraints use jsonpath behavior that PostgreSQL 16 does not provide.

Alembic migrations are the schema authority. Cloud Run instances and clients do not create unmanaged application tables.

### Report engine

The report engine separates language-model work from deterministic controls:

```text
field notes
  -> classify
  -> schema-constrained extraction
  -> deterministic gap/invented-fact checks
  -> Officer-supplied missing information
  -> narrative generation from structured facts
  -> validation
  -> revisioned persistence
  -> deterministic DOCX export
```

Nullable facts, explicit supplement markers, attribution, and immutable revisions are trust controls, not presentation features.

### AI jobs and worker

Longer report operations use durable job and outbox records. The private worker claims work with database concurrency controls, rejects stale results rather than overwriting newer revisions, and returns safe stages/errors through the public API. Redelivery must be idempotent.

### Policy Expert

The Policy Expert performs bounded retrieval and answer generation with citations. Conversation history is request context, not policy evidence. Raw questions, answers, report text, or citation passages are not made durable merely for convenience.

## Client responsibilities

### Microsoft Access

Access provides an employee-focused Windows experience and uses the shared API. It may hold temporary screen state and protected session material required by the approved client design, but it does not become the durable report or authorization store.

The Access source/build harness must pass reconstruction, VBA/reference, bitness, trust, shutdown, ACCDE, signing, and Windows acceptance gates before release.

### React web companion

The planned React application provides a responsive, web-native Officer and Administrator experience. It is not a visual port of Access.

Browser authentication uses a same-origin Flask adapter:

- employee number and PIN are validated by the existing identity service;
- access and renewal credentials remain in Secure, HttpOnly, SameSite cookies;
- React does not store credentials in `localStorage` or IndexedDB;
- state-changing requests require CSRF protection;
- sensitive authenticated responses use no-store caching;
- session revocation, account deactivation, and logout invalidate server state.

The React client consumes the same `/api/v1` capabilities and authorization decisions as Access.

## Roles and report ownership

### Officer

An Officer can work on their own reports from either Access or web, view their history, submit AI jobs, export authorized revisions, manage their sessions, and use the Policy Expert. Changing an identifier in a request must never reveal another Officer's report.

### Administrator

An Administrator has Officer capabilities plus approved staff/account management, report search/oversight, revisioned editing, restore/reopen/transfer operations, bulk export, audit, health, and Review Lab access. Sensitive actions retain Admin elevation and purpose-specific step-up requirements.

Administrators can view and revise every authorized report, but they never erase authorship. Each edit creates a new attributed revision.

### Ownership

Each report has one primary Officer owner. Other Officers do not receive collaborative access in the initial design. Ownership transfer is an audited Admin operation; it is not client-side reassignment.

## Cross-client data flow

1. An employee signs in with the same account from Access or web.
2. The server derives the actor, role, session, and account state.
3. A draft is saved under the server-derived owner.
4. Either client can reopen the same draft and current revision.
5. AI jobs operate against an explicit base revision.
6. A conflicting save is rejected instead of silently overwriting another client.
7. Exports are generated from an explicit durable revision.
8. Every security-sensitive or report-changing operation is attributable in the audit trail.

## Legacy browser migration

The current Flask HTML pages use shared `ACCESS_CODE` / `ADMIN_CODE` gates and transient report flows. They are a migration fallback, not a third permanent client.

The staged cutover is:

1. **Coexistence:** legacy pages remain clearly labeled and cannot grant access to centralized identity-backed capabilities.
2. **Full parity acceptance:** fictional Officer/Admin workflows, authorization isolation, responsive web behavior, and Access/web continuity pass in the test environment.
3. **Cutover:** React becomes `/`; individual login is the normal browser entry; shared-code secrets, cookie gates, and legacy pages are removed.

Emergency recovery uses documented bootstrap and operational procedures, not a permanent universal credential.

## Security assumptions

The approved web design permits sign-in from internet-connected and personal devices and initially retains 4–8 character alphanumeric PINs without MFA. Therefore the following are mandatory controls:

- employee, device, and network login throttling;
- account lockout and safe credential errors;
- Secure/HttpOnly/SameSite cookies;
- CSRF validation;
- short access credentials and controlled renewal;
- named sessions, individual revocation, and logout-all;
- immediate deactivation/PIN-reset effects;
- no intentional offline caching of reports, roster, policy passages, or audit records;
- Admin elevation and purpose-specific step-up;
- audit attribution from the server-derived actor;
- monitoring, alerting, incident response, and shared-device guidance.

No client may weaken these controls because it is running on a facility workstation.

## Delivery and environments

Source and container builds start at the repository root. The retired backend-local deploy script must not return.

Production delivery remains controlled by OP-08 and later release tasks. Required boundaries include:

- isolated test and production environments;
- protected GitHub environments and explicit approvals;
- Workload Identity Federation instead of long-lived keys;
- immutable artifacts and provenance;
- migration/roster/Admin bootstrap ordering;
- deployment verification and rollback evidence;
- no production traffic change from an ordinary unreviewed push.

## Verification layers

- Python 3.12 and 3.14 unit tests
- OpenAPI contract tests
- PostgreSQL 17 integration and migration lifecycle tests
- security/redaction tests
- Terraform and supply-chain checks
- container build, runtime provenance, vulnerability scan, and SBOM
- Access reconstruction and approved Windows matrix
- React component and browser end-to-end tests
- cross-client Access/web acceptance
- pilot, backup/restore, rollback, accessibility, privacy, records, and support approval

A passing feature test does not replace a release gate.

## Planned web workstream

- **W-01:** release cleanup and current documentation
- **W-02:** secure browser authentication/session adapter
- **W-03:** Officer React companion
- **W-04:** Administrator React companion
- **W-05:** cross-client acceptance, cutover, and controlled release

These tasks are additive to the existing 42-task Access + Cloud Run program. They do not renumber or pretend to complete the Access, infrastructure, signed-release, or rollout work.