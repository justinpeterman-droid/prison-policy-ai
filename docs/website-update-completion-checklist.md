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

- [ ] Add the Administrator **Paperwork Center** route.
- [ ] Add **Daily**, **Weekly**, and **Monthly** tabs.
- [ ] Add date and shift selection.
- [ ] Add saved-record search and reopen behavior.
- [ ] Add revision-safe saving.
- [ ] Add autosave and manual-save states.
- [ ] Add print-preview support.
- [ ] Add administrator attribution and audit events.
- [ ] Add desktop, tablet, and mobile layouts.
- [ ] Add keyboard navigation and accessible labels.

### Shift Assignment Roster

- [ ] Build the Shift Assignment Roster editor.
- [ ] Load active staff from Accounts & Staff.
- [ ] Add employee search and selection.
- [ ] Add assignment sections and operational posts.
- [ ] Add leave time and leave-type fields.
- [ ] Add extra assignments.
- [ ] Add alternate shift supervisor.
- [ ] Add briefing notes and roll-call fields.
- [ ] Add captain, lieutenant, and duty-warden fields.
- [ ] Add copy-previous-roster functionality.
- [ ] Add approved assignment rotation.
- [ ] Add coverage warnings without automatically reassigning staff.
- [ ] Save by date and shift.
- [ ] Reopen an existing roster.
- [ ] Create an accurate print layout.
- [ ] Add unit, integration, browser, and print-regression tests.

### Uniform Inspection

- [ ] Build the Uniform Inspection editor.
- [ ] Load staff from the selected Assignment Roster.
- [ ] Include Shirt, Pants, Shoes, Cap, Coat, ID, Hair, Nails, and Comments.
- [ ] Support `S`, `N/I`, `U`, and `NONE`.
- [ ] Require a comment for unsatisfactory entries.
- [ ] Add bulk-mark-column-satisfactory behavior.
- [ ] Add inspector, shift, and date fields.
- [ ] Save and reopen inspections.
- [ ] Create an accurate print layout.
- [ ] Add unit, integration, browser, and print-regression tests.

### Daily Walk-Through Metal Detector Testing

- [ ] Build the detector-testing matrix.
- [ ] Include detectors 1 through 11.
- [ ] Include all seven test positions.
- [ ] Support pass/fail results.
- [ ] Require corrective-action notes for failures.
- [ ] Add tested-by, reviewed-by, date, and comments.
- [ ] Save and reopen records.
- [ ] Create an accurate print layout.
- [ ] Add unit, integration, browser, and print-regression tests.

### Daily Perimeter Checklist

- [ ] Build the perimeter checklist editor.
- [ ] Preserve the complete approved location list.
- [ ] Include Doors, Outside Doors, Fence & Gates, and supporting sections.
- [ ] Support satisfactory/unsatisfactory results.
- [ ] Add Senstar Test, Pipe Chases, Manholes, Metal Detector, Fence, and Alleyways.
- [ ] Add inspector, supervisor, signature, date, and time fields.
- [ ] Save and reopen records.
- [ ] Create an accurate print layout.
- [ ] Add unit, integration, browser, and print-regression tests.

### Daily Random Searches

- [ ] Build repeated structured search-entry rows.
- [ ] Include North 1, North 2, South 1, and South 2.
- [ ] Support four officer blocks per section.
- [ ] Include date, time, inmate name, ADC number, barracks/rack, contraband, and disposition.
- [ ] Save and reopen records.
- [ ] Reproduce the approved blocks in the print view.
- [ ] Add unit, integration, browser, and print-regression tests.

### Handheld Metal Detector Sign-Out

- [ ] Build the detector sign-out editor.
- [ ] Include units D1 through D9.
- [ ] Include staff name and area of assignment.
- [ ] Include shift supervisor and date.
- [ ] Save and reopen records.
- [ ] Create an accurate print layout.
- [ ] Add unit, integration, browser, and print-regression tests.

## 4. Weekly Paperwork Library

- [ ] Define the approved weekly form catalog.
- [ ] Add weekly-form search.
- [ ] Add individual form preview.
- [ ] Add individual print and download.
- [ ] Add multi-select.
- [ ] Add preview-selected.
- [ ] Add print-selected.
- [ ] Add download-selected.
- [ ] Clearly identify physical-only forms.
- [ ] Confirm weekly forms do not create digital completion records unless specifically required.
- [ ] Add browser and print-regression tests.

## 5. Monthly Paperwork Library

### Windows, Bars & Doors Check Log

- [ ] Build the monthly preview template.
- [ ] Include rows for days 1 through 31.
- [ ] Include exterior windows, housing windows, housing doors, cell bars, officer signature, and comments.
- [ ] Preserve the rubber-mallet instruction.
- [ ] Add month prefill.
- [ ] Add print and packet support.

### Use of Chemical Agents Log

- [ ] Build the monthly preview template.
- [ ] Include month and shift supervisor.
- [ ] Include date, staff, inmate name/number, policy conformity, medical attention, and supervisor.
- [ ] Include COS and Warden review fields.
- [ ] Add print and packet support.

### Contraband Search Logs

- [ ] Build the standard-area-rotation template.
- [ ] Build the expanded-area-rotation template.
- [ ] Preserve each approved area schedule.
- [ ] Give the two versions clear, distinct names.
- [ ] Include month, shift, date/time, area searched, contraband, officers, disposition, and comments.
- [ ] Add print and packet support.

### Monthly Packet

- [ ] Add multi-form selection.
- [ ] Add monthly packet preview.
- [ ] Add monthly packet print.
- [ ] Verify month and shift prefilling.
- [ ] Confirm monthly completed entries are not digitally persisted in the first release.
- [ ] Add browser and print-regression tests.

## 6. Site-Wide Visual Polish

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

- [ ] Create stable fictional test data for screenshots and print output.
- [ ] Add desktop screenshots for all primary officer screens.
- [ ] Add mobile screenshots for all primary officer screens.
- [ ] Add desktop screenshots for all administrator screens.
- [ ] Add mobile screenshots for administrator navigation.
- [ ] Add print reference for NCU Days Count.
- [ ] Add print reference for Shift Assignment Roster.
- [ ] Add print reference for Uniform Inspection.
- [ ] Add print reference for Metal Detector Testing.
- [ ] Add print reference for Perimeter Checklist.
- [ ] Add print reference for Daily Random Searches.
- [ ] Add print reference for Detector Sign-Out.
- [ ] Add print reference for Windows, Bars & Doors.
- [ ] Add print reference for Use of Chemical Agents.
- [ ] Add print references for both Contraband Search forms.
- [ ] Add print references for incident-specific digital forms.
- [ ] Confirm page size, orientation, margins, and pagination.
- [ ] Confirm application navigation is hidden while printing.
- [ ] Confirm blank fields print correctly.
- [ ] Confirm grayscale readability.
- [ ] Confirm browser print preview closely matches generated downloads.

## 8. Testing and Release Gate

- [ ] Run all frontend component tests.
- [ ] Run frontend type-checking.
- [ ] Run the production frontend build.
- [ ] Resolve React `act(...)` warnings in affected tests.
- [ ] Run backend unit tests.
- [ ] Run contract tests explicitly.
- [ ] Run security tests explicitly.
- [ ] Run PostgreSQL 17 integration tests.
- [ ] Run migration upgrade, downgrade, and upgrade verification.
- [ ] Run all officer Playwright workflows.
- [ ] Run all administrator Playwright workflows.
- [ ] Run desktop and mobile E2E paths.
- [ ] Run reduced-motion E2E verification.
- [ ] Review failed-test screenshots, videos, and traces.
- [ ] Confirm no real staff or historical operational information appears in fixtures.
- [ ] Confirm no secrets, PINs, session tokens, narratives, or unsafe infrastructure details are exposed.
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
- [ ] Start the Daily Paperwork Center milestone.
