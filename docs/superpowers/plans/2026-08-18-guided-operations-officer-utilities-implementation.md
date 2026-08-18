# Guided Operations Officer Utilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the officer Home dashboard, browser-fillable NCU Days Count, Forms Library, Policy Expert, and personal Account experience using secure shared services and print-accurate output.

**Architecture:** A generic revisioned operational-paperwork store persists typed Pydantic payloads without turning paperwork into incident reports. Count Sheet receives deterministic backend validation and frontend calculations; Forms Library reuses the form catalog, Policy Expert wraps the existing policy service, Account wraps browser-session services, and Home aggregates small authorized summaries rather than downloading full records.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, Alembic, PostgreSQL 17, Pydantic 2, React, TypeScript, TanStack Query, Zod, Vitest, React Testing Library, Playwright, and CSS print templates.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Global Constraints

- Home keeps Start New Incident as the only dominant action.
- Home includes a prominent Open Count Sheet action plus Policy Expert and Forms Library quick actions.
- Home excludes vanity metrics, complicated charts, admin queues, and technical AI details.
- Count Sheet reproduces the supplied source labels, rows, columns, totals, and operational reconciliation.
- Count Sheet inputs are non-negative whole numbers; empty cells remain blank in print unless a source-required zero is calculated.
- A reconciliation mismatch is shown and never silently corrected.
- Saved paperwork uses immutable revisions and stale writes return `409 revision_conflict`.
- Officers do not manage paperwork status.
- Forms Library never offers a digital substitute for a physical-only form.
- Policy Expert answers and citations are not automatically copied into incident facts.
- Account identity fields are read-only; staff corrections remain admin-only.
- No sensitive paperwork payload enters logs or browser localStorage.

---

## File Map

```text
backend/persistence/models/paperwork.py
backend/persistence/models/__init__.py
backend/paperwork/__init__.py
backend/paperwork/models.py
backend/paperwork/schemas.py
backend/paperwork/service.py
backend/paperwork/policy.py
backend/paperwork/count_sheet.py
backend/forms/library.py
backend/webapp/web_api/home.py
backend/webapp/web_api/paperwork.py
backend/webapp/web_api/forms.py
backend/webapp/web_api/policy.py
backend/webapp/web_api/account.py
backend/webapp/web_api/__init__.py
migrations/versions/20260818_0008_operational_paperwork.py
openapi/web-v1.yaml
templates/paperwork/count_sheet.json

tests/unit/test_paperwork_models.py
tests/unit/test_paperwork_service.py
tests/unit/test_count_sheet.py
tests/unit/test_forms_library.py
tests/integration/test_paperwork_api.py
tests/integration/test_web_policy.py
tests/integration/test_web_account.py
tests/integration/test_web_home.py

frontend/web/src/features/dashboard/
  api.ts
  HomePage.tsx
  ContinueIncidentCard.tsx
  QuickActions.tsx
  RecentIncidents.tsx
  FrequentForms.tsx
frontend/web/src/features/paperwork/count-sheet/
  api.ts
  schema.ts
  calculations.ts
  CountSheetPage.tsx
  CountGrid.tsx
  CountTotals.tsx
  CountReconciliation.tsx
  CountSheetPrint.tsx
frontend/web/src/features/forms-library/
  api.ts
  schemas.ts
  FormsLibraryPage.tsx
  FormCard.tsx
  FormSelectionBar.tsx
  FormPreviewDialog.tsx
frontend/web/src/features/policy/
  api.ts
  PolicyExpertPage.tsx
  CitationInspector.tsx
frontend/web/src/features/account/
  api.ts
  AccountPage.tsx
  ChangePinForm.tsx
  SessionList.tsx
frontend/web/tests/e2e/officer-home.spec.ts
frontend/web/tests/e2e/count-sheet.spec.ts
frontend/web/tests/e2e/forms-policy-account.spec.ts
```

## Shared Interfaces Produced by This Plan

```python
class PaperworkKind(str, Enum):
    COUNT_SHEET = "count_sheet"
    ASSIGNMENT_ROSTER = "assignment_roster"
    UNIFORM_INSPECTION = "uniform_inspection"
    METAL_DETECTOR_TEST = "metal_detector_test"
    PERIMETER_CHECK = "perimeter_check"
    RANDOM_SEARCH_LOG = "random_search_log"
    DETECTOR_SIGN_OUT = "detector_sign_out"

@dataclass(frozen=True)
class PaperworkView:
    record_id: UUID
    kind: PaperworkKind
    work_date: date
    shift: str | None
    current_revision_number: int
    payload: dict[str, object]
    created_by_staff_member_id: UUID
    last_editor_staff_member_id: UUID
    created_at: datetime
    updated_at: datetime


def save_paperwork_record(...) -> PaperworkView: ...
def get_paperwork_record(...) -> PaperworkView: ...
def list_paperwork_records(...) -> Page[PaperworkView]: ...
def get_paperwork_revision(...) -> PaperworkRevision: ...
def validate_count_sheet(payload: CountSheetRecordV1) -> CountSheetValidation: ...
```

### Task 1: Add generic revisioned operational-paperwork persistence

**Files:**
- Create: `backend/persistence/models/paperwork.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260818_0008_operational_paperwork.py`
- Test: `tests/unit/test_paperwork_models.py`
- Test: `tests/integration/test_paperwork_migration.py`

**Interfaces:**
- Produces: `PaperworkRecord` and `PaperworkRevision`.

- [ ] **Step 1: Write failing model tests**

Assert:

```text
paperwork_records
paperwork_revisions
```

`PaperworkRecord` contains kind, work_date, shift, current_revision_number, current_payload, creator, last editor, timestamps. `PaperworkRevision` has unique `(record_id, revision_number)`, editor, snapshot, changed_fields, reason, client_version, request_id, and created_at.

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_paperwork_models.py -v
```

- [ ] **Step 3: Implement closed kind/reason constraints**

```text
kind IN ('count_sheet','assignment_roster','uniform_inspection','metal_detector_test','perimeter_check','random_search_log','detector_sign_out')
reason IN ('autosave','manual_save','recovery','restored')
current_revision_number >= 1
```

- [ ] **Step 4: Add migration**

```python
revision = "20260818_0008"
down_revision = "20260818_0007"
```

Use indexes on `(kind, work_date, shift, id)`, creator/update, and updated timestamp.

- [ ] **Step 5: Verify migration lifecycle and commit**

```bash
python -m pytest tests/unit/test_paperwork_models.py tests/integration/test_paperwork_migration.py -v
alembic upgrade head
alembic downgrade 20260818_0007
alembic upgrade head
git add backend/persistence/models migrations/versions/20260818_0008_operational_paperwork.py tests
git commit -m "feat: add operational paperwork persistence"
```

### Task 2: Implement typed paperwork schemas, access policy, revisions, and idempotent saves

**Files:**
- Create: `backend/paperwork/__init__.py`
- Create: `backend/paperwork/models.py`
- Create: `backend/paperwork/schemas.py`
- Create: `backend/paperwork/policy.py`
- Create: `backend/paperwork/service.py`
- Test: `tests/unit/test_paperwork_service.py`
- Test: `tests/integration/test_paperwork_revisions.py`

**Interfaces:**
- Produces: shared paperwork service functions.

- [ ] **Step 1: Write failing policy and revision tests**

Cover creator read/edit, unrelated user denial, admin read/edit, one revision per successful save, idempotent replay, stale revision conflict, restore creating a new revision, and no permanent delete.

- [ ] **Step 2: Define typed request shell**

```python
class SavePaperworkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    work_date: date
    shift: str | None = Field(default=None, max_length=32)
    payload: dict[str, object]
    base_revision_number: int | None = Field(default=None, ge=1)
    reason: Literal["autosave", "manual_save", "recovery"]
```

Kind-specific payload validation occurs before persistence.

- [ ] **Step 3: Implement access policy**

```python
def can_read_paperwork(actor: Actor, record: PaperworkRecord) -> bool:
    return actor.role == "admin" or record.created_by_staff_member_id == actor.staff_member_id


def can_edit_paperwork(actor: Actor, record: PaperworkRecord) -> bool:
    return can_read_paperwork(actor, record)
```

Daily admin-only creation rules are added in the Daily Paperwork plan; Count Sheet remains available to officers.

- [ ] **Step 4: Implement service functions**

Use existing idempotency and audit infrastructure. `save_paperwork_record` creates revision 1 when `record_id is None`; later saves require matching base revision. Changed-field calculation stores field paths, not field values, in audit metadata.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_paperwork_service.py tests/integration/test_paperwork_revisions.py -v
git add backend/paperwork tests/unit/test_paperwork_service.py tests/integration/test_paperwork_revisions.py
git commit -m "feat: add revisioned paperwork service"
```

### Task 3: Encode the exact NCU Days Count structure and validation

**Files:**
- Create: `templates/paperwork/count_sheet.json`
- Create: `backend/paperwork/count_sheet.py`
- Modify: `backend/paperwork/schemas.py`
- Test: `tests/unit/test_count_sheet.py`

**Interfaces:**
- Produces: `CountSheetRecordV1`, `CountSheetValidation`, `calculate_count_totals()`, and `validate_count_sheet()`.

- [ ] **Step 1: Create sanitized structure JSON**

`templates/paperwork/count_sheet.json` contains exactly:

```json
{
  "columns": ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","Iso","Inf"],
  "areas": [
    "A/W Office","Barber Shop I/M","Boiler Room","Bull Pen","Capt. Office","Chapel","Chow Hall","Commissary","Construction","Dog Kennel","Domestics","Field Utility","Front Office","Garage","Gate Pass","Gym","Hall Porter","Horsebarn","I.P.O.","Infirmary","Iso. Porter","Kitchen","Laundry","Lawn, Inside","Library / Law Library","Maint. Inside","Maint. Outside","Major's Office","Mental Health","Mt. Home Crew","Other","Reg. Maint #1","Reg. Maint #2","Sally Port","School","Trail Crew","Visitation","W.W.T.P.","Work Craft","Yard (North)","Yard (South)"
  ],
  "operational_fields": ["on_site","gate_pass","transfers","court","hospital","furlough","other"],
  "attachment_reminders": ["court","hospital","furlough"]
}
```

- [ ] **Step 2: Write failing calculation tests**

Test row totals, column totals, in/out housing totals, unit total, operational total, exact positive/negative reconciliation difference, empty-cell preservation, non-negative integer rejection, unknown row/column rejection, and start/end time validation.

- [ ] **Step 3: Define Pydantic payload**

```python
class CountSheetRecordV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    count_started: time | None = None
    count_ended: time | None = None
    cells: dict[str, dict[str, int | None]]
    out_of_housing: dict[str, int | None]
    in_housing: dict[str, int | None]
    operational: dict[str, int | None]
```

- [ ] **Step 4: Implement deterministic validation**

Return:

```python
@dataclass(frozen=True)
class CountSheetValidation:
    row_totals: dict[str, int]
    column_totals: dict[str, int]
    housing_total: int
    operational_total: int
    difference: int
    reconciled: bool
```

Never modify payload values during calculation.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_count_sheet.py -v
git add templates/paperwork/count_sheet.json backend/paperwork/count_sheet.py backend/paperwork/schemas.py tests/unit/test_count_sheet.py
git commit -m "feat: model NCU days count"
```

### Task 4: Expose paperwork and Count Sheet browser APIs

**Files:**
- Create: `backend/webapp/web_api/paperwork.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_paperwork_api.py`
- Test: `tests/contract/test_web_v1_openapi.py`

**Interfaces:**
- Produces: create/list/get/save/revisions/restore/print-event APIs.

- [ ] **Step 1: Write failing API tests**

Routes:

```text
GET  /api/web/v1/paperwork?kind=count_sheet
POST /api/web/v1/paperwork/count-sheets
GET  /api/web/v1/paperwork/count-sheets/{record_id}
PATCH /api/web/v1/paperwork/count-sheets/{record_id}
GET  /api/web/v1/paperwork/count-sheets/{record_id}/revisions
POST /api/web/v1/paperwork/count-sheets/{record_id}/restore
POST /api/web/v1/paperwork/count-sheets/{record_id}/actions
```

Assert owner/admin authorization, CSRF, idempotency, revision conflict, validated totals returned, and print events audit without payload content.

- [ ] **Step 2: Implement closed requests**

Count save accepts exactly `schema_version`, `work_date`, `shift`, `payload`, `base_revision_number`, and `reason`. Action accepts exactly `action` with `preview|print|download_pdf`.

- [ ] **Step 3: Verify and commit**

```bash
python -m pytest tests/integration/test_paperwork_api.py tests/contract/test_web_v1_openapi.py -v
git add backend/webapp/web_api/paperwork.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests
git commit -m "feat: expose count sheet web API"
```

### Task 5: Build the NCU Days Count editor, keyboard flow, reconciliation, and print view

**Files:**
- Create: `frontend/web/src/features/paperwork/count-sheet/**`
- Modify: `frontend/web/src/app/router.tsx`
- Test: component tests under the feature directory.

**Interfaces:**
- Consumes: Task 4 APIs and count structure.
- Produces: `/workspace/count-sheet`.

- [ ] **Step 1: Write failing calculation parity tests**

The frontend `calculations.ts` uses the same fictional fixture as backend tests. Assert identical row totals, column totals, housing total, operational total, difference, and blank behavior.

- [ ] **Step 2: Implement strict schema**

Use Zod records constrained against the downloaded server structure; reject unknown rows or columns before state changes.

- [ ] **Step 3: Build desktop grid**

Columns are Area, 1–14, Iso, Inf, Total. Area and Total are sticky. Numeric fields select contents on focus, accept digits only, and announce `Area, column, value` to screen readers.

- [ ] **Step 4: Implement keyboard movement**

Arrow keys move one cell; Enter moves down; Shift+Enter moves up; Tab follows row order. Focused row and column receive non-color-only header emphasis.

- [ ] **Step 5: Build totals and mismatch guidance**

Render:

```text
The count does not reconcile. The totals differ by 2.
```

with the signed difference. Do not auto-balance.

- [ ] **Step 6: Build mobile grouped entry**

Mobile groups inputs by housing column with a persistent totals drawer; it edits the same state as desktop. Print always uses the full official grid.

- [ ] **Step 7: Build one-page landscape print**

`CountSheetPrint.tsx` uses `@page { size: letter landscape; margin: 0.3in; }`, hides app chrome, includes title/date/start/end/totals, retains attached-form reminders, and prints empty inputs blank.

- [ ] **Step 8: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/paperwork/count-sheet
npm run typecheck
git add src/features/paperwork/count-sheet src/app/router.tsx
git commit -m "feat: add NCU days count workspace"
```

### Task 6: Add the Forms Library catalog service and browser API

**Files:**
- Create: `backend/forms/library.py`
- Modify: `backend/webapp/web_api/forms.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/unit/test_forms_library.py`
- Test: `tests/integration/test_forms_library_api.py`

**Interfaces:**
- Consumes: `FormTemplate` catalog from Incident Workspace.
- Produces: searchable categorized library and multi-form preview/download metadata.

- [ ] **Step 1: Write failing library tests**

Cover category/search, active-only, frequently-used ordering, physical-only action restrictions, blank/fillable/printable flags, revision label, selection, and incident-attach capability.

- [ ] **Step 2: Define library DTO**

```python
@dataclass(frozen=True)
class FormLibraryItem:
    template_id: UUID
    code: str
    name: str
    category: str
    purpose: str
    when_used: str
    output_kind: str
    revision_label: str
    capabilities: frozenset[str]
```

- [ ] **Step 3: Add APIs**

```text
GET  /api/web/v1/forms?q=&category=&limit=&cursor=
GET  /api/web/v1/forms/{template_id}
POST /api/web/v1/forms/selection/preview
POST /api/web/v1/forms/selection/download
```

Selection bodies contain template IDs only. Physical-only items are returned as guidance and excluded from printable binaries.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/unit/test_forms_library.py tests/integration/test_forms_library_api.py tests/contract/test_web_v1_openapi.py -v
git add backend/forms/library.py backend/webapp/web_api/forms.py openapi/web-v1.yaml tests
git commit -m "feat: add forms library service"
```

### Task 7: Build the Forms Library interface

**Files:**
- Create: `frontend/web/src/features/forms-library/**`
- Modify: `frontend/web/src/app/router.tsx`
- Test: feature component tests.

**Interfaces:**
- Consumes: Task 6 API.
- Produces: `/workspace/forms` and an incident-selection drawer contract.

- [ ] **Step 1: Write failing UI tests**

Assert categories, search, form purpose/when-used, revision, preview/print/download capabilities, physical-only guidance, multi-select bar, clear selection, and Add to current incident only when supported.

- [ ] **Step 2: Implement responsive library**

Desktop uses category rail plus open list/grid; mobile uses filter drawer. Do not default to a repetitive decorative card wall—use compact rows for dense categories and stronger cards only for frequent forms.

- [ ] **Step 3: Implement selection actions**

Preview selected opens ordered document previews; print/download includes only digital items and lists skipped physical items before confirmation.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/forms-library
npm run typecheck
git add src/features/forms-library src/app/router.tsx
git commit -m "feat: add officer forms library"
```

### Task 8: Wrap Policy Expert for browser sessions

**Files:**
- Create: `backend/webapp/web_api/policy.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Create: `frontend/web/src/features/policy/api.ts`
- Create: `frontend/web/src/features/policy/PolicyExpertPage.tsx`
- Create: `frontend/web/src/features/policy/CitationInspector.tsx`
- Test: `tests/integration/test_web_policy.py`
- Test: frontend policy tests.

**Interfaces:**
- Consumes: existing route-neutral Policy Expert service.
- Produces: `POST /api/web/v1/policy/questions` and `/workspace/policy-expert`.

- [ ] **Step 1: Write failing API tests**

Assert authorization, bounded question/history, safe citations, timeout mapping, request ID, and no automatic incident mutation.

- [ ] **Step 2: Reuse policy service**

Do not call the legacy `/api/chat` route internally. Call the same query adapter used by `/api/v1/policy` and return answer, citations, source titles, and safe warnings.

- [ ] **Step 3: Build Policy Expert**

Use a calm conversation area plus citation inspector. Home quick-question navigation passes only unsent draft text in router state; no question is submitted without an explicit Ask action.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/integration/test_web_policy.py -v
cd frontend/web && npm run test -- src/features/policy && npm run typecheck && cd ../..
git add backend/webapp/web_api/policy.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml frontend/web/src/features/policy
git commit -m "feat: add browser policy expert"
```

### Task 9: Build personal Account APIs and interface

**Files:**
- Create: `backend/webapp/web_api/account.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Create: `frontend/web/src/features/account/**`
- Test: `tests/integration/test_web_account.py`
- Test: frontend account tests.

**Interfaces:**
- Consumes: browser authentication/session services.
- Produces: profile, session list/revoke, change PIN, logout, logout-all interface.

- [ ] **Step 1: Write failing API and UI tests**

Assert read-only identity fields, current-session labeling, revoke one, logout all, current PIN/new PIN validation, temporary PIN change, and session-state refresh after mutation.

- [ ] **Step 2: Implement account API adapter**

Return safe profile fields and bounded device labels/timestamps. Do not return token hashes, network data, or staff-edit endpoints.

- [ ] **Step 3: Build Account page**

Sections: Profile, Security, Signed-in Devices. Official name/employee/rank/shift/role are text, not editable inputs. High-impact actions use clear confirmation.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/integration/test_web_account.py -v
cd frontend/web && npm run test -- src/features/account && npm run typecheck && cd ../..
git add backend/webapp/web_api/account.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml frontend/web/src/features/account
git commit -m "feat: add personal account workspace"
```

### Task 10: Add the officer Home summary service and high-end usable dashboard

**Files:**
- Create: `backend/webapp/web_api/home.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Create: `frontend/web/src/features/dashboard/api.ts`
- Replace: `frontend/web/src/features/dashboard/HomePlaceholderPage.tsx` with `HomePage.tsx`
- Create: dashboard components.
- Test: `tests/integration/test_web_home.py`
- Test: frontend dashboard tests.

**Interfaces:**
- Produces: `GET /api/web/v1/home`.

- [ ] **Step 1: Write failing summary tests**

Response contains current profile, most recently updated authorized non-final workflow incident, five recent incidents, six frequent forms at most, last count-sheet summary, and safe AI availability. It never contains complete narratives or admin metrics.

- [ ] **Step 2: Implement bounded aggregation**

Use focused queries; do not call multiple HTTP endpoints. Return IDs, labels, progress, and timestamps only.

- [ ] **Step 3: Write failing dashboard hierarchy tests**

Assert `Start New Incident` is the sole primary `Button` variant, Open Count Sheet is prominent, Ask Policy and Forms Library are secondary, Continue Your Work appears before Recent Incidents, and no chart/metric headings render.

- [ ] **Step 4: Implement approved composition**

Use one strong action surface, three dimensional quick controls, a single continue card, compact recent list, and frequent forms strip. Entry animation uses approved restrained stagger and disappears under reduced motion.

- [ ] **Step 5: Compare to approved Home concepts**

Capture desktop/mobile, inspect concept and render side-by-side, and record/fix at least palette, hierarchy, typography, button depth, whitespace, and mobile collapse.

- [ ] **Step 6: Verify and commit**

```bash
python -m pytest tests/integration/test_web_home.py -v
cd frontend/web && npm run test -- src/features/dashboard && npm run typecheck && cd ../..
git add backend/webapp/web_api/home.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml frontend/web/src/features/dashboard docs/design/guided-operations/README.md
git commit -m "feat: add officer home dashboard"
```

### Task 11: Verify officer utilities, accessibility, and print fidelity

**Files:**
- Create: `frontend/web/tests/e2e/officer-home.spec.ts`
- Create: `frontend/web/tests/e2e/count-sheet.spec.ts`
- Create: `frontend/web/tests/e2e/forms-policy-account.spec.ts`
- Create: `tests/fixtures/paperwork/count_sheet_fictional.json`
- Modify: `README.md`
- Modify: `docs/design/guided-operations/README.md`

**Interfaces:**
- Produces: Officer Utilities release gate.

- [ ] **Step 1: Add Count Sheet E2E path**

Home → Open Count Sheet → enter fictional values with keyboard → verify totals → create a difference of 2 → save → reload → set end time → print preview. Assert app chrome is absent in print media.

- [ ] **Step 2: Add Forms, Policy, and Account paths**

Search/preview/select forms; verify physical item restriction; ask a fictional policy question and open citations; list sessions, change PIN with fictional credentials, and revoke a noncurrent session.

- [ ] **Step 3: Add print regression fixture**

Render the one-page letter-landscape Count Sheet from fictional data and compare text, row/column order, pagination, margins, and grayscale legibility.

- [ ] **Step 4: Run verification twice**

```bash
python -m pytest tests/unit/test_paperwork_* tests/unit/test_count_sheet.py tests/unit/test_forms_library.py tests/integration/test_paperwork_api.py tests/integration/test_web_policy.py tests/integration/test_web_account.py tests/integration/test_web_home.py -v
cd frontend/web && npm run lint && npm run typecheck && npm run test && npm run build && npm run test:e2e && cd ../..
```

Run twice with all passes green.

- [ ] **Step 5: Commit**

```bash
git add frontend/web/tests/e2e tests/fixtures/paperwork README.md docs/design/guided-operations/README.md
git commit -m "test: verify officer utility workspace"
```

## Officer Utilities Completion Gate

- Home matches the approved concept and keeps one dominant action.
- Count Sheet row/column labels exactly match the sanitized source structure.
- Backend and frontend calculations agree.
- Saved Count Sheets reopen without data loss and reject stale revisions.
- Print is one-page letter landscape at the required test fixture.
- Forms Library honors digital/physical capabilities.
- Policy Expert citations remain session-only and separate from incident facts.
- Account identity is read-only and session controls are secure.
- All tests pass twice with fictional data only.
