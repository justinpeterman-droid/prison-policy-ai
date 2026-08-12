# Report Storage and Access API Design

**Date:** 2026-08-12<br>
**Status:** Approved for implementation planning<br>
**Parent:** [Access + Cloud Run Master Design](2026-08-12-access-cloud-run-master-design.md)<br>
**Depends on:** [Cloud Identity Foundation](2026-08-12-cloud-identity-foundation-design.md)

## Purpose

Add centralized incident/report persistence, shared owner/preparer access,
immutable revisions, conflict-safe saving, administrator oversight, resumable AI
jobs, report search, on-demand Word exports, and stable `/api/v1` contracts while
reusing the current report and Policy Expert engines.

## Scope

- Incident workspaces and per-officer reports.
- Owner/preparer access relationships.
- In Progress, Completed, and Archived organization states.
- Immutable report and incident snapshots.
- Optimistic concurrency and recovery revisions.
- User and administrator report/history/search APIs.
- Asynchronous classification, extraction, generation, and disciplinary jobs.
- Policy Expert API for Access.
- On-demand Word generation from an explicit saved revision.
- Report, revision, job, export, and administrator-view audit events.
- OpenAPI contract, pagination, idempotency, errors, and client-version checks.

## Non-goals

- A second implementation of report classification, extraction, validation,
  generation, policy retrieval, or template filling.
- Independent copies when one officer prepares another officer's report.
- Permanent finalization or editing locks.
- Permanent deletion through Access or `/api/v1`.
- Central retention of generated Word binaries in the first release.
- General-purpose offline synchronization.
- Automatic filing, approval, email, or submission.

## Domain model

### `incidents`

- `id`: UUID primary key and public report-workspace identifier.
- `created_by_account_id`, `created_by_staff_member_id`.
- `status`: `in_progress`, `completed`, or `archived`.
- `current_revision_number`: integer used for conflict detection.
- Searchable incident date/time, facility, shift, location, and category fields.
- `field_notes`: current text, with an authoritative maximum of exactly 30,000
  Unicode code points after JSON decoding in release one.
- `classification`, `extracted_facts`, `gap_answers`, `charges`, `validation`:
  validated JSONB values using versioned schemas.
- `created_at`, `updated_at`, `archived_at`.

The current row supports efficient dashboard/search reads. Immutable incident
snapshots preserve prior states.

### `incident_revisions`

- `id`, `incident_id`, `revision_number`.
- `editor_account_id`, `editor_staff_member_id`.
- Complete versioned incident snapshot JSONB.
- Changed-field summary JSONB.
- `reason`: `autosave`, `manual_save`, `ai_result`, `restored`, `status_change`,
  `ownership_change`, or `recovery`.
- `client_version`, `request_id`, `created_at`.

`(incident_id, revision_number)` is unique. Rows are insert-only.

### `reports`

- `id`: UUID primary key.
- `incident_id`: foreign key.
- `report_type`: bounded current report type.
- `reporting_staff_member_id`: owner and named reporting officer.
- `prepared_by_staff_member_id`: initial preparer.
- `status`: `in_progress`, `completed`, or `archived`.
- `current_revision_number`.
- `current_content`: validated versioned JSONB containing editable fields and
  narrative.
- `created_at`, `updated_at`, `archived_at`.

The owner and preparer may be the same person. The reporting staff member may
initially lack an application account.

### `report_access`

- `report_id`, `staff_member_id` composite identity.
- `relationship`: `owner` or `preparer`.
- `granted_by_account_id`, `created_at`, `revoked_at`.

The owner and initial preparer relationships are created transactionally with
the report. Users cannot add arbitrary collaborators. A transfer or correction
is an administrator-only, step-up-protected, revisioned, audited operation.

### `report_revisions`

- `id`, `report_id`, `revision_number`.
- `editor_account_id`, `editor_staff_member_id`.
- Complete versioned report-content snapshot JSONB.
- Changed-field summary JSONB.
- `reason`: same bounded revision reasons as the incident plus `admin_edit`.
- Source incident revision and AI job IDs when applicable.
- Model, prompt, checklist, template, Cloud Run revision, and source commit
  fingerprints when applicable.
- `client_version`, `request_id`, `created_at`.

Rows are immutable and unique per report/revision. The current report row and
new revision commit atomically.

### `ai_jobs`

- `id`: UUID primary key.
- `incident_id`, optional `report_id`.
- `requested_by_account_id`.
- `job_type`: `classify`, `extract`, `generate`, or `disciplinary`.
- `state`: `queued`, `running`, `succeeded`, `failed`, or `cancelled`.
- `stage`: stable progress stage shown by Access.
- `idempotency_key`, request-payload hash, attempt count.
- Validated request/result/error JSONB.
- Configured model names and prompt fingerprints.
- `created_at`, `started_at`, `completed_at`.

`(requested_by_account_id, idempotency_key)` is unique within the documented
idempotency retention window of 24 hours.

### `exports`

- `id`, `report_id`, `report_revision_id`.
- `exported_by_account_id`, `template_version`.
- SHA-256 output hash, byte length, MIME type, and download name.
- `request_id`, `created_at`.

The row persists; the Word bytes are returned and discarded after the response.

### `idempotency_records`

- Actor, key, endpoint/action, normalized request hash, response status and
  durable result reference, timestamps, and 24-hour expiry.

Reusing a key with different input returns 409. Reusing it with identical input
returns the original durable result.

## Authorization rules

A User may read/edit/export a report when their `staff_member_id` has a live
owner or preparer relationship. They may access the containing incident data
needed for that report but do not gain access to unrelated incidents/reports.

An Admin may search, read, edit, restore, transfer, archive, and export every
report. Administrator views and exports of another employee's report create
audit events. Administrator edits create revisions naming the administrator.

Staff without accounts can own reports. They gain normal owner access when an
account is later linked to the same stable staff UUID.

Client-supplied employee numbers, owner IDs, preparer IDs, or report IDs never
bypass the server-side policy check.

## Multi-officer creation

Incident creation accepts one or more reporting staff UUIDs selected from the
active roster. Cloud Run:

1. Creates one incident workspace.
2. Creates one appropriate per-officer report record for each reporting
   officer when generation reaches that stage.
3. Adds the reporting officer as owner.
4. Adds the authenticated creator as preparer when different.
5. Returns canonical report IDs grouped under the incident.

One employee sees owned reports under **My Reports** and prepared reports under
**Reports I Prepared**. Both lists link to the same report ID.

## Revision and save behavior

- Every successful autosave, manual save, AI result application, status change,
  restoration, recovery, ownership correction, and administrator edit creates
  an immutable revision.
- Access supplies `base_revision_number` with a save.
- Cloud Run locks the current row for update, compares the supplied revision,
  validates the payload, inserts the next revision, updates current content,
  writes the audit/outbox record, and commits once.
- A stale base revision returns HTTP 409 `revision_conflict` with safe current
  revision metadata. It does not write.
- A recovery save after conflict uses a dedicated endpoint/action and creates a
  new `recovery` revision without silently replacing content. The user or admin
  then explicitly chooses the desired current content.
- Restoring revision N copies its snapshot into revision current+1 with reason
  `restored` and a reference to N.
- No endpoint updates or deletes a historical revision.

## API conventions

### Response envelope

Successful JSON responses contain `data`, `request_id`, `server_time`, and
`api_version`. Errors contain `error.code`, `error.message`, `error.retryable`,
optional safe `error.details`, `request_id`, and `server_time`.

### Required headers

- `Authorization: Bearer <access-token>`.
- `X-Client-Version` on every Access request.
- `Idempotency-Key` on every modifying or AI-submission request.
- `If-Match` or explicit `base_revision_number` on revisioned saves.

### Compatibility

`GET /api/v1/client-policy` returns latest and minimum compatible Access
versions, API version, release notes, and whether the client must become
read-only. Its closed nine-field response also includes the required integer
`field_notes_max_characters: 30000`, sourced from the same backend constant used
by `IncidentSnapshotV1` and `SaveIncidentRequest`, not from an environment or
version-registry value. Package selection/hash/signer metadata belongs only to
the authenticated update-grant response, never this public policy. The server
rejects writes from clients below the
minimum with `client_upgrade_required` while allowing sign-in, reads, and export
of already saved content.

### Pagination and search

List endpoints use opaque cursors and bounded page sizes. A maximum of 100
records per page applies to administrator views; employee defaults are smaller.
Search filters are explicit, validated, indexed, and authorization-scoped
before pagination.

## API surface

### Staff lookup

- `GET /api/v1/staff?query=` — active roster lookup available to either role;
  returns only fields needed for report selection.

### Incidents

- `POST /api/v1/incidents`
- `GET /api/v1/incidents/{incident_id}`
- `PATCH /api/v1/incidents/{incident_id}`
- `GET /api/v1/incidents/{incident_id}/revisions`
- `GET /api/v1/incidents/{incident_id}/revisions/{revision_number}`
- `POST /api/v1/incidents/{incident_id}/restore`

### Reports

- `GET /api/v1/reports?relationship=owned|prepared`
- `GET /api/v1/reports/{report_id}`
- `PATCH /api/v1/reports/{report_id}`
- `GET /api/v1/reports/{report_id}/revisions`
- `GET /api/v1/reports/{report_id}/revisions/{revision_number}`
- `POST /api/v1/reports/{report_id}/restore`
- `POST /api/v1/reports/{report_id}/recovery-revisions`
- `POST /api/v1/reports/{report_id}/export-docx`

### AI jobs

- `POST /api/v1/incidents/{incident_id}/jobs/classify`
- `POST /api/v1/incidents/{incident_id}/jobs/extract`
- `POST /api/v1/incidents/{incident_id}/jobs/generate`
- `POST /api/v1/incidents/{incident_id}/jobs/disciplinary`
- `GET /api/v1/jobs/{job_id}`

### Policy Expert

- `POST /api/v1/policy/questions`

The Policy Expert remains synchronous in the first release with a 90-second
client/server timeout. Its request preserves the existing bounded
conversation-history rules and citation behavior. Moving it to a background job
requires a later versioned contract change and is outside this design.

### Administrator report operations

- `GET /api/v1/admin/reports`
- `GET /api/v1/admin/reports/{report_id}`
- `PATCH /api/v1/admin/reports/{report_id}`
- `POST /api/v1/admin/reports/{report_id}/restore`
- `POST /api/v1/admin/reports/{report_id}/transfer`
- `POST /api/v1/admin/reports/{report_id}/export-docx`

The ordinary report policy functions remain the source of truth; admin route
names do not duplicate persistence logic.

## AI job execution

1. The API validates authorization, incident revision, request shape, and
   idempotency key.
2. It inserts the queued job and Cloud Tasks outbox record transactionally.
3. A dispatcher sends the task to the private worker using OIDC.
4. The worker claims one queued job, marks stage, and calls the existing Python
   pipeline.
5. Each safe stage/result update commits to Cloud SQL.
6. Success applies results through the same revision service used by manual
   saves and records model/prompt metadata.
7. Access polls the job endpoint with increasing intervals and may close. The
   result remains durable.

Cloud Tasks retries only transient delivery/worker failures. Pipeline retry
behavior remains bounded by `backend/pipeline/retry.py`. Validation,
authorization, or deterministic content failures are terminal. A job cannot
apply results if its incident base revision became stale; it returns a
`result_conflict` requiring employee review.

When a worker recovery attempt follows possible provider acceptance without a
committed result, RP-07 increments `ai_provider_repeat_risk_total`. That metric
is the sole release-one application producer for this residual repeat-billing
risk; it never includes report content or actor identity.

## Word generation

The export endpoint requires a saved report revision. It loads that exact
snapshot, maps validated fields to the existing filler, creates a temporary
DOCX, computes SHA-256 and size, inserts the export/audit records, and streams
the bytes. Temporary files are removed after response completion.

Unsaved Access changes must first be saved successfully. The employee chooses
whether to export after a conflict; the API never exports an ambiguous local
state.

## Audit actions

At minimum:

- `incident.created`, `incident.saved`, `incident.restored`,
  `incident.status_changed`
- `report.created`, `report.viewed_by_admin`, `report.saved`,
  `report.restored`, `report.recovery_created`, `report.status_changed`,
  `report.ownership_transferred`
- `report.exported`, `report.exported_by_admin`
- `ai.job_submitted`, `ai.job_succeeded`, `ai.job_failed`
- `policy.question_answered`, recording identifiers/latency but not the full
  sensitive question/answer in the audit detail

## Error behavior

- `400 validation_failed`: bounded field-level guidance.
- `401 authentication_required`: Access renews once, then shows login.
- `403 permission_denied`: no existence details for unauthorized records.
- `404 not_found`: missing or concealed record.
- `409 revision_conflict`, `idempotency_conflict`, or `job_result_conflict`.
- `413 payload_too_large`.
- `422 blocking_information_required` for generation prerequisites.
- `429 rate_limited` with safe retry timing.
- `503 dependency_unavailable` for database, Google AI, search, or storage
  outages, classified without leaking infrastructure details.

Previously saved work remains available when an AI dependency fails. No error
path clears client content or returns a false success.

## Indexing and query limits

Indexes cover report/incident IDs, owner/preparer relationships, statuses,
incident dates, updated times, staff UUIDs, normalized employee numbers, inmate
search tokens where agency-approved, categories, and job/idempotency identities.

Wildcard search over full narratives is excluded from the first release. Admin
search covers the approved structured fields and bounded name/ADC/location
values. Search input never becomes SQL text.

## Testing

### Persistence and policy tests

- Multi-officer creation produces one canonical report per owner and one
  owner/preparer access relationship.
- Owner, preparer, unrelated User, and Admin permissions for every operation.
- Staff-without-account ownership and later account linkage.
- Current-row/revision atomicity and append-only history.
- Restore and recovery create new revisions without mutating history.
- Admin view/edit/export attribution.
- Status changes remain editable.

### Concurrency and idempotency tests

- Two saves from the same base revision produce one success and one 409.
- Stale AI results cannot overwrite newer facts.
- Repeated identical idempotency key returns one durable job/result/export.
- Same key with changed input returns conflict.
- Concurrent job claims and ordinary Cloud Tasks redelivery apply at most one
  durable result. Idempotency prevents duplicate user submissions and routine
  redelivery calls; a worker crash after Google accepts a request but before the
  result commits can cause a repeated provider call and must be metered and
  audited because the provider offers no transactional exactly-once boundary.

### Pipeline parity tests

- Existing classify/extract/generate/disciplinary outputs flow through the
  service boundary without prompt/rule changes.
- Existing gap, invented-fact, style, roster, and report-validator tests remain
  green.
- Policy citation behavior and bounded conversation context remain intact.
- Metadata captures configured models, prompt/checklist fingerprints, source
  commit, and Cloud Run revision.
- Word export from a known revision matches the existing official template.

### API contract tests

- OpenAPI schema validates all documented requests/responses.
- Pagination bounds and authorization filtering.
- Error envelopes and request IDs.
- Minimum-client read-only enforcement.
- Field notes accept exactly 30,000 characters and reject 30,001 at both the
  schema and incident-route/OpenAPI boundaries.
- Payload, string, collection, and JSON depth limits.
- Sensitive content does not enter ordinary logs.

## Acceptance criteria

1. Ordinary incidents and reports persist centrally and survive Cloud Run
   restarts/deployments.
2. Owner/preparer/Admin authorization matches the approved matrix for every
   endpoint.
3. Preparing another officer's report creates one shared canonical record, not
   duplicate copies.
4. Every successful change creates an immutable attributable revision.
5. Concurrent saves and stale AI results cannot silently overwrite newer work.
6. Restoring/recovering content creates new history without deleting history.
7. AI jobs are durable, resumable, reuse the existing pipeline, and prevent
   duplicate work from repeated client submissions while applying at most one
   durable result.
8. Users can list owned/prepared reports; Admins can search every report through
   bounded structured filters.
9. Word output is generated from an explicit saved revision and audited without
   retaining the binary centrally.
10. Existing report, policy, validation, and Word behavior passes regression
    verification.
