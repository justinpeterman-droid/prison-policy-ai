# Website Update Completion Checklist

This checklist tracks the remaining work required to complete the Guided Operations website update, including the Administrator Command Center, Paperwork Center, visual QA, testing, rollout, and legacy browser retirement.

## 1. Administrator Command Center — Complete

- [x] Fix the Admin Incident Workspace data-loading failure.
- [x] Ensure an administrator can open an incident from **All Incidents**.
- [x] Display the **Administrator incident controls** panel after opening an incident.
- [x] Load the incident number, name, records status, and current revision correctly.
- [x] Preserve the administrator-attribution notice while viewing another employee’s incident.
- [x] Verify the administrator can move from All Incidents into Document Studio.
- [x] Fix the revision-restore workflow.
- [x] Require purpose-scoped confirmation before restoring a revision.
- [x] Remove or rename Audit Log text that exposes or matches restricted narrative information.
- [x] Re-run the Admin Incident Workspace component tests.
- [x] Re-run the administrator Playwright browser tests.
- [x] Confirm all Administrator Command Center workflow checks pass.
- [x] Review the Administrator Command Center at desktop, tablet, and mobile sizes.
- [x] Mark PR #104 ready for review.
- [x] Complete final review of PR #104.
- [x] Merge PR #104 into `main`.

## 2. Documentation and Local Setup — Complete

- [x] Review PR #105.
- [x] Verify the documented PostgreSQL 17 requirement.
- [x] Verify the fictional local officer seeding instructions.
- [x] Clearly document which tests run with each command.
- [x] Correct the duplicated `lint` and `typecheck` documentation.
- [x] Document the Vertex Application Default Credentials requirement.
- [x] Document the behavior of an empty `ACCESS_CODE`.
- [x] Document `LEGACY_REPORT_MODE`.
- [x] Decide whether to create a real staff-provisioning command under `scripts/`.
- [x] Merge the corrected documentation into `main`.

## 3. Daily Paperwork Center

### Shared Foundation

- [x] Add the Administrator **Paperwork Center** route.
- [x] Add **Daily**, **Weekly**, and **Monthly** tabs.
- [x] Add date and shift selection.
- [x] Add saved-record search and reopen behavior.
- [x] Add revision-safe saving.
- [x] Add autosave and manual-save states.
- [x] Add print-preview support.
- [x] Add administrator attribution and audit events.
- [x] Add desktop, tablet, and mobile layouts.
- [x] Add keyboard navigation and accessible labels.

### Shift Assignment Roster

- [x] Build the Shift Assignment Roster editor.
- [x] Load active staff from Accounts & Staff.
- [x] Add employee search and selection.
- [x] Add assignment sections and operational posts.
- [x] Add leave time and leave-type fields.
- [x] Add extra assignments.
- [x] Add alternate shift supervisor.
- [x] Add briefing notes and roll-call fields.
- [x] Add captain, lieutenant, and duty-warden fields.
- [x] Add copy-previous-roster functionality.
- [x] Add approved assignment rotation.
- [x] Add coverage warnings without automatically reassigning staff.
- [x] Save by date and shift.
- [x] Reopen an existing roster.
- [x] Create an accurate print layout.
- [x] Add unit, integration, browser, and print-regression tests.

### Uniform Inspection

- [x] Build the Uniform Inspection editor.
- [x] Load staff from the selected Assignment Roster.
- [x] Include Shirt, Pants, Shoes, Cap, Coat, ID, Hair, Nails, and Comments.
- [x] Support `S`, `N/I`, `U`, and `NONE`.
- [x] Require a comment for unsatisfactory entries.
- [x] Add bulk-mark-column-satisfactory behavior.
- [x] Add inspector, shift, and date fields.
- [x] Save and reopen inspections.
- [x] Create an accurate print layout.
- [x] Add unit, integration, browser, and print-regression tests.

### Daily Walk-Through Metal Detector Testing

- [x] Build the detector-testing matrix.
- [x] Include detectors 1 through 11.
- [x] Include all seven test positions.
- [x] Support pass/fail results.
- [x] Require corrective-action notes for failures.
- [x] Add tested-by, reviewed-by, date, and comments.
- [x] Save and reopen records.
- [x] Create an accurate print layout.
- [x] Add unit, integration, browser, and print-regression tests.

### Daily Perimeter Checklist

- [x] Build the perimeter checklist editor.
- [x] Preserve the complete approved location list.
- [x] Include Doors, Outside Doors, Fence & Gates, and supporting sections.
- [x] Support satisfactory/unsatisfactory results.
- [x] Add Senstar Test, Pipe Chases, Manholes, Metal Detector, Fence, and Alleyways.
- [x] Add inspector, supervisor, signature, date, and time fields.
- [x] Save and reopen records.
- [x] Create an accurate print layout.
- [x] Add unit, integration, browser, and print-regression tests.

### Daily Random Searches

- [x] Build repeated structured search-entry rows.
- [x] Include North 1, North 2, South 1, and South 2.
- [x] Support four officer blocks per section.
- [x] Include date, time, inmate name, ADC number, barracks/rack, contraband, and disposition.
- [x] Save and reopen records.
- [x] Reproduce the approved blocks in the print view.
- [x] Add unit, integration, browser, and print-regression tests.

### Handheld Metal Detector Sign-Out

- [x] Build the detector sign-out editor.
- [x] Include units D1 through D9.
- [x] Include staff name and area of assignment.
- [x] Include shift supervisor and date.
- [x] Save and reopen records.
- [x] Create an accurate print layout.
- [x] Add unit, integration, browser, and print-regression tests.

### Daily Milestone Verification Snapshot — 2026-08-20

- Daily editors now autosave server-backed records after a short quiet interval. First saves remain explicit; failed writes preserve the visible draft for a retry.
- The assembled frontend suite passes 117 component tests, TypeScript checking, and a production build with route- and editor-level code splitting.
- Chromium coverage passes for all six Daily print surfaces plus Weekly/Monthly navigation, desktop/mobile overflow checks, keyboard navigation, save/reopen/failure/retry recovery, and a four-form Monthly packet using fictional data.
- Focused template, contract, delivery-security, and release-gate checks pass (37 tests). PostgreSQL-backed integration tests remain a CI/target-environment release gate.

### Local PostgreSQL Release-Gate Check — 2026-08-20

- `TEST_DATABASE_URL` is not configured in this worktree environment.
- A local `psql` client is not installed, Docker is unavailable, and the active Python installation does not include pytest.
- PostgreSQL 17 integration and migration lifecycle checks were therefore not run locally. Per the repository test policy, no substitute database or guessed connection was used; these remain required CI/target-environment gates.

## 4. Weekly Paperwork Library

- [x] Publish the approved empty weekly catalog; no weekly forms were supplied or invented.
- [x] Render the exact empty state: `No weekly forms have been published.`
- [x] Keep Weekly free of digital completion records until an approved form is published.
- [x] Add browser coverage proving the empty library has no fake form cards.

Search, preview, download, multi-select, and packet actions are intentionally unavailable while the approved catalog is empty.

## 5. Monthly Paperwork Library

### Windows, Bars & Doors Check Log

- [x] Build the monthly preview template.
- [x] Include rows for days 1 through 31.
- [x] Include exterior windows, housing windows, housing doors, cell bars, officer signature, and comments.
- [x] Preserve the rubber-mallet instruction.
- [x] Add month prefill.
- [x] Add print and packet support.

### Use of Chemical Agents Log

- [x] Build the monthly preview template.
- [x] Include month and shift supervisor.
- [x] Include date, staff, inmate name/number, policy conformity, medical attention, and supervisor.
- [x] Include COS and Warden review fields.
- [x] Add print and packet support.

### Contraband Search Logs

- [x] Build the standard-area-rotation template.
- [x] Build the expanded-area-rotation template.
- [x] Preserve each approved area schedule.
- [x] Give the two versions clear, distinct names.
- [x] Include month, shift, date/time, area searched, contraband, officers, disposition, and comments.
- [x] Add print and packet support.

### Monthly Packet

- [x] Add multi-form selection and keyboard reordering.
- [x] Add monthly packet preview.
- [x] Add monthly packet print.
- [x] Verify month and shift prefilling.
- [x] Confirm monthly completed entries are not digitally persisted in the first release.
- [x] Add browser and print-regression tests.

## 6. Site-Wide Visual Polish

Detailed implementation and acceptance checklist: [Guided Operations Site-Wide Visual Polish Checklist](design/guided-operations/site-wide-visual-polish-checklist.md).

- [ ] Review every officer page against the approved visual system.
- [ ] Review every administrator page against the same visual system.
- [ ] Standardize sidebar spacing, icons, selection states, and section headings.
- [ ] Standardize navy, blue, gold, warning, success, and error treatments.
- [ ] Standardize card radius, borders, shadows, and internal padding.
- [ ] Standardize primary, secondary, destructive, and text-button hierarchy.
- [ ] Standardize page headings and typography.
- [ ] Standardize tables, filters, tabs, drawers, and form fields.
- [ ] Standardize loading, empty, reconnecting, unsaved, and error states.
- [ ] Confirm the scenic facility artwork loads correctly in production.
- [ ] Use decorative imagery only where it improves hierarchy.
- [ ] Keep labels and functional interface elements code-native.
- [ ] Check 1366×768 desktop behavior.
- [ ] Check Windows scaling at 100%, 125%, and 150%.
- [ ] Check tablet layouts.
- [ ] Check mobile layouts.
- [ ] Verify minimum touch-target sizes.
- [ ] Verify keyboard focus styling.
- [ ] Verify reduced-motion behavior.
- [ ] Verify WCAG 2.2 AA contrast and interaction requirements.

## 7. Print and Visual Regression

- [x] Create stable fictional test data for screenshots and print output.
- [ ] Add desktop screenshots for all primary officer screens.
- [ ] Add mobile screenshots for all primary officer screens.
- [ ] Add desktop screenshots for all administrator screens.
- [ ] Add mobile screenshots for administrator navigation.
- [ ] Add print reference for NCU Days Count.
- [x] Add print reference for Shift Assignment Roster.
- [x] Add print reference for Uniform Inspection.
- [x] Add print reference for Metal Detector Testing.
- [x] Add print reference for Perimeter Checklist.
- [x] Add print reference for Daily Random Searches.
- [x] Add print reference for Detector Sign-Out.
- [ ] Add print reference for Windows, Bars & Doors.
- [ ] Add print reference for Use of Chemical Agents.
- [ ] Add print references for both Contraband Search forms.
- [ ] Add print references for incident-specific digital forms.
- [x] Confirm page size, orientation, margins, and pagination.
- [x] Confirm application navigation is hidden while printing.
- [x] Confirm blank fields print correctly.
- [ ] Confirm grayscale readability.
- [ ] Confirm browser print preview closely matches generated downloads.

## 8. Testing and Release Gate

- [x] Run all frontend component tests.
- [x] Run frontend type-checking.
- [x] Run the production frontend build.
- [x] Resolve React `act(...)` warnings in affected tests.
- [x] Run backend unit tests.
- [x] Run contract tests explicitly.
- [x] Run security tests explicitly.
- [ ] Run PostgreSQL 17 integration tests.
- [ ] Run migration upgrade, downgrade, and upgrade verification.
- [x] Run all officer Playwright workflows.
- [x] Run all administrator Playwright workflows.
- [x] Run desktop and mobile E2E paths.
- [x] Run reduced-motion E2E verification.
- [x] Review failed-test screenshots, videos, and traces.
- [x] Confirm no real staff or historical operational information appears in fixtures.
- [x] Confirm no secrets, PINs, session tokens, narratives, or unsafe infrastructure details are exposed.
- [ ] Require all release-gate checks to pass before merging each milestone.

## 9. Deployment and Pilot

- [ ] Prepare the Cloud Run production build and static-asset serving path.
- [ ] Verify PostgreSQL 17 in the target environment.
- [ ] Apply database migrations in a controlled environment.
- [ ] Configure production browser-session secrets.
- [ ] Configure Vertex Application Default Credentials for AI features.
- [ ] Configure secure non-empty access settings where legacy routes remain enabled.
- [ ] Verify administrator bootstrap and staff provisioning.
- [ ] Verify account login, PIN change, logout, and session revocation.
- [ ] Verify Policy Expert and incident AI workflows with real cloud services.
- [ ] Verify print and download behavior in supported browsers.
- [ ] Run the new React website beside the existing browser interface.
- [ ] Keep the Microsoft Access client available during the pilot.
- [ ] Select a limited fictional or approved pilot group.
- [ ] Gather officer and administrator usability feedback.
- [ ] Fix pilot-blocking problems.
- [ ] Document support and rollback procedures.
- [ ] Confirm training materials are ready.
- [ ] Obtain explicit owner approval for production rollout.

## 10. Legacy Website Retirement

- [ ] Confirm feature parity with required legacy browser functions.
- [ ] Confirm individual employee accounts replace generic user access.
- [ ] Confirm administrator features replace the generic Admin interface.
- [ ] Confirm all required reports, forms, account tools, and policy tools work in React.
- [ ] Confirm rollback readiness.
- [ ] Stop directing normal users to the legacy shared-code pages.
- [ ] Preserve temporary fallback access during the approved transition period.
- [ ] Remove or disable obsolete generic browser routes.
- [ ] Remove obsolete navigation and documentation.
- [ ] Verify the Access API remains unchanged.
- [ ] Complete a final security review.
- [ ] Complete a final production acceptance test.
- [ ] Mark the Guided Operations website update complete.

## Immediate Next Actions

- [x] Fix PR #104 Admin Incident Workspace loading.
- [x] Fix the PR #104 Audit Log narrative-text failure.
- [x] Make all PR #104 component and browser tests green.
- [x] Merge PR #104.
- [x] Review and merge PR #105.
- [x] Complete the Daily Paperwork Center milestone.
