# Guided Operations Plan Integration Contract

**Date:** 2026-08-18  
**Status:** Authoritative cross-plan self-review rulings  
**Roadmap:** `docs/superpowers/plans/2026-08-18-guided-operations-web-program-roadmap.md`

## Purpose

This contract records the results of the implementation-plan self-review. It resolves cross-plan type details, removes ambiguous source interpretations, and defines the precedence an executor must use when a detailed task can be read more than one way.

## Precedence

1. Approved design specification
2. Sanitized paperwork structure reference
3. This integration contract
4. Detailed subsystem implementation plan
5. Existing implementation, except where a reviewed migration task explicitly changes it

A conflict must be resolved before code is written. An executor must not pick the easier interpretation silently.

---

# 1. Visual Concept Gate

The complete plan:

`docs/superpowers/plans/2026-08-18-guided-operations-visual-concept-pack-implementation.md`

supersedes the smaller visual-concept task embedded in the Web Foundation plan.

After the complete pack is approved, Web Foundation Task 1 is considered satisfied and execution begins with Web Foundation Task 2. Do not generate a second partial Home/shell-only pack.

---

# 2. Browser API Casing Contract

Server JSON uses snake_case. React feature state may use camelCase only through an explicit mapper.

```ts
export const sessionProfileApiSchema = z.object({
  account_id: z.string().uuid(),
  staff_id: z.string().uuid(),
  session_id: z.string().uuid(),
  employee_number: z.string().min(1),
  display_name: z.string().min(1),
  rank: z.string().nullable(),
  shift: z.string().nullable(),
  role: z.enum(["user", "admin"]),
  must_change_pin: z.boolean(),
}).strict();

export interface SessionProfile {
  accountId: string;
  staffId: string;
  sessionId: string;
  employeeNumber: string;
  displayName: string;
  rank: string | null;
  shift: string | null;
  role: "user" | "admin";
  mustChangePin: boolean;
}

export function toSessionProfile(value: z.infer<typeof sessionProfileApiSchema>): SessionProfile {
  return {
    accountId: value.account_id,
    staffId: value.staff_id,
    sessionId: value.session_id,
    employeeNumber: value.employee_number,
    displayName: value.display_name,
    rank: value.rank,
    shift: value.shift,
    role: value.role,
    mustChangePin: value.must_change_pin,
  };
}
```

No component casts API JSON directly to a frontend interface.

---

# 3. Incident Output and Progress Contract

## 3.1 Form and report presentation types

```python
class FormOutputKind(str, Enum):
    DIGITAL_DOCUMENT = "digital_document"
    PHYSICAL_ONLY = "physical_only"


class ReportPresentation(str, Enum):
    DOCUMENT = "document"
    COPY_TEXT = "copy_text"
```

Supervisor Summary and Disciplinary Supplement use `ReportPresentation.COPY_TEXT`. They are reports, not `FormTemplate` rows.

The initial form-catalog code is exactly:

```text
form_005_409
cover_letter
chain_of_custody_physical
medical_documentation_checklist
additional_officer_statement
```

`over_letter` is invalid.

## 3.2 Document-action provenance

Every `DocumentActionEvent` contains enough provenance to determine whether it applies to the current content:

```python
class DocumentActionEvent(Base):
    id: UUID
    incident_id: UUID
    report_id: UUID | None
    packet_item_id: UUID | None
    incident_revision_number: int
    report_revision_number: int | None
    action: Literal["preview", "print", "download_word", "download_pdf", "copy_text"]
    actor_account_id: UUID
    actor_staff_member_id: UUID
    request_id: str
    client_version: str
    created_at: datetime
```

## 3.3 Workflow progress precedence

`printed_or_exported` is true only when a successful Print or Download action references the current incident revision and, when report-specific, the current report revision.

```python
def has_current_output_action(
    *,
    incident_revision_number: int,
    report_revisions: Mapping[UUID, int],
    actions: Sequence[DocumentActionEvent],
) -> bool:
    return any(
        action.action in {"print", "download_word", "download_pdf"}
        and action.incident_revision_number == incident_revision_number
        and (
            action.report_id is None
            or action.report_revision_number == report_revisions.get(action.report_id)
        )
        for action in actions
    )
```

An edit after printing moves the incident back to the progress state calculated from the new revision. A historical print event never labels new content as printed.

The full precedence is:

1. Current-revision Print/Download action → `printed_or_exported`
2. Queued/running classify, extract, or generate job → `generating_reports`
3. Blocking validation gaps or unacknowledged required physical paperwork → `needs_information`
4. Reviewed facts, no generated reports → `ready_to_generate`
5. Generated reports awaiting review → `ready_to_review`
6. Current required digital forms complete and required physical tasks acknowledged → `ready_to_print`
7. Nonempty field notes → `field_notes_started`

---

# 4. Assignment Roster Contract

## 4.1 Explicit assignment state

Blank and No Officer Available are different values.

```python
class AssignmentState(str, Enum):
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    NO_OFFICER_AVAILABLE = "no_officer_available"


class StaffAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: AssignmentState
    staff: StaffSelection | None = None

    @model_validator(mode="after")
    def validate_state(self):
        if self.state is AssignmentState.ASSIGNED and self.staff is None:
            raise ValueError("assigned state requires staff")
        if self.state is not AssignmentState.ASSIGNED and self.staff is not None:
            raise ValueError("unassigned or NOA state cannot carry staff")
        return self
```

Print behavior:

```text
unassigned            blank cell
assigned              selected staff display name
no_officer_available  NOA
```

Coverage warnings distinguish `p1_unfilled` from `p1_no_officer_available`.

## 4.2 Zone 5 priority

The supplied roster does not show a P1/P2 designation for Boiler Room.

```json
{"code":"boiler_room","label":"Boiler Room","priority":null}
```

Do not label Boiler Room P1 or P2 without a later approved form revision.

## 4.3 Equipment keys

The payload contains exactly:

```text
digital_camera
video_camera_gopro
metal_detector_wands_9
```

Each value is `yes`, `no`, or `not_checked`. Unknown keys are rejected.

## 4.4 Source labels

The complete perimeter, count-sheet, roster, uniform, detector, search, sign-out, and monthly labels come from:

`docs/design/guided-operations/sanitized-paperwork-structures.md`

An executor must not abbreviate, modernize, or reorder those print labels without approval.

---

# 5. Count Sheet Calculation Contract

## 5.1 User-entered fields

Users enter:

- area-by-housing cells;
- In Hsg Area values by housing column;
- On Site;
- Gate Pass;
- Transfers;
- Court;
- Hospital;
- Furlough;
- Other;
- Count Started;
- Count Ended.

`Out of Hsg Area`, Unit Total, row totals, column totals, operational total, and reconciliation difference are calculated, not independently editable.

## 5.2 Exact calculations

```python
HOUSING_COLUMNS = (
    "1", "2", "3", "4", "5", "6", "7", "8",
    "9", "10", "11", "12", "13", "14", "Iso", "Inf",
)


def integer_or_zero(value: int | None) -> int:
    return 0 if value is None else value


row_totals = {
    area: sum(integer_or_zero(cells[area][column]) for column in HOUSING_COLUMNS)
    for area in AREA_ROWS
}

out_of_housing = {
    column: sum(integer_or_zero(cells[area][column]) for area in AREA_ROWS)
    for column in HOUSING_COLUMNS
}

unit_totals = {
    column: out_of_housing[column] + integer_or_zero(in_housing[column])
    for column in HOUSING_COLUMNS
}

unit_total = sum(unit_totals.values())

operational_total = sum(
    integer_or_zero(operational[field])
    for field in ("on_site", "gate_pass", "transfers", "court", "hospital", "furlough", "other")
)

reconciliation_difference = unit_total - operational_total
reconciled = reconciliation_difference == 0
```

The UI displays the signed difference and never inserts a balancing value.

---

# 6. Exact Contraband-Log Row Schedules

The monthly print definitions preserve blank rows from the supplied forms. They do not simply repeat a cycle until 25 rows are full.

## 6.1 Standard Area Rotation — rows 1 through 25

```text
1   Gym
2   School
3   Front Office / Barber Shop
4   Boiler Room
5   Kitchen and ODR
6   Laundry Press Area / Main Showers
7   blank
8   blank
9   blank
10  Gym
11  School
12  Front Office / Barber Shop
13  Boiler Room
14  Kitchen and ODR
15  Laundry Press Area / Main Showers
16  blank
17  Gym
18  School
19  Front Office / Barber Shop
20  Boiler Room
21  Kitchen and ODR
22  Laundry Press Area / Main Showers
23  blank
24  blank
25  blank
```

## 6.2 Expanded Area Rotation — rows 1 through 25

```text
1   Gym
2   Chapel
3   Entrance Building
4   School
5   Front Office / Barbershop
6   Boiler Room
7   Kitchen / ODR
8   Laundry
9   Inmate Barbershop
10  Inside Maintenance
11  blank
12  Gym
13  Chapel
14  Entrance Building
15  School
16  Front Office / Barbershop
17  Boiler Room
18  Kitchen / ODR
19  Laundry
20  Inmate Barbershop
21  Inside Maintenance
22  blank
23  blank
24  blank
25  blank
```

The print-template JSON stores these literal 25-entry arrays.

---

# 7. Weekly and Monthly Persistence Contract

- Daily forms and Count Sheet are saved revisioned records.
- Weekly and Monthly templates are preview-and-print only in release one.
- The Weekly catalog is an empty approved catalog and displays `No weekly forms have been published.`
- Monthly month/shift/supervisor prefill remains browser-local until Print/Preview action validation.
- No completed monthly row is saved in release one.
- Print action audit contains template code, actor, request ID, client version, and result—not prefilled names or form rows.

---

# 8. Admin Status and Officer Progress

Officer progress and administrator records status are separate fields.

```json
{
  "workflow_progress": "ready_to_print",
  "records_status": "in_progress"
}
```

- Officers see workflow progress only.
- Administrators see workflow progress plus records status.
- Only authorized administrators may change `in_progress`, `completed`, or `archived`.
- A records-status change does not rewrite workflow progress or prevent an authorized edit.

---

# 9. Self-Review Coverage Matrix

| Approved requirement | Implementing plan/task |
|---|---|
| Complete high-fidelity design before code | Visual Concept Pack, Tasks 1–9 |
| Six-item officer navigation | Web Foundation, Task 11 |
| Secure individual browser sign-in | Web Foundation, Tasks 4–10 |
| Light high-end dimensional design and restrained motion | Visual Concept Pack, Tasks 2–8; Web Foundation, Task 12 |
| Incident number/name organization | Incident Workspace, Tasks 1–4 and 10 |
| No officer status management | Incident Workspace global constraints; Admin Command Center, Tasks 3 and 9 |
| Six-step report workflow | Incident Workspace, Task 11 |
| Populated required forms from reviewed facts | Incident Workspace, Tasks 5–7 and 12 |
| Copy-only summaries/supplements | Incident Workspace, Tasks 8–9 and 12 |
| Physical Chain of Custody reminder | Incident Workspace, Tasks 5–9 and 12 |
| Home with Start Incident and Count Sheet | Officer Utilities, Task 10 |
| NCU Days Count calculations/save/print | Officer Utilities, Tasks 1–5 and 11 |
| Forms Library | Officer Utilities, Tasks 6–7 |
| Policy Expert and Account | Officer Utilities, Tasks 8–9 |
| Admin Command Center | Admin Command Center, Tasks 1–12 |
| All Incidents, Accounts & Staff, Audit, Health | Admin Command Center, Tasks 3–5 and 9–11 |
| Daily roster and inspections | Daily Paperwork, Tasks 1–12 |
| Weekly honest empty state | Print Center/Rollout, Tasks 1 and 5 |
| Four supplied monthly forms | Print Center/Rollout, Tasks 1–6 |
| Print packet and grayscale fidelity | Incident Workspace Task 12; Daily Task 11; Print Center Tasks 3–6 |
| Access/legacy coexistence and rollback | Print Center/Rollout, Tasks 8–11 |
| No sensitive workbook data in repository/image | Every plan global constraints; build/template checks |

# 10. Placeholder and Type Review Result

The committed plan suite was searched for these prohibited placeholders:

```text
TBD
TODO
implement later
fill in details
Similar to Task
```

No matches were found in the Guided Operations plan files.

The shared names in this contract—`BrowserActor`, `BrowserCookiePair`, `WorkflowProgress`, `PaperworkKind`, `FormOutputKind`, `ReportPresentation`, `AssignmentState`, `save_paperwork_record`, `build_incident_packet`, and `populate_form_instance`—are the canonical cross-plan names.
