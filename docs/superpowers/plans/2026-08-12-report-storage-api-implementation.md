# Report Storage and Access API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add centralized, authorization-scoped incidents and reports, immutable revisions, durable AI jobs, Admin oversight, Policy Expert access, and revision-exact Word exports behind `/api/v1`.

**Architecture:** PostgreSQL current rows provide efficient reads while insert-only snapshots preserve every successful change. Route-neutral services wrap the existing report and policy engines; Flask routes enforce the individual Actor policy, and a private Cloud Tasks worker executes long AI work without duplicating the browser orchestration.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2.0.51, Alembic 1.18.5, Psycopg 3.3.4, Pydantic 2.13.4, PostgreSQL 17/JSONB, Google Cloud Tasks 2.23.0, python-docx/ZIP XML, pytest, and OpenAPI 3.1.

## Global Constraints

- Complete ID-01 through ID-08 before RP-01.
- Reuse `backend/reports/classifier.py`, `extraction.py`, `validate.py`, `generator.py`, `report_validator.py`, `filler.py`, and `backend/pipeline/query.py`; do not rewrite prompts, policy retrieval, validation, or Word-template rules.
- The term is **field notes** in every user-facing string.
- Current rows and new immutable revisions commit atomically; historical rows are never updated or deleted.
- Users may access only live owner/preparer relationships. Admin access never creates a hidden overwrite path.
- Completed and Archived remain editable. Permanent report deletion is unavailable.
- All mutation and AI-submission requests require `Idempotency-Key`. Revision saves require a base revision.
- AI jobs are durable and asynchronous; Policy Expert remains synchronous with a 90-second timeout.
- One owner report per selected reporting officer and one preparer relationship for the authenticated creator when different.
- Word output is generated from an explicit saved revision, audited, streamed, and discarded after the response.
- Access never supplies a trusted actor, role, employee number, ownership grant, model name, prompt hash, or audit identity.
- No report text, field notes, person name, employee number, inmate identifier, policy question/answer, token, or PIN enters ordinary logs.
- Every fixture in this plan is fictional. Do not call Google services in unit or PostgreSQL integration tests.
- Implementation agents must not deploy, push, merge, apply infrastructure, access production, or handle secrets.

---

## File Map

- Create `backend/persistence/models/reporting.py`: incidents, incident revisions, reports, report access, and report revisions.
- Create `backend/persistence/models/jobs.py`: AI jobs, task outbox, and exports; shared idempotency records remain owned by ID-06.
- Create `backend/reports/service.py`: route-neutral adapters over the existing report pipeline.
- Create `backend/reports/persistence.py`: incident/report query and creation operations.
- Create `backend/reports/policy.py`: owner/preparer/Admin record policies.
- Create `backend/reports/revisions.py`: atomic save, restore, status, ownership, and recovery operations.
- Create `backend/reports/provenance.py`: prompt/model/template/source fingerprints shared with Review Lab.
- Create `backend/reports/deterministic_docx.py`: normalize DOCX ZIP metadata for repeatable bytes.
- Create `backend/reports/export_service.py`: single and bounded bulk export operations.
- Create `backend/jobs/service.py`: job/idempotency lifecycle and result application.
- Create `backend/jobs/outbox.py`: transactional outbox operations.
- Create `backend/jobs/dispatcher.py`: authenticated Cloud Tasks creation.
- Create `backend/worker/app.py` and `backend/worker/routes.py`: private worker entry point.
- Create/modify `/api/v1` route modules for staff, incidents, reports, jobs, policy, Admin reports, audit, health, and client policy.
- Modify `backend/webapp/routes/reports.py` and `chat.py` only to delegate shared orchestration while preserving legacy behavior.
- Modify `openapi/access-v1.yaml` in the task that introduces each route.
- Create PostgreSQL integration, API contract, security, and engine-parity tests under `tests/`.

## Shared Test-Support Contract

- ID-01 creates `tests/integration/conftest.py` with `db_engine`, `db_session_factory`, function-scoped `db_session`, and `api_client`; it requires `TEST_DATABASE_URL` and skips with the exact safe reason `TEST_DATABASE_URL is not configured` when absent. It never silently falls back to SQLite.
- ID-05 creates `tests/integration/identity_fixtures.py` with `seed_fictional_account`, `issue_fictional_tokens`, and `bearer_headers`, plus fixtures `fictional_user_account`, `fictional_admin_account`, `fictional_user_tokens`, `fictional_admin_tokens`, `user_bearer_headers`, and `admin_bearer_headers`. ID-07 adds fresh purpose-specific Admin step-up header fixtures.
- RP-01 extends `tests/integration/conftest.py` with `user_actor`, `owner_bearer_headers`, `preparer_bearer_headers`, `unrelated_bearer_headers`, and `old_client_bearer_headers`. Each mapping contains only fictional tokens minted by the test token service; mutation tests add their own explicit `Idempotency-Key` and `If-Match` values. Admin tests consume `elevated_admin_bearer_headers` and exact-purpose step-up headers from ID-07.
- RP-01 creates `tests/support/reporting.py`. It exports `FictionalStaffAndAccounts`, `FictionalStaff`, `make_incident(session, account)`, `fictional_report_content(narrative: str) -> dict[str, object]`, and seed functions registered by `tests/integration/conftest.py` as `fictional_staff_and_accounts`, `fictional_staff`, `fictional_incident`, `fictional_report`, `shared_report`, `incident_id`, and `report_id` fixtures.
- RP-06 extends `tests/support/reporting.py` with `queued_outbox`; RP-07 defines `FakeTasksClient` and the `worker_client` fixture in its named test files; RP-09 defines `fictional_docx_bytes` in `tests/unit/test_deterministic_docx.py` by constructing an in-memory DOCX containing fictional text.
- No integration test imports a production roster, uses a real employee number, or silently falls back to SQLite. PostgreSQL-dependent tests fail with a safe setup message when the dedicated test database is absent.

---

### Task RP-01: Incident, report, access, and revision persistence

**Files:**
- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Create: `backend/persistence/models/reporting.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260812_0003_report_storage.py`
- Create: `tests/support/reporting.py`
- Modify: `tests/integration/conftest.py`
- Create: `tests/unit/test_reporting_models.py`
- Create: `tests/integration/test_report_migration.py`

**Interfaces:**
- Consumes: `Base`, identity UUID foreign keys, UTC timestamp helpers, and the migration framework from ID-01/ID-03.
- Produces: `Incident`, `IncidentRevision`, `Report`, `ReportAccess`, `ReportRevision`, `ReportStatus`, `ReportType`, `RevisionReason`, and migration revision `20260812_0003` with `down_revision = "20260812_0002"`.

- [ ] **Step 1: Write the failing model and migration tests**

```python
def test_revision_identity_is_unique(db_session, fictional_staff_and_accounts):
    incident = make_incident(db_session, fictional_staff_and_accounts.user)
    db_session.add_all([
        IncidentRevision(incident_id=incident.id, revision_number=1,
                         editor_account_id=fictional_staff_and_accounts.user.id,
                         editor_staff_member_id=fictional_staff_and_accounts.user.staff_member_id,
                         snapshot={"schema_version": 1}, changed_fields={},
                         reason="manual_save", client_version="0.1.0",
                         request_id="req_model_1"),
        IncidentRevision(incident_id=incident.id, revision_number=1,
                         editor_account_id=fictional_staff_and_accounts.user.id,
                         editor_staff_member_id=fictional_staff_and_accounts.user.staff_member_id,
                         snapshot={"schema_version": 1}, changed_fields={},
                         reason="autosave", client_version="0.1.0",
                         request_id="req_model_2"),
    ])
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_report_access_relationship_is_bounded(db_session, fictional_report):
    db_session.add(ReportAccess(report_id=fictional_report.id,
                                staff_member_id=uuid4(), relationship="viewer",
                                granted_by_account_id=fictional_report.created_by_account_id))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2: Run the focused tests and observe missing-model failures**

Run: `python -m pytest tests/unit/test_reporting_models.py tests/integration/test_report_migration.py -v`

Expected: FAIL because the reporting models and `20260812_0003` migration do not exist.

- [ ] **Step 3: Implement the bounded SQLAlchemy model set**

Add `pydantic>=2.13,<3.0` to both runtime requirement files before importing the strict schemas used by subsequent report tasks. Do not add a second validation library.

```python
class ReportStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class RevisionReason(str, enum.Enum):
    AUTOSAVE = "autosave"
    MANUAL_SAVE = "manual_save"
    AI_RESULT = "ai_result"
    RESTORED = "restored"
    STATUS_CHANGE = "status_change"
    OWNERSHIP_CHANGE = "ownership_change"
    RECOVERY = "recovery"
    ADMIN_EDIT = "admin_edit"

class ReportAccess(Base):
    __tablename__ = "report_access"
    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.id"), primary_key=True)
    staff_member_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id"), primary_key=True)
    relationship: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_by_account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    revoked_at: Mapped[datetime | None]
    __table_args__ = (
        CheckConstraint("relationship IN ('owner','preparer')", name="ck_report_access_relationship"),
    )
```

Implement every field in the approved domain model. Use PostgreSQL `JSONB`, SQLAlchemy `Uuid(as_uuid=True)`, explicit foreign keys, named check constraints, `(parent_id, revision_number)` unique constraints, nonnegative revision checks, and indexes for status/date/category/owner/preparer/updated queries. `report_type` is a named PostgreSQL enum containing `first_person`, `supervisor_summary`, `cover_letter`, `disciplinary`, `investigation`, and `form_005`.

- [ ] **Step 4: Implement the reversible expansion migration**

Set `revision = "20260812_0003"` and `down_revision = "20260812_0002"`. `upgrade()` creates only new enums, tables, constraints, and indexes. `downgrade()` removes them in reverse dependency order and is permitted only in test because production rollback retains expanded schema. Include comments documenting expected empty-database duration, locks, rollback use, and verification queries.

- [ ] **Step 5: Run model and migration lifecycle tests**

Run: `python -m pytest tests/unit/test_reporting_models.py tests/integration/test_report_migration.py -v`

Expected: PASS against PostgreSQL 17; upgrade, downgrade, and second upgrade leave the expected tables and Alembic revision.

- [ ] **Step 6: Commit the reporting schema**

```bash
git add requirements.txt backend/requirements.txt backend/persistence/models/reporting.py backend/persistence/models/__init__.py migrations/versions/20260812_0003_report_storage.py tests/support/reporting.py tests/integration/conftest.py tests/unit/test_reporting_models.py tests/integration/test_report_migration.py
git commit -m "feat: add incident and report revision schema"
```

---

### Task RP-02: Versioned content schemas, provenance, and atomic revisions

**Files:**
- Create: `backend/webapp/api_v1/schemas/reporting.py`
- Create: `backend/reports/provenance.py`
- Create: `backend/reports/revisions.py`
- Modify: `backend/identity/audit.py`
- Modify: `backend/reports/review_schema.py`
- Create: `tests/unit/test_reporting_schemas.py`
- Create: `tests/unit/test_report_provenance.py`
- Create: `tests/unit/test_report_audit_schemas.py`
- Create: `tests/integration/test_revision_service.py`

**Interfaces:**
- Consumes: ID-02 `FIELD_NOTES_MAX_CHARACTERS`, whose release-one value is exactly `30_000`.
- Produces: `IncidentSnapshotV1`, `ReportContentV1`, `SaveIncidentRequest`, `SaveReportRequest`, `RevisionSummary`, the bounded report audit-action allowlist, `collect_provenance() -> dict[str, str | None]`, `save_incident()`, `save_report()`, `restore_report()`, and `create_recovery_revision()`.
- Consumed by: every incident/report route, AI result application, exports, and Access conflict handling.

- [ ] **Step 1: Write strict schema and concurrency tests**

```python
def test_report_content_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ReportContentV1.model_validate({
            "schema_version": 1,
            "narrative": "Fictional narrative.",
            "unexpected": "not accepted",
        })

def test_two_saves_from_same_revision_yield_success_and_conflict(
        db_session_factory, fictional_report, user_actor):
    first = save_report(db_session_factory(), user_actor, fictional_report.id,
                        ReportContentV1(schema_version=1, narrative="First edit."),
                        base_revision_number=1, reason="manual_save")
    assert first.revision_number == 2
    with pytest.raises(RevisionConflict) as caught:
        save_report(db_session_factory(), user_actor, fictional_report.id,
                    ReportContentV1(schema_version=1, narrative="Stale edit."),
                    base_revision_number=1, reason="manual_save")
    assert caught.value.current_revision_number == 2
```

Add direct strict-model boundary tests proving both `IncidentSnapshotV1` and
`SaveIncidentRequest` accept a `field_notes` string of exactly 30,000
characters and reject 30,001. Assert the field constraint is sourced from
`FIELD_NOTES_MAX_CHARACTERS`, not a duplicate literal, environment lookup, or
version metadata. Add the same acceptance/rejection with one non-BMP fictional
Unicode character repeated 30,000/30,001 times, establishing that Pydantic
counts decoded Unicode code points rather than UTF-8 bytes or UTF-16 code units.

- [ ] **Step 2: Run and confirm missing-schema/service failures**

Run: `python -m pytest tests/unit/test_reporting_schemas.py tests/unit/test_report_provenance.py tests/unit/test_report_audit_schemas.py tests/integration/test_revision_service.py -v`

Expected: FAIL on missing `ReportContentV1`, `collect_provenance`, and revision functions.

- [ ] **Step 3: Implement strict Pydantic content contracts**

```python
class StrictApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class ReportContentV1(StrictApiModel):
    schema_version: Literal[1] = 1
    narrative: str = Field(max_length=30_000)
    editable_fields: dict[str, str | int | bool | None] = Field(default_factory=dict)
    validation: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list, max_length=100)
```

Define `field_notes: str = Field(max_length=FIELD_NOTES_MAX_CHARACTERS)` on both `IncidentSnapshotV1` and `SaveIncidentRequest`, importing the one ID-02 backend constant. Define bounded incident classification, extracted facts, gap answers, charges, validation, searchable date/location/category fields, and report editable fields. Reject non-finite numbers, oversized JSON, unknown fields, client-supplied fingerprints, and client-supplied actor/owner/preparer IDs. Do not add a second limit constant or read this contract from an environment/version source.

- [ ] **Step 4: Centralize provenance fingerprints**

Move the hash behavior from `backend/reports/review_schema.py` into `collect_provenance()`. It returns keys `fast_model`, `pro_model`, `model_location`, `classification_prompt_sha256`, `generation_prompt_sha256`, `checklist_sha256`, `template_sha256`, `cloud_run_revision`, and `source_commit`. Review Lab imports this helper so its existing tests remain green.

- [ ] **Step 5: Extend the validated audit catalog once**

Add exact schemas in `backend/identity/audit.py` for `incident.created`, `incident.saved`, `incident.restored`, `incident.status_changed`, `report.created`, `report.viewed_by_admin`, `report.saved`, `report.restored`, `report.recovery_created`, `report.status_changed`, `report.ownership_transferred`, `report.exported`, `report.exported_by_admin`, `ai.job_submitted`, `ai.job_succeeded`, `ai.job_failed`, `policy.question_answered`, `admin.report_search`, `admin.bulk_exported`, `admin.audit_exported`, and `admin.health_viewed`. Allow only stable IDs, revision numbers, result codes, bounded changed-field names, normalized filter names, document counts, hashes, latency, and request/job/export IDs; reject field notes, report text, names, employee numbers, inmate identifiers, policy question/answer text, tokens, and PINs. `tests/unit/test_report_audit_schemas.py` must accept every exact safe example and reject sensitive/unknown keys for every action.

- [ ] **Step 6: Implement one-transaction revision operations**

Select the report row with `FOR UPDATE`, compare the base revision, validate content, calculate changed-field names without storing sensitive values, append the immutable snapshot, update the current row, append the safe audit event, and commit once. Restoration copies the historical snapshot into `current + 1`; recovery appends a `recovery` revision and never silently promotes it over a newer current revision.

- [ ] **Step 7: Run focused and Review Lab regressions**

Run: `python -m pytest tests/unit/test_reporting_schemas.py tests/unit/test_report_provenance.py tests/unit/test_report_audit_schemas.py tests/integration/test_revision_service.py tests/unit/test_review_schema.py -v`

Expected: PASS; concurrency test produces one saved revision and one conflict with no partial audit row.

- [ ] **Step 8: Commit schemas and revision services**

```bash
git add backend/webapp/api_v1/schemas/reporting.py backend/reports/provenance.py backend/reports/revisions.py backend/identity/audit.py backend/reports/review_schema.py tests/unit/test_reporting_schemas.py tests/unit/test_report_provenance.py tests/unit/test_report_audit_schemas.py tests/integration/test_revision_service.py
git commit -m "feat: add conflict-safe report revisions"
```

---

### Task RP-03: Route-neutral engine adapters, staff lookup, and incident creation

**Files:**
- Create: `backend/reports/service.py`
- Create: `backend/reports/persistence.py`
- Create: `backend/reports/policy.py`
- Modify: `backend/reports/roster.py`
- Modify: `backend/webapp/routes/reports.py`
- Create: `backend/webapp/api_v1/staff.py`
- Create: `backend/webapp/api_v1/incidents.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_report_service.py`
- Create: `tests/unit/test_report_policy.py`
- Create: `tests/integration/test_incident_api.py`

**Interfaces:**
- Consumes: ID-06 transactional idempotency for incident creation/saves.
- Produces: `StaffProvider`, `SqlStaffProvider`, `classify_incident_notes()`, `extract_incident_notes()`, `generate_report_set()`, `generate_disciplinary_report()`, `create_incident()`, `get_incident()`, and owner/preparer policy functions.
- Preserves: legacy `/api/reports/*` response behavior and imported private helpers used by current tests.

- [ ] **Step 1: Write adapter, authorization, and multi-officer creation tests**

```python
def test_create_incident_adds_owner_and_preparer_for_each_reporting_officer(
        api_client, owner_bearer_headers, fictional_staff):
    headers = owner_bearer_headers | {"Idempotency-Key": "incident-fictional-0001"}
    response = api_client.post("/api/v1/incidents", headers=headers, json={
        "reporting_staff_ids": [str(fictional_staff.alex.id), str(fictional_staff.blair.id)],
        "field_notes": "Fictional field notes for contract testing.",
    })
    assert response.status_code == 201
    assert response.json["data"]["reporting_staff_ids"] == [
        str(fictional_staff.alex.id), str(fictional_staff.blair.id)]

def test_unrelated_user_cannot_read_incident(api_client, unrelated_bearer_headers, fictional_incident):
    response = api_client.get(f"/api/v1/incidents/{fictional_incident.id}",
                              headers=unrelated_bearer_headers)
    assert response.status_code == 404
```

Add an integration boundary case that sends 30,001 fictional Unicode code points to
`POST /api/v1/incidents` and receives `400 validation_failed` without a row,
revision, idempotent success, or audit write. Keep the exact-30,000 acceptance
case in RP-02's schema tests and validate that this route uses the same model.

- [ ] **Step 2: Run and observe missing routes/services**

Run: `python -m pytest tests/unit/test_report_service.py tests/unit/test_report_policy.py tests/integration/test_incident_api.py -v`

Expected: FAIL because the route-neutral service, SQL staff provider, policies, and routes are absent.

- [ ] **Step 3: Extract route-neutral orchestration without changing engine logic**

Move orchestration from `reports.py` functions `reports_classify`, `reports_extract`, `_prepare_generation`, `_finalize_generation`, `reports_generate`, and `reports_disciplinary` into the named service functions. Legacy routes call the services and retain their old shapes. Inject `StaffProvider` into roster resolution; the Access path uses Cloud SQL and never calls `roster_store.update()`.

- [ ] **Step 4: Implement record policies and transactional incident creation**

`create_incident()` accepts stable active staff UUIDs, validates `field_notes` through RP-02 `SaveIncidentRequest` with the exact 30,000-Unicode-code-point maximum, derives the authenticated preparer from `Actor`, claims/completes `Idempotency-Key` in the same transaction, creates revision 1, creates per-owner report shells only at the generation stage, and audits `incident.created`. `get_incident()` returns only the fields required by a report the actor may access. Unrelated records are concealed as 404.

- [ ] **Step 5: Add staff and incident OpenAPI paths**

Document `GET /api/v1/staff`, `POST /api/v1/incidents`, `GET/PATCH /api/v1/incidents/{incident_id}`, revision list/detail, and restore. Incident create/save examples use fictional field notes and the schema sets `field_notes` `type: string` with `maxLength: 30000`; contract tests assert that exact value and the documented `400 validation_failed` over-limit response. Include bounded examples, pagination cursors, required headers, `422 blocking_information_required`, and all approved error envelopes.

- [ ] **Step 6: Run focused, legacy, and contract tests**

Run: `python -m pytest tests/unit/test_report_service.py tests/unit/test_report_policy.py tests/integration/test_incident_api.py tests/unit/test_report_helpers.py tests/unit/test_deferred_disciplinary.py tests/unit/test_generate_all_reports.py tests/contract/test_access_v1_openapi.py -v`

Expected: PASS with no Google credentials.

- [ ] **Step 7: Commit incident and engine boundaries**

```bash
git add backend/reports/service.py backend/reports/persistence.py backend/reports/policy.py backend/reports/roster.py backend/webapp/routes/reports.py backend/webapp/api_v1/staff.py backend/webapp/api_v1/incidents.py backend/webapp/api_v1/__init__.py openapi/access-v1.yaml tests/unit/test_report_service.py tests/unit/test_report_policy.py tests/integration/test_incident_api.py
git commit -m "feat: add authorized incident api"
```

---

### Task RP-04: Employee reports, queues, revision history, restore, and recovery

**Files:**
- Create: `backend/webapp/api_v1/reports.py`
- Modify: `backend/reports/persistence.py`
- Modify: `backend/reports/revisions.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/integration/test_employee_report_api.py`
- Create: `tests/integration/test_report_concurrency.py`
- Create: `tests/contract/test_report_examples.py`

**Interfaces:**
- Consumes: ID-06 transactional idempotency for saves, restore, recovery, and status changes.
- Produces: owned/prepared report lists, report detail/save, revision list/detail, restore, recovery revision, and reversible status changes.
- Consumed by: Access `modReportWorkflow`, `modAutosave`, `modConflict`, and `frmReportHistory`.

- [ ] **Step 1: Write failing owner/preparer/history/conflict tests**

```python
def test_owner_and_preparer_lists_reference_same_report(
        api_client, owner_bearer_headers, preparer_bearer_headers, shared_report):
    owned = api_client.get("/api/v1/reports?relationship=owned",
                           headers=owner_bearer_headers).json["data"]["items"]
    prepared = api_client.get("/api/v1/reports?relationship=prepared",
                              headers=preparer_bearer_headers).json["data"]["items"]
    assert [item["id"] for item in owned] == [str(shared_report.id)]
    assert [item["id"] for item in prepared] == [str(shared_report.id)]

def test_stale_patch_does_not_write(api_client, owner_bearer_headers, shared_report):
    headers = owner_bearer_headers | {
        "Idempotency-Key": "save-fictional-stale-0001", "If-Match": '"1"'}
    response = api_client.patch(
        f"/api/v1/reports/{shared_report.id}",
        headers=headers,
        json={"base_revision_number": 1, "content": fictional_report_content("Stale edit.")})
    assert response.status_code == 409
    assert response.json["error"]["code"] == "revision_conflict"
```

- [ ] **Step 2: Run and confirm missing employee report API**

Run: `python -m pytest tests/integration/test_employee_report_api.py tests/integration/test_report_concurrency.py tests/contract/test_report_examples.py -v`

Expected: FAIL because `/api/v1/reports` is not registered.

- [ ] **Step 3: Implement authorization-first pagination and summaries**

Apply owner/preparer authorization in SQL before cursor pagination. Default page size is 25 and maximum is 50. Filters are status, incident-date range, category, and updated-date range. Summaries contain no narrative or full field notes.

- [ ] **Step 4: Implement detail, save, restore, and recovery routes**

Validate both `If-Match` and body revision when supplied and reject disagreement. Claim/complete the ID-06 idempotency key in the same transaction as every mutation/revision/audit. Map `RevisionConflict` to safe current revision number/editor display/time/changed-field names. Restore copies the selected snapshot into a new current revision. Recovery appends the local snapshot as a distinct revision and returns its ID without implicit promotion.

- [ ] **Step 5: Add report paths and examples to OpenAPI**

Add every employee report endpoint from the approved API specification with examples for owned, prepared, detail, conflict, restored, and recovery-created responses. Status mutations remain saves and never lock editing.

- [ ] **Step 6: Run focused and authorization regressions**

Run: `python -m pytest tests/integration/test_employee_report_api.py tests/integration/test_report_concurrency.py tests/contract/test_report_examples.py tests/unit/test_report_policy.py tests/unit/test_auth_middleware.py -v`

Expected: PASS; an unrelated User receives concealed 404 and cannot infer record existence.

- [ ] **Step 7: Commit employee report history**

```bash
git add backend/webapp/api_v1/reports.py backend/reports/persistence.py backend/reports/revisions.py backend/webapp/api_v1/__init__.py openapi/access-v1.yaml tests/integration/test_employee_report_api.py tests/integration/test_report_concurrency.py tests/contract/test_report_examples.py
git commit -m "feat: add shared report history and recovery"
```

---

### Task RP-05: Admin report search, edit, restore, transfer, and attribution

**Files:**
- Create: `backend/webapp/api_v1/admin_reports.py`
- Modify: `backend/reports/persistence.py`
- Modify: `backend/reports/revisions.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `migrations/versions/20260812_0004_report_search_indexes.py`
- Create: `tests/integration/test_admin_report_api.py`
- Create: `tests/integration/test_admin_report_search.py`

**Interfaces:**
- Produces these exact Admin oversight paths: `GET /api/v1/admin/reports`, `GET /api/v1/admin/reports/{report_id}`, `GET /api/v1/admin/reports/{report_id}/revisions`, `GET /api/v1/admin/reports/{report_id}/revisions/{revision_number}`, `PATCH /api/v1/admin/reports/{report_id}`, `POST /api/v1/admin/reports/{report_id}/restore`, and `POST /api/v1/admin/reports/{report_id}/transfer`. RP-09 adds the two Admin export paths.
- Consumes: Admin elevation and step-up guards from ID-07; ID-06 idempotency; shared report policies/revision service from RP-02/RP-04.

- [ ] **Step 1: Write failing structured-search and protected-mutation tests**

```python
def test_admin_search_filters_structured_inmate_adc_number(api_client, elevated_admin_bearer_headers):
    response = api_client.get("/api/v1/admin/reports?inmate_adc_number=ADC900001",
                              headers=elevated_admin_bearer_headers)
    assert response.status_code == 200
    assert all(item["inmate_adc_numbers"] == ["ADC900001"]
               for item in response.json["data"]["items"])

def test_transfer_requires_purpose_scoped_step_up(api_client, elevated_admin_bearer_headers, report_id):
    headers = elevated_admin_bearer_headers | {"Idempotency-Key": "transfer-fictional-0001"}
    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/transfer",
        headers=headers,
        json={"new_owner_staff_id": str(uuid4()), "reason": "Correct fictional owner."})
    assert response.status_code == 403
    assert response.json["error"]["code"] == "step_up_required"

def test_admin_restore_uses_closed_source_revision_body(
        api_client, elevated_admin_bearer_headers,
        report_restore_step_up_headers, report_id):
    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/restore",
        headers=elevated_admin_bearer_headers
        | report_restore_step_up_headers
        | {"Idempotency-Key": "restore-fictional-0001"},
        json={"revision_number": 2})
    assert response.status_code == 200
    assert response.json["data"]["source_revision_number"] == 2
    assert response.json["data"]["revision_number"] > 2
```

- [ ] **Step 2: Run and confirm missing Admin report routes/indexes**

Run: `python -m pytest tests/integration/test_admin_report_api.py tests/integration/test_admin_report_search.py -v`

Expected: FAIL because Admin report routes and search indexes are absent.

- [ ] **Step 3: Add bounded indexed Admin search**

Set the search-index migration to `revision = "20260812_0004"` and `down_revision = "20260812_0003"`. Define one closed `AdminReportFilters` schema reused by search and RP-09 bulk export. Its optional fields are exactly `report_id`, `incident_id`, `reporting_staff_id`, `preparer_staff_id`, `incident_date_from`, `incident_date_to`, `created_at_from`, `created_at_to`, `inmate_first_name`, `inmate_middle_name`, `inmate_last_name`, `inmate_adc_number`, `category`, `facility`, `location`, `shift`, `status`, `last_editor_staff_id`, `modified_at_from`, and `modified_at_to`; unknown or empty-string query fields fail as `400 validation_failed`. Apply explicit sort allowlists, opaque cursor, default 50, maximum 100. Audit one bounded search event containing normalized filter names and result count, not submitted values, query text, inmate data, or report contents.

- [ ] **Step 4: Reuse revision services for Admin editing**

Admin save calls `save_report(session, actor, report_id, content, base_revision_number, reason="admin_edit")`; its closed body contains only `content` and `base_revision_number`. Restore is exactly `POST /api/v1/admin/reports/{report_id}/restore` with the closed body `{"revision_number": 2}`, requires purpose `report_restore`, and calls the shared `restore_report()` service to create a new `restored` revision referring to the immutable source. Transfer requires `report_transfer` and the closed body `new_owner_staff_id`, optional `new_preparer_staff_id`, and nonblank `reason` up to 500 characters; it verifies active targets, locks affected rows, replaces access relationships transactionally, and creates an ownership revision plus audit event. Every mutation claims/completes its ID-06 idempotency key in that same transaction. Opening another employee report writes `report.viewed_by_admin`.

Revision list/detail responses expose immutable revision number, reason, source revision when applicable, editor account/staff UUIDs, editor display name/rank snapshot, created time, content hash, and exact content only on authorized detail. They never expose audit internals, PIN/session data, or a delete/overwrite operation.

- [ ] **Step 5: Add Admin report OpenAPI contracts**

Document every exact path above, server-side Admin elevation, the `X-Admin-Step-Up` header, closed request/response schemas, exact filters, attribution banner fields, conflict shape, restore, and transfer. Add route-contract tests that reject the obsolete `/revisions/{revision_number}/restore` shape. Do not define an elevation token/header or delete endpoints.

- [ ] **Step 6: Run focused authorization/search tests**

Run: `python -m pytest tests/integration/test_admin_report_api.py tests/integration/test_admin_report_search.py tests/integration/test_report_concurrency.py tests/unit/test_report_policy.py -v`

Expected: PASS; Users cannot discover the routes and expired/wrong-purpose grants are rejected.

- [ ] **Step 7: Commit Admin report oversight**

```bash
git add backend/webapp/api_v1/admin_reports.py backend/reports/persistence.py backend/reports/revisions.py backend/webapp/api_v1/__init__.py openapi/access-v1.yaml migrations/versions/20260812_0004_report_search_indexes.py tests/integration/test_admin_report_api.py tests/integration/test_admin_report_search.py
git commit -m "feat: add attributed admin report oversight"
```

---

### Task RP-06: AI-job idempotency integration and transactional outbox

**Files:**
- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Create: `backend/persistence/models/jobs.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260812_0005_jobs_exports.py`
- Create: `backend/jobs/service.py`
- Create: `backend/jobs/outbox.py`
- Create: `backend/webapp/api_v1/jobs.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_idempotency_service.py`
- Create: `tests/integration/test_job_submission.py`
- Create: `tests/integration/test_job_redelivery.py`

**Interfaces:**
- Consumes: ID-06 `IdempotencyRecord`, `claim_idempotency()`, and `complete_idempotency()`.
- Produces: `AiJob`, `TaskOutbox`, `Export`, `submit_job()`, `claim_job()`, `apply_job_result()`, and AI submission/status routes.
- Consumed by: dispatcher/worker in RP-07 and Access `modJobs`.

- [ ] **Step 1: Write failing idempotency and outbox atomicity tests**

```python
def test_same_idempotency_key_returns_same_job(api_client, owner_bearer_headers, incident_id):
    headers = owner_bearer_headers | {"Idempotency-Key": "job-fictional-0001"}
    first = api_client.post(f"/api/v1/incidents/{incident_id}/jobs/classify",
                            headers=headers, json={"base_revision_number": 1})
    second = api_client.post(f"/api/v1/incidents/{incident_id}/jobs/classify",
                             headers=headers, json={"base_revision_number": 1})
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json["data"]["id"] == second.json["data"]["id"]

def test_changed_payload_with_same_key_conflicts(api_client, owner_bearer_headers, incident_id):
    headers = owner_bearer_headers | {"Idempotency-Key": "job-fictional-0002"}
    api_client.post(f"/api/v1/incidents/{incident_id}/jobs/extract",
                    headers=headers, json={"base_revision_number": 1})
    response = api_client.post(f"/api/v1/incidents/{incident_id}/jobs/extract",
                               headers=headers, json={"base_revision_number": 2})
    assert response.status_code == 409
    assert response.json["error"]["code"] == "idempotency_conflict"
```

- [ ] **Step 2: Run and observe missing job persistence/routes**

Run: `python -m pytest tests/unit/test_idempotency_service.py tests/integration/test_job_submission.py tests/integration/test_job_redelivery.py -v`

Expected: FAIL because AI job/outbox/export models and job routes do not exist; the shared ID-06 idempotency service already exists and its focused tests remain green.

- [ ] **Step 3: Implement the migration and bounded records**

Add `google-cloud-tasks>=2.23,<3.0` to both runtime requirement files. Set the job migration to `revision = "20260812_0005"` and `down_revision = "20260812_0004"`. Create approved AI job/export fields and constraints plus `task_outbox(id, ai_job_id, state, attempts, available_at, dispatched_at, last_error_code, created_at)`. Job submissions claim the ID-06 idempotency record with a normalized request SHA-256 and store only the stable AI job ID in its response reference; never store raw authorization headers. Add queue-state, requested-actor, incident/report, expiry, and export lookup indexes.

- [ ] **Step 4: Implement transactional job submission and result guards**

In one transaction: authorize incident/revision, claim idempotency, create queued job, create outbox row, write safe audit, and commit. `claim_job()` uses `FOR UPDATE SKIP LOCKED`. `apply_job_result()` rejects a stale incident base revision with `job_result_conflict`; ordinary Cloud Tasks redelivery can apply at most one durable result.

- [ ] **Step 5: Register job submission/status routes and OpenAPI**

Add classify, extract, generate, disciplinary submission paths and `GET /api/v1/jobs/{job_id}`. Return stable stages `queued`, `classifying`, `extracting`, `validating`, `generating`, `disciplinary`, `completed`, and `failed`. Only the requesting actor with incident access or an Admin may read a job.

- [ ] **Step 6: Run focused migration/idempotency tests**

Run: `python -m pytest tests/unit/test_idempotency_service.py tests/integration/test_job_submission.py tests/integration/test_job_redelivery.py tests/integration/test_report_migration.py -v`

Expected: PASS; rollback leaves neither orphan job nor outbox row.

- [ ] **Step 7: Commit durable job submission**

```bash
git add requirements.txt backend/requirements.txt backend/persistence/models/jobs.py backend/persistence/models/__init__.py migrations/versions/20260812_0005_jobs_exports.py backend/jobs/service.py backend/jobs/outbox.py backend/webapp/api_v1/jobs.py backend/webapp/api_v1/__init__.py openapi/access-v1.yaml tests/unit/test_idempotency_service.py tests/integration/test_job_submission.py tests/integration/test_job_redelivery.py
git commit -m "feat: add durable idempotent ai jobs"
```

---

### Task RP-07: Private worker and Cloud Tasks dispatcher

**Files:**
- Create: `backend/jobs/dispatcher.py`
- Create: `backend/worker/__init__.py`
- Create: `backend/worker/app.py`
- Create: `backend/worker/routes.py`
- Create: `scripts/dispatch_outbox.py`
- Modify: `Dockerfile`
- Create: `tests/unit/test_task_dispatcher.py`
- Create: `tests/unit/test_worker_routes.py`
- Create: `tests/integration/test_worker_pipeline.py`

**Interfaces:**
- Produces: `dispatch_pending(limit: int = 100) -> DispatchSummary`, worker `POST /internal/jobs/{job_id}/run`, and `python scripts/dispatch_outbox.py --limit 100`.
- Consumes: RP-03 route-neutral report services and RP-06 job/outbox services.

- [ ] **Step 1: Write failing dispatcher and worker-auth tests**

```python
def test_dispatcher_uses_oidc_and_stable_task_name(fake_tasks_client, queued_outbox):
    result = dispatch_pending(limit=10, client=fake_tasks_client)
    task = fake_tasks_client.created[0]
    assert result.dispatched == 1
    assert task.http_request.oidc_token.service_account_email == "task-invoker@example.invalid"
    assert task.name.endswith(str(queued_outbox.ai_job_id))

def test_worker_rejects_request_without_cloud_tasks_metadata(worker_client):
    response = worker_client.post(f"/internal/jobs/{uuid4()}/run")
    assert response.status_code == 401
```

- [ ] **Step 2: Run and confirm missing dispatcher/worker failures**

Run: `python -m pytest tests/unit/test_task_dispatcher.py tests/unit/test_worker_routes.py tests/integration/test_worker_pipeline.py -v`

Expected: FAIL because dispatcher and worker application do not exist.

- [ ] **Step 3: Implement Cloud Tasks creation after database commit**

Build deterministic task names from environment project/region/queue and job UUID. POST only `{"job_id":"00000000-0000-4000-8000-000000000001"}`-shaped JSON to the configured private worker URL with the task-invoker service account OIDC token and audience equal to the worker origin. Map already-exists to dispatched success; retry only safe transient API errors and store bounded error codes.

- [ ] **Step 4: Implement the private worker entry point**

Cloud Run IAM is the worker authentication boundary; the application additionally requires Cloud Tasks metadata headers and validates the route job ID against the JSON body. It claims one job, executes the existing classifier/extractor/generator adapter, writes stable progress, validates output, applies results through revision services, and records safe terminal failure categories. Deterministic validation/authorization failures return 2xx after recording terminal failure so Cloud Tasks does not retry them. Terraform tests in OP-04 prove only the task-invoker service account has `run.invoker`; application headers are defense in depth and are never treated as a substitute for IAM.

- [ ] **Step 5: Document the narrow provider-crash limitation in code and metrics**

The dispatcher/job idempotency prevents duplicate submissions and durable result application. A worker process crash after Google accepts a request but before the result commits can repeat a provider call; increment `ai_provider_repeat_risk_total` on recovery attempts and never claim exactly-once external billing.

- [ ] **Step 6: Update Docker image entry points and run tests**

Copy `alembic.ini`, `migrations/`, and required root assets into the image. Keep API default command; Terraform supplies the worker command `gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 900 "backend.worker.app:create_worker_app()"`.

Run: `python -m pytest tests/unit/test_task_dispatcher.py tests/unit/test_worker_routes.py tests/integration/test_worker_pipeline.py tests/unit/test_retry.py -v`

Expected: PASS without Google credentials; fake Tasks and fake report engine receive one call.

- [ ] **Step 7: Commit dispatcher and worker**

```bash
git add backend/jobs/dispatcher.py backend/worker/__init__.py backend/worker/app.py backend/worker/routes.py scripts/dispatch_outbox.py Dockerfile tests/unit/test_task_dispatcher.py tests/unit/test_worker_routes.py tests/integration/test_worker_pipeline.py
git commit -m "feat: add private report job worker"
```

---

### Task RP-08: Policy Expert `/api/v1` contract

**Files:**
- Modify: `backend/webapp/routes/chat.py`
- Create: `backend/webapp/api_v1/policy.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_policy_v1.py`
- Create: `tests/contract/test_policy_examples.py`

**Interfaces:**
- Consumes: ID-06 transactional idempotency to prevent a repeated key from issuing a second synchronous provider request.
- Produces: `clean_policy_history(raw: object) -> list[dict[str, str]]` and `POST /api/v1/policy/questions`.
- Preserves: existing answer, citations, sources, retrieved-source behavior and browser chat route.

- [ ] **Step 1: Write failing bounded-history and safe-error tests**

```python
def test_policy_v1_passes_only_bounded_clean_history(api_client, user_bearer_headers, monkeypatch):
    captured = {}
    monkeypatch.setattr("backend.webapp.api_v1.policy.answer_question",
                        lambda question, history: captured.update(history=history) or
                        {"answer": "Fictional answer.", "citations": [], "sources": []})
    history = [{"question": f"Question {index}", "answer": "A" * 100}
               for index in range(10)]
    headers = user_bearer_headers | {"Idempotency-Key": "policy-fictional-0001"}
    response = api_client.post("/api/v1/policy/questions", headers=headers,
                               json={"question": "What does the fictional policy say?",
                                     "history": history})
    assert response.status_code == 200
    assert len(captured["history"]) <= 6
```

- [ ] **Step 2: Run and confirm the route is missing**

Run: `python -m pytest tests/unit/test_policy_v1.py tests/contract/test_policy_examples.py -v`

Expected: FAIL with 404 or missing module.

- [ ] **Step 3: Share history cleaning and implement the synchronous route**

Promote `_clean_history` without changing current limits. Require `Idempotency-Key`, hash the normalized question/history without logging it, and claim ID-06 idempotency before calling the provider. The record stores only request hash, result status, latency bucket, and response SHA-256—never question, answer, citation passage, or source text. A duplicate key while the first call is running returns `409 request_in_progress`; a completed duplicate returns `409 idempotent_response_unavailable` and never repeats the provider call because the sensitive response is deliberately not persisted. The client may ask again only through a new explicit submission/key. Validate one question, enforce a 90-second server budget, call `answer_question`, return citations/source titles/passages, and audit identifiers/latency/result only. Translate `classify_error()` categories to stable `/api/v1` errors and never persist the question or answer in Cloud SQL, audit, or ordinary logs.

- [ ] **Step 4: Add OpenAPI examples and run policy regressions**

Run: `python -m pytest tests/unit/test_policy_v1.py tests/contract/test_policy_examples.py tests/unit/test_chat_history.py tests/unit/test_chat_errors.py tests/unit/test_citations.py tests/unit/test_retrieval.py -v`

Expected: PASS; browser response shapes remain unchanged.

- [ ] **Step 5: Commit Policy Expert API**

```bash
git add backend/webapp/routes/chat.py backend/webapp/api_v1/policy.py backend/webapp/api_v1/__init__.py openapi/access-v1.yaml tests/unit/test_policy_v1.py tests/contract/test_policy_examples.py
git commit -m "feat: expose cited policy expert api"
```

---

### Task RP-09: Deterministic single and bounded bulk Word exports

**Files:**
- Create: `backend/reports/deterministic_docx.py`
- Create: `backend/reports/export_service.py`
- Modify: `backend/webapp/api_v1/reports.py`
- Modify: `backend/webapp/api_v1/admin_reports.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_deterministic_docx.py`
- Create: `tests/integration/test_export_api.py`
- Create: `tests/integration/test_admin_bulk_export.py`

**Interfaces:**
- Produces: `normalize_docx_bytes(raw: bytes) -> bytes`, `export_report_docx()`, `export_reports_zip()`, ordinary `POST /api/v1/reports/{report_id}/export-docx?revision={positive_integer}`, Admin `POST /api/v1/admin/reports/{report_id}/export-docx?revision={positive_integer}`, and `POST /api/v1/admin/reports/bulk-export` capped at 100 documents.
- Consumes: explicit immutable report revisions and the existing `fill_template()`.

- [ ] **Step 1: Write failing deterministic/idempotent export tests**

```python
def test_docx_normalization_is_byte_stable(fictional_docx_bytes):
    first = normalize_docx_bytes(fictional_docx_bytes)
    second = normalize_docx_bytes(fictional_docx_bytes)
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()

def test_same_export_key_returns_one_export_record(api_client, owner_bearer_headers, report_id):
    headers = owner_bearer_headers | {"Idempotency-Key": "export-fictional-0001"}
    first = api_client.post(f"/api/v1/reports/{report_id}/export-docx?revision=2",
                            headers=headers)
    second = api_client.post(f"/api/v1/reports/{report_id}/export-docx?revision=2",
                             headers=headers)
    assert first.status_code == second.status_code == 200
    assert hashlib.sha256(first.data).digest() == hashlib.sha256(second.data).digest()

def test_admin_single_export_uses_admin_route_and_explicit_revision(
        api_client, elevated_admin_bearer_headers, report_id):
    response = api_client.post(
        f"/api/v1/admin/reports/{report_id}/export-docx?revision=2",
        headers=elevated_admin_bearer_headers
        | {"Idempotency-Key": "admin-export-fictional-0001"})
    assert response.status_code == 200
    assert response.headers["X-Report-Revision"] == "2"

def test_bulk_export_rejects_more_than_one_hundred_matches(
        api_client, elevated_admin_bearer_headers, bulk_export_step_up_headers):
    response = api_client.post(
        "/api/v1/admin/reports/bulk-export",
        headers=elevated_admin_bearer_headers
        | bulk_export_step_up_headers
        | {"Idempotency-Key": "bulk-export-fictional-0001"},
        json={
            "selection": {"mode": "filters", "filters": {"status": "Completed"}},
            "revision_selection": "current_at_request",
            "reason": "Fictional records request fixture.",
        })
    assert response.status_code == 409
    assert response.json["error"]["code"] == "bulk_export_limit_exceeded"
```

- [ ] **Step 2: Run and confirm missing deterministic export service**

Run: `python -m pytest tests/unit/test_deterministic_docx.py tests/integration/test_export_api.py tests/integration/test_admin_bulk_export.py -v`

Expected: FAIL because deterministic normalization and versioned export routes are absent.

- [ ] **Step 3: Normalize volatile ZIP metadata and own cleanup**

Read every DOCX ZIP member, sort by name, preserve content, compression type, permissions, comments, and extra fields, and rewrite ZIP entry timestamps to `(1980, 1, 1, 0, 0, 0)` before hashing. Normalize volatile `docProps/core.xml` created/modified values to the saved report revision timestamp in UTC and use that same source value on every regeneration. Pass a deep copy of revision content into `fill_template()` because it mutates metadata. Use a temporary directory and response-close cleanup.

- [ ] **Step 4: Implement single export metadata and audit**

Require the positive integer `revision` query parameter on both exact single-export paths; do not accept it in a body, infer latest, or silently coerce malformed values. Authorize the exact immutable revision, create deterministic bytes, insert one `exports` row with SHA-256/size/MIME/name/template version, append the route-appropriate User/Admin audit action, and stream with `Content-Disposition`, `Digest`, `X-Export-ID`, `X-Report-Revision`, and `X-Template-Version`.

- [ ] **Step 5: Implement bounded Admin ZIP export**

Require `bulk_export` step-up and one of these two closed selection branches; every object sets `additionalProperties: false` in OpenAPI:

```json
{"selection":{"mode":"report_ids","report_ids":["00000000-0000-4000-8000-000000000001"]},"revision_selection":"current_at_request","reason":"Fictional records request fixture."}
```

```json
{"selection":{"mode":"filters","filters":{"status":"Completed"}},"revision_selection":"current_at_request","reason":"Fictional records request fixture."}
```

The filter branch reuses RP-05 `AdminReportFilters`; the ID branch requires 1–100 unique UUIDs. `revision_selection` has the sole release-1 value `current_at_request`; do not accept a client limit or a floating `latest` value. In one repeatable-read transaction, resolve and persist the sorted `(report_id, revision_number)` selection before generating any document. Reject zero matches as `404 not_found` and more than 100 as `409 bulk_export_limit_exceeded` without generating a partial archive.

ZIP each successfully authorized DOCX plus `manifest.json` containing the resolved report/revision/export IDs, hashes, actor ID, normalized filter names (never filter values), persisted idempotency-record timestamp, failures, and reason. Sort report entries by report UUID and serialize the manifest with sorted keys so a repeated key regenerates the same bytes. A failure after the bounded selection is established may produce the documented partial-failure archive, but each failure remains explicit in the manifest and is never marked exported. Never store the ZIP or DOCX centrally after the response closes.

- [ ] **Step 6: Add OpenAPI binary contracts and run regressions**

Define both single routes and the bulk route in OpenAPI with explicit binary success content types, required `revision` query parameter, closed bulk body, `Idempotency-Key`, Admin elevation/step-up requirements, response headers, and stable errors including `bulk_export_limit_exceeded`.

Run: `python -m pytest tests/unit/test_deterministic_docx.py tests/integration/test_export_api.py tests/integration/test_admin_bulk_export.py tests/unit/test_filler_boxes.py -v`

Expected: PASS; database stores metadata only and temporary files are removed.

- [ ] **Step 7: Commit revision-exact exports**

```bash
git add backend/reports/deterministic_docx.py backend/reports/export_service.py backend/webapp/api_v1/reports.py backend/webapp/api_v1/admin_reports.py openapi/access-v1.yaml tests/unit/test_deterministic_docx.py tests/integration/test_export_api.py tests/integration/test_admin_bulk_export.py
git commit -m "feat: export audited report revisions"
```

---

### Task RP-10: Client policy, Admin overview/audit/health, legacy pilot controls, and full verification

**Files:**
- Create: `backend/build_info.py`
- Modify: `backend/webapp/api_v1/client_policy.py`
- Create: `backend/webapp/api_v1/admin_audit.py`
- Create: `backend/webapp/api_v1/admin_health.py`
- Modify: `backend/webapp/api_v1/admin.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `backend/webapp/app.py`
- Modify: `backend/webapp/routes/reports.py`
- Modify: `backend/pipeline/config.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_build_info.py`
- Modify: `tests/unit/test_client_policy.py`
- Create: `tests/integration/test_admin_audit_health.py`
- Create: `tests/integration/test_legacy_pilot_controls.py`
- Modify: `tests/contract/test_access_v1_openapi.py`
- Create: `tests/security/test_sensitive_logging.py`

**Interfaces:**
- Produces: public `GET /api/v1/client-policy`; elevated-Admin `GET /api/v1/admin/overview`, `GET /api/v1/admin/audit-events`, and `GET /api/v1/admin/health`; stepped-up `POST /api/v1/admin/audit-events/export`; sanitized dependency-health, queue, backup/restore-recency, and client-upgrade-required observability signals; build metadata; and the `LEGACY_REPORT_MODE` pilot/restriction control.
- Completes: report/API acceptance and Access contract fixture baseline.

- [ ] **Step 1: Write failing compatibility, safe-health, and legacy-control tests**

```python
def test_client_below_minimum_can_read_but_cannot_write(api_client, old_client_bearer_headers, report_id):
    assert api_client.get(f"/api/v1/reports/{report_id}",
                          headers=old_client_bearer_headers).status_code == 200
    response = api_client.patch(f"/api/v1/reports/{report_id}",
                                headers=old_client_bearer_headers | {"Idempotency-Key": "old-client-write-0001"},
                                json={"base_revision_number": 1,
                                      "content": fictional_report_content("Blocked update.")})
    assert response.status_code == 409
    assert response.json["error"]["code"] == "client_upgrade_required"

def test_admin_health_never_returns_secret_or_report_text(api_client, elevated_admin_bearer_headers):
    payload = api_client.get("/api/v1/admin/health",
                             headers=elevated_admin_bearer_headers).get_data(as_text=True).lower()
    assert "password" not in payload
    assert "fictional field notes" not in payload

def test_audit_export_requires_exact_step_up(
        api_client, elevated_admin_bearer_headers):
    response = api_client.post(
        "/api/v1/admin/audit-events/export",
        headers=elevated_admin_bearer_headers
        | {"Idempotency-Key": "audit-export-fictional-0001"},
        json={
            "filters": {"action_family": "report", "result": "success"},
            "format": "csv",
            "reason": "Fictional oversight fixture.",
        })
    assert response.status_code == 403
    assert response.json["error"]["code"] == "step_up_required"
```

- [ ] **Step 2: Run and observe missing operational contracts**

Run: `python -m pytest tests/unit/test_build_info.py tests/unit/test_client_policy.py tests/integration/test_admin_audit_health.py tests/integration/test_legacy_pilot_controls.py tests/security/test_sensitive_logging.py -v`

Expected: FAIL because the policy, Admin operational routes, and pilot write gate do not exist.

- [ ] **Step 3: Add reviewed release compatibility metadata**

`backend/build_info.py` adds `SOURCE_COMMIT`, `K_REVISION`, and current Alembic revision. Extend the ID-02 public bootstrap response to read validated runtime settings for `RELEASE_VERSION`, `LATEST_CLIENT_VERSION`, `MINIMUM_CLIENT_VERSION`, `MINIMUM_SERVER_VERSION`, `RELEASE_NOTES`, and `PUBLIC_BASE_URL`. Its closed safe response contains exactly `release_version`, `latest_client_version`, `minimum_client_version`, `minimum_server_version`, `api_version`, `release_notes`, `read_only_required`, the validated HTTPS origin-only `review_lab_origin`, and integer `field_notes_max_characters` equal to the ID-02 constant `30000`; it contains no package URL, package selection, expected hash, signer, bucket, token, credential, internal host, or handoff path for any caller. OP-09's authenticated update-grant response, not client policy, owns release/package selection metadata. Until OP-08 creates the authoritative source-controlled `release/version.json` registry and deployment projection, local/test defaults are explicit development sentinels and production startup fails if any version sentinel remains, if release notes are empty/over 500 characters, or if `PUBLIC_BASE_URL` is not a pathless HTTPS origin. `field_notes_max_characters` is not added to `release/version.json`, an environment setting, or that deployment projection. Middleware rejects writes below minimum while allowing sign-in/read/export.

- [ ] **Step 4: Implement bounded Admin overview, audit, and health**

Overview returns counts/recent safe actions. `GET /api/v1/admin/audit-events` supports the closed query filter set `occurred_at_from`, `occurred_at_to`, `actor_account_id`, `actor_staff_member_id`, `action_family`, `target_type`, `target_id`, and `result`, plus opaque cursor and limit (default 50, maximum 100). It returns immutable events with safe bounded details and never returns device/network hashes or request content.

`POST /api/v1/admin/audit-events/export` requires purpose `audit_export`, `Idempotency-Key`, and the closed body `filters` using that same filter schema, `format` with sole release-1 value `csv`, and nonblank `reason` up to 500 characters. Resolve a maximum of 10,000 rows in deterministic `(occurred_at,id)` order; reject larger matches as `409 audit_export_limit_exceeded`. Stream UTF-8 CSV with a fixed column allowlist and `Content-Disposition`, `Digest`, `X-Export-ID`, and `X-Audit-Row-Count`; never include event detail JSON, hashes, PIN/session fields, report text, inmate fields, or free-form request data. Audit both the bounded search and export using filter names/count only; export is itself idempotent and audited.

Health reports Operational/Degraded/Unavailable for database, migration, AI configuration, policy search, queue age/depth, latest backup metadata, and last restore exercise; it never controls infrastructure. Within RP-10's existing allowed files, emit the sanitized signal types `dependency_health`, `queue_health`, `backup_restore_health`, and `client_upgrade_required`. Their values are limited respectively to stable dependency/result/latency-bucket fields; queue result/depth/oldest-age plus job-type/stage/result/latency buckets; backup/restore result and recency buckets; and result/parsed-client-version fields. Reuse ID-02's stable event fields/codes where applicable; include no report/request content, person/account/session/device/network identity, token, raw exception, SQL/query value, host, or secret. These RP-10 signals, ID-02 `request_event`, and RP-07 `ai_provider_repeat_risk_total` are the application producers consumed by OP-05; RP-09 produces no health contract.

- [ ] **Step 5: Add the legacy pilot write gate**

Define one environment contract, `LEGACY_REPORT_MODE`, with exact values `pilot_fallback` and `restricted`; default to `restricted`. In `pilot_fallback`, preserve the existing transient browser report workflow and display a persistent pilot-fallback warning, but never write its ordinary work into Cloud SQL or present it as centralized history. In `restricted`, legacy classify/extract/generate/disciplinary/download actions return a plain safe maintenance message. Neither mode accepts Access bearer tokens, creates a second durable report history, or changes approved Review Lab behavior. Emit a startup warning in `pilot_fallback`; reject every other value.

- [ ] **Step 6: Complete OpenAPI examples and sensitive-log scan**

Ensure every approved endpoint, header, enum, response, binary export, cursor, and error has a fictional example. Require operation-level `security: []` only on client policy, login, and renewal. Lock the exact nine-field public client policy, integer `field_notes_max_characters: 30000`, audit list/export paths, and `audit_export_limit_exceeded` response. The sensitive-log test captures `caplog` across auth, saves, jobs, policy, exports, Admin search, `dependency_health`, `queue_health`, `backup_restore_health`, `client_upgrade_required`, and failures and asserts supplied marker values never appear. `tests/integration/test_admin_audit_health.py` asserts those exact four sanitized RP-10 signal types and bounded fields, and asserts no RP-09 health field/source is referenced.

- [ ] **Step 7: Run all backend gates**

Run: `python -m pytest -q`

Run: `python -m pytest tests/integration tests/contract tests/security -v`

Run: `python scripts/optimize_images.py --check`

Run: `git diff --check`

Expected: all credential-free tests PASS; no OpenAPI validation errors, sensitive marker leaks, image drift, or whitespace errors.

- [ ] **Step 8: Run optional ADC parity only in the approved test project**

Run: `python tests/test_pipeline.py --demo all --output-dir tests/output/access-api-parity`

Run: `python tests/eval/run_eval.py --gate-only`

Expected: report artifacts and policy gate meet the existing baseline. Stop rather than running these commands if ADC points to production or the separate test Discovery Engine store is not confirmed.

- [ ] **Step 9: Commit report/API completion**

```bash
git add backend/build_info.py backend/webapp/api_v1/client_policy.py backend/webapp/api_v1/admin_audit.py backend/webapp/api_v1/admin_health.py backend/webapp/api_v1/admin.py backend/webapp/api_v1/__init__.py backend/webapp/app.py backend/webapp/routes/reports.py backend/pipeline/config.py openapi/access-v1.yaml tests/unit/test_build_info.py tests/unit/test_client_policy.py tests/integration/test_admin_audit_health.py tests/integration/test_legacy_pilot_controls.py tests/contract/test_access_v1_openapi.py tests/security/test_sensitive_logging.py
git commit -m "feat: complete access api operational contracts"
```

## Plan Acceptance Checklist

- [ ] Owner, preparer, unrelated User, and Admin authorization is tested for every report operation.
- [ ] Every successful save/status/AI/restore/recovery/transfer/Admin edit creates one immutable attributable revision.
- [ ] Stale saves and stale job results never overwrite current content.
- [ ] Repeated identical keys return one durable job/export result; changed payloads conflict.
- [ ] Worker restarts/redelivery preserve jobs and apply at most one durable result.
- [ ] Policy Expert preserves citations and stores no report fact/history automatically.
- [ ] Word bytes come from an explicit revision and only metadata persists centrally.
- [ ] Admin structured search, edit, restore, transfer, single/bulk export, audit, and health are bounded and attributed.
- [ ] Legacy browser behavior remains available only under the explicit pilot control and never authenticates `/api/v1`.
- [ ] Existing report, policy, validation, roster, Review Lab, and Word regression suites remain green.
