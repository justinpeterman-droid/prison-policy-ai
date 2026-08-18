# Guided Operations Web Program Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved Guided Operations browser application without replacing the existing report engine, Access client, policy-search pipeline, individual identity system, revision controls, or Word export behavior.

**Architecture:** A complete high-fidelity visual contract is approved first. A new React/TypeScript/Vite application is then built under `frontend/web/` and served as versioned static assets by the existing Flask/Cloud Run service. A separate cookie-authenticated `/api/web/v1` adapter reuses the same identity, authorization, incident, report, job, policy, audit, and export service layers that currently back the bearer-authenticated Access API; new form and operational-paperwork resources remain behind the same server-enforced controls.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, Alembic, PostgreSQL 17, React, TypeScript, Vite, React Router, TanStack Query, Zod, Vitest, React Testing Library, MSW, Playwright, CSS variables, native CSS/WAAPI motion, dedicated HTML/CSS print templates, and OpenAI Image Generation for the visual contract.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

**Sanitized Source Reference:** `docs/design/guided-operations/sanitized-paperwork-structures.md`

## Global Constraints

- The complete visual concept pack is approved before production UI code begins.
- The officer navigation is exactly Home, New Report, Reports, Policy Expert, Forms Library, and Account.
- The normal application is light-first: approximately 80% light surfaces, 15% navy structure, and 5% gold/bronze or semantic accent.
- The visual system is `Light Precision Workspace`; dimensional controls are selective and never reduce readability.
- Every official incident number uses `YYYY-MM-NNN`; `2026-08-029` is a valid example, leading zeroes are preserved, invalid months are rejected, and duplicates are refused.
- Officers never manage records-management status directly; officer progress is derived from workflow state.
- Field notes remain bounded by the existing backend constant `FIELD_NOTES_MAX_CHARACTERS = 30_000`.
- Raw field notes never directly populate official forms; reviewed structured facts and gap answers are the only population source.
- Supervisor Summary and Disciplinary Supplement are editable copy-only outputs with no Print or Word-download action.
- Chain of Custody remains a physical carbon-copy requirement; the web app provides guidance and acknowledgment but no digital substitute.
- Uploaded workbooks, real names, employee numbers, phone numbers, equipment identifiers, signatures, and historical operational entries are never committed, copied into fixtures, or placed in screenshots.
- Browser authentication uses HttpOnly, Secure cookies and server-side session resolution; access and renewal tokens never enter JavaScript or `localStorage`.
- Cookie-authenticated mutations require origin validation plus a session-bound CSRF token.
- The existing `/api/v1` bearer contract remains unchanged for Microsoft Access.
- All modifying requests use idempotency keys; revisioned writes reject stale clients with `409 revision_conflict`.
- Network failure never clears visible work; the UI uses Saved, Saving, Unsaved changes, Reconnecting, and Save failed—work preserved.
- WCAG 2.2 AA, full keyboard operation, visible focus, 44px primary touch targets, reduced motion, and print legibility are release gates.
- Legacy Jinja pages and the Access client remain available during pilot; shared-code browser routes are retired only after parity, rollback, training, and explicit user approval.
- Each detailed plan produces independently testable software and one focused commit per task.

---

## Detailed Plans

1. `docs/superpowers/plans/2026-08-18-guided-operations-visual-concept-pack-implementation.md`
2. `docs/superpowers/plans/2026-08-18-guided-operations-web-foundation-implementation.md`
3. `docs/superpowers/plans/2026-08-18-guided-operations-incident-workspace-implementation.md`
4. `docs/superpowers/plans/2026-08-18-guided-operations-officer-utilities-implementation.md`
5. `docs/superpowers/plans/2026-08-18-guided-operations-admin-command-center-implementation.md`
6. `docs/superpowers/plans/2026-08-18-guided-operations-daily-paperwork-implementation.md`
7. `docs/superpowers/plans/2026-08-18-guided-operations-print-center-rollout-implementation.md`

## Dependency Graph

```text
Complete Visual Concept Pack
└── Web Foundation
    ├── Incident Workspace
    │   └── Officer Utilities Home and Forms integrations
    ├── Officer Utilities
    └── Admin Command Center
        └── Daily Paperwork Center

Incident Workspace + Officer Utilities + Admin Command Center + Daily Paperwork
└── Weekly/Monthly Print Center and Rollout
```

The visual concept pack lands and receives explicit approval first. The web foundation lands next. Incident Workspace and Officer Utilities may proceed in parallel only after browser authentication, SPA delivery, common API envelopes, design tokens, query client, and complete visual contract are stable. Admin Command Center begins after the same foundation and reuses existing admin authorization/elevation services. Daily Paperwork depends on the generic paperwork persistence introduced by Officer Utilities and the protected admin shell. Rollout is last.

## Locked Repository Structure

```text
docs/design/guided-operations/
  README.md
  concept-index.md
  source-copy-inventory.md
  sanitized-paperwork-structures.md
  *.png

frontend/web/
  package.json
  package-lock.json
  tsconfig.json
  vite.config.ts
  playwright.config.ts
  src/
    main.tsx
    app/
    api/
    components/
      primitives/
      layout/
      feedback/
      documents/
    features/
      auth/
      dashboard/
      incidents/
      paperwork/
      forms-library/
      policy/
      account/
      administration/
    print/
    styles/
    test/
  tests/e2e/

backend/
  identity/
    browser_sessions.py
    browser_admin.py
  paperwork/
    __init__.py
    models.py
    schemas.py
    service.py
    policy.py
    count_sheet.py
    daily.py
    daily_templates.py
    templates.py
  forms/
    __init__.py
    catalog.py
    library.py
    packets.py
    population.py
    physical.py
    output_events.py
  reports/
    incident_numbers.py
    workflow_progress.py
    admin_incidents.py
  webapp/
    web_api/
      __init__.py
      context.py
      responses.py
      middleware.py
      auth.py
      incidents.py
      reports.py
      jobs.py
      forms.py
      paperwork.py
      policy.py
      account.py
      admin_auth.py
      admin_overview.py
      admin_incidents.py
      admin_accounts.py
      admin_audit.py
      admin_health.py
      admin_review_lab.py
      admin_daily_paperwork.py
      print_templates.py
    routes/
      web_app.py
    static/web/

backend/persistence/models/
  browser.py
  paperwork.py
  forms.py

migrations/versions/
  20260818_0006_browser_sessions.py
  20260818_0007_incident_packets.py
  20260818_0008_operational_paperwork.py

openapi/
  web-v1.yaml

templates/paperwork/
  catalog.json
  count_sheet.json
  daily/
  weekly/
  monthly/

tests/
  contract/test_web_v1_openapi.py
  integration/test_web_auth.py
  integration/test_web_incidents.py
  integration/test_form_packets.py
  integration/test_paperwork_api.py
  integration/test_web_admin_*.py
  unit/test_browser_sessions.py
  unit/test_incident_progress.py
  unit/test_count_sheet.py
  unit/test_daily_*.py
  security/test_web_cookie_security.py
  security/test_web_admin_authorization.py
```

## Shared Python Interfaces

The detailed plans may add fields but must not rename these contracts without updating all consumers and `openapi/web-v1.yaml` in the same task.

```python
@dataclass(frozen=True)
class BrowserActor:
    account_id: UUID
    staff_member_id: UUID
    session_id: UUID
    role: Literal["user", "admin"]
    auth_version: int
    must_change_pin: bool


@dataclass(frozen=True)
class BrowserCookiePair:
    access_token: str
    renewal_token: str
    csrf_token: str
    access_expires_at: datetime
    renewal_expires_at: datetime
    persistent: bool


@dataclass(frozen=True)
class WorkflowProgress:
    code: Literal[
        "field_notes_started",
        "needs_information",
        "ready_to_generate",
        "generating_reports",
        "ready_to_review",
        "ready_to_print",
        "printed_or_exported",
    ]
    label: str
    blocking_count: int


class PaperworkKind(str, Enum):
    COUNT_SHEET = "count_sheet"
    ASSIGNMENT_ROSTER = "assignment_roster"
    UNIFORM_INSPECTION = "uniform_inspection"
    METAL_DETECTOR_TEST = "metal_detector_test"
    PERIMETER_CHECK = "perimeter_check"
    RANDOM_SEARCH_LOG = "random_search_log"
    DETECTOR_SIGN_OUT = "detector_sign_out"


class FormOutputKind(str, Enum):
    DIGITAL_DOCUMENT = "digital_document"
    PHYSICAL_ONLY = "physical_only"


class ReportPresentation(str, Enum):
    DOCUMENT = "document"
    COPY_TEXT = "copy_text"


class AssignmentState(str, Enum):
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    NO_OFFICER_AVAILABLE = "no_officer_available"
```

Required service signatures:

```python
def create_browser_session(
    db: Session,
    *,
    employee_number: str,
    pin: str,
    device_id: str,
    device_label: str,
    persistent: bool,
    now: datetime,
    settings: IdentitySettings,
    audit_writer: AuditWriter,
    request_id: str,
) -> tuple[BrowserActor, BrowserCookiePair]: ...


def renew_browser_session(
    db: Session,
    *,
    renewal_token: str,
    device_id: str,
    csrf_token: str,
    now: datetime,
    settings: IdentitySettings,
    audit_writer: AuditWriter,
    request_id: str,
) -> tuple[BrowserActor, BrowserCookiePair]: ...


def resolve_browser_actor(
    db: Session,
    *,
    access_token: str,
    now: datetime,
) -> BrowserActor: ...


def calculate_workflow_progress(
    *,
    incident: Incident,
    reports: Sequence[Report],
    jobs: Sequence[AiJob],
    packet_items: Sequence[IncidentPacketItem],
    current_revision_actions: Sequence[DocumentActionEvent],
) -> WorkflowProgress: ...


def save_paperwork_record(
    db: Session,
    actor: Actor,
    *,
    record_id: UUID | None,
    kind: PaperworkKind,
    work_date: date,
    shift: str | None,
    payload: dict[str, object],
    base_revision_number: int | None,
    idempotency_key: str,
    request_id: str,
    client_version: str,
    audit_writer: AuditWriter,
) -> PaperworkView: ...


def build_incident_packet(
    db: Session,
    actor: Actor,
    *,
    incident_id: UUID,
    incident_revision_number: int,
) -> list[IncidentPacketItemView]: ...


def populate_form_instance(
    db: Session,
    actor: Actor,
    *,
    packet_item_id: UUID,
    incident_revision_number: int,
) -> FormInstanceView: ...
```

## Shared Browser HTTP Rules

- Browser endpoints use `/api/web/v1` and the same success/failure envelope shape as `/api/v1`.
- `POST /api/web/v1/auth/login` accepts exactly `employee_number`, `pin`, and `persistent`; the server derives a random device identifier when none exists in an HttpOnly device cookie.
- Authentication responses return safe profile/session state only; token values are written only to cookies.
- Cookies are named `slut_web_access`, `slut_web_renewal`, `slut_web_device`, and `slut_web_csrf`.
- Access, renewal, and device cookies are HttpOnly; the CSRF cookie is readable by same-origin JavaScript and contains only a random anti-CSRF value.
- Production cookies use `Secure`, `SameSite=Lax`, bounded paths, and explicit max ages. Local HTTP development may omit `Secure` only when development mode is explicit and the host is loopback.
- Every mutation validates `Origin`, `Sec-Fetch-Site`, and `X-CSRF-Token` against the session-bound digest.
- Read requests never rotate renewal credentials. `POST /api/web/v1/auth/renew` rotates both session credentials and the CSRF token.
- React sends `X-Client-Version` from the built package version, `X-Request-ID`, and `Idempotency-Key` where required.
- Browser APIs return stable error codes and safe request IDs; they never return raw HTML, traces, secrets, tokens, field notes in logs, or infrastructure details.

## Cross-Plan Release Gates

- [ ] The complete high-fidelity concept pack is approved and recorded.
- [ ] Web foundation unit, contract, integration, security, accessibility, and SPA smoke tests pass.
- [ ] Incident-number uniqueness and workflow progress are server-tested.
- [ ] Printed/exported progress considers actions for the current saved revision only.
- [ ] Populated forms are generated only from a saved reviewed incident revision.
- [ ] Copy-only and physical-only actions are impossible through UI and API metadata, not merely hidden by CSS.
- [ ] Count-sheet totals and reconciliation pass unit, integration, keyboard, and print tests.
- [ ] Every daily form has typed backend validation and a print regression fixture using fictional data.
- [ ] Admin route authorization, elevation, step-up, attribution, and audit tests pass.
- [ ] Desktop, tablet, mobile, 1366×768, 100–150% Windows scaling, reduced motion, and grayscale print checks pass.
- [ ] Pilot rollback restores legacy Jinja routes without data migration or report loss.
- [ ] Uploaded reference workbooks are absent from Git history and production images.

## Program Execution Order

- [ ] **Gate 0:** Generate, review, revise, and approve the complete Visual Concept Pack.
- [ ] **Gate 1:** Complete and approve the Web Foundation.
- [ ] **Gate 2A:** Complete Incident Workspace.
- [ ] **Gate 2B:** Complete Officer Utilities after the shared paperwork-record contract lands.
- [ ] **Gate 3A:** Complete Admin Command Center.
- [ ] **Gate 3B:** Complete Daily Paperwork Center.
- [ ] **Gate 4:** Complete Weekly/Monthly Print Center and rollout verification.
- [ ] **Gate 5:** Pilot alongside Access and legacy Jinja, collect usability findings, fix regressions, and obtain explicit primary-cutover approval.
- [ ] **Gate 6:** Obtain separate explicit approval before retiring any legacy route.
