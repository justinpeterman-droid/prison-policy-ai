# Guided Operations — Officer Utilities

## Purpose

Officer Utilities completes the day-to-day officer workspace around the Incident Workspace. It replaces placeholder destinations with individually authenticated, authorization-scoped tools while preserving the approved light navy-and-gold design language.

The milestone includes:

- a real officer Home summary;
- a revisioned NCU Days Count workspace;
- a searchable approved Forms Library;
- a citation-backed Policy Expert;
- a personal Account and browser-session workspace; and
- the generic operational-paperwork persistence layer used by later daily-paperwork features.

## Officer navigation

The officer navigation remains intentionally small:

1. Home
2. New Report
3. Reports
4. Policy Expert
5. Forms Library
6. Account

The NCU Days Count is available from Home as a primary daily action. Administrators receive a separate command-center navigation in a later milestone.

## Home

Home is populated from `GET /api/web/v1/home` and contains only safe operational metadata:

- the best authorized incident to continue;
- recent authorized incidents;
- server-calculated workflow progress;
- report and required-paperwork counts;
- approved quick forms; and
- the signed-in officer's Count Sheet state for the selected date and shift.

It never returns field notes, report narratives, extracted facts, gap answers, PIN information, tokens, or another officer's unauthorized records. No fictional incident is substituted when the officer has no current work.

`Start New Incident` remains the sole dominant Home action. Count Sheet, Policy Expert, and Forms Library are prominent but visually secondary.

## Operational-paperwork store

The shared persistence layer uses two tables:

- `paperwork_records` stores record identity and the current validated payload.
- `paperwork_revisions` stores immutable snapshots, editor attribution, changed-field paths, save reason, client version, request ID, and creation time.

Supported kinds are closed to:

- `count_sheet`
- `assignment_roster`
- `uniform_inspection`
- `metal_detector_test`
- `perimeter_check`
- `random_search_log`
- `detector_sign_out`

Every save uses optimistic revision control and idempotency. A stale write returns a conflict while preserving the officer's visible local entries. Audit metadata records identifiers, revisions, action names, and bounded field paths—not paperwork contents.

## NCU Days Count

The Count Sheet structure is server-owned in `templates/paperwork/count_sheet.json`. The browser cannot add, remove, or reorder rows, columns, or operational fields.

The workspace provides:

- sparse nonnegative whole-number entry;
- exact approved row and column ordering;
- automatic row, out-of-housing, unit, housing, and operational totals;
- a signed reconciliation difference;
- explicit mismatch guidance without changing any entered value;
- arrow-key and Enter-key navigation;
- desktop grid and mobile grouped entry;
- 60-second idle autosave plus manual save;
- revision history and restore support in the service/API layer;
- dedicated landscape print markup; and
- audited preview, print, and supported download actions.

A mismatch is information to investigate, not a value the application is allowed to balance automatically.

## Forms Library

The Forms Library is backed by the sanitized form catalog. Its public response exposes only:

- template ID, code, name, category;
- purpose and when-used guidance;
- output kind and revision label;
- a closed capability list;
- frequent-form status; and
- approved obtain-from guidance for physical paperwork.

Digital capabilities may include preview, print, supported download formats, blank/fillable behavior, and adding the form to an incident. Physical-only paperwork exposes guidance and incident attachment only. It never receives a generated digital substitute.

Officers can search, filter by category, select multiple forms, preview a mixed packet in order, and review which physical forms are excluded from digital output.

## Policy Expert

Policy Expert reuses the existing policy retrieval and generation pipeline through `POST /api/web/v1/policy/questions`.

The browser API:

- accepts one bounded question;
- requires the individual browser session and same-origin CSRF confirmation;
- returns an answer only with at least one cited source passage;
- translates provider failures into stable public error codes;
- does not persist the question, answer, or source excerpts; and
- audits only bounded control metadata such as citation count and latency.

Policy answers never automatically add or change incident facts. Confirmed incident information must still be entered through the incident workflow.

## Account

The Account workspace displays read-only employee identity and provides:

- PIN change;
- active browser-session listing;
- current-session identification;
- revocation of another browser session;
- sign out on the current device; and
- sign out everywhere.

PIN changes rotate opaque HttpOnly credentials, revoke other sessions, and never return PINs or readable identity tokens in JSON. A user with a temporary PIN is held at the PIN-change screen until the replacement succeeds and the authenticated profile refreshes.

## Browser API surface

Officer Utilities adds these cookie-authenticated routes:

```text
GET    /api/web/v1/home

GET    /api/web/v1/paperwork?kind=count_sheet
GET    /api/web/v1/paperwork/count-sheets/structure
POST   /api/web/v1/paperwork/count-sheets
GET    /api/web/v1/paperwork/count-sheets/{record_id}
PATCH  /api/web/v1/paperwork/count-sheets/{record_id}
GET    /api/web/v1/paperwork/count-sheets/{record_id}/revisions
POST   /api/web/v1/paperwork/count-sheets/{record_id}/restore
POST   /api/web/v1/paperwork/count-sheets/{record_id}/actions

GET    /api/web/v1/forms
GET    /api/web/v1/forms/{template_id}
POST   /api/web/v1/forms/selection/preview
POST   /api/web/v1/forms/selection/download

POST   /api/web/v1/policy/questions

POST   /api/web/v1/account/change-pin
GET    /api/web/v1/account/sessions
DELETE /api/web/v1/account/sessions/{session_id}
POST   /api/web/v1/account/logout-all
```

Mutation bodies are closed schemas. Browser writes require same-origin validation and the session-bound CSRF token.

## Accessibility, responsive behavior, and print

The release gate covers:

- keyboard-only operation;
- visible focus treatment;
- accessible names for navigation, forms, status, and dialogs;
- reduced-motion operation;
- desktop and mobile layouts;
- persistent Count Sheet totals on mobile;
- dedicated print markup rather than screenshots; and
- physical-form warnings that remain visible without relying on color alone.

## Verification

The Officer Utilities release gate includes:

- Python unit and PostgreSQL 17 integration tests;
- migration upgrade → downgrade → upgrade;
- OpenAPI contract validation;
- React component tests and TypeScript checking;
- production Vite build;
- Playwright officer workflows for Home, Count Sheet, Forms Library, Policy Expert, and Account;
- the complete repository unit-test matrix on supported Python versions;
- Guided Operations Foundation and Web regression workflows; and
- the security scan.

Only fictional fixtures are used in tests and visual artifacts.