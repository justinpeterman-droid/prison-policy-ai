# Guided Operations High-Fidelity Visual Concept Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and obtain approval for the complete high-fidelity visual contract used to implement every officer, incident, administrator, paperwork, form-viewer, print, mobile, and motion surface in the Guided Operations web application.

**Architecture:** Image generation produces coordinated, readable, implementation-ready screen concepts rather than decorative mood boards. Each concept uses the same Light Precision Workspace tokens, typography, dimensional-control family, icon treatment, spacing system, document treatment, and responsive rules; a written extraction ledger converts the approved images into exact code-native constraints before production frontend work begins.

**Tech Stack:** OpenAI Image Generation, browser image inspection, responsive screen review, markdown design-token documentation, and the existing repository design/specification files.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

**Source Structure Reference:** `docs/design/guided-operations/sanitized-paperwork-structures.md`

## Global Constraints

- No production frontend code begins until the user approves the complete concept pack.
- The visual system is light-first: approximately 80% light surfaces, 15% medium navy structure, and 5% muted gold/bronze or semantic accent.
- The site must feel premium, modern, and dimensional without becoming dark, intimidating, decorative, or difficult to use.
- Officer screens are calm and guided; administrator screens may be denser but use the same system.
- Dimensional effects are strongest on primary actions, tabs, document fixtures, and selected navigation—not on every data cell or editor field.
- Officer navigation is exactly Home, New Report, Reports, Policy Expert, Forms Library, and Account.
- Required copy, report output types, incident number format, physical Chain of Custody behavior, count-sheet anatomy, daily forms, and monthly forms must match the approved specification and sanitized structure reference.
- UI controls and text remain code-native. Concept imagery must not turn entire screens or documents into raster assets.
- No real names, employee numbers, equipment identifiers, source dates, source signatures, or historical operational content appear in a concept.
- Use fictional identities such as Officer Avery Cole, Officer Morgan Lee, and Sgt. Riley Jordan.
- Concepts must show desktop and mobile behavior where the layout materially changes.
- Reduced-motion behavior is documented even though a static image cannot animate.

---

## File Map

```text
docs/design/guided-operations/
  README.md
  concept-index.md
  source-copy-inventory.md
  officer-home-desktop.png
  officer-home-mobile.png
  app-shell-desktop.png
  app-shell-mobile.png
  reports-library-desktop.png
  incident-document-studio-desktop.png
  incident-document-studio-mobile.png
  incident-required-paperwork.png
  copy-to-records-state.png
  populated-form-viewer.png
  count-sheet-desktop.png
  count-sheet-mobile.png
  count-sheet-print.png
  forms-library-desktop.png
  forms-library-mobile.png
  policy-expert-desktop.png
  account-desktop.png
  admin-overview-desktop.png
  admin-all-incidents.png
  admin-accounts-staff.png
  admin-audit-health.png
  paperwork-center-daily.png
  assignment-roster-editor.png
  uniform-inspection-editor.png
  monthly-print-center.png
  component-fixtures.png
  motion-storyboard.png
```

## Required Concept Groups

1. Officer shell and Home
2. Incident Library and Document Studio
3. NCU Days Count and Forms Library
4. Policy Expert, Account, populated-form viewer, and copy interaction
5. Administrator Operational Command Center
6. Daily/Weekly/Monthly Paperwork Center and print surfaces
7. Shared dimensional fixtures, icons, states, and motion storyboard

### Task 1: Lock the exact visible-copy inventory

**Files:**
- Create: `docs/design/guided-operations/source-copy-inventory.md`

**Interfaces:**
- Consumes: approved design spec and sanitized paperwork structures.
- Produces: the only copy Image Generation may place in concepts.

- [ ] **Step 1: Write the officer shell inventory**

Record exactly:

```markdown
## Officer navigation
- Home
- New Report
- Reports
- Policy Expert
- Forms Library
- Account

## Home primary actions
- Start New Incident
- Open Count Sheet
- Ask a Policy Question
- Open Forms Library

## Home sections
- Continue Your Work
- Recent Incidents
- Frequently Used Forms
```

- [ ] **Step 2: Write the incident inventory**

Record exactly:

```markdown
## Incident tabs
- Overview
- Officer Reports
- Copy to Records
- Required Paperwork
- Notes & Facts
- History

## Output labels
- Supervisor Summary
- Disciplinary Supplement
- Copy Supervisor Summary
- Copy Disciplinary Supplement
- PHYSICAL CARBON-COPY FORM REQUIRED
- Mark Physical Form Completed
```

Use fictional incident `2026-08-029` and fictional name `Barracks 4 Fight`.

- [ ] **Step 3: Write administrator and paperwork inventory**

Record exactly:

```markdown
## Administration
- Overview
- All Incidents
- Paperwork Center
- Accounts & Staff
- Audit Log
- System Health
- Review Lab

## Paperwork tabs
- Daily
- Weekly
- Monthly

## Daily forms
- Shift Assignment Roster
- Uniform Inspection Log
- NCU Days Count
- Walk-Through Metal Detector Testing
- Perimeter Check List
- Random Searches
- Handheld Metal Detector Sign-Out
```

- [ ] **Step 4: Add prohibited above-the-fold copy**

The inventory prohibits invented marketing claims, fake metrics, hero eyebrow labels, slogans not present in the spec, organization seals, fake version badges, technical model names, and extra officer navigation.

- [ ] **Step 5: Commit**

```bash
git add docs/design/guided-operations/source-copy-inventory.md
git commit -m "design: lock guided operations visible copy"
```

### Task 2: Generate the officer shell and Home concepts

**Files:**
- Create: `officer-home-desktop.png`
- Create: `officer-home-mobile.png`
- Create: `app-shell-desktop.png`
- Create: `app-shell-mobile.png`

**Interfaces:**
- Consumes: Task 1 copy inventory.
- Produces: app-shell and Home visual contracts.

- [ ] **Step 1: Generate the desktop Home concept**

Request a complete 1366×768 light premium internal web application with a medium-navy sidebar, exact six-item officer navigation, one dominant raised gold Start New Incident control, secondary dimensional Count Sheet/Policy/Forms actions, Continue Your Work, compact Recent Incidents, Frequently Used Forms, current user block, Online and Saved states, generous whitespace, Inter-style UI typography, restrained Instrument Serif accent only where appropriate, and no dark canvas.

- [ ] **Step 2: Generate the mobile Home concept**

Request a 390×844 continuation of the same design, with drawer navigation, Start New Incident first, Open Count Sheet prominent, no horizontal overflow, and the same exact copy.

- [ ] **Step 3: Generate neutral shell concepts**

Create desktop and mobile shell concepts showing content placeholders only for layout extraction: sidebar/rail, top bar, connection/save state, user identity, content gutter, drawer, focus state, and admin-section separation.

- [ ] **Step 4: Inspect readability and regenerate weak details**

Reject any concept with illegible text, extra nav items, black background, excessive card grids, neon glow, unrequested charts, tiny controls, generic stock imagery, or decorative police/correctional branding.

- [ ] **Step 5: Commit**

```bash
git add docs/design/guided-operations/officer-home-*.png docs/design/guided-operations/app-shell-*.png
git commit -m "design: add officer shell and home concepts"
```

### Task 3: Generate Incident Library and Document Studio concepts

**Files:**
- Create: `reports-library-desktop.png`
- Create: `incident-document-studio-desktop.png`
- Create: `incident-document-studio-mobile.png`
- Create: `incident-required-paperwork.png`
- Create: `copy-to-records-state.png`

**Interfaces:**
- Produces: incident-centered information architecture and editor contract.

- [ ] **Step 1: Generate the Reports Library**

Show one row per incident, official number before incident name, search, relationship filters `All incidents`, `I am a reporting officer`, and `I prepared for another officer`, calculated progress labels, officer names, report/form counts, and a clean table/list rather than a decorative card wall.

- [ ] **Step 2: Generate desktop Document Studio**

Show incident `2026-08-029`, six incident tabs, left workflow or section rail, large central editable report/document surface, right facts/forms/save inspector, revision state, no officer status dropdown, and premium paper/document depth.

- [ ] **Step 3: Generate mobile Document Studio**

Convert the inspector to a labelled drawer, retain report text readability, keep Save/Copy/Print actions accessible, and avoid shrinking the desktop three-column layout.

- [ ] **Step 4: Generate Required Paperwork state**

Show Required, Recommended, and Additional groups; a populated 005/409 digital document; a Chain of Custody physical-only reminder; selection reason; View/Print/Download only where allowed; and a whole-packet action.

- [ ] **Step 5: Generate Copy to Records state**

Show Supervisor Summary and Disciplinary Supplement as editable text surfaces with prominent tactile Copy controls, a Copied check state, and no Print or Download controls.

- [ ] **Step 6: Commit**

```bash
git add docs/design/guided-operations/reports-library-desktop.png docs/design/guided-operations/incident-*.png docs/design/guided-operations/copy-to-records-state.png
git commit -m "design: add incident workspace concepts"
```

### Task 4: Generate Count Sheet, Forms Library, populated-form, Policy, and Account concepts

**Files:**
- Create: `count-sheet-desktop.png`
- Create: `count-sheet-mobile.png`
- Create: `count-sheet-print.png`
- Create: `forms-library-desktop.png`
- Create: `forms-library-mobile.png`
- Create: `populated-form-viewer.png`
- Create: `policy-expert-desktop.png`
- Create: `account-desktop.png`

**Interfaces:**
- Produces: officer utility and document-viewer visual contracts.

- [ ] **Step 1: Generate Count Sheet desktop and mobile**

Desktop shows sticky Area and Total columns, housing columns 1–14/Iso/Inf, number-entry focus, totals, Count Started/Ended, operational totals, and a visible reconciliation difference. Mobile shows grouped housing entry plus totals drawer, not a compressed spreadsheet.

- [ ] **Step 2: Generate Count Sheet print concept**

Show one-page letter landscape output with complete row/column structure, title/date/times, operational section, attached-form reminders, no app chrome, and black/grayscale-safe rules.

- [ ] **Step 3: Generate Forms Library desktop and mobile**

Show categories, search, frequent forms, compact form rows/cards, purpose/when-used/revision/capabilities, multi-select print bar, and a physical-only form with guidance rather than Print.

- [ ] **Step 4: Generate populated-form viewer**

Show a realistic paper page, zoom/page controls, populated/missing/source inspector, Edit Fields, Print, and supported Download. Do not rasterize the page as the final UI solution; the concept is a layout reference.

- [ ] **Step 5: Generate Policy Expert and Account**

Policy Expert uses a calm answer/conversation area plus citation inspector. Account uses read-only profile fields, Change PIN, signed-in devices, and clear sign-out controls with no admin roster editing.

- [ ] **Step 6: Commit**

```bash
git add docs/design/guided-operations/count-sheet-*.png docs/design/guided-operations/forms-library-*.png docs/design/guided-operations/populated-form-viewer.png docs/design/guided-operations/policy-expert-desktop.png docs/design/guided-operations/account-desktop.png
git commit -m "design: add officer utility concepts"
```

### Task 5: Generate administrator command-center concepts

**Files:**
- Create: `admin-overview-desktop.png`
- Create: `admin-all-incidents.png`
- Create: `admin-accounts-staff.png`
- Create: `admin-audit-health.png`

**Interfaces:**
- Produces: denser but consistent admin visual contract.

- [ ] **Step 1: Generate Administration Overview**

Show Today’s Paperwork first, Assignment Roster and Uniform Inspection fixtures, Incidents Needing Attention, Account Conditions, System Availability, Recent Administrative Activity, and quick links. Use no vanity charts or fake production metrics.

- [ ] **Step 2: Generate All Incidents**

Show incident-centered filters/table, official number/name, officer/preparer, calculated workflow progress, separate admin records status, and a persistent attribution banner when another employee’s incident is opened.

- [ ] **Step 3: Generate Accounts & Staff**

Show a searchable staff list and split details panel with roster identity, linked account, role/status, temporary PIN/reset actions, sessions, and a clear separation between staff data and account controls.

- [ ] **Step 4: Generate Audit and Health**

Create one coordinated concept board containing Audit Log table/details and System Health safe Operational/Degraded/Unavailable states. Do not show narratives, secrets, raw logs, or infrastructure controls.

- [ ] **Step 5: Commit**

```bash
git add docs/design/guided-operations/admin-*.png
git commit -m "design: add administrator command center concepts"
```

### Task 6: Generate Paperwork Center and daily/monthly editor concepts

**Files:**
- Create: `paperwork-center-daily.png`
- Create: `assignment-roster-editor.png`
- Create: `uniform-inspection-editor.png`
- Create: `monthly-print-center.png`

**Interfaces:**
- Consumes: sanitized paperwork structure reference.
- Produces: Paperwork Center and operational-form visual contracts.

- [ ] **Step 1: Generate Paperwork Center Daily**

Show dimensional Daily/Weekly/Monthly tabs; Assignment Roster and Uniform Inspection first; Count Sheet, Metal Detector, Perimeter, Random Searches, and Detector Sign-Out; date/shift/save/warning state; and an approachable high-end command workspace.

- [ ] **Step 2: Generate Assignment Roster editor**

Show the five-zone source structure, Initial/Rotation staff columns, post priority labels, active staff picker, leave/extra assignment/briefing/equipment sections, P1 coverage warning, Save/Preview/Print, and a realistic official print preview fixture.

- [ ] **Step 3: Generate Uniform Inspection editor**

Show the exact Name/Shirt/Pants/Shoes/Cap/Coat/I.D./Hair/Nails/Comments structure, S/N-I/U/NONE controls, roster import, bulk satisfactory action, one visible exception/comment, and print preview.

- [ ] **Step 4: Generate Monthly Print Center**

Show four supplied monthly forms, month/shift prefill, multi-select packet bar, Preview/Print, and an honest Weekly empty-state inset. Do not invent weekly forms.

- [ ] **Step 5: Commit**

```bash
git add docs/design/guided-operations/paperwork-center-daily.png docs/design/guided-operations/assignment-roster-editor.png docs/design/guided-operations/uniform-inspection-editor.png docs/design/guided-operations/monthly-print-center.png
git commit -m "design: add operational paperwork concepts"
```

### Task 7: Generate shared component fixtures and motion storyboard

**Files:**
- Create: `component-fixtures.png`
- Create: `motion-storyboard.png`

**Interfaces:**
- Produces: reusable component and animation contract.

- [ ] **Step 1: Generate component fixtures**

Show primary raised gold, secondary ceramic, destructive, icon-only, selected navigation, raised tabs, input, select, checkbox, radio/button group, status fixture, save fixture, alert, modal, drawer, paper surface, compact table row, empty state, and focus/hover/pressed/disabled variants.

- [ ] **Step 2: Lock dimensional behavior**

The fixture sheet must communicate:

```text
Primary press travel: 2px
Primary minimum height: 44px
Control radius: 11px
No full-pill primary controls
Subtle top highlight
Darker lower edge
Compressed shadow on press
No neon glow
```

- [ ] **Step 3: Generate motion storyboard**

Show sequential frames for navigation indicator glide, page fade/shift, dashboard stagger, button press, save spinner→check, report-step progress, form-selection stagger, citation drawer, document-viewer expansion, Copy→Copied, and reduced-motion equivalents.

- [ ] **Step 4: Lock timing**

```text
Control interaction: 150–180ms
Navigation: 200–240ms
Panel/drawer: 250–320ms
No content-blocking transition
Reduced motion: opacity/state change only, 1–100ms
```

- [ ] **Step 5: Commit**

```bash
git add docs/design/guided-operations/component-fixtures.png docs/design/guided-operations/motion-storyboard.png
git commit -m "design: add component and motion contract"
```

### Task 8: Extract the complete design system and verify concept consistency

**Files:**
- Create: `docs/design/guided-operations/README.md`
- Create: `docs/design/guided-operations/concept-index.md`

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces: exact implementation tokens, component families, and per-screen evidence.

- [ ] **Step 1: Record exact palette and typography**

Use sampled concept values and lock at least canvas, surface, raised/inset surface, navy, slate, gold, gold highlight, text, muted text, border, focus, success, warning, and danger. Record Inter for application UI and restrained Instrument Serif usage only where approved.

- [ ] **Step 2: Record spacing, geometry, and shadows**

Document sidebar widths, content max widths, gutters, spacing scale, control heights, radii, border weights, paper shadows, raised-control shadows, modal/drawer widths, and desktop/tablet/mobile breakpoints.

- [ ] **Step 3: Record icon inventory**

For every visible icon, list meaning, outline/filled treatment, stroke width, optical size, selected state, and source family. Unshown major icons are prohibited unless a required action cannot be understood without one.

- [ ] **Step 4: Create concept index**

For each image, record native dimensions, route/state, visible copy, layout zones, permitted components, responsive continuation, motion cues, and any intentionally fictional data.

- [ ] **Step 5: Perform consistency review**

Compare all concepts for palette, typography, sidebar, primary control, tabs, tables, paper surfaces, statuses, focus treatment, icon family, and density. Regenerate any concept that looks like a different product.

- [ ] **Step 6: Run prohibited-content scan**

Confirm no real source identity/number/date, extra officer navigation, invented weekly form, dark-first screen, fake metric, unapproved status control, printable copy-only output, or printable Chain of Custody substitute appears.

- [ ] **Step 7: Commit**

```bash
git add docs/design/guided-operations/README.md docs/design/guided-operations/concept-index.md
git commit -m "design: extract guided operations design system"
```

### Task 9: Obtain explicit user approval for the complete concept pack

**Files:**
- Modify: `docs/design/guided-operations/README.md`

**Interfaces:**
- Produces: the visual approval gate consumed by every production frontend plan.

- [ ] **Step 1: Present concepts in logical groups**

Review officer shell/Home, Incident Workspace, officer utilities, admin command center, Paperwork Center, and shared fixtures/motion. Do not present only a hero or overview image.

- [ ] **Step 2: Apply requested revisions**

Regenerate affected complete screens or standalone detail concepts; do not crop and enlarge an unreadable old concept as the implementation source.

- [ ] **Step 3: Record approval**

Append:

```markdown
## Approval
- Status: Approved for faithful implementation
- Approved by: Justin
- Approval date: YYYY-MM-DD
- Approved concept files: [complete list]
- Intentional deviations: none, or explicit list
```

Use the actual approval date when the user approves; do not prefill a future date.

- [ ] **Step 4: Commit**

```bash
git add docs/design/guided-operations
git commit -m "design: approve complete guided operations concept pack"
```

## Visual Concept Completion Gate

- Every required concept file exists and is readable at native dimensions.
- The complete product—not only Home—has an approved visual source of truth.
- All screens use one coherent Light Precision Workspace system.
- Exact copy, navigation, document actions, daily/monthly structures, and output restrictions match the approved specification.
- Desktop and mobile behavior is explicit for every materially changing workspace.
- Component, icon, motion, print, accessibility, and reduced-motion contracts are documented.
- The user has explicitly approved the complete concept pack.
- Production UI implementation remains blocked until this gate passes.
