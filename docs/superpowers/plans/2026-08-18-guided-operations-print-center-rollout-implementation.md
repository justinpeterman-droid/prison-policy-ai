# Guided Operations Weekly/Monthly Print Center and Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the Weekly and Monthly print libraries—including the four supplied monthly logs—then verify the complete web application, pilot it alongside the Access and legacy Jinja clients, and provide a configuration-only rollback path before any legacy retirement.

**Architecture:** Sanitized print-template definitions contain official labels, row schedules, page geometry, and editable prefill fields without persisting completed weekly/monthly entries in release one. Flask exposes read-only template and packet-definition APIs; React renders dedicated print documents and multi-form packets, while `WEB_APP_MODE=off|preview|primary` controls route exposure so primary cutover can be reversed without database changes.

**Tech Stack:** Python 3.14, Flask 3, React, TypeScript, TanStack Query, Zod, Playwright, HTML/CSS paged print, Docker multi-stage builds, GitHub Actions, Cloud Run, and existing operations/runbook conventions.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Global Constraints

- Weekly and Monthly are curated preview-and-print libraries in release one.
- Completed weekly/monthly row entries are not persisted in release one.
- Month and shift may be prefilled into monthly previews, but remain browser-local until printing.
- The four supplied monthly templates are Windows, Bars & Doors Check Log; Use of Chemical Agents Log; Contraband Search Log — Standard Area Rotation; and Contraband Search Log — Expanded Area Rotation.
- Both contraband schedules remain available until an administrator explicitly approves retirement of one.
- No weekly form is invented. Until approved weekly templates are supplied, the Weekly tab displays `No weekly forms have been published.`
- All template definitions and fixtures are sanitized; real names, employee numbers, equipment identifiers, and historical entries are prohibited.
- Print output uses dedicated markup, correct letter page geometry, explicit page breaks, grayscale-safe line weights, and no application chrome.
- `WEB_APP_MODE=preview` leaves all legacy routes unchanged and serves the SPA under `/workspace`.
- `WEB_APP_MODE=primary` is enabled only after the pilot gates pass and explicit user approval is recorded.
- Rollback changes configuration only; it does not downgrade the database or delete web-created data.
- Access `/api/v1`, the Access client, report engine, Policy Expert, and Word exports remain available throughout rollout.
- No agent deploys, changes production configuration, or retires a route without separate explicit authorization.

---

## File Map

```text
templates/paperwork/weekly/catalog.json
templates/paperwork/monthly/
  catalog.json
  windows_bars_doors.json
  chemical_agents.json
  contraband_search_standard.json
  contraband_search_expanded.json

backend/paperwork/templates.py
backend/paperwork/monthly.py
backend/forms/library.py
backend/webapp/web_api/print_templates.py
backend/webapp/web_api/forms.py
backend/webapp/web_api/__init__.py
backend/webapp/routes/web_app.py
backend/webapp/app.py
backend/webapp/assets.py
backend/webapp/routes/chat.py
backend/webapp/routes/reports.py
backend/webapp/routes/roster.py
backend/webapp/routes/review_lab.py
openapi/web-v1.yaml
firebase.json
Dockerfile

frontend/web/src/features/administration/paperwork/
  WeeklyPaperworkTab.tsx
  MonthlyPaperworkTab.tsx
  PrintTemplateCard.tsx
  PrintTemplatePreview.tsx
  PrintPacketBuilder.tsx
  monthly/WindowsBarsDoorsPrint.tsx
  monthly/ChemicalAgentsPrint.tsx
  monthly/ContrabandSearchPrint.tsx
frontend/web/src/features/forms-library/
  FormCard.tsx
  FormSelectionBar.tsx
frontend/web/src/print/
  PrintDocument.tsx
  PrintPacket.tsx
  print-registry.tsx
frontend/web/src/styles/print.css
frontend/web/tests/e2e/weekly-monthly-print.spec.ts
frontend/web/tests/e2e/full-product-regression.spec.ts
frontend/web/tests/e2e/legacy-fallback.spec.ts

scripts/check_web_build.py
scripts/check_print_templates.py
.github/workflows/tests.yml
.github/workflows/pages.yml

tests/unit/test_print_template_definitions.py
tests/unit/test_monthly_templates.py
tests/unit/test_web_primary_routes.py
tests/integration/test_print_template_api.py
tests/integration/test_web_rollout_modes.py
tests/contract/test_web_v1_openapi.py
tests/security/test_web_security_headers.py
tests/fixtures/paperwork/monthly/
  windows_bars_doors_fictional.json
  chemical_agents_fictional.json
  contraband_standard_fictional.json
  contraband_expanded_fictional.json

docs/runbooks/guided-operations-web-pilot.md
docs/runbooks/guided-operations-web-rollback.md
docs/user-guides/guided-operations-officer-quick-start.md
docs/user-guides/guided-operations-admin-quick-start.md
docs/operations/guided-operations-release-gates.md
```

## Shared Interfaces Produced by This Plan

```python
class PrintTemplatePeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True)
class PrintTemplateDefinition:
    code: str
    title: str
    period: PrintTemplatePeriod
    category: str
    schema_version: int
    page_size: Literal["letter"]
    orientation: Literal["portrait", "landscape"]
    definition: dict[str, object]


def load_print_template(code: str) -> PrintTemplateDefinition: ...
def list_print_templates(period: PrintTemplatePeriod) -> tuple[PrintTemplateDefinition, ...]: ...
def validate_print_prefill(template: PrintTemplateDefinition, payload: dict[str, object]) -> dict[str, object]: ...
```

Frontend print registry:

```ts
export type PrintTemplateCode =
  | "monthly_windows_bars_doors"
  | "monthly_chemical_agents"
  | "monthly_contraband_standard"
  | "monthly_contraband_expanded";

export const printRegistry: Record<
  PrintTemplateCode,
  React.ComponentType<{ prefill: MonthlyPrintPrefill }>
>;
```

### Task 1: Create sanitized weekly and monthly print-template definitions

**Files:**
- Create: `templates/paperwork/weekly/catalog.json`
- Create: `templates/paperwork/monthly/*.json`
- Create: `backend/paperwork/templates.py`
- Test: `tests/unit/test_print_template_definitions.py`
- Test: `tests/unit/test_monthly_templates.py`

**Interfaces:**
- Produces: `PrintTemplateDefinition`, loader, list, and prefill validation.

- [ ] **Step 1: Write the failing catalog tests**

Assert:

- Weekly catalog exists and contains an empty `templates` array.
- Monthly catalog lists exactly four unique codes.
- Every definition uses `schema_version: 1`, `page_size: letter`, and `orientation: landscape`.
- Unknown keys, HTML, absolute paths, real names, employee-number patterns, and historical filled entries are prohibited.
- Contraband variants have different schedules and descriptive titles.

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_print_template_definitions.py tests/unit/test_monthly_templates.py -v
```

Expected: FAIL because the definitions and loader do not exist.

- [ ] **Step 3: Create the Weekly catalog**

`templates/paperwork/weekly/catalog.json`:

```json
{
  "schema_version": 1,
  "period": "weekly",
  "templates": []
}
```

The API and UI use the exact empty-state text `No weekly forms have been published.` No sample weekly forms are invented.

- [ ] **Step 4: Create Windows, Bars & Doors definition**

`windows_bars_doors.json` contains:

```json
{
  "code": "monthly_windows_bars_doors",
  "title": "Windows, Bars & Doors Check Log",
  "period": "monthly",
  "category": "security_checks",
  "schema_version": 1,
  "page_size": "letter",
  "orientation": "landscape",
  "definition": {
    "prefill_fields": ["month", "shift"],
    "days": 31,
    "columns": [
      "Date",
      "Exterior Bks. Windows",
      "All Inmate Housing Windows",
      "Housing Doors",
      "All Cell Bars",
      "Officer's Signature"
    ],
    "footer_note": "All bars will be checked with a rubber mallet.",
    "comments_label": "Comments"
  }
}
```

- [ ] **Step 5: Create Chemical Agents definition**

`chemical_agents.json` contains month and shift-supervisor prefill plus columns Date, Staff, Inmate Name / #, Conforms To Policy, Medical Attention, Supervisor, followed by COS Review / Date and Warden Review / Date sign-off areas. It contains blank rows only.

- [ ] **Step 6: Create both Contraband Search definitions**

Both contain prefill fields Month and Shift plus Date/Time, Area Searched, Contraband Found, Searching Officers, Disposition of Contraband, and Additional Comments.

The standard schedule, in source order, is:

```json
[
  "Gym",
  "School",
  "Front Office / Barber Shop",
  "Boiler Room",
  "Kitchen and ODR",
  "Laundry Press Area / Main Showers"
]
```

The expanded schedule, in source order, is:

```json
[
  "Gym",
  "Chapel",
  "Entrance Building",
  "School",
  "Front Office / Barbershop",
  "Boiler Room",
  "Kitchen / ODR",
  "Laundry",
  "Inmate Barbershop",
  "Inside Maintenance"
]
```

Each definition includes the source schedule repeated to the number of printed rows in its supplied form, rather than a runtime-generated random rotation.

- [ ] **Step 7: Implement strict loader and prefill validator**

```python
ALLOWED_PREFILL_FIELDS = {"month", "shift", "shift_supervisor"}


def validate_print_prefill(template, payload):
    if set(payload) - set(template.definition.get("prefill_fields", [])):
        raise ValueError("print prefill contains an unsupported field")
    # month must be YYYY-MM; shift is 1–32 characters; supervisor is at most 160.
    return normalized
```

`month` must match `^[0-9]{4}-(0[1-9]|1[0-2])$`. The loader caches immutable definitions and rejects duplicate codes across weekly and monthly catalogs.

- [ ] **Step 8: Verify and commit**

```bash
python -m pytest tests/unit/test_print_template_definitions.py tests/unit/test_monthly_templates.py -v
git add templates/paperwork/weekly templates/paperwork/monthly backend/paperwork/templates.py tests/unit/test_print_template_definitions.py tests/unit/test_monthly_templates.py
git commit -m "feat: add weekly and monthly print templates"
```

### Task 2: Expose read-only print-template and packet-definition APIs

**Files:**
- Create: `backend/webapp/web_api/print_templates.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Modify: `backend/webapp/web_api/forms.py`
- Modify: `backend/forms/library.py`
- Modify: `openapi/web-v1.yaml`
- Test: `tests/integration/test_print_template_api.py`
- Test: `tests/contract/test_web_v1_openapi.py`

**Interfaces:**
- Consumes: Task 1 definitions.
- Produces: template list/detail and packet validation APIs.

- [ ] **Step 1: Write failing API tests**

Cover authenticated access, weekly empty list, monthly four-item list, detail, invalid code, month/shift normalization, packet order, duplicate template rejection, unsupported prefill rejection, and no persistence side effect.

- [ ] **Step 2: Add routes**

```text
GET  /api/web/v1/print-templates?period=weekly|monthly
GET  /api/web/v1/print-templates/{template_code}
POST /api/web/v1/print-templates/packet
POST /api/web/v1/print-templates/actions
```

Packet body:

```json
{
  "period": "monthly",
  "template_codes": ["monthly_windows_bars_doors", "monthly_chemical_agents"],
  "prefill": {"month": "2026-08", "shift": "D"}
}
```

The response contains ordered validated definitions and normalized prefill only. It creates no database record.

- [ ] **Step 3: Add bounded action audit**

Actions accept `preview|print` plus one or more template codes and period. Audit records actor, template codes, action, result, request ID, and client version without prefilled names or form content.

- [ ] **Step 4: Integrate Forms Library**

Monthly templates appear under Monthly Paperwork with capabilities `preview` and `print`. Weekly returns no items until catalog entries exist. Print-only templates cannot be attached to incidents unless their definition explicitly adds an `incident_attachable` capability in a future reviewed change.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/integration/test_print_template_api.py tests/contract/test_web_v1_openapi.py -v
git add backend/webapp/web_api/print_templates.py backend/webapp/web_api/__init__.py backend/webapp/web_api/forms.py backend/forms/library.py openapi/web-v1.yaml tests
git commit -m "feat: expose print template library API"
```

### Task 3: Build the shared print registry and packet renderer

**Files:**
- Create: `frontend/web/src/print/PrintDocument.tsx`
- Create: `frontend/web/src/print/PrintPacket.tsx`
- Create: `frontend/web/src/print/print-registry.tsx`
- Modify: `frontend/web/src/styles/print.css`
- Test: `frontend/web/src/print/PrintPacket.test.tsx`

**Interfaces:**
- Consumes: validated print definitions and prefill.
- Produces: deterministic single-form and multi-form rendering.

- [ ] **Step 1: Write failing registry tests**

Assert every API template code has one renderer, unknown codes fail safely, packet order follows selection order, every form begins on a new sheet, app chrome is absent in print media, and no empty trailing page is produced.

- [ ] **Step 2: Implement PrintDocument**

```tsx
export function PrintDocument({ title, children }: Props) {
  return (
    <section className="print-document" aria-label={title}>
      {children}
    </section>
  );
}
```

CSS:

```css
@page { size: letter landscape; margin: 0.35in; }
.print-document { break-after: page; }
.print-document:last-child { break-after: auto; }
@media print {
  .app-shell, .no-print { display: none !important; }
  .print-root { display: block !important; color: #000; background: #fff; }
}
```

- [ ] **Step 3: Implement strict registry**

```ts
export const printRegistry: Record<PrintTemplateCode, React.ComponentType<PrintProps>> = {
  monthly_windows_bars_doors: WindowsBarsDoorsPrint,
  monthly_chemical_agents: ChemicalAgentsPrint,
  monthly_contraband_standard: ContrabandSearchPrint,
  monthly_contraband_expanded: ContrabandSearchPrint,
};
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/print/PrintPacket.test.tsx
npm run typecheck
git add src/print src/styles/print.css
git commit -m "feat: add shared print packet renderer"
```

### Task 4: Build the four monthly print documents

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/monthly/WindowsBarsDoorsPrint.tsx`
- Create: `frontend/web/src/features/administration/paperwork/monthly/ChemicalAgentsPrint.tsx`
- Create: `frontend/web/src/features/administration/paperwork/monthly/ContrabandSearchPrint.tsx`
- Test: monthly print component tests.

**Interfaces:**
- Consumes: exact Task 1 definitions and normalized prefill.
- Produces: paper-accurate monthly output.

- [ ] **Step 1: Write failing Windows/Bars/Doors tests**

Assert month and shift header, days 1–31, six columns in exact order, rubber-mallet note, Comments area, and no historical values.

- [ ] **Step 2: Implement Windows/Bars/Doors**

Use semantic table headers, fixed row height sufficient for handwritten marks, visible signature column, and a comments block that remains on the same page. Month labels are formatted for display without changing the stored `YYYY-MM` prefill.

- [ ] **Step 3: Write failing Chemical Agents tests**

Assert title, month, shift supervisor, six source columns, blank log rows, COS Review / Date, Warden Review / Date, and signature-ready spacing.

- [ ] **Step 4: Implement Chemical Agents**

The prefilled supervisor name is optional and never persisted by this print-only workflow. Blank rows remain blank; no zero, placeholder person, or example incident is rendered.

- [ ] **Step 5: Write failing Contraband tests**

Assert common columns, month/shift, Additional Comments, standard schedule order, expanded schedule order, distinct titles, and all scheduled areas rendered.

- [ ] **Step 6: Implement one parameterized Contraband renderer**

```tsx
export function ContrabandSearchPrint({ definition, prefill }: PrintProps) {
  const rows = definition.definition.schedule as string[];
  return <PrintDocument title={definition.title}>{/* exact table */}</PrintDocument>;
}
```

Do not branch on title text; use template code and definition data.

- [ ] **Step 7: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/monthly
npm run typecheck
git add src/features/administration/paperwork/monthly
git commit -m "feat: render supplied monthly paperwork"
```

### Task 5: Build Weekly and Monthly Paperwork Center tabs and packet selection

**Files:**
- Create: `frontend/web/src/features/administration/paperwork/WeeklyPaperworkTab.tsx`
- Create: `frontend/web/src/features/administration/paperwork/MonthlyPaperworkTab.tsx`
- Create: `frontend/web/src/features/administration/paperwork/PrintTemplateCard.tsx`
- Create: `frontend/web/src/features/administration/paperwork/PrintTemplatePreview.tsx`
- Create: `frontend/web/src/features/administration/paperwork/PrintPacketBuilder.tsx`
- Modify: `frontend/web/src/features/administration/paperwork/PaperworkCenterPage.tsx`
- Test: Weekly/Monthly tab tests.

**Interfaces:**
- Consumes: Task 2 API and Task 3 registry.
- Produces: complete Daily/Weekly/Monthly Paperwork Center.

- [ ] **Step 1: Write failing Weekly tests**

Assert selected raised tab, exact empty-state text, no fake form cards, and a short explanation that forms appear after approved publication.

- [ ] **Step 2: Write failing Monthly tests**

Assert four descriptive form names, month selector, shift input, Preview, Print, multi-selection, Preview Monthly Packet, Print Monthly Packet, clear selection, and selection persistence while switching preview documents.

- [ ] **Step 3: Implement month and shift prefill**

Default month is the current local month displayed to the user; sending to the server uses `YYYY-MM`. Shift is selected from the current profile’s shift when available but remains editable. Neither value is written to a completed-record endpoint.

- [ ] **Step 4: Implement preview**

Preview opens a document viewer with page navigation and zoom. It renders code-native HTML, not a raster screenshot. Print buttons call `window.print()` only after the validated definition has loaded.

- [ ] **Step 5: Implement packet builder**

Show selected forms in drag/keyboard-reorderable order. Reordering changes packet order only, never the source row order inside a form. Before print, list included form titles and month/shift.

- [ ] **Step 6: Verify and commit**

```bash
cd frontend/web
npm run test -- src/features/administration/paperwork/WeeklyPaperworkTab.test.tsx src/features/administration/paperwork/MonthlyPaperworkTab.test.tsx src/features/administration/paperwork/PrintPacketBuilder.test.tsx
npm run typecheck
git add src/features/administration/paperwork
git commit -m "feat: add weekly and monthly print center"
```

### Task 6: Add print-template validation and visual regression gates

**Files:**
- Create: `scripts/check_print_templates.py`
- Create: `tests/fixtures/paperwork/monthly/*.json`
- Create: `frontend/web/tests/e2e/weekly-monthly-print.spec.ts`
- Modify: `docs/design/guided-operations/README.md`

**Interfaces:**
- Produces: deterministic template and print checks.

- [ ] **Step 1: Implement repository template check**

`scripts/check_print_templates.py` loads all weekly/monthly definitions and fails on duplicate code, unsupported period, unsupported orientation, missing registry code, historical filled value, path traversal, HTML, source staff names, employee-number patterns, or nonblank log-entry fields.

- [ ] **Step 2: Create fictional prefill fixtures**

Use only month `2026-08`, shift `D`, and fictional supervisor `Sgt. Riley Jordan`. No operational row is completed.

- [ ] **Step 3: Add print regression assertions**

For every monthly form and a four-form packet, assert exact headings, source schedule/order, page count, letter landscape geometry, 0.35-inch margins, no clipping, no horizontal overflow, no empty trailing page, no application chrome, and grayscale legibility.

- [ ] **Step 4: Compare against supplied workbook structure**

Inspect render screenshots against the source workbook’s hierarchy: title/header placement, row counts, column grouping, review/signature areas, comments area, and form separation. Record and fix every material mismatch without copying historical content.

- [ ] **Step 5: Verify and commit**

```bash
python scripts/check_print_templates.py
cd frontend/web && npm run test:e2e -- tests/e2e/weekly-monthly-print.spec.ts && cd ../..
git add scripts/check_print_templates.py tests/fixtures/paperwork/monthly frontend/web/tests/e2e/weekly-monthly-print.spec.ts docs/design/guided-operations/README.md
git commit -m "test: verify weekly and monthly print templates"
```

### Task 7: Harden static delivery, cache policy, and browser security headers

**Files:**
- Modify: `backend/webapp/assets.py`
- Modify: `backend/webapp/routes/web_app.py`
- Modify: `backend/webapp/app.py`
- Modify: `Dockerfile`
- Test: `tests/security/test_web_security_headers.py`
- Test: `tests/unit/test_web_asset_cache.py`

**Interfaces:**
- Produces: safe SPA document and immutable asset delivery.

- [ ] **Step 1: Write failing header tests**

Assert:

- SPA HTML: `Cache-Control: no-store`;
- hashed assets: `Cache-Control: public, max-age=31536000, immutable`;
- `Content-Security-Policy` permits only same-origin scripts/styles/images/fonts plus required data-image support;
- `frame-ancestors 'none'`;
- `object-src 'none'`;
- `base-uri 'self'`;
- `form-action 'self'`;
- `Referrer-Policy: no-referrer`;
- `X-Content-Type-Options: nosniff`;
- `Permissions-Policy` disables camera, microphone, geolocation, and payment unless a later approved feature needs one.

- [ ] **Step 2: Implement CSP without inline exceptions**

The Vite application contains no inline executable script or `eval`; do not add `'unsafe-inline'` or `'unsafe-eval'` to `script-src`.

- [ ] **Step 3: Verify asset manifest and compression**

`assets.py` recognizes Vite hashed filenames and keeps existing content-versioned legacy behavior. Text assets may be gzip-compressed; DOCX/PDF outputs are not recompressed by this handler.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/security/test_web_security_headers.py tests/unit/test_web_asset_cache.py tests/unit/test_assets.py -v
git add backend/webapp/assets.py backend/webapp/routes/web_app.py backend/webapp/app.py Dockerfile tests
git commit -m "security: harden guided operations web delivery"
```

### Task 8: Implement primary-route mode, legacy aliases, and configuration-only rollback

**Files:**
- Modify: `backend/webapp/routes/web_app.py`
- Modify: `backend/webapp/app.py`
- Modify: `backend/webapp/routes/chat.py`
- Modify: `backend/webapp/routes/reports.py`
- Modify: `backend/webapp/routes/roster.py`
- Modify: `backend/webapp/routes/review_lab.py`
- Modify: `firebase.json`
- Test: `tests/unit/test_web_primary_routes.py`
- Test: `tests/integration/test_web_rollout_modes.py`
- Create: `frontend/web/tests/e2e/legacy-fallback.spec.ts`

**Interfaces:**
- Consumes: `WEB_APP_MODE=off|preview|primary` from the Foundation plan.
- Produces: reversible route ownership.

- [ ] **Step 1: Write the complete mode matrix as tests**

```text
off:
  /workspace/* -> 404
  legacy /, /chat, /reports, /roster, /review-lab -> unchanged

preview:
  /workspace/* -> SPA
  legacy routes -> unchanged

primary:
  /, /home, /new-report, /reports, /reports/*, /policy-expert,
  /forms, /count-sheet, /account, /admin/* -> SPA
  /legacy, /legacy/chat, /legacy/reports, /legacy/roster,
  /legacy/review-lab -> legacy pages under existing authorization
```

Legacy API routes remain at their existing paths during pilot and are not routed to the SPA.

- [ ] **Step 2: Move legacy page handlers behind explicit aliases**

Create route functions that can register the same render handlers at the legacy alias paths without duplicating business logic. Blueprint endpoint names remain unique. In `off` and `preview`, original page paths remain registered. In `primary`, original client paths belong to the SPA.

- [ ] **Step 3: Preserve safe auth behavior**

The SPA login uses individual browser sessions. `/legacy/*` keeps legacy shared-code behavior until retirement approval. A browser-session cookie never automatically grants legacy shared-code admin access, except the already-approved Review Lab one-time handoff.

- [ ] **Step 4: Add rollback test**

Changing `WEB_APP_MODE` from `primary` to `preview` restores the old routes without schema downgrade, record conversion, data deletion, or token migration. Web-created incidents and paperwork remain in PostgreSQL and continue to be accessible after returning to `primary`.

- [ ] **Step 5: Update Firebase route behavior**

The managed public host sends application paths to Cloud Run; it does not serve a second stale SPA bundle. Preserve only required redirects and hosting configuration.

- [ ] **Step 6: Verify and commit**

```bash
python -m pytest tests/unit/test_web_primary_routes.py tests/integration/test_web_rollout_modes.py tests/unit/test_safe_next.py tests/unit/test_admin_tier.py -v
cd frontend/web && npm run test:e2e -- tests/e2e/legacy-fallback.spec.ts && cd ../..
git add backend/webapp/routes backend/webapp/app.py firebase.json tests frontend/web/tests/e2e/legacy-fallback.spec.ts
git commit -m "feat: add reversible guided operations route cutover"
```

### Task 9: Add CI, build, and release gates for the complete browser product

**Files:**
- Modify: `.github/workflows/tests.yml`
- Modify: `.github/workflows/pages.yml`
- Modify: `Dockerfile`
- Modify: `scripts/check_web_build.py`
- Create: `docs/operations/guided-operations-release-gates.md`
- Test: workflow contract tests under `tests/unit/`.

**Interfaces:**
- Produces: repeatable verification and artifact build without deployment.

- [ ] **Step 1: Write failing workflow-contract tests**

Assert CI runs npm lockfile install, lint, typecheck, unit tests, Vite build, Playwright Chromium, print-template check, Python unit/contract/security suites, and retains existing PostgreSQL integration gates.

- [ ] **Step 2: Stop publishing the old standalone forms app as the primary product**

`pages.yml` may continue publishing `frontend/forms` only under its existing legacy/demo path during pilot. It must not overwrite or masquerade as the Cloud Run Guided Operations application.

- [ ] **Step 3: Define release gates document**

The document requires:

```text
- all automated suites pass twice;
- approved concept fidelity is complete;
- all print regressions pass;
- accessibility checks pass;
- test and production configuration are isolated;
- database migration backup and rollback readiness are documented;
- pilot acceptance is signed off;
- WEB_APP_MODE remains preview until explicit primary approval;
- no source workbook or real identity exists in the image or repository.
```

- [ ] **Step 4: Verify Docker image contents**

Build the image and assert it contains Vite assets, templates, and migrations but does not contain `frontend/web/node_modules`, uploaded `.xls/.xlsx` files, Playwright output, screenshots with real data, or source workbook previews.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_web_build_contract.py tests/unit/test_operations_prerequisites.py -v
python scripts/check_print_templates.py
docker build -t prison-policy-ai:guided-operations .
git add .github/workflows Dockerfile scripts/check_web_build.py docs/operations/guided-operations-release-gates.md tests/unit
git commit -m "ci: gate guided operations web releases"
```

### Task 10: Write pilot, rollback, and role-specific quick-start guides

**Files:**
- Create: `docs/runbooks/guided-operations-web-pilot.md`
- Create: `docs/runbooks/guided-operations-web-rollback.md`
- Create: `docs/user-guides/guided-operations-officer-quick-start.md`
- Create: `docs/user-guides/guided-operations-admin-quick-start.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: usable pilot and support documentation.

- [ ] **Step 1: Write the pilot runbook**

Include exact phases:

1. test environment acceptance;
2. `WEB_APP_MODE=preview` internal review at `/workspace`;
3. small fictional-data usability exercise;
4. limited authorized pilot using real production accounts;
5. parity review against Access and legacy Jinja;
6. issue triage and repair;
7. explicit go/no-go review for `primary`;
8. post-cutover observation; and
9. explicit legacy-retirement review.

The runbook states that an agent does not perform production steps.

- [ ] **Step 2: Write configuration-only rollback**

Document:

```text
Trigger conditions:
- sign-in failure rate increase;
- report save/export regression;
- print-template mismatch;
- authorization defect;
- inaccessible critical officer workflow.

Action:
- set WEB_APP_MODE=preview;
- verify legacy routes;
- keep database migrations and data intact;
- preserve logs/request IDs;
- open a controlled incident review;
- repair in test before another primary attempt.
```

No database downgrade is part of routine UI rollback.

- [ ] **Step 3: Write officer guide**

Cover individual sign-in, Home, New Report, incident Reports, copy-only outputs, populated required forms, physical Chain of Custody reminder, Count Sheet, Forms Library, Policy Expert, Account, save states, and safe sign-out.

- [ ] **Step 4: Write admin guide**

Cover elevation, Overview, All Incidents attribution, Paperwork Center Daily/Weekly/Monthly, Accounts & Staff, one-time PIN handling, Audit, Health, Review Lab, and sensitive step-up prompts.

- [ ] **Step 5: Update repository entry points and commit**

```bash
git add docs/runbooks docs/user-guides README.md AGENTS.md
git commit -m "docs: add guided operations pilot and user guides"
```

### Task 11: Run complete product, security, print, and rollback verification twice

**Files:**
- Create: `frontend/web/tests/e2e/full-product-regression.spec.ts`
- Modify: `docs/operations/guided-operations-release-gates.md`
- Modify: `docs/design/guided-operations/README.md`

**Interfaces:**
- Produces: pilot-ready release evidence.

- [ ] **Step 1: Add the complete officer path**

Individual sign in → Home → Count Sheet save/print → New Report → generated reports → copy Supervisor Summary → populated 005 preview → physical Chain of Custody acknowledgment → Forms Library → Policy Expert → Account session view.

- [ ] **Step 2: Add the complete admin path**

Elevate → Overview → All Incidents attributed view → Accounts & Staff fictional PIN reset → Daily Assignment Roster/Uniform Inspection → Monthly four-form packet → Audit verification → Health → Review Lab handoff.

- [ ] **Step 3: Add mode and rollback path**

Run smoke tests in `off`, `preview`, and `primary`; switch primary → preview and verify legacy pages plus retained web data.

- [ ] **Step 4: Add final accessibility and responsive pass**

Test login, Home, Count Sheet, Reports, Document Studio, Forms Library, Account, Admin Overview, All Incidents, Accounts & Staff, Audit, Health, Daily editors, Weekly empty state, and Monthly packet at desktop 1366×768, tablet 1024×768, mobile 390×844, Windows scaling assumptions 100–150%, keyboard-only, high-contrast text, and reduced motion.

- [ ] **Step 5: Add final visual-fidelity ledger**

Use the approved concept and latest render images in the same review pass. Record copy, navigation, first-viewport hierarchy, palette, typography, dimensional controls, paper treatment, spacing, responsive behavior, motion, and icon treatment. Fix every remaining agency-review comment.

- [ ] **Step 6: Run the complete suite twice**

```bash
cd frontend/web
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
cd ../..
python scripts/check_web_build.py
python scripts/check_print_templates.py
python -m pytest tests/unit tests/contract tests/security -q
python -m pytest tests/integration -q
```

Run the same sequence a second time. Both runs must pass against an isolated test PostgreSQL database.

- [ ] **Step 7: Record evidence and commit**

Update release gates with command outputs, tested commit SHA, viewport matrix, print templates checked, and known intentional deviations. No production deployment claim is recorded.

```bash
git add frontend/web/tests/e2e/full-product-regression.spec.ts docs/operations/guided-operations-release-gates.md docs/design/guided-operations/README.md
git commit -m "test: verify guided operations pilot release"
```

## Print Center and Rollout Completion Gate

- Weekly shows an honest empty state until approved forms are added.
- Monthly contains exactly the four supplied forms with sanitized blank rows and exact schedules.
- Single and packet print output passes page, order, clipping, grayscale, and no-chrome checks.
- Monthly print workflows do not persist completed row entries.
- Security headers and cache rules are verified.
- `off`, `preview`, and `primary` route matrices pass.
- Primary-to-preview rollback restores legacy UI without database downgrade or data loss.
- Officer, admin, Access, legacy, security, print, accessibility, and full-product suites pass twice.
- Primary cutover and legacy retirement remain blocked on separate explicit user authorization.
