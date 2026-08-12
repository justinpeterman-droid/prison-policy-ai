# Access + Cloud Run Program Execution Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved Microsoft Access client and centralized Cloud Run system without replacing the existing report, policy-search, validation, or Word-template engines.

**Architecture:** The existing Flask application gains a versioned `/api/v1` boundary, PostgreSQL persistence, individual authentication, immutable report revisions, and private background workers. A rebuildable Microsoft Access client consumes only that API; Terraform, GitHub Actions, signed release tooling, and operational runbooks provide isolated test and production delivery.

**Tech Stack:** Python 3.14 container and Python 3.12/3.14 CI, Flask 3, SQLAlchemy 2.0.51, Alembic 1.18.5, Psycopg 3.3.4, Pydantic 2.13.4, Argon2-cffi 25.1.0, PostgreSQL 17, Google Cloud Run/Cloud SQL/Cloud Tasks/Secret Manager/Cloud Armor, Terraform 1.15.8 with Google provider 7.40.0, Microsoft Access/VBA7, WinHTTP, Windows DPAPI, PowerShell, and a .NET 8 self-contained updater.

## Global Constraints

- Windows clients are agency-managed Windows 11 workstations with Microsoft Access already installed.
- The existing Flask report pipeline, Policy Expert citation behavior, validation rules, anti-fabrication controls, and `templates/005_template_v3.docx` remain the behavioral baseline.
- Access never connects directly to PostgreSQL, Vertex AI, Discovery Engine, Cloud Storage, Secret Manager, or Cloud Tasks.
- `/api/v1` uses individual bearer authentication; legacy shared-code browser cookies never authenticate `/api/v1`.
- All database and API timestamps are UTC; all public identities are server-generated UUIDs.
- Employee numbers are normalized case-insensitively but remain display identifiers, not secrets.
- PINs contain only ASCII letters and digits, preserve leading zeroes, are 4–8 characters, and compare case-insensitively after uppercase normalization.
- PIN hashes use Argon2id with 64 MiB memory, three iterations, parallelism 1, a 16-byte salt, and a 32-byte hash; one verification must benchmark below 500 ms on the selected Cloud Run minimum instance.
- Access tokens last 15 minutes. Nonpersistent renewal tokens remain in memory and expire within 12 hours. Persistent renewal tokens are DPAPI-protected and expire after 30 days of inactivity.
- Admin Center elevation expires after 15 minutes of inactivity. Sensitive Admin step-up grants expire after five minutes and are purpose-scoped.
- Every successful content change creates an immutable, attributable revision. Completed and Archived are organizational statuses and never permanently lock editing.
- Owner and preparer access the same canonical report; no copied report is created for collaboration.
- All modifying and AI-submission requests use idempotency keys. Revisioned writes require a base revision and return `409 revision_conflict` rather than overwriting.
- Report AI work uses durable Cloud Tasks jobs. Policy Expert remains synchronous with a 90-second timeout in release 1.
- Word documents are generated from an explicit saved revision, streamed, hashed, audited, and not retained centrally.
- Production regional resources are in `us-central1`. Production PostgreSQL is Cloud SQL PostgreSQL 17 with regional high availability, private IP, deletion protection, automated backups, and point-in-time recovery.
- Test and production use separate projects or equivalently isolated resources, identities, databases, queues, buckets, secrets, hostnames, audit data, and Discovery Engine data stores. Production data is prohibited in test.
- Terraform CLI is pinned to `1.15.8`; `hashicorp/google` is pinned to `7.40.0`; `.terraform.lock.hcl` is committed with Linux and Windows AMD64 hashes.
- VBA declarations use `PtrSafe` and `LongPtr` with `#If VBA7` and `#If Win64` where pointer width matters.
- VBA-JSON is vendored from tag `v2.3.1`, commit `1e49ba826b979d1851029dc965ecb6a3ead2a32c`. `JsonConverter.bas` SHA-256 is `1C240AA3C7EF536C25BF44061B02B0FADEB39BFB449F67C419822650E23F6169`; `LICENSE` SHA-256 is `F902104A3E36DAEA3A33F7ADFCD25C5AC69791E9164B83A81B8D0B235728C9BD`.
- Every automated test uses fictional identities and incidents. PINs, tokens, field notes, reports, names, employee numbers, and inmate identifiers never enter logs, diagnostics, alerts, or public issues.
- Codex and Claude Code may edit and test local/test-scope code only. They must not deploy, push, merge, delete resources/data, access production data, handle signing keys, or change secrets without separate explicit authorization.
- One task produces one focused commit and passes an independent specification-compliance and code-quality review before a dependent task begins.

---

## Approved Specifications

- `docs/superpowers/specs/2026-08-12-access-cloud-run-master-design.md`
- `docs/superpowers/specs/2026-08-12-cloud-identity-foundation-design.md`
- `docs/superpowers/specs/2026-08-12-report-storage-api-design.md`
- `docs/superpowers/specs/2026-08-12-access-user-client-design.md`
- `docs/superpowers/specs/2026-08-12-access-admin-client-design.md`
- `docs/superpowers/specs/2026-08-12-access-deployment-rollout-design.md`

## Detailed Plans

- `docs/superpowers/plans/2026-08-12-cloud-identity-foundation-implementation.md`
- `docs/superpowers/plans/2026-08-12-report-storage-api-implementation.md`
- `docs/superpowers/plans/2026-08-12-access-user-client-implementation.md`
- `docs/superpowers/plans/2026-08-12-access-admin-client-implementation.md`
- `docs/superpowers/plans/2026-08-12-access-deployment-rollout-implementation.md`

## Locked Repository Structure

```text
backend/
  build_info.py
  identity/
    __init__.py
    config.py
    normalization.py
    pins.py
    tokens.py
    accounts.py
    sessions.py
    audit.py
    idempotency.py
    rate_limits.py
    elevation.py
    browser_handoffs.py
    roster_import.py
  persistence/
    __init__.py
    base.py
    database.py
    models/
      identity.py
      sessions.py
      security.py
      reporting.py
      jobs.py
  reports/
    service.py
    persistence.py
    policy.py
    revisions.py
    provenance.py
    export_service.py
    deterministic_docx.py
  jobs/
    __init__.py
    service.py
    outbox.py
    dispatcher.py
  worker/
    __init__.py
    app.py
    routes.py
  webapp/api_v1/
    __init__.py
    context.py
    responses.py
    errors.py
    pagination.py
    middleware.py
    auth.py
    admin.py
    admin_reports.py
    admin_audit.py
    admin_health.py
    staff.py
    incidents.py
    reports.py
    jobs.py
    policy.py
    client_policy.py
    schemas/
      __init__.py
      reporting.py
  webapp/routes/
    browser_handoffs.py
migrations/
  env.py
  script.py.mako
  versions/
openapi/
  access-v1.yaml
scripts/
  dispatch_outbox.py
  import_roster_to_postgres.py
tests/
  unit/
  integration/
  contract/
  security/
  support/
  fixtures/access_api/
access-client/
  SLUT-Client.accdb
  src/
    modules/
    classes/
    forms/
    reports/
    queries/
    tables/
    assets/
  vendor/json/
  build/
  tests/
    vba/
    fixtures/
    automation/
access-updater/
  SLUT.AccessUpdater.sln
  src/SLUT.AccessUpdater/
  tests/SLUT.AccessUpdater.Tests/
infra/terraform/
  bootstrap/state/
  modules/access_platform/
  environments/
    test/
    production/
  tests/
infra/monitoring/dashboards/
release/
scripts/release/
docs/
  claude-prompts/
  operations/
  runbooks/
  user-guides/
```

## Shared Python Interfaces

The subsystem plans may add fields but must not rename these contracts without updating every consumer and the OpenAPI bundle in the same reviewed task.

- `Actor(account_id: UUID, staff_member_id: UUID, session_id: UUID, role: Literal["user", "admin"], auth_version: int, must_change_pin: bool)` is an immutable dataclass attached to Flask request context.
- `ApiError.__init__(self, code: str, message: str, *, status: int, retryable: bool = False, details: dict[str, object] | None = None) -> None` is the only exception translated into an intentional `/api/v1` client error.
- `init_database(settings: IdentitySettings) -> None` and `session_scope() -> Iterator[Session]` own SQLAlchemy lifecycle and commit/rollback behavior.
- `success(data: object, status: int = 200) -> Response` and `failure(code: str, message: str, status: int, retryable: bool = False, details: dict[str, object] | None = None) -> Response` own the envelope.
- `require_access_token(view: Callable) -> Callable`, `require_role(role: str) -> Callable`, `require_admin_elevation(view: Callable) -> Callable`, and `require_step_up(purpose: str) -> Callable` are declarative route guards.
- `normalize_employee_number(value: str) -> str`, `normalize_pin(value: str) -> str`, `validate_new_pin(pin: str, employee_number: str) -> str`, `hash_pin(pin: str) -> str`, and `verify_pin(encoded_hash: str, pin: str) -> bool` own identity normalization and PIN policy; validation returns the normalized accepted PIN for immediate request-local use only.
- `issue_credential() -> OpaqueCredential` returns `raw` once and its SHA-256 `digest`; `hash_token(token: str) -> bytes` never logs or persists plaintext.
- `classify_incident_notes(notes: str) -> dict`, `extract_incident_notes(notes: str, category: str, staff_provider: StaffProvider) -> dict`, `generate_report_set(payload: dict, *, staff_provider: StaffProvider) -> dict`, and `generate_disciplinary_report(payload: dict, *, staff_provider: StaffProvider) -> dict` are route-neutral adapters over the existing report engine.
- `can_read_report(actor: Actor, report: Report) -> bool`, `can_edit_report(actor: Actor, report: Report) -> bool`, and `can_export_report(actor: Actor, report: Report) -> bool` are the shared record policies used by both ordinary and Admin routes.
- `save_report(session: Session, actor: Actor, report_id: UUID, content: ReportContentV1, base_revision_number: int, reason: str) -> ReportRevision`, `restore_report(session: Session, actor: Actor, report_id: UUID, revision_number: int) -> ReportRevision`, and `create_recovery_revision(session: Session, actor: Actor, report_id: UUID, content: ReportContentV1, base_revision_number: int) -> ReportRevision` own all report writes.
- `submit_job(session: Session, actor: Actor, command: SubmitJobCommand, idempotency_key: str, base_revision_number: int) -> AiJob`, `claim_job(session: Session, job_id: UUID) -> AiJob | None`, and `apply_job_result(session: Session, job_id: UUID, expected_incident_revision: int) -> None` own durable AI work.
- `export_report_docx(session: Session, actor: Actor, report_id: UUID, revision_number: int, idempotency_key: str) -> ExportResult` owns revision-exact Word generation and metadata.

## Shared HTTP Rules

- JSON success example: `{"data":{"status":"ok"},"request_id":"req_20260812_000001","server_time":"2026-08-12T18:30:00Z","api_version":"v1"}`.
- JSON failure example: `{"error":{"code":"permission_denied","message":"You do not have permission to perform this action.","retryable":false,"details":{}},"request_id":"req_20260812_000002","server_time":"2026-08-12T18:30:01Z"}`.
- Access sends `Authorization`, `X-Client-Version`, and `X-Request-ID` on authenticated calls.
- Mutations and AI submissions send `Idempotency-Key`.
- Revision saves send an integer entity tag such as `If-Match: "7"` or the documented `base_revision_number` body field, never conflicting values.
- Protected Admin reads use the bearer session's server-side elevation state and send no elevation credential. Sensitive actions send the single-use `X-Admin-Step-Up` token issued for the exact purpose.
- The server returns stable error codes; Access maps codes to approved language and never displays raw HTML or stack traces.

### Locked cross-client wire contracts

- `GET /api/v1/client-policy`, `POST /api/v1/auth/login`, and `POST /api/v1/auth/renew` are the only Access bootstrap/authentication operations with OpenAPI `security: []`. Login and renewal still require `X-Client-Version`; client policy may omit it. Browser cookies never authenticate these or any other `/api/v1` route.
- Renewal is attempted at most once and only after a bearer-authenticated request receives the documented expired-access-token response. A definitive renewal rejection such as `session_reauthentication_required` clears the local session; a transient `dependency_unavailable` response retains the renewal credential and current profile so the user can retry later.
- `POST /api/v1/auth/change-pin`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/logout-all`, `DELETE /api/v1/auth/sessions/{session_id}`, and `POST /api/v1/auth/admin-step-up` require `Idempotency-Key` even though their response bodies are small.
- `POST /api/v1/auth/admin-step-up` with purpose `admin_center` is the sole Admin elevation-entry exception: it requires an Admin bearer, PIN confirmation, compatible client, and idempotency, but cannot require a pre-existing elevation or step-up token. A sensitive purpose requires current elevation and returns one single-use token for the exact purpose.
- `GET /api/v1/admin/accounts/{account_id}/sessions` returns a bounded, cursor-paginated list with session ID, device label, persistence flag, created/last-used/idle-expiry/revoked timestamps, and current-session flag. `POST /api/v1/admin/accounts/{account_id}/revoke-sessions` accepts exactly `{"scope":"all"}` or the fictional example `{"scope":"one","session_id":"00000000-0000-4000-8000-000000000001"}` with no additional fields.
- Admin account create and PIN reset return the typed fields `operation_reference_id`, `account_id`, optional write-only `temporary_pin`, and `one_time_value_unavailable`. The first successful response contains the PIN and `false`; an identical-key replay returns the durable IDs, omits the PIN, and returns `true`.
- Admin report restore is exactly `POST /api/v1/admin/reports/{report_id}/restore` with the example body `{"revision_number":7}`. It creates a new attributable revision and never overwrites, deletes, or renumbers the selected historical revision.
- Ordinary Word export is exactly `POST /api/v1/reports/{report_id}/export-docx?revision=7`; Admin oversight export is exactly `POST /api/v1/admin/reports/{report_id}/export-docx?revision=7`. Both use the same revision-exact service while preserving their distinct authorization/audit contexts. Admin bulk export is `POST /api/v1/admin/reports/bulk-export`; its closed body selects either explicit `report_ids` or an `AdminReportFilters` object, requires `revision_selection: "current_at_request"` and a reason, resolves exact revision numbers atomically, sorts by report UUID, and rejects more than 100 matches as `bulk_export_limit_exceeded`.
- Admin audit operations are `GET /api/v1/admin/audit-events` and `POST /api/v1/admin/audit-events/export`; audit export requires purpose `audit_export`. Admin report history uses `GET /api/v1/admin/reports/{report_id}/revisions` and `GET /api/v1/admin/reports/{report_id}/revisions/{revision_number}`.
- `/api/v1/client-policy` returns safe release compatibility fields plus a validated HTTPS `review_lab_origin`. Browser handoff URLs must use that same origin; Access validates it against policy instead of assuming the browser and API origins match.

### Stable cross-client error codes

Detailed plans may add endpoint-specific codes, but they must not rename or alias these locked values: `validation_failed`, `invalid_credentials`, `account_locked`, `session_reauthentication_required`, `dependency_unavailable`, `permission_denied`, `admin_elevation_required`, `step_up_required`, `duplicate_employee_number`, `staff_has_history`, `account_already_exists`, `last_active_admin`, `account_conflict`, `idempotency_conflict`, `request_in_progress`, `idempotent_response_unavailable`, `revision_conflict`, `bulk_export_limit_exceeded`, `audit_export_limit_exceeded`, `client_upgrade_required`, and `not_found`. In particular, `admin_step_up_required` is not a valid alias.

### Canonical version projection

`release/version.json` is the single checked-in version registry and contains exactly `$schema`, `schema_version`, `backend_version`, `api_version`, `client_version`, `minimum_client_version`, `minimum_server_version`, `release_notes`, and `channel`. Deployment projects those values to `RELEASE_VERSION`, `API_VERSION`, `LATEST_CLIENT_VERSION`, `MINIMUM_CLIENT_VERSION`, `MINIMUM_SERVER_VERSION`, and `RELEASE_NOTES`; no workflow, Terraform variable, Python default, or Access file becomes a competing production source.

## Task Dependency Order

| Order | Task IDs | Deliverable | Requires |
|---:|---|---|---|
| 1 | OP-01 | Retire unsafe auto-deployment/Pages exposure and define external/workstation gates | Approved specs |
| 2 | ID-01–ID-08 | Database, individual identity, sessions, Admin grants, audit, handoff | OP-01 inputs may remain test-only |
| 3 | RP-01–RP-10 | Central reports, revisions, jobs, exports, health, legacy controls | ID-01–ID-08 |
| 4 | OP-02–OP-08 | Isolated test infrastructure and controlled backend delivery | Backend contracts green |
| 5 | AC-01–AC-09 | Access User client and Windows matrix evidence | Stable OpenAPI + test hostname |
| 6 | AD-01–AD-05 | Access Admin Center and Review Lab handoff | Access User client + Admin APIs |
| 7 | OP-09–OP-10 | Signed updater/release pipeline, pilot, DR, rollback, rollout | Full cross-system acceptance |

## Program Gates

### Gate A: Backend foundation

- [ ] Identity and report plans pass all unit, PostgreSQL integration, OpenAPI, authorization, revision, idempotency, and sensitive-log tests.
- [ ] Existing credential-free report/policy/Word regression suite remains green.
- [ ] No `/api/v1` endpoint accepts shared browser cookies or client-supplied role/actor IDs.

### Gate B: Test environment

- [ ] Terraform format, validate, provider-lock, policy, and test-environment plan checks pass.
- [ ] Alembic upgrade and non-destructive rollback test pass against PostgreSQL 17.
- [ ] Test API/worker/queue/database/hostname use fictional data and do not share production identities, secrets, or policy index.

### Gate C: Access User client

- [ ] Text exports deterministically reconstruct the development `.accdb` and compile to each supported `.accde`.
- [ ] Fake-API VBA tests and COM smoke tests pass on every inventoried Access bitness/version.
- [ ] Persistent and nonpersistent session, recovery, conflict, job resume, history, Policy Expert, and Word export scenarios pass.

### Gate D: Admin Center

- [ ] User/Admin authorization matrix, elevation expiry, step-up purpose/expiry, account lifecycle, report oversight, audit, health, bulk export, and Review Lab handoff tests pass.
- [ ] Every Admin report action is visibly and durably attributed; no UI route creates an overwrite/delete bypass.

### Gate E: Production readiness

- [ ] Security review, dependency/container/IaC scans, load/cost tests, backup/PITR restore, and rollback exercise pass.
- [ ] Signed `.accde`, signed updater, signed/protected release manifest, user/admin documentation, runbooks, support ownership, and records approval are complete.
- [ ] Named business, IT/security, and records stakeholders approve the 5–10 employee/2 administrator pilot.

## Agent Task Protocol

Each implementation task follows this exact lifecycle:

1. Read `AGENTS.md`, the relevant approved specification, this roadmap, the relevant detailed plan task, and the matching Claude prompt.
2. Run `git status --short`; stop on unexpected changes that overlap allowed files.
3. Create a dedicated task branch from current reviewed `main`; never work directly on production resources.
4. Write the named failing test first and run the focused command to observe the expected failure.
5. Implement only the task's declared interfaces and allowed files.
6. Run focused tests, the task's regression set, `git diff --check`, and the task's sensitive-data scan.
7. Review the complete diff against the specification and forbidden scope.
8. Commit once with the required message; do not push, merge, deploy, sign, or apply infrastructure.
9. Return the handoff report required by the prompt.
10. A separate reviewer checks specification compliance first and code quality second. Dependent work waits for both approvals.

## Official Reference Baseline

- Google Cloud Run + Cloud Tasks private OIDC pattern: https://docs.cloud.google.com/run/docs/triggering/using-tasks
- Cloud Run ingress behind load balancing: https://docs.cloud.google.com/run/docs/securing/ingress
- Cloud SQL from Cloud Run and private IP: https://docs.cloud.google.com/sql/docs/postgres/connect-run
- Cloud SQL PostgreSQL version support: https://docs.cloud.google.com/sql/docs/postgres/db-versions
- Terraform provider lock files: https://developer.hashicorp.com/terraform/language/files/dependency-lock
- Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Access `SaveAsText`: https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/application-save-as-text
- Access `LoadFromText`: https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/application-load-from-text
- Windows DPAPI: https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- 64-bit VBA: https://learn.microsoft.com/en-gb/office/VBA/Language/Concepts/Getting-Started/64-bit-visual-basic-for-applications-overview
- WinHTTP request object: https://learn.microsoft.com/en-us/windows/win32/winhttp/winhttprequest

## Completion Definition

The program is complete only when every detailed task is reviewed, all five program gates pass, the backup/rollback exercises meet the approved RPO/RTO targets, the pilot obtains written acceptance, and the legacy website write surface is restricted so it cannot bypass the individual Cloud Run system of record.
