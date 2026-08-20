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

### Visual Contract and Frontend Consolidation

- [ ] Treat the richer officer Home/dashboard reference as the visual target for Home and shared application-shell polish.
- [ ] Reconcile target-specific additions with the approved design and security documentation, including the crest, hero wording, service-status wording, quote, version label, and avatar behavior.
- [ ] Update the visible-copy inventory and visual specification before implementation so future work does not revert the approved target.
- [ ] Keep the data-driven `OfficerHomePage` and its authorization-scoped API response as the production source of truth.
- [ ] Migrate useful layout and component ideas from the dormant `HomePage.tsx` into the active Home page without carrying over static demonstration data.
- [ ] Migrate reusable target styling from the dormant `App.css` into the active scoped shell and Home styles.
- [ ] Remove or retire the duplicate Home implementation and dead global CSS after migration.
- [ ] Preserve honest loading, empty, reconnecting, unsaved, and error states; never substitute sample incidents, forms, activity, dates, or statuses in production.

### Application Shell, Sidebar, Branding, and Utilities

- [ ] Recompose the wide desktop Home screen as a dense main dashboard plus a permanent right utility rail.
- [ ] Add a centered maximum-width dashboard container and disciplined gutters so wide screens do not end in a large unused canvas.
- [ ] Rebuild the brand header with the target curved or angled lower-right shape and gold separator rule.
- [ ] Replace the CSS placeholder shield with a detailed, privacy-safe S.L.U.T crest asset while keeping the brand name and subtitle code-native.
- [ ] Add a lower-sidebar scenic landscape asset with a dark text-safe fade and optimized production formats.
- [ ] Move detailed service health out of the sidebar and retain a compact brand tagline near the bottom.
- [ ] Display a version label only when it is populated from actual package or build metadata.
- [ ] Preserve exactly the six officer navigation destinations: Home, New Report, Reports, Policy Expert, Forms Library, and Account.
- [ ] Replace mixed thin-outline and text-glyph navigation symbols with one coherent filled or duotone SVG icon family.
- [ ] Standardize navigation spacing, optical icon size, selected state, hover state, pressed state, and keyboard focus state.
- [ ] Integrate the top utility controls with the hero/top edge instead of leaving a visually detached empty status bar.
- [ ] Separate the meaning of **Online** from **Last refreshed/synced** and prevent contradictory status text.
- [ ] Add an accessible notifications button with a real actionable count and a usable zero-count state.
- [ ] Convert the profile chip into a real keyboard-operable menu with Account, role/shift context, session status, and Sign Out.
- [ ] Support an optional employee avatar only when a legitimate source exists, with initials as the privacy-safe fallback.
- [ ] Keep Home-only utility-rail content off report, document, and editor routes where it would reduce working space.

### Officer Home Hero and Primary Actions

- [ ] Replace or supplement the simple horizon illustration with a high-fidelity, non-identifying sunrise, watchtower, and perimeter scene.
- [ ] Use an edge fade or text-safe composition rather than a heavy color wash that obscures the hero artwork.
- [ ] Confirm the scenic facility artwork loads from the production static-asset path and has an optimized fallback.
- [ ] Preserve the signed-in employee’s dynamic display name and never hardcode the officer shown in the reference image.
- [ ] Decide and document whether shift information remains in the hero, moves to the profile menu, or appears as smaller metadata.
- [ ] Match the approved greeting hierarchy, tighter name typography, supporting message, and Professionalism/Accountability/Integrity placement.
- [ ] Rebuild the four primary action cards to match the target density and dimensional hierarchy.
- [ ] Remove the pale `01` through `04` watermark numbers.
- [ ] Add distinct dimensional fixtures for New Incident Report, Count Sheet, Policy Question, and Forms Library.
- [ ] Keep all action labels, descriptions, buttons, and destinations code-native and accessible.
- [ ] Reconcile the shorter target action copy with the current citation, reconciliation, and approved-form trust language.
- [ ] Standardize gold primary and blue secondary action buttons with a top highlight, darker lower edge, contact shadow, SVG arrow, and 2-pixel pressed travel.
- [ ] Add hover, focus, active, loading, disabled, and reduced-motion behavior for every primary action.
- [ ] Surface Count Sheet state inside its action or checklist entry instead of relying on a separate oversized Home panel.

### Home Dashboard Panels and Right Utility Rail

- [ ] Add the **Quick Access** panel with View My Reports, Open Forms Library, Policy Expert, Open Count Sheet, and Daily Paperwork.
- [ ] Give Daily Paperwork a real destination or an honest filtered library route; do not add a dead link.
- [ ] Add the **System Status** panel using a safe summarized health contract for API Services, AI Services, Database, and Policy Search.
- [ ] Limit service states to useful summaries such as Operational, Degraded, Unavailable, and Unknown without exposing infrastructure details.
- [ ] Add the **Need Help?** panel with a working Policy Expert or approved support destination.
- [ ] Restyle **Continue Your Work** with the target icon-led header, active-incident count, inset incident card, relative update time, compact status, and gold Continue control.
- [ ] Remove the current three-stat block from Continue Your Work unless it is intentionally retained elsewhere.
- [ ] Restyle **Recent Incidents** as compact, fully clickable rows with official number first, incident name, semantic progress chip, relative time, and chevron.
- [ ] Standardize progress variants for Ready to review, Needs information, Complete, and other calculated workflow states.
- [ ] Rename or redesign **Quick Forms** as **Frequently Used Forms** only after defining whether the list is truly usage-ranked or intentionally curated.
- [ ] Show form print actions only when the form capability allows printing; retain honest guidance for physical-only forms.
- [ ] Add **Your Daily Checklist** using real date-, shift-, role-, and officer-scoped task data.
- [ ] Treat checklist circles as derived status indicators unless the employee is explicitly allowed to mark a task complete.
- [ ] Add **Quick Links** for Forms Library, Policy Expert, My Account, and a real Help & Support destination.
- [ ] Add **Recent Activity** using safe personal event summaries and authorized destinations.
- [ ] Exclude narrative excerpts, policy prompts, form values, credentials, raw audit payloads, and other employees’ unauthorized activity from Home activity data.
- [ ] Remove or relocate the current full-width NCU Days Count panel so the primary action, checklist, and Quick Access surfaces do not compete with a fourth equally prominent shortcut.
- [ ] Add the footer trust strip with approved quote copy, Security, Service, Teamwork, Excellence, and locale-aware current date/time.
- [ ] Simplify or rearrange the trust strip on narrow screens rather than compressing every item into an unreadable row.
- [ ] Add target-quality skeleton, loading, empty, reconnecting, and recoverable-error presentations for each panel.

### Shared Visual System Across All Pages

- [ ] Review every officer page against the approved visual system.
- [ ] Review every administrator page against the same visual system.
- [ ] Standardize the light canvas, white/raised surfaces, medium-navy structure, muted gold accents, and semantic colors.
- [ ] Standardize navy, blue, gold, warning, success, error, neutral, and completed-state treatments.
- [ ] Define shared elevation tokens for controls, cards, and feature fixtures.
- [ ] Standardize card radius, borders, shadows, internal padding, and section spacing.
- [ ] Use dimensional effects selectively for primary controls, selected navigation, tabs, document fixtures, and important empty states rather than every data surface.
- [ ] Standardize primary, secondary, destructive, icon-only, and text-button hierarchy.
- [ ] Standardize page headings, panel headings, body copy, metadata, labels, and control typography.
- [ ] Standardize tables, filters, tabs, drawers, menus, alerts, modals, form fields, status chips, and list rows.
- [ ] Standardize loading, empty, reconnecting, unsaved, conflict, success, warning, and error states.
- [ ] Use one coherent interface icon family and reserve custom dimensional artwork for major feature fixtures.
- [ ] Replace plain text chevrons and arrows with accessible SVG icons.
- [ ] Keep labels and functional interface elements code-native.
- [ ] Use decorative imagery only where it improves hierarchy, orientation, or confidence.
- [ ] Avoid unnecessary nested cards, decorative metrics, technical jargon, or competing primary actions on officer pages.

### Assets, Data-Backed UI, and Production Integrity

- [ ] Add and optimize the crest, hero scene, sidebar landscape, four primary-action fixtures, and any approved empty-state illustrations.
- [ ] Provide stable dimensions, high-density variants, appropriate transparent backgrounds, and WebP/AVIF or SVG delivery where suitable.
- [ ] Confirm assets blend naturally with their surrounding backgrounds and do not obscure text or controls.
- [ ] Do not use real facilities, staff portraits, employee numbers, signatures, historical operational content, license plates, or identifying signage in visual assets or fixtures.
- [ ] Extend the Home summary contract for daily checklist, recent activity, notification count, and a trustworthy generated/refreshed timestamp.
- [ ] Keep summarized service health in a separate endpoint with appropriate authorization, caching, and redaction.
- [ ] Add optional avatar metadata only after defining its legitimate source and privacy behavior.
- [ ] Preserve authorization-scoped incident and form retrieval and honest empty states.
- [ ] Preserve the anti-fabrication rule: target sample rows may appear in tests and screenshots but not as production fallbacks.
- [ ] Ensure health, activity, notifications, and profile menus never expose secrets, PINs, session tokens, narratives, raw logs, model configuration, database hosts, or unsafe infrastructure details.
- [ ] Update unit, integration, contract, and browser fixtures for the expanded Home response without introducing real staff or operational information.

### Responsive Layout, Accessibility, and Motion

- [ ] Match and review the Home target at its approximately 1536×1024 reference size.
- [ ] Check 1366×768 desktop behavior without clipped cards, hidden actions, or excessive empty space.
- [ ] Check Windows scaling at 100%, 125%, and 150%.
- [ ] At medium desktop widths, convert the four actions to a 2×2 grid and reposition the right rail without compressing labels.
- [ ] Check tablet layouts with a compact rail or drawer and purpose-built panel rearrangement.
- [ ] Check approximately 390-pixel mobile layouts with a drawer, one-column actions, no horizontal overflow, and Count Sheet still immediately reachable.
- [ ] Ensure daily tasks, activity, and support remain reachable on mobile rather than disappearing only to simplify the layout.
- [ ] Verify minimum 44-pixel touch targets and comfortable spacing around adjacent controls.
- [ ] Verify complete keyboard navigation, logical focus order, visible focus styling, and Escape behavior for menus/drawers.
- [ ] Verify screen-reader names for notification counts, print controls, status indicators, menus, and icon-only actions.
- [ ] Add restrained page, panel, navigation, and button motion that clarifies state without delaying interaction.
- [ ] Verify reduced-motion behavior removes travel and retains immediate opacity/state feedback.
- [ ] Verify WCAG 2.2 AA contrast, reflow, target-size, focus, status-message, and interaction requirements.

### Visual QA and Acceptance

- [ ] Capture the active Home implementation at the target reference size and compare it directly with the approved reference.
- [ ] Inspect copy, shell proportions, hero treatment, typography, card density, right-rail placement, icons, shadows, spacing, and footer composition side by side.
- [ ] Add populated, loading, empty, error, reconnecting, and reduced-motion screenshot states.
- [ ] Confirm visual polish does not regress Reports, Document Studio, Policy Expert, Forms Library, Count Sheet, Account, Administration, or Paperwork Center working space.
- [ ] Verify all generated and static assets load correctly in the production build.
- [ ] Run frontend type-checking, component tests, production build, and the relevant desktop/mobile Playwright paths after each visual milestone.
- [ ] Record intentional deviations from the reference with a product, accessibility, security, or data-integrity reason.
- [ ] Mark Site-Wide Visual Polish complete only after no material, fixable reference mismatch remains.

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
