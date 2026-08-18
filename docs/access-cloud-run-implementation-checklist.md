# Access + Cloud Run Implementation Checklist

Last updated: 2026-08-18

This is the persistent progress ledger for the approved 42-task Access + Cloud
Run program and the additive five-task web-companion workstream. A task is
checked only after its exact commit exists, allowed paths and whitespace pass,
required tests pass (or an explicit external gate is recorded), and independent
specification and code-quality reviews pass. Checked does not mean deployed or
approved for production.

Status terms used by current entries:

- `MAIN` — present on GitHub `main`.
- `CANDIDATE` — reviewed/integrated on `integration/access-cloud-run-rp02`, but
  not yet on `main`.
- `IN PROGRESS` — being implemented or reviewed on a feature branch/PR.
- `BLOCKED` — waiting on a real dependency or external approval.

Historical commit references remain as evidence even where the status label has
been updated.

## Current release topology

- `main` is the reviewed backend/PostgreSQL checkpoint at `a333271`.
- `integration/access-cloud-run-rp02` is the current Access/cloud release
  candidate. On 2026-08-18 it was 114 commits ahead of `main` and 0 behind.
- Draft PR #84 contains the approved unified Microsoft Access + React
  architecture and implementation plans; it is documentation/planning only.
- Draft PR #85 contains W-01 release cleanup and documentation fixes.
- No current candidate is production-approved merely because its hosted checks
  pass.

## Safety and identity

- [x] 001 OP-01 — Retire unsafe automation. `MAIN`
- [x] 002 ID-01 — Database/Alembic foundation. `MAIN`
- [x] 003 ID-02 — Versioned API contract. `MAIN`
- [x] 004 ID-03 — Identity schema and roster import. `MAIN`
- [x] 005 ID-04 — PIN/account lockout lifecycle. `MAIN`
- [x] 006 ID-05 — Opaque rotating sessions. `MAIN`
- [x] 007 ID-06 — Bearer auth, audit, and idempotency. `MAIN`
- [x] 008 ID-07 — Admin identity APIs and step-up. `MAIN`; implementation
  reference `b2b6578`.
- [x] 009 ID-08 — Attributable Review Lab handoff. `MAIN`; implementation
  reference `9c047f2`.

## Report backend

- [x] 010 RP-01 — Report persistence. `MAIN`; implementation reference
  `0e47067` plus the later PostgreSQL isolation repair.
- [x] 011 RP-02 — Schemas, provenance, audit, and atomic revisions. `MAIN`;
  commits `0d8e3b0..c050c9d` and later review corrections.
- [x] 012 RP-03 — Engine adapters, staff lookup, and incidents. `MAIN`;
  commits `c8fbc32`, `972e499`, and `268983c`; final two-pass review READY,
  1,210 unit/contract tests and 82 PostgreSQL tests passed.
- [x] 013 RP-04 — User report API. `MAIN`; commits `a1ae719` and `577480d`;
  final independent review READY, 1,214 unit/contract tests and two PostgreSQL
  runs of 106 tests passed; fresh focused PostgreSQL verification passed 44
  tests.
- [x] 014 RP-05 — Admin report API. `MAIN`; commits `3954b92` and `e361eba`;
  final independent re-review READY, fresh focused PostgreSQL verification
  passed 53 tests.
- [x] 015 RP-06 — AI jobs/outbox. `MAIN`; commits `1ae8bca` and `4e682a7`;
  final independent re-review READY, fresh focused PostgreSQL verification
  passed 40 tests, and full PostgreSQL integration passed 170 tests with one
  existing opt-in skip.
- [x] 016 RP-07 — Private worker/dispatcher. `MAIN`; commits `98ef263` and
  `9c43b1b`; final independent re-review READY, fresh focused PostgreSQL
  verification passed 54 tests, and full PostgreSQL integration passed 189
  tests with one existing opt-in skip.
- [x] 017 RP-08 — Policy Expert API. `MAIN`; reviewed implementation `8b409d8`,
  integrated by merge `a129c54`. The authorized narrow shared-query
  reconciliation removes raw question logging and applies one 90-second
  deadline to credential, search, gate, and model calls. Focused policy/browser
  tests passed 156; credential-free focused run passed 20 with 30 expected
  PostgreSQL skips; full unit/contract passed 1,285 and PostgreSQL integration
  passed 189 with one existing opt-in skip.
- [x] 018 RP-09 — Word exports. `MAIN`; reviewed rebased implementation
  `00fbd78`, integrated by merge `7f6e243`. The rebase preserves RP-08
  hardening, sorts every ZIP member (including manifest), and suppresses the
  internal selection query's search audit so the bulk route writes only its
  route-specific audit. Required export/filler tests passed 75; full
  unit/contract passed 1,295 and PostgreSQL integration passed 244 with one
  existing opt-in skip.
- [x] 019 RP-10 — Reporting operations and legacy controls. `MAIN`;
  implementation `646a998`, integrated by merge `2390f14`. Adds the exact
  nine-field client policy, elevated safe overview/audit/health routes,
  fixed-column replayable audit CSV export, allowlisted operational telemetry,
  and explicit legacy pilot/restricted controls with a visible transient-history
  warning. Focused RP-10 tests passed 14; unit/contract passed 1,266 with 30
  expected skips; related PostgreSQL integration passed 39.

## Google Cloud and delivery infrastructure

- [x] 020 OP-02 — Terraform state bootstrap. `MAIN`
- [x] 021 OP-03 — Private network, PostgreSQL 17, identities, secrets.
  `CANDIDATE`; independently reviewed at `fc1159f`.
- [x] 022 OP-04 — Serverless edge and storage. `CANDIDATE`; independently
  reviewed at `0ce9d8d`.
- [x] 023 OP-05 — Monitoring, backup, and budgets. `CANDIDATE`; independently
  reviewed at `f5e8f24`.
- [x] 024 OP-06 — Migration, roster, and first-Admin jobs. `CANDIDATE`;
  reviewed and integrated at `00119a9`; live environment lifecycle gates remain
  external.
- [x] 025 OP-07 — Quality and supply-chain gates. `CANDIDATE`. The signed
  Anchore release-asset flow was corrected in `33cb8d2` (not unsigned OCI-image
  verification), and redaction narrowing was reviewed in `ecce737`.
  GitHub-hosted run `31760769637` at code commit `096796f` passed locked
  Ruff/mypy, unit, PostgreSQL integration, OpenAPI, redaction, Pages, and exact
  unfiltered pinned Checkov gates; paired Container Security run `31760769639`
  passed real `cosign verify-blob`/Rekor verification before Syft and Grype,
  plus SPDX binding and fixed-High/Critical scanning. The candidate is not on
  `main` and is not production-approved.
- [ ] 026 OP-08 — Controlled delivery workflows. `IN PROGRESS` only as an
  approved plan. The retired backend-local manual deployment path must not be
  restored.

## Web companion

This workstream is additive to the original 42 tasks; it does not renumber or
replace the Access, cloud, signed-release, or rollout program.

- [ ] W-01 — Release cleanup and current documentation. `IN PROGRESS` in draft
  PR #85. Scope: resolve #71/#72, retire obsolete #69 instructions, refresh
  README/HANDOFF, document the unified platform, and prepare current release
  evidence.
- [ ] W-02 — Secure browser authentication/session adapter. Planned after W-01:
  employee-number/PIN login through the existing identity service, Secure
  HttpOnly cookies, renewal, CSRF, no-store responses, and server-side
  revocation.
- [ ] W-03 — Officer React companion. Planned after W-02: responsive dashboard,
  report workspace, jobs, personal history/revisions, exports, Policy Expert,
  PIN/account/session controls, and cross-client continuity.
- [ ] W-04 — Administrator React companion. Planned after W-03: staff/accounts,
  Admin elevation and purpose-specific step-up, all-report oversight,
  attributable editing, restore/reopen/transfer, bulk export, audit, health, and
  Review Lab entry where approved.
- [ ] W-05 — Cross-client acceptance, cutover, and controlled release. Planned
  after W-04: Access/web parity, Officer isolation, responsive browser testing,
  React at `/`, removal of shared-code secrets and legacy Flask pages, rollback,
  documentation, and release evidence.

## Microsoft Access employee client

- [ ] 027 AC-01 — Source/build harness. `CANDIDATE` with complete importable
  export dependencies in `4ed0fcd`, checkout-stable pinned vendor bytes in
  `e18e1f8`, and canonical-form normalization in `4b265bd`. The export/form
  changes are independently reviewed; the candidate is not on `main`.
  Steps 1-7 and 9-10 complete. The editable master `SLUT-Client.accdb` holds
  frmShell, frmLogin, frmErrorDialog, macro AutoExec, and modules JsonConverter,
  TestAssert, TestRunner, all exported to text sources.
  Evidence on Access 16.0 build 20228 x64 with matching x64 PowerShell: a fresh
  Windows `core.autocrlf=true` clone passed all 5 source-layout tests;
  `ValidateAccessBuild.ps1` passed for x64 (bitness match, zero application
  tables, vendor hashes, no forbidden references, VBA compiles); full
  credential-free regression passed 1,247 with 30 skips; `git diff --check`
  clean; the commit contains exactly the 28 allowlisted paths. VBA-JSON v2.3.1
  is pinned at `1e49ba82`, verified by byte length and SHA-256.
  A trusted, ignored project-output reconstruction passed import, bounded waits
  for only its own Access processes, self-contained export, and logical
  manifest equality with rewritten in-root dependency paths.
  A later fresh rerun exposed an intermittent database-session shutdown defect:
  the exact responsive `MSACCESS.EXE` instance can remain alive beyond the
  120-second bounded wait. Explicit `UserControl` and VBE-child-release
  experiments did not repair it and were reverted; this needs a controlled
  Access-host lifecycle remedy, not a longer wait or process termination.
  Form canonicalization removes only Access export metadata proven volatile on
  import: `Checksum`, `NameMap`, and a repeated adjacent
  `NoSaveCTIWhenDisabled` property. The test copies the master before export, so
  it does not mutate the tracked `.accdb`; `access_com` is registered as a
  Windows-only pytest marker.
  Two load-bearing gates remain: controlled Access COM shutdown and ACCDE
  creation on the approved Access matrix. `SysCmd 603` returns without error and
  produces no file, and no supported COM alternative exists
  (`acCmdMakeMDEFile` only opens a dialog). AC-02 remains blocked until AC-01 is
  independently accepted and merged.
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
- [x] **PostgreSQL 17 is a hard floor for the test bed, not a preference.**
  RP-06's hardened `ai_jobs` CHECK constraint uses the jsonpath `.string()`
  method, which PostgreSQL 16 does not have. On PG16 every migration, and
  therefore the PostgreSQL integration suite, fails independently of feature
  correctness. Verify with `SHOW server_version` before trusting a red run.
- [x] PostgreSQL report migration/revision suite passed twice consecutively on a
  fresh PostgreSQL 17.10 instance: full Alembic upgrade -> downgrade -> upgrade,
  unit (1,273 passed), contract (23 passed), integration (253 passed / 1
  existing opt-in skip), and security (1 passed), repeated with identical
  results.
- [x] Backend tasks 012-019 merged to `main` and Gate B accepted.
- [x] Current Access/cloud candidate is based on `main` and was 0 commits behind
  on 2026-08-18.
- [ ] Current Access/cloud release candidate merged to `main`.
- [ ] Infrastructure task 026 complete and all infrastructure external gates
  accepted.
- [ ] Access tasks 027-035 complete on the approved Windows/Access matrix.
- [ ] Admin tasks 036-040 complete on the approved Windows/Access matrix.
- [ ] Web tasks W-01 through W-05 complete and accepted.
- [ ] Signed release task 041 complete.
- [ ] Pilot/DR/rollout task 042 complete.

## External prerequisites

- [x] Dedicated local PostgreSQL 17 test database available.
- [ ] Google Cloud test/production projects, billing, regions, and IDs approved.
- [ ] GitHub protected environments and WIF approved/configured.
- [ ] `main` branch protection and required checks configured.
- [ ] Domains, DNS, certificates, ingress, and workstation/browser access
  approved.
- [ ] Secret custodians and first-Admin approval/PIN delivery assigned.
- [ ] Approved production roster import separately authorized.
- [ ] Windows 11 and Access version/bitness matrix documented and available.
- [ ] Access trust/signing and endpoint-protection acceptance documented.
- [ ] Records, privacy, revision, export, audit, retention, and deletion policy
  approved.
- [ ] Internet/personal-device browser policy and support expectations approved.
- [ ] Backup/PITR/DR exercises pass.
- [ ] Budgets, quotas, monitoring, alerts, and support ownership approved.
- [ ] Pilot users/Admins selected and trained.
- [ ] Business, IT, security, records, privacy, and support approve rollout.

## Release gates

- [ ] Gate A — Architecture, contracts, classification, and prerequisites
  approved. Product architecture is approved in PR #84; external prerequisites
  remain open.
- [x] Gate B — Backend and PostgreSQL acceptance complete.
- [ ] Gate C — Test cloud infrastructure/security/backup/delivery accepted.
- [ ] Gate D — Signed Access and responsive web clients pass
  Windows/browser/mobile/accessibility/security/support acceptance.
- [ ] Gate E — Pilot, DR, rollback, training, records/privacy, and rollout
  approvals complete.
