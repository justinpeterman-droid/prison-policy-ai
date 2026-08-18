# Guided Operations Daily Paperwork Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the administrator Daily Paperwork Center with a browser-fillable Shift Assignment Roster, Uniform Inspection Log, Walk-Through Metal Detector Test, Perimeter Check List, Random Searches Log, and Handheld Metal Detector Sign-Out, all saved by date and shift and rendered in print-accurate layouts.

**Architecture:** Sanitized JSON template definitions preserve the supplied workbook’s labels, post order, inspection groups, and print hierarchy without storing real names or equipment identifiers. Typed Pydantic payloads validate each record before the generic revisioned paperwork service persists it; protected `/api/web/v1/admin/paperwork/daily` routes enforce administrator elevation, while React editors share a daily-workspace shell, autosave contract, staff picker, save state, and print framework.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, PostgreSQL 17, Pydantic 2, React, TypeScript, TanStack Query, Zod, Vitest, React Testing Library, Playwright, CSS Grid, accessible drag-and-drop using pointer and keyboard controls, and dedicated HTML/CSS print templates.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Global Constraints

- Daily Paperwork is administrator-only and requires a current server-side Admin Center elevation.
- Daily paperwork is operational paperwork, not an incident report and not an officer-managed records status.
- Records are saved by work date and shift, create immutable revisions, and reject stale saves with `409 revision_conflict`.
- Every editor shows Saved, Saving, Unsaved changes, Reconnecting, and Save failed—work preserved.
- Assignment Roster and Uniform Inspection appear first in Today’s Paperwork.
- The roster uses active production staff from Accounts & Staff; no committed template contains a real person name or employee number.
- The supplied roster’s five zones, post order, priority labels, briefing fields, equipment fields, signatures, and distribution note are preserved in the print template.
- Coverage warnings never auto-assign or move an employee.
- Uniform Inspection loads the selected roster’s employees and requires a comment for each Unsatisfactory result.
- A failed metal-detector test requires a corrective-action comment.
- Perimeter locations preserve the complete supplied list and source grouping.
- Real equipment identifiers from the source workbook are not committed; the record allows an administrator to enter current identifiers when needed.
- Print output uses dedicated markup, remains readable in grayscale, and excludes application chrome.
- Every fixture, screenshot, and test uses fictional staff and operational data.

---

## File Map

```text
templates/paperwork/daily/
  assignment_roster.json
  uniform_inspection.json
  metal_detector_test.json
  perimeter_check.json
  random_search_log.json
  detector_sign_out.json

backend/paperwork/daily.py
backend/paperwork/daily_templates.py
backend/paperwork/schemas.py
backend/paperwork/service.py
backend/webapp/web_api/admin_daily_paperwork.py
backend/webapp/web_api/admin_overview.py
backend/webapp/web_api/__init__.py
openapi/web-v1.yaml

tests/unit/test_daily_template_definitions.py
tests/unit/test_assignment_roster.py
tests/unit/test_uniform_inspection.py
tests/unit/test_metal_detector_test.py
tests/unit/test_perimeter_check.py
tests/unit/test_random_search_log.py
tests/unit/test_detector_sign_out.py
tests/integration/test_web_daily_paperwork.py
tests/contract/test_web_v1_openapi.py
tests/fixtures/paperwork/daily/
  assignment_roster_fictional.json
  uniform_inspection_fictional.json
  metal_detector_test_fictional.json
  perimeter_check_fictional.json
  random_search_log_fictional.json
  detector_sign_out_fictional.json

frontend/web/src/features/administration/paperwork/
  api.ts
  schemas.ts
  PaperworkCenterPage.tsx
  DailyPaperworkTab.tsx
  DailyRecordCard.tsx
  DailyRecordWorkspace.tsx
  shared/DailyEditorHeader.tsx
  shared/StaffPicker.tsx
  shared/SaveState.tsx
  shared/PrintPreviewDialog.tsx
  roster/AssignmentRosterEditor.tsx
  roster/ZoneAssignmentTable.tsx
  roster/CoverageWarnings.tsx
  roster/AssignmentRosterPrint.tsx
  uniform/UniformInspectionEditor.tsx
  uniform/UniformInspectionPrint.tsx
  metal/MetalDetectorEditor.tsx
  metal/MetalDetectorPrint.tsx
  perimeter/PerimeterCheckEditor.tsx
  perimeter/PerimeterCheckPrint.tsx
  searches/RandomSearchesEditor.tsx
  searches/RandomSearchesPrint.tsx
  signout/DetectorSignOutEditor.tsx
  signout/DetectorSignOutPrint.tsx
frontend/web/tests/e2e/daily-paperwork.spec.ts
frontend/web/tests/e2e/daily-paperwork-keyboard.spec.ts
frontend/web/tests/e2e/daily-paperwork-print.spec.ts
```

## Shared Interfaces Produced by This Plan

```python
class DailyPaperworkKind(str, Enum):
    ASSIGNMENT_ROSTER = "assignment_roster"
    UNIFORM_INSPECTION = "uniform_inspection"
    METAL_DETECTOR_TEST = "metal_detector_test"
    PERIMETER_CHECK = "perimeter_check"
    RANDOM_SEARCH_LOG = "random_search_log"
    DETECTOR_SIGN_OUT = "detector_sign_out"


@dataclass(frozen=True)
class DailyTemplateDefinition:
    kind: DailyPaperworkKind
    title: str
    schema_version: int
    print_orientation: Literal["portrait", "landscape"]
    definition: dict[str, object]


def load_daily_template(kind: DailyPaperworkKind) -> DailyTemplateDefinition: ...
def validate_daily_payload(kind: DailyPaperworkKind, payload: dict[str, object]) -> BaseModel: ...
def copy_previous_daily_record(...) -> PaperworkView: ...
def calculate_roster_coverage(...) -> list[CoverageWarning]: ...
```

Frontend daily record summary:

```ts
export interface DailyRecordSummary {
  recordId: string | null;
  kind: DailyPaperworkKind;
  title: string;
  workDate: string;
  shift: string;
  revision: number | null;
  state: "not_started" | "unsaved" | "saved" | "needs_attention";
  warningCount: number;
  updatedAt: string | null;
}
```

### Task 1: Create strict sanitized daily-template definitions

**Files:**
- Create: `templates/paperwork/daily/*.json`
- Create: `backend/paperwork/daily_templates.py`
- Test: `tests/unit/test_daily_template_definitions.py`

**Interfaces:**
- Produces: `DailyTemplateDefinition` and `load_daily_template()`.

- [ ] **Step 1: Write the failing template-contract test**

Create `tests/unit/test_daily_template_definitions.py` with assertions that:

```python
EXPECTED_KINDS = {
    "assignment_roster",
    "uniform_inspection",
    "metal_detector_test",
    "perimeter_check",
    "random_search_log",
    "detector_sign_out",
}
```

Each file has exactly `kind`, `title`, `schema_version`, `print_orientation`, and `definition`; schema version is `1`; paths and HTML are prohibited; no value matches employee-number patterns or contains a real source-workbook name.

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_daily_template_definitions.py -v
```

Expected: FAIL because the files and loader do not exist.

- [ ] **Step 3: Create the assignment-roster definition**

`templates/paperwork/daily/assignment_roster.json` must contain these zone/post codes in this exact order:

```json
{
  "zones": [
    {
      "code": "zone_1",
      "label": "Zone 1",
      "area": "Bks 8-14 Hallway and Service Area",
      "supervisor_label": "South Hall Sergeant",
      "posts": [
        {"code":"bks_8_control","label":"Bks 8 Control Booth","priority":"P1"},
        {"code":"bks_9_10_control","label":"Bks 9-10 Control Booth","priority":"P1"},
        {"code":"bks_9_10_desk","label":"Bks 9-10 Desk","priority":"P2"},
        {"code":"bks_11_12_control","label":"Bks 11-12 Control Booth","priority":"P1"},
        {"code":"bks_13_14_control","label":"Bks 13-14 Control Booth","priority":"P1"},
        {"code":"south_tower","label":"South Tower Officer","priority":"P1"},
        {"code":"east_tower","label":"East Tower Officer","priority":"P1"},
        {"code":"south_hall_rover","label":"South Hall Rover","priority":"P2"}
      ]
    },
    {
      "code": "zone_2",
      "label": "Zone 2",
      "area": "Bks 1-7 Hallway and Service Area",
      "supervisor_label": "North Hall Sergeant",
      "posts": [
        {"code":"bks_1_control","label":"Bks 1 Control Booth","priority":"P1"},
        {"code":"bks_2_3_control","label":"Bks 2-3 Control Booth","priority":"P1"},
        {"code":"bks_4_5_control","label":"Bks 4-5 Control Booth","priority":"P1"},
        {"code":"bks_4_5_desk","label":"Bks 4-5 Desk","priority":"P2"},
        {"code":"bks_6_7_control","label":"Bks 6-7 Control Booth","priority":"P1"},
        {"code":"north_tower","label":"North Tower Officer","priority":"P1"},
        {"code":"west_tower","label":"West Tower Officer","priority":"P1"},
        {"code":"school_security","label":"School Security Officer","priority":"P1"},
        {"code":"north_hall_rover","label":"North Hall Rover","priority":"P2"}
      ]
    },
    {
      "code": "zone_3",
      "label": "Zone 3",
      "area": "Isolation and Service Area",
      "supervisor_label": "Isolation Sergeant",
      "posts": [
        {"code":"isolation_1","label":"Isolation Officer #1","priority":"P1"},
        {"code":"isolation_2","label":"Isolation Officer #2","priority":"P1"},
        {"code":"isolation_rover","label":"Rover","priority":"P2"}
      ]
    },
    {
      "code": "zone_4",
      "label": "Zone 4",
      "area": "Front Entrance and Service Area",
      "supervisor_label": "Front Entrance Sergeant",
      "posts": [
        {"code":"master_control_1","label":"Master Control #1","priority":"P1"},
        {"code":"master_control_2","label":"Master Control #2","priority":"P2"},
        {"code":"infirmary_officer","label":"Infirmary Officer","priority":"P1"},
        {"code":"outside_rover","label":"Outside Rover","priority":"P1"},
        {"code":"biometrics_lobby","label":"Biometrics Officer Lobby","priority":"P2"},
        {"code":"front_rover","label":"Rover","priority":"P2"}
      ]
    },
    {
      "code": "zone_5",
      "label": "Zone 5",
      "area": "Sally Port and Service Area",
      "supervisor_label": "Sergeant",
      "posts": [
        {"code":"boiler_room","label":"Boiler Room","priority":"P1"}
      ]
    }
  ]
}
```

The same definition also contains source labels for Initial Officer, Rotation Officer, Leave Time (Type of Leave), Extra Assignments, Alternate Shift Supervisor, Shift Briefing Minutes, Roll Call, Uniform Inspection, Assigned to post and dismissed, Security Equipment Accounted For, Guests at Shift Briefing, Captain, Lieutenant, Duty Warden, lieutenant signature, date, priority-one staffing warning, NOA note, CGPS note, and distribution list.

- [ ] **Step 4: Create the remaining five definitions**

Use these exact controlled values:

```json
{
  "uniform_inspection": {
    "columns": ["shirt","pants","shoes","cap","coat","id","hair","nails"],
    "values": ["S","N/I","U","NONE"]
  },
  "metal_detector_test": {
    "detectors": ["1","2","3","4","5","6","7","8","9","10","11"],
    "positions": [
      "Inner left leg, pointing down",
      "Centered on front of body, pointing down",
      "Left side of body, pointing down",
      "Center of back, pointing down",
      "Center of back, pointing left",
      "Under left arm, pointing down",
      "Centered on top of head, pointing forward"
    ],
    "values": ["P","F"]
  },
  "random_search_log": {
    "sections": ["North 1","North 2","South 1","South 2"],
    "blocks_per_section": 4,
    "fields": ["officer_staff_id","date","time","individual_last_name","individual_number","barracks_rack","contraband_disposition"]
  },
  "detector_sign_out": {
    "units": ["D1","D2","D3","D4","D5","D6","D7","D8","D9"],
    "fields": ["staff_id","area_of_assignment","shift_supervisor_staff_id","date"]
  }
}
```

The metal definition contains an optional blank `location` and `equipment_identifier` for each detector; no source identifier is committed.

- [ ] **Step 5: Encode the complete perimeter location lists**

`perimeter_check.json` contains the full Doors, Outside Doors, Fence & Gates, additional checks, and sign-off labels from the supplied source. The loader asserts each item code is unique and preserves array order.

- [ ] **Step 6: Implement the strict loader**

```python
DAILY_TEMPLATE_FILES = {
    DailyPaperworkKind.ASSIGNMENT_ROSTER: "assignment_roster.json",
    DailyPaperworkKind.UNIFORM_INSPECTION: "uniform_inspection.json",
    DailyPaperworkKind.METAL_DETECTOR_TEST: "metal_detector_test.json",
    DailyPaperworkKind.PERIMETER_CHECK: "perimeter_check.json",
    DailyPaperworkKind.RANDOM_SEARCH_LOG: "random_search_log.json",
    DailyPaperworkKind.DETECTOR_SIGN_OUT: "detector_sign_out.json",
}
```

Reject unknown keys, duplicate codes, unsupported orientations, schema versions other than 1, path separators, HTML tags, and any string matching `ADC#\s*[0-9]{4,}`.

- [ ] **Step 7: Verify and commit**

```bash
python -m pytest tests/unit/test_daily_template_definitions.py -v
git add templates/paperwork/daily backend/paperwork/daily_templates.py tests/unit/test_daily_template_definitions.py
git commit -m "feat: add sanitized daily paperwork templates"
```

### Task 2: Add typed daily-paperwork payloads and validation dispatcher

**Files:**
- Create: `backend/paperwork/daily.py`
- Modify: `backend/paperwork/schemas.py`
- Test: `tests/unit/test_assignment_roster.py`
- Test: `tests/unit/test_uniform_inspection.py`
- Test: `tests/unit/test_metal_detector_test.py`
- Test: `tests/unit/test_perimeter_check.py`
- Test: `tests/unit/test_random_search_log.py`
- Test: `tests/unit/test_detector_sign_out.py`

**Interfaces:**
- Consumes: Task 1 definitions and generic paperwork service.
- Produces: six strict Pydantic models and `validate_daily_payload()`.

- [ ] **Step 1: Write failing closed-schema tests**

Every model rejects unknown fields, invalid staff UUIDs, invalid dates, unknown zone/post/check codes, duplicate assignments where prohibited, strings over the defined limit, and values outside closed enums.

- [ ] **Step 2: Define shared models**

```python
class StaffSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff_id: UUID
    display_name_snapshot: str = Field(min_length=1, max_length=160)


class DailyPayloadBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    work_date: date
    shift: str = Field(min_length=1, max_length=32)
```

Display-name snapshots are for print continuity only; authorization and current identity use staff UUIDs.

- [ ] **Step 3: Define AssignmentRosterV1**

```python
class PostAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_code: str
    initial_staff: StaffSelection | None = None
    rotation_staff: StaffSelection | None = None


class ZoneAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_code: str
    supervisor: StaffSelection | None = None
    posts: list[PostAssignment]


class AssignmentRosterV1(DailyPayloadBase):
    captain: StaffSelection | None = None
    lieutenant: StaffSelection | None = None
    duty_warden: str | None = Field(default=None, max_length=160)
    alternate_shift_supervisor: StaffSelection | None = None
    leave_entries: list[dict[str, str]] = Field(default_factory=list, max_length=40)
    extra_assignments: list[dict[str, str]] = Field(default_factory=list, max_length=40)
    zones: list[ZoneAssignment]
    briefing_minutes: str = Field(default="", max_length=10_000)
    roll_call_completed: bool = False
    uniform_inspection_completed: bool = False
    equipment: dict[str, Literal["yes", "no", "not_checked"]]
    briefing_guests: list[str] = Field(default_factory=list, max_length=20)
    assigned_and_dismissed: bool = False
    lieutenant_signature_name: str | None = Field(default=None, max_length=160)
```

Validation requires every configured zone exactly once and every configured post exactly once within its zone.

- [ ] **Step 4: Define UniformInspectionV1**

```python
InspectionValue = Literal["S", "N/I", "U", "NONE"]

class UniformInspectionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff: StaffSelection
    shirt: InspectionValue | None = None
    pants: InspectionValue | None = None
    shoes: InspectionValue | None = None
    cap: InspectionValue | None = None
    coat: InspectionValue | None = None
    id: InspectionValue | None = None
    hair: InspectionValue | None = None
    nails: InspectionValue | None = None
    comments: str = Field(default="", max_length=500)
```

Any `U` value requires a nonblank comment. Duplicate staff IDs are rejected.

- [ ] **Step 5: Define the other four models**

- `MetalDetectorTestV1`: every detector and position exactly once; result is `P`, `F`, or null; each detector has optional location and equipment identifier; any `F` requires a nonblank corrective-action note; tested/reviewed by fields are optional staff selections.
- `PerimeterCheckV1`: every configured check code exactly once; result is `S`, `U`, or null; includes perimeter inspector, signature name, date/time, Senstar inspector, supervisor signature, and date/time.
- `RandomSearchLogV1`: four configured sections, each with exactly four blocks; dates/times are nullable; individual last name/number and barracks-rack are bounded strings; contraband/disposition is bounded to 2,000 characters.
- `DetectorSignOutV1`: D1–D9 exactly once; staff, assignment area, supervisor, and date may remain null until completed.

- [ ] **Step 6: Implement the dispatcher**

```python
DAILY_PAYLOAD_MODELS = {
    DailyPaperworkKind.ASSIGNMENT_ROSTER: AssignmentRosterV1,
    DailyPaperworkKind.UNIFORM_INSPECTION: UniformInspectionV1,
    DailyPaperworkKind.METAL_DETECTOR_TEST: MetalDetectorTestV1,
    DailyPaperworkKind.PERIMETER_CHECK: PerimeterCheckV1,
    DailyPaperworkKind.RANDOM_SEARCH_LOG: RandomSearchLogV1,
    DailyPaperworkKind.DETECTOR_SIGN_OUT: DetectorSignOutV1,
}


def validate_daily_payload(kind, payload):
    return DAILY_PAYLOAD_MODELS[kind].model_validate(payload)
```

- [ ] **Step 7: Verify and commit**

```bash
python -m pytest tests/unit/test_assignment_roster.py tests/unit/test_uniform_inspection.py tests/unit/test_metal_detector_test.py tests/unit/test_perimeter_check.py tests/unit/test_random_search_log.py tests/unit/test_detector_sign_out.py -v
git add backend/paperwork/daily.py backend/paperwork/schemas.py tests/unit/test_*inspection.py tests/unit/test_assignment_roster.py tests/unit/test_metal_detector_test.py tests/unit/test_perimeter_check.py tests/unit/test_random_search_log.py tests/unit/test_detector_sign_out.py
git commit -m "feat: validate daily paperwork payloads"
```

### Task 3: Implement roster coverage, copy-previous, and uniform-row derivation services

**Files:**
- Modify: `backend/paperwork/daily.py`
- Modify: `backend/paperwork/service.py`
- Test: `tests/unit/test_assignment_roster.py`
- Test: `tests/unit/test_uniform_inspection.py`

**Interfaces:**
- Produces: `calculate_roster_coverage()`, `copy_previous_daily_record()`, and `build_uniform_rows_from_roster()`.

- [ ] **Step 1: Write failing coverage tests**

Assert:

- each blank P1 initial assignment produces one warning;
- P2 blank assignments are informational, not blocking;
- one staff member assigned to two simultaneous initial P1 posts produces a duplicate warning;
- rotation assignments are evaluated separately;
- the service never changes assignments;
- warnings contain post codes and labels, not sensitive content.

- [ ] **Step 2: Implement immutable warnings**

```python
@dataclass(frozen=True)
class CoverageWarning:
    code: Literal["p1_unfilled", "duplicate_initial_assignment", "duplicate_rotation_assignment"]
    message: str
    zone_code: str
    post_code: str | None
    staff_id: UUID | None
```

- [ ] **Step 3: Write failing copy-previous tests**

Copying the previous roster:

- finds the latest earlier record for the requested shift;
- creates a new record for the target date;
- copies zone/post assignments, equipment keys, and extra-assignment labels;
- clears signatures, leave entries, briefing minutes, completion booleans, guests, and print events;
- uses a new idempotency key and revision 1;
- refuses a target date that already has a roster unless the caller opens that existing record.

- [ ] **Step 4: Implement uniform-row derivation**

Collect unique staff from supervisors, initial assignments, and rotation assignments in printed source order. Create blank inspection rows; do not copy prior inspection results. Include the roster record ID and revision as provenance in the uniform payload.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_assignment_roster.py tests/unit/test_uniform_inspection.py -v
git add backend/paperwork/daily.py backend/paperwork/service.py tests/unit/test_assignment_roster.py tests/unit/test_uniform_inspection.py
git commit -m "feat: add daily roster workflow services"
```

### Task 4: Expose protected daily-paperwork APIs

**Files:**
- Create: `backend/webapp/web_api/admin_daily_paperwork.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `backend/webapp/web_api/admin_overview.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_daily_paperwork.py`
- Test: `tests/contract/test_web_v1_openapi.py`

**Interfaces:**
- Consumes: generic paperwork service, daily validation, admin elevation.
- Produces: daily list/create/get/save/copy/derive/action routes.

- [ ] **Step 1: Write failing authorization and lifecycle tests**

Assert user denial, admin-without-elevation denial, elevated admin read/create/save, CSRF/idempotency requirements, revision conflict, date/shift filters, safe summaries, print action audit, and no payload in request logs.

- [ ] **Step 2: Add routes**

```text
GET  /api/web/v1/admin/paperwork/daily?work_date=YYYY-MM-DD&shift=D&kind=assignment_roster
POST /api/web/v1/admin/paperwork/daily/{kind}
GET  /api/web/v1/admin/paperwork/daily/{kind}/{record_id}
PATCH /api/web/v1/admin/paperwork/daily/{kind}/{record_id}
GET  /api/web/v1/admin/paperwork/daily/{kind}/{record_id}/revisions
POST /api/web/v1/admin/paperwork/daily/{kind}/{record_id}/restore
POST /api/web/v1/admin/paperwork/daily/{kind}/copy-previous
POST /api/web/v1/admin/paperwork/daily/assignment-roster/{record_id}/uniform-inspection
POST /api/web/v1/admin/paperwork/daily/{kind}/{record_id}/actions
```

- [ ] **Step 3: Define closed bodies**

Create/save uses the generic paperwork request shell and validates payload by kind. Copy-previous accepts exactly `target_work_date`, `shift`, and optional `source_record_id`. Uniform derivation accepts exactly `target_work_date` and `shift`. Actions accept `preview|print|download_pdf` only.

- [ ] **Step 4: Return validation metadata**

Roster responses include `coverage_warnings`. Uniform responses include `unsatisfactory_count` and `missing_comment_count`. Metal responses include `failed_test_count`. Other forms include `incomplete_count`.

- [ ] **Step 5: Connect Today’s Paperwork**

The admin overview returns current-date/selected-shift summaries for Assignment Roster and Uniform Inspection, including record ID, revision, state, warning count, and updated time.

- [ ] **Step 6: Verify and commit**

```bash
python -m pytest tests/integration/test_web_daily_paperwork.py tests/integration/test_web_admin_overview.py tests/contract/test_web_v1_openapi.py -v
git add backend/webapp/web_api/admin_daily_paperwork.py backend/webapp/web_api/__init__.py backend/webapp/web_api/admin_overview.py openapi/web-v1.yaml tests
git commit -m "feat: expose daily paperwork web API"
```

### Task 5: Build the Paperwork Center shell and Daily tab

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/api.ts`
- Create: `frontend/web/src/features/administration/paperwork/schemas.ts`
- Create: `frontend/web/src/features/administration/paperwork/PaperworkCenterPage.tsx`
- Create: `frontend/web/src/features/administration/paperwork/DailyPaperworkTab.tsx`
- Create: `frontend/web/src/features/administration/paperwork/DailyRecordCard.tsx`
- Create: `frontend/web/src/features/administration/paperwork/DailyRecordWorkspace.tsx`
- Create: shared components.
- Modify: `frontend/web/src/app/router.tsx`
- Test: Paperwork Center component tests.

**Interfaces:**
- Consumes: Task 4 APIs.
- Produces: `/workspace/admin/paperwork?tab=daily` and editor routing.

- [ ] **Step 1: Write failing tab and summary tests**

Assert raised keyboard-operable Daily/Weekly/Monthly tabs; Daily is selected by URL; Assignment Roster, Uniform Inspection, Count Sheet, Metal Detector, Perimeter Check, Random Searches, and Detector Sign-Out appear in that order; each card shows date, shift, save state, warning count, and Open/Start action.

- [ ] **Step 2: Implement strict API schemas**

Parse daily summaries and full records using Zod discriminated unions by `kind`. Unknown schema versions display a safe compatibility error and never enter editor state.

- [ ] **Step 3: Build the shared workspace**

Every editor receives:

```ts
interface DailyEditorProps<TPayload> {
  record: DailyRecord<TPayload>;
  save(payload: TPayload, reason: "autosave" | "manual_save"): Promise<void>;
  preview(): void;
  print(): void;
  reload(): Promise<void>;
}
```

The header contains Back, title, date, shift, save state, Save Now, Preview, and Print. Autosave begins 60 seconds after the last change.

- [ ] **Step 4: Implement responsive behavior**

Desktop uses a broad working surface; tablet retains editable tables with sticky labels; mobile uses structured row editors and opens print preview separately. No desktop table is merely scaled down.

- [ ] **Step 5: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/PaperworkCenterPage.test.tsx src/features/administration/paperwork/DailyPaperworkTab.test.tsx
npm run typecheck
git add src/features/administration/paperwork src/app/router.tsx
git commit -m "feat: add daily paperwork center shell"
```

### Task 6: Build the Shift Assignment Roster editor and print document

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/roster/**`
- Test: roster component tests.

**Interfaces:**
- Consumes: active staff API, assignment definition, copy-previous API.
- Produces: fillable/printable roster.

- [ ] **Step 1: Write failing interaction tests**

Test staff search/select, initial and rotation columns, five zones in source order, supervisor selection, post labels/priorities, keyboard reorder, pointer reorder, copy previous, leave entries, extra assignments, briefing notes, equipment values, command fields, coverage warnings, and no automatic reassignment.

- [ ] **Step 2: Implement StaffPicker**

The picker searches active staff by name or employee number and stores staff UUID plus display snapshot. It supports keyboard navigation, clear, and an explicit `No Officer Available` choice represented as null plus a visible NOA label in print.

- [ ] **Step 3: Implement zone tables**

Each row displays post, priority, Initial Officer, and Rotation Officer. Drag handles are buttons with `Move up` and `Move down` keyboard alternatives. Reordering changes only visual/print order within the approved zone and cannot move a post into another zone.

- [ ] **Step 4: Implement copy previous**

The action shows source date/shift, explains which fields reset, and requires confirmation. On success, navigate to the new record and announce creation.

- [ ] **Step 5: Build the official print layout**

The print component reproduces unit title, shift/date, Shift Personnel and Housing Zones columns, Initial/Rotation headings, Zones 1–5, side operational fields, priority warning, signatures, notes, and distribution footer. Use a controlled multipage break only when content cannot fit one page at approved font size; never shrink below 8pt.

- [ ] **Step 6: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/roster
npm run typecheck
git add src/features/administration/paperwork/roster
git commit -m "feat: add assignment roster workspace"
```

### Task 7: Build the Uniform Inspection editor and print document

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/uniform/**`
- Test: uniform component tests.

**Interfaces:**
- Consumes: roster-to-uniform derivation API.
- Produces: source-aligned inspection log.

- [ ] **Step 1: Write failing tests**

Assert Name, Shirt, Pants, Shoes, Cap, Coat, I.D., Hair, Nails, Comments; values S/N-I/U/NONE; roster import; duplicate prevention; bulk-mark one column S; exceptions remain editable; U requires comment; inspecting staff/date/shift; save/preview/print.

- [ ] **Step 2: Implement efficient matrix entry**

Use button groups or select controls with explicit labels. `Mark column Satisfactory` fills blank values only unless the administrator confirms overwriting existing exceptions.

- [ ] **Step 3: Enforce comments before save**

A row with `U` and blank comment remains visible and editable; autosave is blocked with a plain error pointing to the employee row. No value is silently changed.

- [ ] **Step 4: Build print layout**

Render the source column order, legend, staff-conducting-inspection line, date/shift, and distribution line. Long comments wrap without hiding status columns.

- [ ] **Step 5: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/uniform
npm run typecheck
git add src/features/administration/paperwork/uniform
git commit -m "feat: add uniform inspection workspace"
```

### Task 8: Build the Walk-Through Metal Detector editor and print document

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/metal/**`
- Test: metal detector component tests.

**Interfaces:**
- Produces: 7×11 test matrix with validation.

- [ ] **Step 1: Write failing matrix tests**

Assert seven test positions, detectors 1–11, P/F/blank entry, sticky detector headers, tested by, reviewed by, optional location/equipment identifier, corrective-action requirement for any F, bulk-mark one detector P, and keyboard navigation.

- [ ] **Step 2: Build the matrix**

Desktop shows positions as rows and detectors as columns. Mobile selects one detector and presents seven positions as a vertical checklist while retaining the same payload.

- [ ] **Step 3: Implement failure review**

Selecting F opens the related detector corrective-action field and moves focus there only after the user completes the current matrix cell. Save is blocked until every failed detector has a nonblank note.

- [ ] **Step 4: Build print layout**

Render title, date, full matrix, P/F legend, tested-by, comments/corrective actions, detector location/identifier guidance, reviewed-by, and distribution note.

- [ ] **Step 5: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/metal
npm run typecheck
git add src/features/administration/paperwork/metal
git commit -m "feat: add metal detector test workspace"
```

### Task 9: Build the Perimeter Check editor and print document

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/perimeter/**`
- Test: perimeter component tests.

**Interfaces:**
- Produces: grouped S/U inspection workspace.

- [ ] **Step 1: Write failing tests**

Assert every configured Doors, Outside Doors, Fence & Gates, Senstar, Pipe Chases, Manholes, Metal Detector, and Fence and Alleyways item appears exactly once and in source order; S/U/blank values; group bulk-S; exceptions; sign-off fields; source-accurate print grouping.

- [ ] **Step 2: Build grouped desktop and mobile editors**

Desktop uses three aligned groups with sticky headings. Mobile uses accordions with count summaries; collapsing a group does not lose values.

- [ ] **Step 3: Add incomplete and unsatisfactory summaries**

Display total unchecked and U counts with text labels. The form may save incomplete work; Print Preview warns before printing incomplete entries.

- [ ] **Step 4: Build print layout**

Use the three source columns and S/U subcolumns, followed by additional checks and both signature/date-time lines. Keep all source labels readable in grayscale.

- [ ] **Step 5: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/perimeter
npm run typecheck
git add src/features/administration/paperwork/perimeter
git commit -m "feat: add perimeter check workspace"
```

### Task 10: Build Random Searches and Detector Sign-Out editors and print documents

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/searches/**`
- Create: `frontend/web/src/features/administration/paperwork/signout/**`
- Test: both feature test suites.

**Interfaces:**
- Produces: the final two daily-record editors.

- [ ] **Step 1: Write failing Random Searches tests**

Assert North 1, North 2, South 1, South 2; four blocks each; officer; date; time; individual last name; individual number; barracks-rack; contraband/disposition; bounded text; source-block print structure.

- [ ] **Step 2: Build Random Searches editor and print**

Use repeated structured blocks with section navigation. The print component recreates the four source sections and officer blocks rather than printing a generic table.

- [ ] **Step 3: Write failing Detector Sign-Out tests**

Assert D1–D9, staff picker, area of assignment, shift supervisor, date, duplicate unit prevention, clear row, save, preview, and print.

- [ ] **Step 4: Build Detector Sign-Out editor and print**

Use a compact table on desktop and one unit card per row on mobile. Print uses the source unit order and signature-ready blank space.

- [ ] **Step 5: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/searches src/features/administration/paperwork/signout
npm run typecheck
git add src/features/administration/paperwork/searches src/features/administration/paperwork/signout
git commit -m "feat: add daily searches and detector sign-out"
```

### Task 11: Add daily print fixtures and visual regression

**Files:**
- Create: `tests/fixtures/paperwork/daily/*.json`
- Create: `frontend/web/tests/e2e/daily-paperwork-print.spec.ts`
- Modify: `docs/design/guided-operations/README.md`

**Interfaces:**
- Consumes: all six print components.
- Produces: stable fictional print references.

- [ ] **Step 1: Create fictional fixtures**

Use fictional employees such as `Officer Avery Cole`, `Officer Morgan Lee`, and `Sgt. Riley Jordan`; fictional employee numbers must never be rendered in print fixtures unless a form field explicitly requires one. Use a fictional date and no copied source narrative.

- [ ] **Step 2: Add print assertions**

For each form, assert title, source order, page size/orientation, no app navigation, no clipped fields, no horizontal page overflow, no real source strings, and grayscale contrast.

- [ ] **Step 3: Capture reference images**

Render Assignment Roster, Uniform Inspection, Metal Detector, Perimeter, Random Searches, and Detector Sign-Out at the approved print viewport. Inspect each against the supplied source previews for hierarchy and field placement while keeping sanitized content.

- [ ] **Step 4: Record fidelity ledger**

Document at least five comparison points per form: headings, grouped structure, column order, signature/footer placement, page breaks, line weights, and type size. Fix all material drift.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/paperwork/daily frontend/web/tests/e2e/daily-paperwork-print.spec.ts docs/design/guided-operations/README.md
git commit -m "test: add daily paperwork print regression"
```

### Task 12: Verify security, accessibility, recovery, and end-to-end daily workflows

**Files:**
- Create: `frontend/web/tests/e2e/daily-paperwork.spec.ts`
- Create: `frontend/web/tests/e2e/daily-paperwork-keyboard.spec.ts`
- Modify: `README.md`

**Interfaces:**
- Produces: Daily Paperwork release gate.

- [ ] **Step 1: Add primary E2E path**

Admin sign in → elevate → Paperwork Center → Daily → copy previous Assignment Roster → update fictional staff → resolve P1 warnings → save → derive Uniform Inspection → bulk mark S → set one U and comment → save → print both.

- [ ] **Step 2: Add remaining-form paths**

Complete one fictional metal test with one F/corrective action; perimeter with one U; random-search block; and detector sign-out. Save, reload, preview, and print each.

- [ ] **Step 3: Add keyboard-only path**

Navigate tabs, staff picker, roster rows, inspection matrix, metal matrix, perimeter groups, and print controls without pointer input. Verify logical focus and visible focus.

- [ ] **Step 4: Add failure/recovery path**

Simulate network failure during autosave; confirm work remains visible, state reads `Save failed—work preserved`, retry succeeds, and duplicate submissions do not create duplicate revisions.

- [ ] **Step 5: Run complete verification twice**

```bash
python -m pytest tests/unit/test_daily_template_definitions.py tests/unit/test_assignment_roster.py tests/unit/test_uniform_inspection.py tests/unit/test_metal_detector_test.py tests/unit/test_perimeter_check.py tests/unit/test_random_search_log.py tests/unit/test_detector_sign_out.py tests/integration/test_web_daily_paperwork.py tests/contract/test_web_v1_openapi.py -v
cd frontend/web && npm run lint && npm run typecheck && npm run test && npm run build && npm run test:e2e && cd ../..
```

Run the same sequence twice. Both runs must pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/web/tests/e2e/daily-paperwork.spec.ts frontend/web/tests/e2e/daily-paperwork-keyboard.spec.ts README.md
git commit -m "test: verify daily paperwork center"
```

## Daily Paperwork Completion Gate

- All six supplied daily forms are represented by strict sanitized definitions.
- Assignment Roster preserves five zones and exact post order.
- No committed file contains source staff or equipment identifiers.
- All daily payloads are typed and revisioned.
- Only elevated administrators can access Daily Paperwork APIs and screens.
- Coverage and validation warnings never alter user data.
- Assignment Roster and Uniform Inspection populate Today’s Paperwork.
- Every form saves, reopens, previews, and prints with fictional regression fixtures.
- Desktop, tablet, mobile, keyboard, reduced-motion, grayscale, network-recovery, and visual-fidelity checks pass twice.
