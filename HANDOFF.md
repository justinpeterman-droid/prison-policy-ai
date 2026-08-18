# Current Handoff and External Gates

Last updated: 2026-08-18

This file lists actions that require repository-owner, Google Cloud, Microsoft Access, security, records, privacy, or operational approval. It is not a deployment script and does not override the release ledger in `docs/access-cloud-run-implementation-checklist.md`.

## Current repository state

- `main` contains the reviewed backend/PostgreSQL checkpoint.
- `integration/access-cloud-run-rp02` is the current Access/cloud release-candidate line and remains ahead of `main`.
- The approved unified Access + React architecture and five staged web tasks are recorded in `docs/architecture/unified-platform.md` and `docs/access-cloud-run-implementation-checklist.md`.
- W-01 release cleanup must pass its complete hosted checks and review before it is accepted into the release-candidate line.
- The legacy Flask browser application and shared access codes remain temporary migration surfaces. They are not the target identity model.

No item below should be treated as completed merely because code exists on an integration or feature branch.

## 1. Use the approved planning baseline

Review `docs/architecture/unified-platform.md` and the Web companion section of `docs/access-cloud-run-implementation-checklist.md` against the approved product decisions:

- one employee-number/PIN identity shared by Access and web;
- Administrator-created accounts from the approved roster;
- React + TypeScript web companion;
- Secure, HttpOnly browser sessions with CSRF protection;
- one authoritative `/api/v1` and PostgreSQL data model;
- full Officer and Administrator web parity;
- staged retirement, then removal, of `ACCESS_CODE`, `ADMIN_CODE`, and legacy Flask pages.

The planning baseline does not authorize implementation or deployment by itself. Each stage still requires its own tests and review.

## 2. Accept W-01 release cleanup

Accept W-01 only after all required checks and review are green. Its scope includes:

- bounded GitHub feedback submissions;
- deletion of route-owned temporary DOCX files while preserving caller-owned paths;
- retirement of stale backend-local deployment instructions;
- replacement of obsolete README and handoff material;
- a current unified-platform architecture document and web-companion ledger.

After W-01 is accepted into the release-candidate line, close issues #71 and #72 as completed. Close #69 as obsolete/not planned because the unsafe backend-local script no longer exists and controlled delivery belongs to OP-08.

## 3. Protect `main` before release consolidation

Repository-owner action is required. Configure branch rules for `main` before merging the Access/cloud candidate:

- require pull requests;
- require the approved Backend Quality, Unit Tests, and Container Security checks;
- require branches to be current before merge;
- prevent force pushes and deletion;
- restrict direct pushes;
- preserve required-review dismissal rules appropriate for the repository.

Record the exact required-check names after a successful current workflow run. Do not guess names from old documentation.

## 4. Complete OP-08 controlled delivery

The retired backend-local manual deploy path must not be restored. Source and container builds always begin at the repository root, but production deployment must wait for OP-08.

OP-08 must provide reviewed workflows for:

- test and production environment separation;
- protected GitHub environments and approvals;
- Workload Identity Federation rather than long-lived service-account keys;
- immutable image/release identification;
- migrations, roster import, initial-Admin bootstrap, service deployment, verification, rollback, and evidence capture;
- no uncontrolled traffic shift or production mutation from an ordinary push.

Until OP-08 passes review, use the repository for validation only; do not substitute an old manual command.

## 5. Supply and approve cloud prerequisites

The platform still needs organization-approved values and ownership for:

- Google Cloud test and production projects, billing, regions, quotas, and labels;
- domains, DNS, certificates, ingress, Cloud Armor, and workstation/browser access policy;
- remote-state bucket and environment initialization;
- database, application, worker, dispatcher, migration, rollback, roster, and first-Admin identities;
- Secret Manager values and named custodians;
- approved source roster and first-Admin enrollment/PIN delivery;
- backup, PITR, restore, rollback, monitoring, budget, and alert destinations;
- support ownership and incident escalation.

Use the Terraform, secret, migration, Admin-enrollment, edge-verification, and disaster-recovery runbooks under `docs/runbooks/`. Never place real secrets, roster data, report content, or production identifiers in Git.

## 6. Finish the Microsoft Access AC-01 external gates

The source/build harness is substantial but not release-ready. It still requires an approved Windows/Access matrix and controlled resolution of:

1. **Access COM shutdown:** a responsive `MSACCESS.EXE` instance can remain alive beyond the bounded shutdown wait. Do not fix this by killing unrelated Access processes or by extending the wait indefinitely.
2. **ACCDE creation:** verify the supported interactive Access workflow, exact artifact path, read-only reopen, Access version/channel/bitness, and artifact hash.
3. **Trust and endpoint controls:** document the approved Trusted Location, VBA-project access needed for the build machine, macro/signing policy, and endpoint-protection acceptance.
4. **Source reconstruction:** rerun export/import/validation from a fresh Windows clone with matching PowerShell and Access bitness.

See `access-client/README.md`. AC-02 and later client work should not claim release readiness while AC-01's load-bearing gates are open.

## 7. Approve policy, privacy, records, and support rules

Before a pilot, owners must approve:

- report ownership, revision, reopening, transfer, export, retention, and deletion policy;
- audit access, audit retention, and oversight responsibilities;
- policy-corpus source approval and update ownership;
- internet/browser use, personal-device expectations, shared-device warnings, session lifetime, and incident response;
- production roster handling and employee offboarding;
- support hours, escalation, training, and user communications;
- disaster-recovery objectives and evidence from a completed restore exercise.

The initial web design intentionally uses employee number + 4–8 character alphanumeric PIN without MFA. That decision makes rate limiting, lockout, secure cookies, CSRF protection, session revocation, no-store caching, Admin step-up, and monitoring mandatory acceptance controls.

## 8. Web-companion execution order

After the planning baseline and W-01 are accepted, implement the approved workstream in order:

1. **W-02 — Browser authentication/session adapter**
2. **W-03 — Officer React companion**
3. **W-04 — Administrator React companion**
4. **W-05 — Cross-client acceptance, cutover, and controlled release**

Each stage needs its own tests and review. Do not retire shared-code access until full Officer and Administrator parity, Access/web continuity, authorization-isolation, and rollback acceptance pass in the test environment.

## 9. Final release gates

A production release still requires all of the following:

- Gate A: architecture, data classification, and prerequisites approved;
- Gate B: backend and PostgreSQL acceptance remains green on the exact candidate;
- Gate C: test cloud infrastructure, security, backup, and delivery accepted;
- Gate D: signed Access and responsive web clients pass Windows, browser, mobile, accessibility, security, and support acceptance;
- Gate E: pilot, disaster recovery, rollback, training, records/privacy, and business approvals complete.

Only a reviewed release candidate that satisfies the persistent ledger may advance. A green feature PR, successful local command, or existing Cloud Run revision is not production approval.