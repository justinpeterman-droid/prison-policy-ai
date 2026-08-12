# Access + Cloud Run Implementation Checklist

Last updated: 2026-08-12

This is the persistent progress ledger for the approved 42-task program. A
task is checked only after its exact commit exists, allowed paths and
whitespace pass, required tests pass (or an explicit external gate is
recorded), and independent specification and code-quality reviews pass.
Checked does not mean deployed or approved for production.

Status: `MERGED` is on GitHub main; `LOCAL` is reviewed on the integration
branch; `IN PROGRESS` is being implemented/reviewed; `BLOCKED` awaits a real
dependency or external approval.

## Safety and identity

- [x] 001 OP-01 — Retire unsafe automation. `MERGED`
- [x] 002 ID-01 — Database/Alembic foundation. `MERGED`
- [x] 003 ID-02 — Versioned API contract. `MERGED`
- [x] 004 ID-03 — Identity schema and roster import. `MERGED`
- [x] 005 ID-04 — PIN/account lockout lifecycle. `MERGED`
- [x] 006 ID-05 — Opaque rotating sessions. `MERGED`
- [x] 007 ID-06 — Bearer auth, audit, and idempotency. `MERGED`
- [x] 008 ID-07 — Admin identity APIs and step-up. `LOCAL b2b6578`
- [x] 009 ID-08 — Attributable Review Lab handoff. `LOCAL 9c047f2`

## Report backend

- [x] 010 RP-01 — Report persistence. `LOCAL 0e47067`; PostgreSQL isolation
  repair in progress after real database execution exposed test leakage.
- [x] 011 RP-02 — Schemas, provenance, audit, and atomic revisions. `LOCAL`
  commits `0d8e3b0..c050c9d`; final two-pass review ready, 526 passed/8 skipped
  before dedicated PostgreSQL became available.
- [ ] 012 RP-03 — Engine adapters, staff lookup, and incidents. `IN PROGRESS`
- [ ] 013 RP-04 — User report API.
- [ ] 014 RP-05 — Admin report API.
- [ ] 015 RP-06 — AI jobs/outbox.
- [ ] 016 RP-07 — Private worker/dispatcher.
- [ ] 017 RP-08 — Policy Expert API.
- [ ] 018 RP-09 — Word exports.
- [ ] 019 RP-10 — Reporting operations and legacy controls.

## Google Cloud and delivery infrastructure

- [x] 020 OP-02 — Terraform state bootstrap. `MERGED`
- [ ] 021 OP-03 — Private network, PostgreSQL 17, identities, secrets.
- [ ] 022 OP-04 — Serverless edge and storage.
- [ ] 023 OP-05 — Monitoring, backup, and budgets.
- [ ] 024 OP-06 — Migration, roster, and first-Admin jobs.
- [ ] 025 OP-07 — Quality and supply-chain gates.
- [ ] 026 OP-08 — Controlled delivery workflows.

## Microsoft Access employee client

- [ ] 027 AC-01 — Source/build harness.
- [ ] 028 AC-02 — API core.
- [ ] 029 AC-03 — Authentication and DPAPI persistence.
- [ ] 030 AC-04 — Shell and client policy.
- [ ] 031 AC-05 — Report workflow foundation.
- [ ] 032 AC-06 — AI job workflow.
- [ ] 033 AC-07 — Editor, recovery, and revisions.
- [ ] 034 AC-08 — History, policy, and account experience.
- [ ] 035 AC-09 — Word, accessibility, and Windows acceptance.

## Microsoft Access administrator client

- [ ] 036 AD-01 — Admin navigation and elevation.
- [ ] 037 AD-02 — Staff and accounts.
- [ ] 038 AD-03 — Report oversight/search/edit/export/reopen.
- [ ] 039 AD-04 — Audit and health.
- [ ] 040 AD-05 — Review Lab and Windows regression.

## Release and rollout

- [ ] 041 OP-09 — Signed Access release/updater.
- [ ] 042 OP-10 — Pilot, disaster recovery, and rollout.

## Integration and verification

- [x] Correct integration worktree created from reviewed GitHub main.
- [x] OP-02 + ID-07 + ID-08 + RP-01 + repaired RP-02 integrated in order.
- [x] Disposable localhost-only PostgreSQL 17 test database created with
  fictional credentials and no production data.
- [ ] PostgreSQL report migration/revision suite passes twice consecutively.
- [ ] Corrected integration branch pushed and merged to GitHub main.
- [ ] Full backend unit, contract, PostgreSQL integration, and migration
  lifecycle suites pass from integrated main.
- [ ] Backend tasks 012-019 complete and reviewed.
- [ ] Infrastructure tasks 021-026 complete and reviewed.
- [ ] Access tasks 027-035 complete on the approved Windows/Access matrix.
- [ ] Admin tasks 036-040 complete on the approved Windows/Access matrix.
- [ ] Signed release task 041 complete.
- [ ] Pilot/DR/rollout task 042 complete.

## External prerequisites

- [x] Dedicated local PostgreSQL 17 test database available.
- [ ] Google Cloud test/production projects, billing, regions, and IDs approved.
- [ ] GitHub protected environments and WIF approved/configured.
- [ ] Domains, DNS, certificates, ingress, and workstation access approved.
- [ ] Secret custodians and first-Admin approval/PIN delivery assigned.
- [ ] Approved production roster import separately authorized.
- [ ] Windows 11 and Access version/bitness matrix documented and available.
- [ ] Access trust/signing and endpoint-protection acceptance documented.
- [ ] Records, privacy, revision, export, audit, retention, and deletion policy
  approved.
- [ ] Backup/PITR/DR exercises pass.
- [ ] Budgets, quotas, monitoring, alerts, and support ownership approved.
- [ ] Pilot users/Admins selected and trained.
- [ ] Business, IT, security, records, privacy, and support approve rollout.

## Release gates

- [ ] Gate A — Architecture, contracts, classification, prerequisites approved.
- [ ] Gate B — Backend and PostgreSQL acceptance complete.
- [ ] Gate C — Test cloud infrastructure/security/backup/delivery accepted.
- [ ] Gate D — Signed Access clients pass Windows/accessibility/security/support.
- [ ] Gate E — Pilot, DR, rollback, training, and rollout approvals complete.
