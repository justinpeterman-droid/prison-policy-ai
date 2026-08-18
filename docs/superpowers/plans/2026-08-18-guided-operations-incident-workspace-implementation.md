# Guided Operations Incident Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the incident-centered Reports library, six-step New Report workflow, Document Studio, populated digital forms, copy-to-records outputs, and physical-paperwork reminders on top of the existing incident/report/job services.

**Architecture:** PostgreSQL incidents gain official number/name fields, while deterministic services calculate officer-facing progress and build checklist-driven incident packets. New form catalog, packet, instance, physical-acknowledgment, and output-event models preserve provenance; `/api/web/v1` routes call the existing service layer, and the React client presents one canonical incident workspace rather than detached report documents.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, Alembic, PostgreSQL 17, Pydantic 2, React, TypeScript, React Router, TanStack Query, Zod, Vitest, React Testing Library, Playwright, and dedicated print HTML/CSS.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Global Constraints

- The incident is the digital folder; every officer report, copy-only output, form, fact, and history item stays under one incident ID.
- Official numbers use `YYYY-MM-NNN`; digit-only input is normalized, invalid months and duplicates are rejected, and unnumbered drafts remain allowed.
- Officers do not edit `in_progress`, `completed`, or `archived` status.
- Workflow progress is server-derived.
- Required forms come from deterministic checklist rules.
- Official fields are populated only from a saved reviewed incident revision.
- Unknown facts remain blank or visibly marked; no form is completed with invented values.
- Supervisor Summary and Disciplinary Supplement are copy-only.
- Chain of Custody is physical-only and never receives a digital Print or Download action.
- All writes use idempotency and stale revisions return `409 revision_conflict`.
- Existing Access APIs and legacy Jinja report flow remain operational.

---

## File Map

```text
backend/persistence/models/reporting.py
backend/persistence/models/forms.py
backend/persistence/models/__init__.py
backend/reports/incident_numbers.py
backend/reports/workflow_progress.py
backend/reports/persistence.py
backend/forms/__init__.py
backend/forms/catalog.py
backend/forms/packets.py
backend/forms/population.py
backend/forms/physical.py
backend/forms/output_events.py
backend/webapp/api_v1/schemas/reporting.py
backend/webapp/web_api/incidents.py
backend/webapp/web_api/reports.py
backend/webapp/web_api/forms.py
backend/webapp/web_api/jobs.py
backend/webapp/web_api/__init__.py
migrations/versions/20260818_0007_incident_packets.py
openapi/web-v1.yaml
templates/paperwork/catalog.json
tests/unit/test_incident_numbers.py
tests/unit/test_incident_progress.py
tests/unit/test_form_catalog.py
tests/unit/test_incident_packets.py
tests/unit/test_form_population.py
tests/integration/test_web_incidents.py
tests/integration/test_form_packets.py
tests/contract/test_web_v1_openapi.py

frontend/web/src/features/incidents/
  api.ts
  schemas.ts
  progress.ts
  IncidentLibraryPage.tsx
  IncidentWorkspacePage.tsx
  IncidentOverview.tsx
  NewReportPage.tsx
  workflow/ReportWorkflowProvider.tsx
  workflow/WorkflowRail.tsx
  workflow/OfficerStep.tsx
  workflow/FieldNotesStep.tsx
  workflow/ReviewFactsStep.tsx
  workflow/MissingInformationStep.tsx
  workflow/ReportsStep.tsx
  workflow/FormsExportStep.tsx
  reports/OfficerReportsPanel.tsx
  reports/CopyToRecordsPanel.tsx
  forms/PacketInspector.tsx
  forms/FormViewer.tsx
  forms/PhysicalPaperworkCard.tsx
  history/IncidentHistoryPanel.tsx
frontend/web/src/print/IncidentPacketPrint.tsx
frontend/web/tests/e2e/incident-workflow.spec.ts
frontend/web/tests/e2e/copy-and-physical.spec.ts
```

## Shared Interfaces Produced by This Plan

```python
INCIDENT_NUMBER_RE = re.compile(r"^(?P<year>[0-9]{4})-(?P<month>0[1-9]|1[0-2])-(?P<sequence>[0-9]{3})$")


def normalize_incident_number(value: str | None) -> str | None: ...

def suggest_incident_name(*, location: str | None, category_label: str | None) -> str | None: ...

def calculate_workflow_progress(...) -> WorkflowProgress: ...

def list_incident_summaries(...) -> Page[IncidentSummary]: ...

def build_incident_packet(...) -> list[IncidentPacketItemView]: ...

def populate_form_instance(...) -> FormInstanceView: ...

def acknowledge_physical_paperwork(...) -> PhysicalPaperworkAcknowledgment: ...

def record_document_action(...) -> DocumentActionEvent: ...
```

Frontend summary shape:

```ts
export interface IncidentSummary {
  incidentId: string;
  incidentNumber: string | null;
  incidentName: string | null;
  incidentDate: string | null;
  category: string | null;
  location: string | null;
  reportingOfficers: Array<{ staffId: string; displayName: string }>;
  relationship: "reporting_officer" | "preparer" | "both";
  progress: WorkflowProgress;
  officerReportCount: number;
  requiredPaperworkCount: number;
  updatedAt: string;
}
```

### Task 1: Add incident number/name and packet persistence

**Files:**
- Modify: `backend/persistence/models/reporting.py`
- Create: `backend/persistence/models/forms.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260818_0007_incident_packets.py`
- Test: `tests/unit/test_incident_packet_models.py`
- Test: `tests/integration/test_incident_packet_migration.py`

**Interfaces:**
- Consumes: existing `Incident`, `Report`, `StaffMember`, `Account`, and `IncidentRevision` IDs.
- Produces: incident metadata and form/packet persistence.

- [ ] **Step 1: Write failing model-contract tests**

Assert `Incident.incident_number` is nullable, length 11, and protected by a partial unique index; `incident_name` is nullable length 160. Assert these tables exist:

```text
form_templates
incident_packet_items
form_instances
physical_paperwork_acknowledgments
document_action_events
```

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_incident_packet_models.py -v
```

- [ ] **Step 3: Extend Incident**

```python
incident_number: Mapped[str | None] = mapped_column(String(11))
incident_name: Mapped[str | None] = mapped_column(String(160))
```

Add:

```python
Index(
    "uq_incidents_incident_number",
    "incident_number",
    unique=True,
    postgresql_where=text("incident_number IS NOT NULL"),
)
```

- [ ] **Step 4: Implement packet models**

Use closed check constraints:

```text
output_kind IN ('digital_document','physical_only')
packet_group IN ('required','recommended','additional')
packet_state IN ('selected','not_applicable','removed')
action IN ('preview','print','download_word','download_pdf','copy_text')
```

`FormInstance` is one-to-one with `IncidentPacketItem`, records `source_incident_revision_number`, `populated_fields`, `manual_fields`, `completeness`, and `updated_at`. `PhysicalPaperworkAcknowledgment.packet_item_id` is unique.

- [ ] **Step 5: Add migration and lifecycle test**

Use:

```python
revision = "20260818_0007"
down_revision = "20260818_0006"
```

Verify upgrade → downgrade → upgrade.

- [ ] **Step 6: Commit**

```bash
git add backend/persistence/models migrations/versions/20260818_0007_incident_packets.py tests/unit/test_incident_packet_models.py tests/integration/test_incident_packet_migration.py
git commit -m "feat: add incident packet persistence"
```

### Task 2: Implement official incident-number and descriptive-name rules

**Files:**
- Create: `backend/reports/incident_numbers.py`
- Modify: `backend/webapp/api_v1/schemas/reporting.py`
- Modify: `backend/reports/persistence.py`
- Modify: `backend/webapp/api_v1/incidents.py`
- Test: `tests/unit/test_incident_numbers.py`
- Test: `tests/integration/test_incident_number_uniqueness.py`

**Interfaces:**
- Produces: `normalize_incident_number()` and `suggest_incident_name()`.

- [ ] **Step 1: Write failing normalization tests**

```python
@pytest.mark.parametrize(("raw", "expected"), [
    ("2026-08-029", "2026-08-029"),
    ("202608029", "2026-08-029"),
    (" 2026-08-029 ", "2026-08-029"),
    ("", None),
    (None, None),
])
def test_normalize_incident_number(raw, expected): ...

@pytest.mark.parametrize("raw", ["2026-13-001", "26-08-001", "2026-8-001", "2026-08-01", "2026-08-1000"])
def test_rejects_invalid_incident_number(raw): ...
```

- [ ] **Step 2: Implement normalization**

```python
def normalize_incident_number(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    compact = value.strip()
    if compact.isdigit() and len(compact) == 9:
        compact = f"{compact[:4]}-{compact[4:6]}-{compact[6:]}"
    if not INCIDENT_NUMBER_RE.fullmatch(compact):
        raise ValueError("incident number must use YYYY-MM-NNN")
    return compact
```

- [ ] **Step 3: Extend save schemas and revision snapshots**

Add `incident_number` and `incident_name` to allowed fields, Pydantic schemas, `IncidentRevision` snapshots, view serialization, change tracking, and OpenAPI examples. Trim names, permit null, and enforce 160 characters.

- [ ] **Step 4: Map duplicate numbers to a stable error**

A unique-index conflict returns:

```json
{"code":"incident_number_conflict","message":"This incident number is already in use."}
```

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_incident_numbers.py tests/integration/test_incident_number_uniqueness.py tests/integration/test_incident_api.py -v
git add backend/reports/incident_numbers.py backend/webapp/api_v1/schemas/reporting.py backend/reports/persistence.py backend/webapp/api_v1/incidents.py tests
git commit -m "feat: add official incident identity"
```

### Task 3: Add deterministic workflow progress

**Files:**
- Create: `backend/reports/workflow_progress.py`
- Test: `tests/unit/test_incident_progress.py`

**Interfaces:**
- Produces: `WorkflowProgress` and `calculate_workflow_progress()`.

- [ ] **Step 1: Write the complete precedence table as tests**

Test this order:

1. Any successful print/download action → `printed_or_exported`.
2. Any queued/running classify/extract/generate job → `generating_reports`.
3. Blocking validation gaps → `needs_information`.
4. Reviewed facts with no generated reports → `ready_to_generate`.
5. Generated editable reports not yet acknowledged/reviewed → `ready_to_review`.
6. Required digital forms complete and no physical task missing → `ready_to_print`.
7. Otherwise, nonempty field notes → `field_notes_started`.

- [ ] **Step 2: Implement immutable result**

```python
@dataclass(frozen=True)
class WorkflowProgress:
    code: str
    label: str
    blocking_count: int = 0
```

Use explicit booleans derived by a query adapter; the pure function performs no database calls.

- [ ] **Step 3: Verify and commit**

```bash
python -m pytest tests/unit/test_incident_progress.py -v
git add backend/reports/workflow_progress.py tests/unit/test_incident_progress.py
git commit -m "feat: calculate officer workflow progress"
```

### Task 4: Add incident-centered listing and search service

**Files:**
- Modify: `backend/reports/persistence.py`
- Create: `backend/webapp/web_api/incidents.py`
- Test: `tests/integration/test_web_incident_list.py`

**Interfaces:**
- Consumes: Task 3 progress calculator.
- Produces: `list_incident_summaries()` and `GET /api/web/v1/incidents`.

- [ ] **Step 1: Write failing authorization and aggregation tests**

Cover reporting-officer, preparer, both, unrelated-user exclusion, admin inclusion, one row per incident, report counts, packet counts, search by number/name/officer/category/location/date, and cursor pagination.

- [ ] **Step 2: Implement query filters**

Accepted query keys:

```text
q
relationship=all|reporting|prepared
category
date_from
date_to
location
limit
cursor
```

`q` is normalized and searches incident number, incident name, and authorized staff display names. Limit is 1–50, default 25.

- [ ] **Step 3: Serialize a stable summary**

Return exactly the `IncidentSummary` shape in this plan header plus `next_cursor`.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/integration/test_web_incident_list.py -v
git add backend/reports/persistence.py backend/webapp/web_api/incidents.py tests/integration/test_web_incident_list.py
git commit -m "feat: add incident-centered report library API"
```

### Task 5: Create the sanitized form catalog

**Files:**
- Create: `templates/paperwork/catalog.json`
- Create: `backend/forms/catalog.py`
- Create: `backend/forms/__init__.py`
- Test: `tests/unit/test_form_catalog.py`

**Interfaces:**
- Produces: `FormTemplateDefinition`, `load_form_catalog()`, and `sync_form_catalog()`.

- [ ] **Step 1: Write a failing catalog test**

Assert unique codes, allowed output kinds, no absolute paths, no real person data, and these initial entries:

```text
form_005_409
over_letter
chain_of_custody_physical
medical_documentation_checklist
additional_officer_statement
```

Use the exact code `cover_letter`, correcting the obvious spelling in the list above during implementation.

- [ ] **Step 2: Create sanitized catalog JSON**

Example entry:

```json
{
  "code": "chain_of_custody_physical",
  "name": "Chain of Custody Form",
  "category": "evidence",
  "output_kind": "physical_only",
  "revision_label": "official carbon-copy form",
  "active": true,
  "definition": {
    "obtain_from": "approved paperwork location",
    "guidance_fields": ["incident_number", "incident_date", "reporting_officer", "evidence_description", "recovery_location"]
  }
}
```

- [ ] **Step 3: Implement strict loader and sync**

Reject unknown keys, duplicate codes, invalid output kinds, missing names, or path traversal. Sync creates/updates active database rows but never deletes historical templates; removed catalog entries become inactive.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/unit/test_form_catalog.py -v
git add backend/forms templates/paperwork/catalog.json tests/unit/test_form_catalog.py
git commit -m "feat: add incident form catalog"
```

### Task 6: Build deterministic required/recommended/additional packets

**Files:**
- Create: `backend/forms/packets.py`
- Test: `tests/unit/test_incident_packets.py`
- Test: `tests/integration/test_form_packets.py`

**Interfaces:**
- Consumes: `incident_checklist_v2.json`, catalog, saved incident revision.
- Produces: `build_incident_packet()`, `add_additional_form()`, `remove_recommended_form()`, and `mark_not_applicable()`.

- [ ] **Step 1: Write failing packet tests**

Cover deterministic checklist requirements, idempotent rebuild, physical Chain of Custody selection for evidence conditions, recommended form removal, additional form add, required-form removal refusal, and required not-applicable reason.

- [ ] **Step 2: Define packet view**

```python
@dataclass(frozen=True)
class IncidentPacketItemView:
    packet_item_id: UUID
    template_code: str
    name: str
    output_kind: str
    packet_group: str
    state: str
    selection_reason: str
    not_applicable_reason: str | None
    reporting_staff_member_id: UUID | None
```

- [ ] **Step 3: Implement checklist mapping**

Map authoritative checklist form names to catalog codes in one closed dictionary. Unknown required names raise a configuration error and block packet generation; they are never silently skipped.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/unit/test_incident_packets.py tests/integration/test_form_packets.py -v
git add backend/forms/packets.py tests/unit/test_incident_packets.py tests/integration/test_form_packets.py
git commit -m "feat: build checklist-driven incident packets"
```

### Task 7: Populate digital form instances from reviewed facts

**Files:**
- Create: `backend/forms/population.py`
- Modify: `backend/reports/export_service.py`
- Test: `tests/unit/test_form_population.py`
- Test: `tests/integration/test_form_instance_population.py`

**Interfaces:**
- Produces: `populate_form_instance()` and `render_form_preview()`.

- [ ] **Step 1: Write failing provenance tests**

Assert population requires a saved incident revision, reads reviewed structured facts and gap answers, never reads unsaved raw request text, stores source revision number, leaves unknown fields null, reports missing fields, and produces the existing 005 data mapping without a second model call.

- [ ] **Step 2: Implement a closed field resolver**

```python
FIELD_RESOLVERS = {
    "incident_number": lambda snapshot: snapshot.get("incident_number"),
    "incident_date": lambda snapshot: snapshot.get("incident_date"),
    "incident_time": lambda snapshot: snapshot.get("incident_time"),
    "location": lambda snapshot: snapshot.get("location"),
    "category": lambda snapshot: snapshot.get("category"),
    "reporting_officer": resolve_reporting_officer,
    "narrative": resolve_saved_first_person_report,
}
```

Catalog fields not present in this map fail configuration validation.

- [ ] **Step 3: Store completeness**

```json
{"state":"missing_information","missing_fields":["reviewer_name"],"review_fields":["narrative"]}
```

Allowed states are `ready`, `needs_review`, and `missing_information`.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/unit/test_form_population.py tests/integration/test_form_instance_population.py tests/unit/test_deterministic_docx.py -v
git add backend/forms/population.py backend/reports/export_service.py tests
git commit -m "feat: populate incident forms from reviewed facts"
```

### Task 8: Add physical acknowledgment and document-action audit services

**Files:**
- Create: `backend/forms/physical.py`
- Create: `backend/forms/output_events.py`
- Test: `tests/unit/test_physical_paperwork.py`
- Test: `tests/unit/test_document_actions.py`

**Interfaces:**
- Produces: `acknowledge_physical_paperwork()`, `clear_physical_acknowledgment()`, and `record_document_action()`.

- [ ] **Step 1: Write failing restriction tests**

Assert physical-only packet items reject print/download, acknowledgments require selected physical items, actor/time are recorded, repeated acknowledgment is idempotent, and copy_text is accepted only for Supervisor Summary or Disciplinary Supplement.

- [ ] **Step 2: Implement closed action policy**

```python
def allowed_document_actions(output_kind: str) -> frozenset[str]:
    return {
        "digital_document": frozenset({"preview", "print", "download_word", "download_pdf"}),
        "physical_only": frozenset(),
    }[output_kind]
```

Copy-only report actions are validated against report type, not form output kind.

- [ ] **Step 3: Write protected audit events**

Use existing `AUDIT_WRITER` with bounded metadata: action, incident/report/packet IDs, result, request ID, client version. Do not duplicate narrative or form field content.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/unit/test_physical_paperwork.py tests/unit/test_document_actions.py -v
git add backend/forms/physical.py backend/forms/output_events.py tests/unit/test_physical_paperwork.py tests/unit/test_document_actions.py
git commit -m "feat: track physical and document actions"
```

### Task 9: Complete web incident, report, job, packet, and form routes

**Files:**
- Modify: `backend/webapp/web_api/incidents.py`
- Create: `backend/webapp/web_api/reports.py`
- Create: `backend/webapp/web_api/jobs.py`
- Create: `backend/webapp/web_api/forms.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_incidents.py`
- Test: `tests/integration/test_web_report_routes.py`
- Test: `tests/integration/test_web_form_routes.py`
- Test: `tests/contract/test_web_v1_openapi.py`

**Interfaces:**
- Consumes: Tasks 1–8 and existing report/job services.
- Produces: all browser APIs required by the incident client.

- [ ] **Step 1: Write failing route tests**

Cover create/get/save/revisions; classify/extract/generate job submission/status; report get/save/revisions/export; packet get/rebuild/add/remove/not-applicable; form populate/preview/download/action; physical guidance/acknowledge; and clean-text copy event.

- [ ] **Step 2: Reuse service functions directly**

Do not issue internal HTTP calls to `/api/v1`. Route adapters resolve the cookie actor and call the same Python services used by Access routes.

- [ ] **Step 3: Enforce metadata actions**

A report response includes:

```json
{"presentation":"copy_text","allowed_actions":["edit","copy_text"]}
```

for Supervisor Summary and Disciplinary Supplement. Digital documents include only supported preview/print/download actions. Physical items include guidance and acknowledgment actions only.

- [ ] **Step 4: Verify OpenAPI and integration**

```bash
python -m pytest tests/integration/test_web_incidents.py tests/integration/test_web_report_routes.py tests/integration/test_web_form_routes.py tests/contract/test_web_v1_openapi.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/web_api openapi/web-v1.yaml tests/integration tests/contract/test_web_v1_openapi.py
git commit -m "feat: expose incident workspace web APIs"
```

### Task 10: Build the incident library

**Files:**
- Create: `frontend/web/src/features/incidents/api.ts`
- Create: `frontend/web/src/features/incidents/schemas.ts`
- Create: `frontend/web/src/features/incidents/progress.ts`
- Create: `frontend/web/src/features/incidents/IncidentLibraryPage.tsx`
- Modify: `frontend/web/src/app/router.tsx`
- Test: `frontend/web/src/features/incidents/IncidentLibraryPage.test.tsx`

**Interfaces:**
- Consumes: `GET /api/web/v1/incidents`.
- Produces: incident-centered Reports route.

- [ ] **Step 1: Write failing UI tests**

Assert number before name, `Unnumbered Incident`, search, relationship filters, progress text, reporting officers, counts, pagination, empty state, and mobile card/desktop row semantics.

- [ ] **Step 2: Implement strict query schema**

Parse every summary with Zod and use query key:

```ts
["incidents", { q, relationship, category, dateFrom, dateTo, location, cursor }]
```

- [ ] **Step 3: Implement the page**

Use one Reports destination with filters `All incidents`, `I am a reporting officer`, and `I prepared for another officer`. No officer status filter or status control is rendered.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/incidents/IncidentLibraryPage.test.tsx
npm run typecheck
git add src/features/incidents src/app/router.tsx
git commit -m "feat: add incident-centered reports library"
```

### Task 11: Build the six-step New Report workflow and AI job flow

**Files:**
- Create: `frontend/web/src/features/incidents/NewReportPage.tsx`
- Create: `frontend/web/src/features/incidents/workflow/**`
- Test: `frontend/web/src/features/incidents/workflow/ReportWorkflowProvider.test.tsx`
- Test: `frontend/web/src/features/incidents/workflow/steps.test.tsx`

**Interfaces:**
- Consumes: browser incident/staff/job APIs.
- Produces: resumable six-step workflow.

- [ ] **Step 1: Write failing state-machine tests**

Test exact stages, cannot skip blocking gaps, switch steps without losing edits, autosave after 60 seconds idle, stale-save conflict preservation, resume job by ID, and no AI submission until explicit Continue.

- [ ] **Step 2: Implement reducer state**

```ts
interface ReportWorkflowState {
  incidentId: string | null;
  revision: number;
  activeStep: 1 | 2 | 3 | 4 | 5 | 6;
  reportingStaffIds: string[];
  fieldNotes: string;
  incidentNumber: string | null;
  incidentName: string | null;
  category: string | null;
  facts: Record<string, unknown>;
  gapAnswers: Record<string, unknown>;
  dirty: boolean;
  pendingJobId: string | null;
}
```

- [ ] **Step 3: Build stages**

Officer selection defaults to current user. Field Notes enforces 30,000 Unicode code points. Review Facts exposes editable AI suggestions and provenance. Missing Information renders server-defined controls. Reports and Forms & Export use saved outputs only.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/incidents/workflow
npm run typecheck
git add src/features/incidents/NewReportPage.tsx src/features/incidents/workflow
git commit -m "feat: add guided incident report workflow"
```

### Task 12: Build Document Studio, copy-only outputs, packet inspector, and form viewer

**Files:**
- Create: `frontend/web/src/features/incidents/IncidentWorkspacePage.tsx`
- Create: `frontend/web/src/features/incidents/IncidentOverview.tsx`
- Create: `frontend/web/src/features/incidents/reports/**`
- Create: `frontend/web/src/features/incidents/forms/**`
- Create: `frontend/web/src/features/incidents/history/IncidentHistoryPanel.tsx`
- Create: `frontend/web/src/print/IncidentPacketPrint.tsx`
- Test: corresponding component tests.

**Interfaces:**
- Consumes: Task 9 routes.
- Produces: Overview, Officer Reports, Copy to Records, Required Paperwork, Notes & Facts, and History tabs.

- [ ] **Step 1: Write failing presentation-policy tests**

Assert printable documents show only allowed actions, copy-only outputs show no Print/Download controls, physical forms show the required carbon-copy warning and no digital actions, copy uses plain text, and packet reasons are visible.

- [ ] **Step 2: Implement desktop Document Studio**

Use left workflow/tab rail, central document/editor surface, and right packet/completeness inspector. On tablet/mobile, inspector becomes a labelled drawer without losing state.

- [ ] **Step 3: Implement clean copy**

```ts
await navigator.clipboard.writeText(reportText);
```

After success, button label becomes `Copied` with a checkmark and an `aria-live="polite"` message. Record the copy event after clipboard success; a failed clipboard write does not record success.

- [ ] **Step 4: Implement physical card**

Display `PHYSICAL CARBON-COPY FORM REQUIRED`, approved obtain-from text, confirmed handwriting guidance, completion guidance, and acknowledgment actor/time. The component has no print or download props.

- [ ] **Step 5: Implement populated form viewer**

Render a paper-accurate preview with zoom, page navigation, completeness inspector, populated/missing/source sections, Edit Fields, Print, and supported downloads. Print uses dedicated markup, not a screenshot.

- [ ] **Step 6: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/incidents/reports src/features/incidents/forms
npm run typecheck
git add src/features/incidents src/print/IncidentPacketPrint.tsx
git commit -m "feat: add incident document studio"
```

### Task 13: Verify complete incident workflows and visual fidelity

**Files:**
- Create: `frontend/web/tests/e2e/incident-workflow.spec.ts`
- Create: `frontend/web/tests/e2e/copy-and-physical.spec.ts`
- Create: `frontend/web/tests/e2e/incident-responsive.spec.ts`
- Modify: `docs/design/guided-operations/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: incident-workspace release gate.

- [ ] **Step 1: Add end-to-end scenarios**

1. Sign in → Start New Incident → officers → field notes → classify/extract → answer gaps → generate → view populated 005 → print preview.
2. Open incident → edit Supervisor Summary → copy clean text → verify no Print button.
3. Chain of Custody → view guidance → acknowledge → verify actor/time.
4. Duplicate `2026-08-029` → stable conflict message.
5. Stale revision → local text preserved and conflict UI shown.

- [ ] **Step 2: Add visual checks**

Capture incident library, workflow, Document Studio, form viewer, copy state, and physical card at desktop, tablet, and mobile sizes. Compare to approved concepts and record fixes for layout, typography, palette, control depth, paper treatment, and responsive behavior.

- [ ] **Step 3: Run backend and frontend verification twice**

```bash
python -m pytest tests/unit/test_incident_* tests/unit/test_form_* tests/integration/test_web_incidents.py tests/integration/test_form_packets.py tests/contract/test_web_v1_openapi.py -v
cd frontend/web && npm run lint && npm run typecheck && npm run test && npm run build && npm run test:e2e && cd ../..
```

Run twice; both passes must be green.

- [ ] **Step 4: Commit**

```bash
git add frontend/web/tests/e2e docs/design/guided-operations/README.md README.md
git commit -m "test: verify guided incident workspace"
```

## Incident Workspace Completion Gate

- Incident numbers and names persist through every revision and form instance.
- The Reports page has one row/card per incident.
- Officers cannot change records-management status.
- Required forms are deterministic and explain selection reasons.
- Digital forms are sourced from saved reviewed facts.
- Copy-only and physical-only restrictions are enforced by metadata and tested.
- Access `/api/v1` report, incident, job, and export tests remain green.
- Desktop, tablet, mobile, keyboard, reduced-motion, print, and visual fidelity checks pass.
