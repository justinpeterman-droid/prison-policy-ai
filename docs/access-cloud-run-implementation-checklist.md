# Access + Cloud Run Implementation Checklist

Last updated: 2026-08-13

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
- [x] 012 RP-03 — Engine adapters, staff lookup, and incidents. `LOCAL`
  commits `c8fbc32`, `972e499`, and `268983c`; final two-pass review READY,
  1,210 unit/contract tests and 82 PostgreSQL tests passed.
- [x] 013 RP-04 — User report API. `LOCAL`
  commits `a1ae719` and `577480d`; final independent review READY,
  1,214 unit/contract tests and two PostgreSQL runs of 106 tests passed;
  fresh focused PostgreSQL verification passed 44 tests.
- [x] 014 RP-05 — Admin report API. `LOCAL`
  commits `3954b92` and `e361eba`; PR #78 merged into
  `integration/access-cloud-run-rp02`; final independent re-review READY,
  fresh focused PostgreSQL verification passed 53 tests.
- [x] 015 RP-06 — AI jobs/outbox. `LOCAL`
  commits `1ae8bca` and `4e682a7`; final independent re-review READY,
  fresh focused PostgreSQL verification passed 40 tests, and full PostgreSQL
  integration passed 170 tests with one existing opt-in skip.
- [x] 016 RP-07 — Private worker/dispatcher. `LOCAL`
  commits `98ef263` and `9c43b1b`; final independent re-review READY,
  fresh focused PostgreSQL verification passed 54 tests, and full PostgreSQL
  integration passed 189 tests with one existing opt-in skip.
- [x] 017 RP-08 — Policy Expert API. `REVIEWED` implementation `8b409d8`,
  integrated by merge `a129c54`; independent re-review READY. The authorized
  narrow shared-query reconciliation removes raw question logging and applies
  one 90-second deadline to credential, search, gate, and model calls. Focused
  policy/browser tests passed 156; credential-free focused run passed 20 with
  30 expected PostgreSQL skips; full unit/contract passed 1,285 and PostgreSQL
  integration passed 189 with one existing opt-in skip (one time-sensitive
  Admin fixture retry passed in isolation).
- [x] 018 RP-09 — Word exports. `REVIEWED` rebased implementation `00fbd78`,
  integrated by merge `7f6e243`; independent re-review READY. The rebase
  preserves RP-08 hardening, sorts every ZIP member (including manifest), and
  suppresses the internal selection query's search audit so the bulk route
  writes only its route-specific audit. Required export/filler tests passed 75;
  full unit/contract passed 1,295 and PostgreSQL integration passed 244 with
  one existing opt-in skip.
- [x] 019 RP-10 — Reporting operations and legacy controls. `REVIEWED`
  implementation `646a998`, integrated by merge `2390f14`; independent
  re-review READY. Adds the exact nine-field client policy, elevated safe
  overview/audit/health routes, fixed-column replayable audit CSV export,
  allowlisted operational telemetry, and explicit legacy pilot/restricted
  controls with a visible transient-history warning. Focused RP-10 tests
  passed 14; unit/contract passed 1,266 with 30 expected skips; related
  PostgreSQL integration passed 39.

## Google Cloud and delivery infrastructure

- [x] 020 OP-02 — Terraform state bootstrap. `MERGED`
- [x] 021 OP-03 — Private network, PostgreSQL 17, identities, secrets. `MERGED` and independently reviewed at `fc1159f`.
- [x] 022 OP-04 — Serverless edge and storage. `MERGED` and independently reviewed at `0ce9d8d`.
- [x] 023 OP-05 — Monitoring, backup, and budgets. `MERGED` and independently reviewed at `f5e8f24`.
- [x] 024 OP-06 — Migration, roster, and first-Admin jobs. Reviewed and integrated at `00119a9`; local Docker and dedicated PostgreSQL lifecycle gates remain external.
- [ ] 025 OP-07 — Quality and supply-chain gates. `LOCAL` in release candidate
  `8069dc1`, with signed Anchore release-asset verification corrected in
  `33cb8d2` (not unsigned OCI-image verification), and reviewed redaction
  narrowing in `ecce737`. Focused release gates passed 21; locked Ruff/mypy,
  workflow-pin, Pages redaction, and the exact unfiltered pinned Checkov scan
  are green. A real local Docker build passed (nonroot plus health check), as
  did digest-pinned runtime pull, SPDX generation, generated/read-only SBOM
  binding validation, SBOM/SARIF redaction, and the fixed-High/Critical Grype
  scan. Do not mark complete until real `cosign verify-blob` reaches Rekor;
  the public Rekor endpoint currently fails locally with `SEC_E_LOGON_DENIED`.
- [ ] 026 OP-08 — Controlled delivery workflows.

## Microsoft Access employee client

- [x] 027 AC-01 - Source/build harness. `LOCAL` in the pushed release candidate
  `4b265bd`, with complete importable export dependencies in `6e1bb06` and
  checkout-stable pinned vendor bytes in `e18e1f8`. The current canonical-form
  update awaits its independent review; the candidate is not merged.
  Steps 1-7 and 9-10 complete. The editable master `SLUT-Client.accdb` holds
  frmShell, frmLogin, frmErrorDialog, macro AutoExec, and modules JsonConverter,
  TestAssert, TestRunner, all exported to text sources.
  Evidence on Access 16.0 build 20228 x64 with matching x64 PowerShell:
  a fresh Windows `core.autocrlf=true` clone passed all 5 source-layout tests;
  `ValidateAccessBuild.ps1`
  OK for x64 (bitness match, zero application tables, vendor hashes, no forbidden
  references, VBA compiles); full credential-free regression 1,247 passed /
  30 skipped; `git diff --check` clean; the commit contains exactly the 28
  allowlisted paths and no others. VBA-JSON v2.3.1 pinned at `1e49ba82`, verified
  by byte length and SHA-256; `Export-AccessSource` writes every required
  import dependency while preserving the vendor pin.
  A trusted, ignored project-output reconstruction now passes import, bounded
  waits for only its own Access processes (never terminating one), self-contained
  export, and logical manifest equality with rewritten in-root dependency paths.
  Form canonicalization removes only Access
  export metadata proven to be volatile on import: `Checksum`, `NameMap`, and a
  repeated adjacent `NoSaveCTIWhenDisabled` property. The test copies the master
  before export, so it does not mutate the tracked `.accdb`; `access_com` is
  registered as a Windows-only pytest marker.
  TASK COMPLETION DOES NOT MEAN MERGED. One external gate remains open: ACCDE
  creation is UNPROVEN on this Access build - `SysCmd 603` returns
  without error and produces no file, and no supported COM alternative exists
  (`acCmdMakeMDEFile` only opens a dialog), so this matrix row is stopped per plan;
  AC-02 is BLOCKED until this task is independently reviewed and merged, per its
  own stated precondition.
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
  method, which PostgreSQL 16 does not have, so on PG16 every migration — and
  therefore the whole PostgreSQL integration suite — fails on the integration
  branch itself, independent of any feature branch. A PG16 test bed reports a
  false failure, not a real one. Verify with `SHOW server_version` before
  trusting a red integration run.
- [x] PostgreSQL report migration/revision suite passes twice consecutively.
  Verified on a fresh PostgreSQL 17.10 instance (port 5433, disposable
  `app`/`access_test` fictional local credentials): full alembic
  upgrade -> downgrade -> upgrade lifecycle clean, then unit (1,273 passed),
  contract (23 passed), integration (253 passed / 1 existing opt-in skip),
  and security (1 passed) suites run twice consecutively with identical
  results both times.
- [x] Corrected integration branch pushed and merged to GitHub main.
- [x] Full backend unit, contract, PostgreSQL integration, and migration
  lifecycle suites pass from integrated main. Same verification as above,
  run from `integration/access-cloud-run-rp02` immediately prior to the
  merge into `main`.
- [x] Backend tasks 012-019 complete and reviewed.
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
- [x] Gate B — Backend and PostgreSQL acceptance complete.
- [ ] Gate C — Test cloud infrastructure/security/backup/delivery accepted.
- [ ] Gate D — Signed Access clients pass Windows/accessibility/security/support.
- [ ] Gate E — Pilot, DR, rollback, training, and rollout approvals complete.
