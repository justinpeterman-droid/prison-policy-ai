# Guided Operations Administrator Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the role-protected administrator Overview, All Incidents, Accounts & Staff, Audit Log, System Health, and Review Lab entry inside the same Guided Operations shell used by officers.

**Architecture:** Browser admin routes reuse the existing account, staff, report, audit, health, elevation, step-up, and handoff services rather than duplicating authorization. Admin elevation remains server-side; one-use sensitive step-up credentials are stored only in bounded HttpOnly cookies and consumed by the next matching mutation, while the React client receives safe state and explicit attribution notices.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, PostgreSQL 17, existing identity/admin/report/audit services, React, TypeScript, TanStack Query, Zod, Vitest, React Testing Library, and Playwright.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Global Constraints

- Admins retain every normal officer navigation item and gain a visibly separate Administration section.
- Hidden UI is never an authorization boundary.
- Admin entry requires current server-side elevation; sensitive mutations require a fresh purpose-scoped five-minute step-up.
- JavaScript never receives readable step-up credentials.
- Opening or editing another employee’s incident displays persistent attribution copy.
- All Incidents is incident-centered even though existing Access admin services remain report-centered internally.
- Accounts & Staff replaces the old roster-management page; personal Account remains separate.
- Audit is read-only and excludes narratives, PINs, tokens, credentials, and unsafe infrastructure details.
- System Health is diagnostic only.
- Admin overview may be denser than officer Home but remains light, premium, and approachable.
- Every admin read/mutation is server-authorized and audited.

---

## File Map

```text
backend/identity/browser_admin.py
backend/reports/admin_incidents.py
backend/webapp/web_api/admin_auth.py
backend/webapp/web_api/admin_overview.py
backend/webapp/web_api/admin_incidents.py
backend/webapp/web_api/admin_accounts.py
backend/webapp/web_api/admin_audit.py
backend/webapp/web_api/admin_health.py
backend/webapp/web_api/admin_review_lab.py
backend/webapp/web_api/__init__.py
openapi/web-v1.yaml

tests/unit/test_browser_admin.py
tests/unit/test_admin_incident_summary.py
tests/integration/test_web_admin_elevation.py
tests/integration/test_web_admin_overview.py
tests/integration/test_web_admin_incidents.py
tests/integration/test_web_admin_accounts.py
tests/integration/test_web_admin_audit_health.py
tests/integration/test_web_admin_review_lab.py
tests/security/test_web_admin_authorization.py

frontend/web/src/features/administration/
  api.ts
  schemas.ts
  AdminLayout.tsx
  AdminGate.tsx
  AdminElevationDialog.tsx
  AdminStepUpDialog.tsx
  overview/AdminOverviewPage.tsx
  overview/TodaysPaperwork.tsx
  overview/AttentionQueue.tsx
  overview/SystemAvailability.tsx
  incidents/AdminIncidentsPage.tsx
  incidents/AdminIncidentWorkspace.tsx
  incidents/AdminAttributionBanner.tsx
  accounts/AccountsStaffPage.tsx
  accounts/StaffPanel.tsx
  accounts/AccountPanel.tsx
  accounts/TemporaryPinDialog.tsx
  audit/AuditLogPage.tsx
  audit/AuditDetailsDrawer.tsx
  health/SystemHealthPage.tsx
  review-lab/ReviewLabLaunch.tsx
frontend/web/tests/e2e/admin-command-center.spec.ts
frontend/web/tests/e2e/admin-authorization.spec.ts
```

## Shared Interfaces Produced by This Plan

```python
@dataclass(frozen=True)
class BrowserAdminState:
    elevated: bool
    elevation_expires_at: datetime | None


def enter_browser_admin_center(...) -> BrowserAdminState: ...
def issue_browser_admin_step_up(...) -> datetime: ...
def consume_browser_admin_step_up(...) -> None: ...
def list_admin_incident_summaries(...) -> Page[AdminIncidentSummary]: ...
def build_admin_overview(...) -> AdminOverview: ...
```

### Task 1: Implement browser admin elevation and HttpOnly one-use step-up

**Files:**
- Create: `backend/identity/browser_admin.py`
- Create: `backend/webapp/web_api/admin_auth.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/unit/test_browser_admin.py`
- Test: `tests/integration/test_web_admin_elevation.py`
- Test: `tests/security/test_web_admin_authorization.py`

**Interfaces:**
- Consumes: existing `confirm_admin_pin`, `touch_admin_elevation`, and `AdminStepUpToken` services.
- Produces: `/api/web/v1/admin/elevation` and `/api/web/v1/admin/step-up`.

- [ ] **Step 1: Write failing elevation tests**

Cover user denial, admin PIN confirmation, 15-minute idle elevation, elevation expiry, purpose validation, five-minute sensitive step-up, wrong-purpose rejection, single-use consumption, cookie clearing, and session revocation invalidating elevation.

- [ ] **Step 2: Define cookie policy**

```python
ADMIN_STEP_UP_COOKIE = "slut_web_admin_step_up"
ADMIN_STEP_UP_COOKIE_PATH = "/api/web/v1/admin"
```

The cookie is HttpOnly, Secure under HTTPS, SameSite=Lax, max-age at most 300 seconds, and never returned in JSON.

- [ ] **Step 3: Implement elevation entry**

`POST /api/web/v1/admin/elevation` accepts exactly:

```json
{"pin":"A12345"}
```

It calls `confirm_admin_pin(..., purpose="admin_center")` and returns `elevated` plus expiry only.

- [ ] **Step 4: Implement purpose-scoped step-up**

`POST /api/web/v1/admin/step-up` accepts exactly `pin` and one allowed purpose. It stores the returned one-use value in the HttpOnly cookie. `require_browser_admin_step_up(purpose)` reads, verifies, consumes, and clears the cookie before the protected operation commits.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_browser_admin.py tests/integration/test_web_admin_elevation.py tests/security/test_web_admin_authorization.py -v
git add backend/identity/browser_admin.py backend/webapp/web_api/admin_auth.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests
git commit -m "feat: add browser admin elevation"
```

### Task 2: Add the administrator overview aggregation service and API

**Files:**
- Create: `backend/webapp/web_api/admin_overview.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_admin_overview.py`

**Interfaces:**
- Consumes: incident progress, account state, paperwork records, audit summaries, and existing health service.
- Produces: `GET /api/web/v1/admin/overview`.

- [ ] **Step 1: Write failing bounded-summary tests**

Response must include:

```text
todays_paperwork.assignment_roster
todays_paperwork.uniform_inspection
incidents_needing_attention
account_conditions
system_availability
recent_administrative_activity
```

It must not include narratives, full paperwork payloads, PIN data, tokens, or raw dependency errors.

- [ ] **Step 2: Define safe shape**

```python
@dataclass(frozen=True)
class AdminOverview:
    todays_paperwork: dict[str, object]
    incidents_needing_attention: list[dict[str, object]]
    account_conditions: dict[str, int]
    system_availability: dict[str, str]
    recent_activity: list[dict[str, object]]
```

Lists are capped at 10; counts are aggregate only.

- [ ] **Step 3: Implement one transaction-scoped aggregation**

Use service functions directly. Do not make internal HTTP calls. Before the Daily Paperwork plan creates current records, Assignment Roster and Uniform Inspection return `not_started`, not fabricated completion.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/integration/test_web_admin_overview.py -v
git add backend/webapp/web_api/admin_overview.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests/integration/test_web_admin_overview.py
git commit -m "feat: add admin operations overview API"
```

### Task 3: Add incident-centered administrator search and workspace APIs

**Files:**
- Create: `backend/reports/admin_incidents.py`
- Create: `backend/webapp/web_api/admin_incidents.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/unit/test_admin_incident_summary.py`
- Test: `tests/integration/test_web_admin_incidents.py`

**Interfaces:**
- Consumes: existing admin report search, incident/report policies, revisions, export, and status services.
- Produces: All Incidents summary/detail/edit/restore/ownership/status APIs.

- [ ] **Step 1: Write failing aggregation tests**

Assert one result per incident, all report owners/preparers, report and packet counts, calculated progress, admin search filters, and no duplicate incidents when multiple reports match.

- [ ] **Step 2: Implement filters**

Accepted filters:

```text
q
incident_number
reporting_staff_id
prepared_by_staff_id
incident_date_from
incident_date_to
created_at_from
created_at_to
category
facility
location
shift
records_status
last_editor_staff_id
updated_at_from
updated_at_to
limit
cursor
```

Officer progress and admin records status are separate response fields.

- [ ] **Step 3: Add protected actions**

Routes include:

```text
GET   /api/web/v1/admin/incidents
GET   /api/web/v1/admin/incidents/{incident_id}
PATCH /api/web/v1/admin/incidents/{incident_id}/records-status
POST  /api/web/v1/admin/incidents/{incident_id}/restore
POST  /api/web/v1/admin/reports/{report_id}/transfer
```

Restore and transfer require matching step-up purpose and a reason. Records-status accepts only `in_progress`, `completed`, or `archived` and never appears in normal officer UI.

- [ ] **Step 4: Preserve attribution and conflict behavior**

Admin edits use existing revision services with `admin_edit`; stale revisions return the same detailed conflict metadata as Access.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_admin_incident_summary.py tests/integration/test_web_admin_incidents.py tests/integration/test_admin_report_api.py -v
git add backend/reports/admin_incidents.py backend/webapp/web_api/admin_incidents.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests
git commit -m "feat: add admin all-incidents API"
```

### Task 4: Add browser Accounts & Staff APIs

**Files:**
- Create: `backend/webapp/web_api/admin_accounts.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_admin_accounts.py`

**Interfaces:**
- Consumes: existing staff/account/admin services.
- Produces: role-protected staff/account lifecycle endpoints.

- [ ] **Step 1: Write failing lifecycle tests**

Cover list/search staff, create/correct staff, active/inactive roster state, create account, one-time temporary PIN, reset PIN, role change, deactivate/reactivate, unlock, list sessions, revoke one/all, duplicate employee number, stable staff UUID, and last-active-admin protection.

- [ ] **Step 2: Add closed routes**

Use `/api/web/v1/admin/staff` and `/api/web/v1/admin/accounts`. Sensitive mutations require these purposes:

```text
staff_write
account_create
account_role_status
account_reset_pin
account_unlock
account_revoke_sessions
```

- [ ] **Step 3: Protect one-time PIN output**

The temporary PIN appears in exactly one successful JSON response, is never replayed from idempotency storage, and is never logged. A repeated idempotency request returns `idempotent_response_unavailable`.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/integration/test_web_admin_accounts.py tests/integration/test_account_creation.py tests/integration/test_admin_session_revocation.py -v
git add backend/webapp/web_api/admin_accounts.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests/integration/test_web_admin_accounts.py
git commit -m "feat: add browser accounts and staff API"
```

### Task 5: Add browser Audit Log and System Health APIs

**Files:**
- Create: `backend/webapp/web_api/admin_audit.py`
- Create: `backend/webapp/web_api/admin_health.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_admin_audit_health.py`

**Interfaces:**
- Consumes: existing admin audit and health services.
- Produces: read-only audit and safe health endpoints.

- [ ] **Step 1: Write failing audit tests**

Test time/actor/action/target/result filters, cursor pagination, safe details, no mutation methods, and no report text/PIN/token fields.

- [ ] **Step 2: Write failing health tests**

Assert client compatibility, API, database, AI stages, Policy Expert, queue, backups, and notices return only Operational/Degraded/Unavailable plus bounded timestamps/version references.

- [ ] **Step 3: Implement adapters**

Routes:

```text
GET /api/web/v1/admin/audit
GET /api/web/v1/admin/audit/{event_id}
GET /api/web/v1/admin/health
```

Audit export is deferred unless the existing service already supports it; no empty or fake control is rendered.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/integration/test_web_admin_audit_health.py tests/integration/test_admin_audit_health.py -v
git add backend/webapp/web_api/admin_audit.py backend/webapp/web_api/admin_health.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests
git commit -m "feat: add admin audit and health web APIs"
```

### Task 6: Add secure Review Lab browser handoff

**Files:**
- Create: `backend/webapp/web_api/admin_review_lab.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_admin_review_lab.py`

**Interfaces:**
- Consumes: existing one-time browser handoff service.
- Produces: `POST /api/web/v1/admin/review-lab-handoffs`.

- [ ] **Step 1: Write failing handoff tests**

Assert admin elevation, fresh `review_lab_handoff` step-up, 60-second one-use URL, no bearer/renewal/PIN/shared code in URL or response, issuance/redemption audit, and user denial.

- [ ] **Step 2: Reuse existing handoff service**

The route returns only the already-approved fragment URL and expiry. Do not implement a second token format.

- [ ] **Step 3: Verify and commit**

```bash
python -m pytest tests/integration/test_web_admin_review_lab.py tests/integration/test_browser_handoff_flow.py -v
git add backend/webapp/web_api/admin_review_lab.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests/integration/test_web_admin_review_lab.py
git commit -m "feat: add admin review lab handoff"
```

### Task 7: Build AdminGate, elevation, step-up, and administration navigation

**Files:**
- Create: `frontend/web/src/features/administration/api.ts`
- Create: `frontend/web/src/features/administration/schemas.ts`
- Create: `frontend/web/src/features/administration/AdminLayout.tsx`
- Create: `frontend/web/src/features/administration/AdminGate.tsx`
- Create: `frontend/web/src/features/administration/AdminElevationDialog.tsx`
- Create: `frontend/web/src/features/administration/AdminStepUpDialog.tsx`
- Modify: `frontend/web/src/app/router.tsx`
- Modify: `frontend/web/src/components/layout/Sidebar.tsx`
- Test: administration gate tests.

**Interfaces:**
- Consumes: Task 1 browser admin auth.
- Produces: protected `/workspace/admin/*` shell.

- [ ] **Step 1: Write failing authorization tests**

Assert users cannot see Administration, direct navigation renders not found, admins see Overview/All Incidents/Paperwork Center/Accounts & Staff/Audit Log/System Health/Review Lab, expired elevation prompts without losing route, and step-up preserves pending action.

- [ ] **Step 2: Implement elevation query**

`AdminGate` loads safe admin state. When not elevated it opens a PIN dialog; successful confirmation invalidates the admin-state query and renders the route.

- [ ] **Step 3: Implement step-up action helper**

`runWithStepUp(purpose, action)` prompts for PIN, calls the step-up endpoint, runs the mutation once, and never stores a credential in React state.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/AdminGate.test.tsx src/features/administration/AdminStepUpDialog.test.tsx
npm run typecheck
git add src/features/administration src/app/router.tsx src/components/layout/Sidebar.tsx
git commit -m "feat: add protected admin workspace"
```

### Task 8: Build the Operational Command Center overview

**Files:**
- Create: `frontend/web/src/features/administration/overview/**`
- Test: overview component tests.

**Interfaces:**
- Consumes: `GET /api/web/v1/admin/overview`.
- Produces: Administration Overview.

- [ ] **Step 1: Write failing hierarchy tests**

Assert Today’s Paperwork first, Incidents Needing Attention, Account Conditions, System Availability, Recent Administrative Activity, quick links, and no full narratives or vanity charts.

- [ ] **Step 2: Implement command-center composition**

Use denser rows and status fixtures than officer Home, while retaining the same palette, controls, typography, and motion. `Assignment Roster` and `Uniform Inspection` show Not started, Saved time, or Needs attention.

- [ ] **Step 3: Compare to approved admin concept**

Capture desktop and 1366×768; fix palette, density, hierarchy, raised fixtures, text scale, and whitespace drift.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/overview
npm run typecheck
git add src/features/administration/overview docs/design/guided-operations/README.md
git commit -m "feat: add admin operations overview"
```

### Task 9: Build All Incidents and admin-attributed incident workspace

**Files:**
- Create: `frontend/web/src/features/administration/incidents/**`
- Test: incident admin tests.

**Interfaces:**
- Consumes: Task 3 APIs and existing Document Studio components.
- Produces: searchable All Incidents and admin edit context.

- [ ] **Step 1: Write failing UI tests**

Assert structured filters, incident-number-first rows, one incident per row, admin records status separate from officer progress, persistent attribution banner, revision-safe editing, restore/transfer reason, and step-up requirements.

- [ ] **Step 2: Reuse Document Studio primitives**

Do not fork officer document components. Wrap them with admin context, attribution banner, extra history/ownership/status controls, and stricter confirmation.

- [ ] **Step 3: Implement persistent banner copy**

```text
You are viewing another employee’s incident. Your access and every saved change are attributed to your administrator account.
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/incidents
npm run typecheck
git add src/features/administration/incidents
git commit -m "feat: add admin all-incidents workspace"
```

### Task 10: Build Accounts & Staff

**Files:**
- Create: `frontend/web/src/features/administration/accounts/**`
- Test: account/staff admin tests.

**Interfaces:**
- Consumes: Task 4 APIs.
- Produces: combined staff/account management workspace.

- [ ] **Step 1: Write failing UI tests**

Test search, stable staff identity, separate roster/account state, create account, one-time PIN dialog, reset, role/status, unlock, sessions, revoke, last-admin errors, and temporary PIN disappearing on close.

- [ ] **Step 2: Implement split workspace**

Desktop uses searchable staff list plus details panel. Mobile uses list → details navigation. Staff profile is primary; linked account controls appear in a clearly separated section.

- [ ] **Step 3: Protect temporary PIN**

Display once in a modal with explicit Copy button. Clear React state and DOM text on close; do not store it in query cache, URL, toast history, clipboard automatically, or local storage.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/accounts
npm run typecheck
git add src/features/administration/accounts
git commit -m "feat: add accounts and staff workspace"
```

### Task 11: Build Audit Log, System Health, and Review Lab launcher

**Files:**
- Create: `frontend/web/src/features/administration/audit/**`
- Create: `frontend/web/src/features/administration/health/**`
- Create: `frontend/web/src/features/administration/review-lab/**`
- Test: feature tests.

**Interfaces:**
- Consumes: Tasks 5–6.
- Produces: remaining admin destinations.

- [ ] **Step 1: Write failing Audit tests**

Assert server filters, pagination, readable action labels, safe detail drawer, immutable UI, request reference, and no narrative/PIN/token content.

- [ ] **Step 2: Write failing Health tests**

Assert Operational/Degraded/Unavailable with text and icon, no raw infrastructure controls, refresh, last checked time, and safe degraded notices.

- [ ] **Step 3: Build Review Lab launcher**

Explain that Review Lab opens in a browser session, require confirmation/step-up, navigate only to returned same-origin managed URL, and show safe failure with request ID.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/audit src/features/administration/health src/features/administration/review-lab
npm run typecheck
git add src/features/administration/audit src/features/administration/health src/features/administration/review-lab
git commit -m "feat: add admin audit health and review lab"
```

### Task 12: Verify administrator authorization, usability, and visual fidelity

**Files:**
- Create: `frontend/web/tests/e2e/admin-command-center.spec.ts`
- Create: `frontend/web/tests/e2e/admin-authorization.spec.ts`
- Modify: `docs/design/guided-operations/README.md`
- Modify: `README.md`

**Interfaces:**
- Produces: Administrator Command Center release gate.

- [ ] **Step 1: Add role-matrix E2E tests**

User cannot discover or invoke admin routes. Admin must elevate. Sensitive action requires step-up. Step-up is single-use/wrong-purpose rejected. Closing/signing out removes elevation. Persistent account session does not persist elevation.

- [ ] **Step 2: Add admin workflows**

Overview → All Incidents → another employee’s incident → attributed edit; Accounts & Staff → reset fictional PIN → revoke sessions; Audit → find matching actions; Health → safe status; Review Lab → one-use handoff.

- [ ] **Step 3: Run security and regression suites twice**

```bash
python -m pytest tests/unit/test_browser_admin.py tests/unit/test_admin_incident_summary.py tests/integration/test_web_admin_* tests/security/test_web_admin_authorization.py tests/integration/test_admin_api.py tests/integration/test_admin_report_api.py tests/integration/test_admin_audit_health.py -v
cd frontend/web && npm run lint && npm run typecheck && npm run test && npm run build && npm run test:e2e && cd ../..
```

Run twice; both passes must be green.

- [ ] **Step 4: Compare rendered admin screens to concepts**

Inspect Overview, All Incidents, Accounts & Staff, Audit, Health, and mobile admin navigation for density, palette, typography, dimensional fixtures, attribution clarity, and responsive collapse. Fix all unapproved drift.

- [ ] **Step 5: Commit**

```bash
git add frontend/web/tests/e2e docs/design/guided-operations/README.md README.md
git commit -m "test: verify admin command center"
```

## Administrator Completion Gate

- Admin controls are inaccessible to users at API and UI layers.
- Elevation and step-up behavior matches existing identity rules.
- JavaScript never receives step-up credentials.
- All Incidents is incident-centered and preserves admin attribution/revision conflict behavior.
- Accounts & Staff safely manages roster and account state without exposing existing PINs.
- Audit and Health are bounded, safe, and useful.
- The admin interface matches the approved Operational Command Center concept and remains part of the Light Precision Workspace system.
