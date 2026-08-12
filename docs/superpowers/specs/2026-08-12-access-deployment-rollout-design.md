# Access Deployment, Testing, and Rollout Design

**Date:** 2026-08-12<br>
**Status:** Design approved; written specification awaiting final user review<br>
**Parent:** [Access + Cloud Run Master Design](2026-08-12-access-cloud-run-master-design.md)<br>
**Depends on:** Cloud identity, report API, Access User client, and Access Admin
Center specifications

## Purpose

Define production infrastructure, Access packaging/signing/updating, environment
separation, testing, data migration, pilot operation, monitoring, backup and
recovery, general rollout, rollback, documentation, and joint Codex/Claude Code
delivery controls.

## Scope

- Test and production Google Cloud environments.
- Cloud SQL, Cloud Run API/worker, Cloud Tasks, load balancer, Cloud Armor,
  Secret Manager, storage, monitoring, backups, and recovery controls.
- Access workstation inventory, builds, digital signatures, trusted location,
  release manifest, update helper, rollback, and client compatibility policy.
- Database/roster migration and initial account enrollment.
- Automated, manual, security, load, backup, and disaster-recovery testing.
- Pilot, parallel operation, acceptance, general deployment, and legacy-web
  restriction.
- Operational ownership, runbooks, budgets, alerts, and change management.
- Complete Claude Code prompt-pack requirements and integration review gates.

## Non-goals

- An unattended mass rollout without agency IT approval.
- Production testing with real report/PIN data before security approval.
- Deleting or disabling the current website before Access acceptance.
- Treating backups as verified without restore exercises.
- Giving either AI coding tool standing permission to deploy, push, delete,
  modify production data, or handle credentials.
- Fixing the production Access version/bitness before inventory is collected.

## Environment topology

### Test

- Separate Cloud SQL database/instance, Cloud Run API/worker services, task
  queue, buckets, secrets, service accounts, hostname, and audit data.
- Uses fictional staff and incidents only.
- A separate test Discovery Engine data store is built from the same approved
  policy corpus. Test service identities do not query the production index.
- Test deployments may be automated from an approved non-main branch after
  checks pass.

### Production

- Managed HTTPS hostname behind Google HTTPS load balancer.
- Cloud Armor attached to the backend.
- Cloud Run API ingress restricted to load balancer/internal traffic.
- Private Cloud Run worker invoked by Cloud Tasks with OIDC.
- All production regional resources remain in `us-central1`, matching the
  existing deployment. Production Cloud SQL uses regional high availability
  with deletion protection, automated backups,
  point-in-time recovery, automatic storage increase, encrypted connections,
  and no public workstation access.
- Secret Manager and single-purpose least-privilege service identities.
- Private buckets with uniform access and lifecycle rules.
- Production deployment remains GitHub Actions + Workload Identity Federation;
  long-lived deployment keys are prohibited.

Infrastructure is codified in Terraform using the Google provider, exact
versions pinned in configuration and the dependency lock file, and protected
remote state in a dedicated versioned GCS bucket. CI separates `plan` from an
explicitly approved `apply`. Mixing ad-hoc console changes with Terraform
requires a recorded emergency exception and a subsequent reconciliation plan.

## Database migration strategy

- Alembic migrations are reviewed, tested against production-like volumes, and
  applied by a dedicated migration job before traffic depends on them.
- Schema evolution uses expand/migrate/contract:
  1. Add backward-compatible tables/columns/indexes.
  2. Deploy code that supports old and new shape.
  3. Backfill/validate in bounded batches.
  4. Raise the minimum client version only after rollout.
  5. Remove obsolete shape in a later release.
- Production rollback never assumes a destructive downgrade. The usual rollback
  is application revision rollback while the expanded schema remains.
- Every migration documents expected duration, locking risk, rollback, and
  verification query.

## Roster and account migration

1. Export and validate `templates/staff_roster.json`.
2. Normalize employee numbers case-insensitively and report duplicates,
   missing IDs, invalid shifts, and ambiguous names.
3. Correct source data through an administrator-approved mapping; the importer
   does not guess identities.
4. Import stable staff UUID records and compare counts/field checksums.
5. Create only explicitly approved Admin accounts initially.
6. Pilot administrators create or batch-enroll pilot User accounts with
   one-time temporary PINs.
7. General account activation follows an approved roster list and secure
   temporary-PIN communication procedure.

Normal historical reports are not currently stored centrally. Existing Word
files are not imported automatically. A later controlled import may attach
read-only legacy-document references after records-policy review.

## Access workstation inventory

Before building release artifacts, inventory every pilot/production workstation
class:

- Windows 11 edition/build and patch policy.
- Microsoft Access/Microsoft 365 exact version, update channel, and 32/64-bit.
- Installed Word version/bitness.
- Windows display scale and common resolution.
- Trust Center and macro policy.
- Ability for IT to configure a narrow local trusted location.
- Proxy/firewall/TLS inspection and required Google host allowlists.
- User permissions for `%LOCALAPPDATA%` recovery/token storage.
- Endpoint protection behavior for signed `.accde` and update helper.

Build/support matrices are derived from evidence. If both Access bitnesses are
present, release and test both. Unsupported outliers are remediated by IT or
explicitly excluded before rollout.

## Access release artifacts

Each release contains:

- Compiled `.accde` for each supported Access bitness/version combination.
- Signed update helper.
- Release manifest JSON with version, API version, minimum server/client
  compatibility, file names, sizes, SHA-256 hashes, Authenticode signer,
  release time, and source commit.
- Release notes and rollback notes.
- User guide and Admin quick-reference version.

The editable `.accdb`, signing private key, test fixtures, source exports, and
build intermediates are not in the user package.

The application and helper are Authenticode-signed with an organization-managed
code-signing certificate. Signing occurs in a restricted CI/signing workstation
or managed signing service. The private key is never stored in the repository or
given to Codex/Claude Code.

## Trusted location

Agency IT creates a narrow local directory, for example under Program Files or
another managed application folder, as the Access trusted location. The root
drive, entire user profile, Documents, Downloads, network shares, and removable
media are not trusted locations.

Users receive read/execute access. The signed updater receives the minimum
write privilege required to replace the release. DPAPI tokens and recovery
snapshots remain under the current user's LocalAppData, outside the application
directory.

## Client update design

### Startup policy

Access calls `/api/v1/client-policy` and verifies:

- Current API compatibility.
- Latest and minimum client versions.
- Release notes.
- Package URL or update channel metadata.
- Expected hash and signer.

An optional update shows a notice and deferral. A client below minimum becomes
read-only: it may authenticate, recover/view saved work, and export existing
revisions, but cannot create or modify data until updated.

### Update helper

The helper is a C# .NET 8 self-contained Windows executable. The baseline build
targets `win-x64`; if the workstation inventory contains Windows on ARM, a
separately signed `win-arm64` artifact must pass the same gates before those
devices enter the pilot. The signed helper:

1. Downloads over HTTPS to a temporary local path.
2. Verifies Authenticode trust and exact published SHA-256/size.
3. Verifies the manifest is signed or delivered from an authenticated protected
   endpoint.
4. Requests Access close while preserving/saving work.
5. Retains the immediately previous known-good release.
6. Atomically swaps the package.
7. Opens a validation mode that checks version, signature, source metadata, API
   reachability, and startup form.
8. Rolls back automatically if validation fails.
9. Records only safe local/update telemetry and request IDs.

The helper does not update Microsoft Access/Office itself.

## Automated quality gates

### Backend

- Formatting/lint/static checks already used by the repository.
- Complete credential-free pytest suite.
- PostgreSQL unit/integration tests and migration upgrade/rollback tests.
- OpenAPI schema/compatibility tests.
- Authorization matrix, session, revision, idempotency, audit, logging, and job
  tests.
- Existing policy/report evaluation and Word-template tests.
- Dependency and container vulnerability scans.
- Infrastructure validation/plan checks.

### Access

- Exported-source consistency check: binary Access source matches committed
  text exports.
- Compile all VBA with missing-reference detection.
- Static scan for forbidden secrets/URLs/logging patterns and 32/64-bit unsafe
  declarations.
- VBA unit/contract tests against fictional fake API fixtures.
- Automated Access COM smoke workflows on each supported build matrix runner.
- `.accde`, Authenticode signature, manifest hash, startup, update, and rollback
  verification.

### Cross-system

- OpenAPI examples consumed by Python and Access contract tests.
- Test-environment end-to-end flows for User and Admin.
- Network interruption, Cloud Run restart, job redelivery, database failover
  behavior, token revocation, and Access crash recovery.
- Load tests modeling expected employees, reports/day, AI requests, and admin
  searches with explicit cost ceilings.
- Sensitive-data scan over logs and error telemetry.

No production deployment proceeds while a required quality gate is failing.

## Manual acceptance scenarios

Using fictitious identities/incidents:

1. Create Admin and User; temporary PIN and first-use change.
2. Persist both roles, close Access, restore session, and verify Admin Center
   elevation has expired.
3. Create own report and a report for another officer.
4. Verify owner/preparer history on different workstations.
5. Interrupt network before/during save and recover after forced termination.
6. Cause a simultaneous-edit conflict and create a recovery revision.
7. Close Access during every AI job stage and resume later without duplicate
   model work.
8. Generate and inspect Word output against the official template.
9. Admin search/view/edit/restore/transfer/export and audit attribution.
10. PIN reset/deactivation/role change/session revocation.
11. Optional and required Access update plus automatic rollback.
12. Degrade each dependency and verify safe, truthful UI behavior.

Acceptance includes keyboard navigation, high contrast, display scaling, and
expected officer terminology.

## Backup and disaster recovery

### Controls

- Cloud SQL automated backups and point-in-time recovery enabled before pilot.
- Deletion protection and final-backup policy enabled.
- Scheduled logical exports to a separately protected bucket provide additional
  instance-deletion protection.
- Bucket configuration/template assets use versioning or controlled release
  artifacts.
- Infrastructure and OpenAPI/configuration source remain in Git.
- Audit and data retention inherit the approved agency schedule; indefinite
  retention is the initial fail-safe default.

### Recovery objectives

Required recovery targets:

- Report database recovery point objective: five minutes or less through PITR.
- Production service recovery time objective: four hours.
- Access client rollback: 30 minutes after a bad release is identified.

These are acceptance targets, not vendor guarantees. Load/restore tests must
demonstrate them or the documented targets are revised before production.

### Exercises

- Restore a backup/PITR into an isolated test instance before pilot.
- Verify schema, row counts, revisions, account/session revocation behavior, and
  representative report reads/exports.
- Repeat at least quarterly and after material database/backup changes.
- Record exercise time, achieved RPO/RTO, gaps, owner, and corrective actions.

## Monitoring, alerts, and budgets

Dashboards and alerts cover:

- API availability, latency, 4xx/5xx categories, and request volume.
- Authentication failures/lockouts and permission denials without PII.
- Database CPU, memory, storage, connections, backup/PITR status, and migration
  version.
- AI job queue depth/age, success/failure/latency, model usage, and idempotency
  conflict rates.
- Policy search health.
- Export failures.
- Access version distribution and upgrade-required events.
- Cloud spend budgets and anomaly alerts, particularly Cloud SQL and AI tokens.
- Sensitive-log detection failures.

Alerts identify a named response owner and link to a runbook. Raw report content
is excluded from alert payloads.

## Pilot and parallel operation

### Entry gates

- Approved specs and implementation plans.
- Focused/full automated gates green.
- Security review complete.
- Production-like backup restore successful.
- Workstation inventory/build compatibility complete.
- Roster import verified.
- User/Admin documentation and support contacts ready.

### Pilot

- Approximately 5–10 employees and 2 administrators.
- Two to four weeks of parallel Access and existing-web availability.
- Access uses the new individual system of record. The legacy web interface is
  marked as pilot fallback and must not create an independent ordinary-report
  history.
- Pilot uses controlled production authorization and real operational data only
  after agency approval and participant training.
- Feedback records usability issue, severity, application version, and request
  ID without copying sensitive report content into public GitHub issues.

### Exit gates

- No unresolved critical/high security or data-loss issue.
- All core acceptance scenarios completed by named pilot participants.
- Backup/recovery and rollback demonstrated.
- Support load and performance/cost within approved limits.
- Written business, IT/security, and records-management acceptance.

## General rollout and legacy website

Agency IT deploys the signed Access package/update helper to the approved local
trusted location. Accounts are activated in scheduled groups with temporary-PIN
instructions and training.

The existing website remains available as a controlled fallback until written
acceptance. Afterward:

- Shared-code ordinary report endpoints are disabled or restricted so they
  cannot bypass individual authorization or create unsaved parallel work.
- Health/operational endpoints and any approved Review Lab behavior remain as
  specifically configured.
- Immediate rollback can re-enable the last accepted client/backend revision;
  it does not resurrect insecure shared-code write access without an explicit
  incident decision.

## Release rollback

- Cloud Run retains the prior known-good revision with compatible schema.
- Access updater retains the prior signed `.accde`.
- Database changes use expansion so application rollback does not require
  destructive schema rollback.
- A rollback decision identifies whether to roll back client, API, worker, or
  all three and verifies version compatibility before reopening writes.
- Report/revision data created under a failed release is preserved and reviewed;
  rollback never deletes it automatically.

## Documentation and ownership

Before production, name:

- Business/system owner.
- Technical service owner/on-call contact.
- Access release/signing owner.
- Database backup/recovery owner.
- Account and roster administrators.
- Security/incident-response contact.
- Records-retention authority.

Required documents:

- User quick start and report workflow.
- Administrator account/report/audit guide.
- PIN reset and employee onboarding/offboarding procedure.
- Access deployment/update/rollback runbook.
- Cloud deployment/migration/rollback runbook.
- Backup restore and disaster-recovery runbook.
- AI/policy outage and general incident-response runbook.
- Data classification, retention, export, printing, and local-file rules.
- Change log and release acceptance record.

## Claude Code prompt pack

Implementation planning creates `docs/claude-prompts/README.md` plus one numbered
prompt per independently reviewable task. Prompts are ordered by dependency and
may be assigned to Claude Code or executed by Codex.

Every prompt contains:

1. Task ID, objective, user-visible outcome, and rationale.
2. Repository root and required `AGENTS.md`, design, plan, and interface files.
3. Expected branch/base commit and clean-worktree verification.
4. Exact allowed create/modify/test files and explicitly forbidden scope.
5. Consumed interfaces and exact produced signatures/schemas.
6. Test-first steps, commands, and expected initial failure/final success.
7. Security/privacy/logging constraints and fictional test-data requirement.
8. Explicit non-goals and no-unapproved-refactor rule.
9. Acceptance checklist mapped to the specification.
10. Required focused and regression verification.
11. Required commit message; one task produces one intentional commit unless the
    plan explicitly divides it.
12. Handoff report template: commit SHA, files, commands/results, behavior,
    assumptions, risks, blockers, and next-interface notes.
13. Stop conditions for requirement conflict, missing dependency, unexpected
    dirty files, credential need, production access, or destructive operation.
14. Prohibitions on deploy, push, merge, deletion, secret exposure, production
    data access, and concurrent modification without explicit authorization.

Codex/Claude Code task owners work serially on dependent files. A separate
review gate checks specification compliance and code quality before the next
dependent task starts. Failed review returns to the original task owner with
concrete findings.

## Acceptance criteria

1. Test and production infrastructure are isolated, reproducible, least-
   privileged, monitored, backed up, and free of workstation database access.
2. Production `.accde` and updater artifacts are signed, hash-verified,
   bitness-compatible, and installed only in a narrow IT-managed trusted
   location.
3. Required-client updates enforce read-only compatibility safely and rollback
   preserves the last known-good client.
4. Roster import produces stable, reviewed staff identities; account enrollment
   does not expose PINs.
5. Backend, Access, cross-system, security, load, migration, update, and manual
   acceptance gates pass with fictional data before operational use.
6. Backup/PITR restore and client/API rollback are demonstrated before pilot and
   repeated on schedule.
7. Pilot entry/exit criteria and written agency acceptance are satisfied before
   general rollout.
8. The legacy website remains a controlled fallback until acceptance and is
   later restricted so it cannot bypass the individual system of record.
9. Monitoring, budgets, alerts, runbooks, ownership, onboarding/offboarding, and
   incident procedures are operational before rollout.
10. The detailed implementation plan and Claude Code prompt pack make every
    task independently executable, testable, reviewable, and safe to hand off.
