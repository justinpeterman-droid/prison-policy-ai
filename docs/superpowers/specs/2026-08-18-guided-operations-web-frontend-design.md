# Guided Operations Web Frontend Design

**Date:** 2026-08-18  
**Status:** Approved design direction; written specification pending final user review  
**Product:** Standard Logistics & Unit Tools (S-L-U-T)  
**Selected experience:** Guided Operations Workspace for officers, Document Studio for incident work, and Operational Command Center for administrators  
**Target:** A modern browser companion to the Microsoft Access client, backed by the existing Cloud Run identity, reporting, policy, audit, and export services

## 1. Purpose

Replace the current shared-code, page-by-page browser experience with an individual-account web application that gives correctional staff one approachable place to:

- prepare incident reports;
- reopen incidents by official number or descriptive name;
- review and print forms already populated from confirmed report facts;
- copy non-printable report text into external records systems;
- search policies with citations;
- find and print common forms;
- complete and print the NCU Days Count;
- manage personal account sessions; and
- use role-protected administrative tools.

The web application must feel premium and carefully designed without becoming dark, intimidating, decorative, or difficult to learn. Officers should be able to identify the next action within seconds. Administrators may receive a denser command-center view, but it must remain part of the same visual and interaction system.

## 2. Source references reviewed

The design incorporates the structure and print behavior of three locally supplied workbooks:

1. A daily master workbook containing the shift assignment roster, uniform inspection log, walk-through metal detector test, perimeter checklist, random-search logs, handheld detector sign-out, and supporting roster data.
2. The NCU Days Count workbook.
3. A monthly workbook containing:
   - Windows, Bars & Doors Check Log;
   - Use of Chemical Agents Log;
   - Contraband Search Log, standard area rotation; and
   - Contraband Search Log, expanded area rotation.

These reference workbooks are design inputs only. They must not be committed to the repository, copied into the production image, or used as a source of production staff identities. Real names, employee numbers, telephone numbers, and historical operational entries found in source files must not enter fixtures, screenshots, demos, logs, or source control.

## 3. Goals

- Give every employee an individual employee-number and PIN sign-in.
- Make the officer experience simple enough for infrequent computer users.
- Preserve the anti-fabrication promise: forms are populated from reviewed structured facts, never from invented values.
- Organize report work by incident number and incident name.
- Use the official incident-number format `YYYY-MM-NNN`, for example `2026-08-029`.
- Remove manual officer status management; progress is calculated from workflow state.
- Make required forms visible, reviewable, printable, and downloadable from the incident.
- Make Supervisor Summary and Disciplinary Supplement easy to edit and copy as clean text, without presenting them as printable forms.
- Treat the Chain of Custody form as a required physical carbon-copy task, not as a digital substitute.
- Add a high-quality Forms Library.
- Add an administrator Paperwork Center with Daily, Weekly, and Monthly tabs.
- Put a prominent NCU Days Count shortcut on the officer home page.
- Preserve the existing Access client and `/api/v1` contract while the browser client is built and piloted.
- Deliver polished desktop, tablet, mobile, keyboard, print, and reduced-motion behavior.

## 4. Non-goals

- Automatically filing, submitting, approving, emailing, or finalizing an incident.
- Letting an officer invent or select arbitrary report statuses.
- Replacing the official physical Chain of Custody carbon-copy form.
- Reimplementing the report engine, policy corpus, prompts, checklist rules, or Word generation logic in JavaScript.
- Exposing Cloud SQL, Google credentials, API secrets, or renewal tokens to browser code.
- Importing historical daily or monthly workbook entries in the first release.
- Turning the officer home page into an analytics dashboard.
- Adding a dark-first or neon visual theme.
- Committing uploaded workbooks or real staff information.

## 5. Product principles

### 5.1 Guided before dense

The normal officer interface emphasizes one next action, clear labels, and progressive disclosure. Dense tables and operational metrics belong in administrator views.

### 5.2 Incident-centered organization

The incident is the digital folder. Officer narratives, copy-to-records text, forms, facts, and history remain grouped under one official incident number.

### 5.3 Visible trust

The interface shows where information came from, what remains unknown, what needs review, and why a form is required. It never hides missing information simply to make a packet look complete.

### 5.4 Nothing files itself

Generated content remains editable draft material. Printing, downloading, copying, or marking a physical task complete always requires a deliberate employee action.

### 5.5 Soft physicality

The interface may use dimensional buttons, paper depth, raised tabs, inset controls, and refined 3D fixtures. Depth must improve hierarchy and tactile confidence, not imitate an old desktop program or make controls look like toys.

## 6. Information architecture

### 6.1 Officer navigation

- Home
- New Report
- Reports
- Policy Expert
- Forms Library
- Account

### 6.2 Administrator navigation

Administrators keep all normal officer navigation and gain:

- Administration
  - Overview
  - All Incidents
  - Paperwork Center
  - Accounts & Staff
  - Audit Log
  - System Health
  - Review Lab

### 6.3 Route model

Recommended browser routes:

```text
/
├── /login
├── /home
├── /new-report
├── /reports
├── /reports/:incident-id
├── /policy-expert
├── /forms
├── /count-sheet
├── /account
└── /admin
    ├── /overview
    ├── /incidents
    ├── /paperwork
    ├── /accounts-staff
    ├── /audit
    ├── /health
    └── /review-lab
```

Authenticated application pages may show official document names and unit terminology. The public sign-in page and unauthenticated browser metadata remain generic.

## 7. Application shell

### 7.1 Desktop

A medium-navy left navigation rail anchors the product. The main workspace uses warm light-gray and white surfaces. A slim top utility bar shows:

- current page or incident;
- online/reconnecting state;
- save state;
- notifications requiring action;
- signed-in employee menu; and
- administrator context when applicable.

The sidebar bottom contains the current employee’s name, role, shift, and account menu.

### 7.2 Tablet

The sidebar collapses to a compact icon rail or drawer. The primary work area remains full height. Document inspectors become slide-over panels.

### 7.3 Mobile

Navigation becomes a drawer with a compact top bar. Core actions remain thumb-friendly. Wide workspaces use purpose-built mobile layouts rather than shrinking desktop tables.

## 8. Visual design system

### 8.1 Direction: Light Precision Workspace

The interface should feel like a high-end operational product, not a generic government portal and not a consumer entertainment app.

Recommended starting tokens:

```text
Canvas                 #F4F6F5
Surface                #FFFFFF
Raised surface         #FAFBFC
Inset surface          #E9EEF1
Primary navy           #1B2E45
Secondary slate        #58728A
Muted gold             #B58A3B
Gold highlight         #D8B66A
Primary text           #17212D
Secondary text         #627080
Border                 #D7DEE4
Success                #2E7D5B
Warning                #B7791F
Danger                 #B4433C
Focus                  #2E6FA3
```

The product should be approximately:

- 80% light surfaces;
- 15% navy structure; and
- 5% gold, bronze, or semantic accent.

No near-black full-page backgrounds are used in normal operation.

### 8.2 Typography

- Inter or a comparable highly legible sans serif for navigation, controls, tables, forms, and body copy.
- Instrument Serif may be used sparingly for large dashboard headings, sign-in presentation, or a single refined display line.
- Document previews use the typeface required by the official form, not the application display font.
- Controls receive explicit font sizing, weight, tracking, and line height; browser defaults are not acceptable.

### 8.3 Dimensional controls

Primary actions use a refined raised treatment:

- subtle top-edge highlight;
- restrained gold-to-bronze vertical gradient;
- darker lower edge;
- soft contact shadow;
- 10–12px radius, not a full pill;
- 2–3px press travel;
- compressed shadow on active press;
- quick spring return.

Secondary actions resemble raised white ceramic or light metal controls with navy text and a fine border.

Use dimensional fixtures selectively for:

- primary dashboard actions;
- print and copy controls;
- active tab rails;
- document stacks;
- form-preview frames;
- save-state fixtures;
- count-sheet keypad controls; and
- important empty states.

Tables, editors, and dense data surfaces remain mostly flat for readability.

### 8.4 Iconography and 3D assets

Use one coherent icon family for ordinary controls. A small set of custom 3D or dimensional assets may be generated for:

- incident folder;
- policy book;
- forms tray;
- count clipboard;
- print stack;
- administrator operations console; and
- empty-state illustrations.

All labels, fields, buttons, and data remain code-native. Raster artwork never replaces functional UI.

## 9. Motion system

Motion must clarify state and make controls feel well made.

### 9.1 Standard timings

- Button and control response: 120–180ms.
- Navigation and tab transitions: 180–240ms.
- Panel, drawer, and document transitions: 240–340ms.
- Staggered result entry: no more than 40–60ms between items.

### 9.2 Approved motion patterns

- Active navigation indicator glides to the new item.
- Page content fades with a small vertical shift.
- Dashboard actions enter with a restrained stagger.
- Raised buttons depress physically.
- Save spinner morphs into a checkmark.
- Workflow progress line fills as steps complete.
- Required paperwork enters after classification with a short stagger.
- Document preview rises from a paper stack and settles.
- Citation inspector slides in.
- Copy control transforms to a checkmark and `Copied`.
- Form tabs slide their underline or raised selection fixture.
- Reconnecting state pulses softly without flashing.

### 9.3 Motion restrictions

- No permanent floating or bobbing elements.
- No large parallax effects in workspaces.
- No flashing warnings.
- No animation inside report narrative text.
- No motion that delays interaction.
- Honor `prefers-reduced-motion` by eliminating travel and retaining immediate opacity/state changes.

## 10. Officer home dashboard

The home page is the product’s primary impression and must also be the fastest path into work.

### 10.1 First viewport hierarchy

1. Greeting and current save/connection state.
2. One dominant `Start New Incident` action.
3. Three high-value quick actions:
   - `Open Count Sheet`;
   - `Ask a Policy Question`; and
   - `Open Forms Library`.
4. `Continue Your Work`, showing the most recent unfinished incident.
5. Recent incidents.
6. Frequently used forms.

### 10.2 Desktop composition

```text
┌──────────────────┬────────────────────────────────────────────────────┐
│ S-L-U-T          │ Good afternoon, Officer                  ● Online │
│                  │                                           ✓ Saved │
│ Home             ├────────────────────────────────────────────────────┤
│ New Report       │                                                    │
│ Reports          │  Start a new incident                              │
│ Policy Expert    │  Large raised primary action                       │
│ Forms Library    │                                                    │
│ Account          │  [Open Count Sheet] [Ask Policy] [Forms Library]  │
│                  │                                                    │
│                  │  Continue your work                                │
│                  │  Incident 2026-08-029 • descriptive name          │
│                  │  Current workflow progress          [Continue]     │
│                  │                                                    │
│                  │  Recent incidents                                  │
│                  │  Compact, readable list                            │
│                  │                                                    │
│                  │  Frequently used paperwork                         │
└──────────────────┴────────────────────────────────────────────────────┘
```

### 10.3 What the officer dashboard excludes

- vanity metrics;
- complicated charts;
- system architecture language;
- account-management warnings not relevant to the employee;
- admin queues;
- multiple competing primary actions; and
- technical AI status details beyond useful availability.

## 11. NCU Days Count

### 11.1 Placement

`Open Count Sheet` is a first-class raised quick action on Home. The same tool is also reachable from Forms Library and, for administrators, Paperwork Center > Daily.

### 11.2 Purpose

Provide a browser-fillable and print-accurate count sheet that follows the NCU Days Count structure while improving data entry, validation, reconciliation, and accessibility.

### 11.3 Header

- Title: `NORTH CENTRAL UNIT COUNT SHEET`.
- Date.
- Count started.
- Count ended.
- `Set current time` controls beside the start and end fields.
- Save state.
- `New Count`, `Save`, `Print`, and `Clear` actions.

### 11.4 Main count grid

Columns:

```text
Area | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | Iso | Inf | Total
```

Rows, in source order:

1. A/W Office
2. Barber Shop I/M
3. Boiler Room
4. Bull Pen
5. Capt. Office
6. Chapel
7. Chow Hall
8. Commissary
9. Construction
10. Dog Kennel
11. Domestics
12. Field Utility
13. Front Office
14. Garage
15. Gate Pass
16. Gym
17. Hall Porter
18. Horsebarn
19. I.P.O.
20. Infirmary
21. Iso. Porter
22. Kitchen
23. Laundry
24. Lawn, Inside
25. Library / Law Library
26. Maint. Inside
27. Maint. Outside
28. Major's Office
29. Mental Health
30. Mt. Home Crew
31. Other
32. Reg. Maint #1
33. Reg. Maint #2
34. Sally Port
35. School
36. Trail Crew
37. Visitation
38. W.W.T.P.
39. Work Craft
40. Yard (North)
41. Yard (South)

### 11.5 Totals and reconciliation

The lower grid preserves:

- Out of Hsg Area;
- In Hsg Area;
- Unit Total per Barracks/Isolation/Infirmary;
- On Site;
- Gate Pass;
- Transfers;
- Court;
- Hospital;
- Furlough;
- Other; and
- final Unit Total.

Behavior:

- Every input accepts non-negative whole numbers only.
- Row totals update immediately.
- Column totals update immediately.
- `Unit Total` equals `Out of Hsg Area + In Hsg Area` for each housing column.
- The bottom operational total reconciles against the housing total.
- A mismatch shows an amber reconciliation message with the exact difference.
- Reconciliation never silently changes an entered number.
- Court, Furlough, and Hospital retain a visible `See Attached Form` reminder.
- Keyboard entry supports arrows, Enter, Tab, and numeric-keypad flow.
- The current row and column receive subtle focus highlighting.
- Empty cells print blank, not as zero, unless the source form requires a displayed zero.
- The print view is a one-page, letter-size landscape document matching the source hierarchy and labels.
- Print output hides app chrome and includes date/start/end values and calculated totals.

### 11.6 Responsive behavior

- Desktop: full grid with sticky Area and Total columns.
- Tablet: horizontally scrollable grid with sticky Area column and a visible total rail.
- Mobile: grouped area-entry view by Barracks/Isolation/Infirmary with a persistent totals drawer; print output remains the full official grid.

### 11.7 Persistence

A count sheet is saved as a dated record with creator, last editor, start/end time, values, and print/export events. It can be reopened from the Count Sheet tool. Officers do not manage a separate status; progress derives from whether required count fields reconcile and whether the count has ended.

## 12. New Report workflow

The new report experience follows six guided stages:

1. Officers
2. Field Notes
3. Review Facts
4. Missing Information
5. Reports
6. Forms & Export

### 12.1 Document Studio layout

Desktop uses:

- left workflow rail;
- central active workspace; and
- right inspector for incident packet, validation, provenance, save state, and contextual help.

The inspector collapses into a drawer on smaller screens.

### 12.2 Incident number

Official numbers use `YYYY-MM-NNN`, such as `2026-08-029`.

Behavior:

- Preserve leading zeros.
- Reject invalid month values.
- Reject duplicates.
- Permit an unnumbered draft until an official number is known.
- Format a digit-only entry such as `202608029` into `2026-08-029`.
- Display the number before the descriptive incident name everywhere.
- Changing the number updates all attached digital form instances.

### 12.3 Incident name

The system suggests a short name from confirmed location and incident category, for example:

- `Barracks 4 Fight`;
- `East Hall Contraband Search`; or
- `Forced Cell Movement — Cell 218`.

The officer may edit the descriptive name without changing incident classification.

### 12.4 Automatic progress

Normal officers do not receive a status dropdown. The interface calculates progress:

- Field notes started
- Needs information
- Ready to generate
- Generating reports
- Ready to review
- Ready to print
- Printed or exported

Administrative records-management controls such as close, reopen, or archive remain admin-only and visually separate from officer workflow progress.

## 13. Reports: incident library

### 13.1 Organization

The Reports page lists incidents, not detached report documents.

Primary card or row content:

- official incident number or `Unnumbered Incident`;
- descriptive name;
- date;
- incident category;
- reporting officers;
- signed-in employee relationship;
- calculated progress;
- officer-report count;
- required-paperwork count; and
- `Open Incident` or `Continue`.

### 13.2 Search

Search across authorized records by:

- official incident number;
- descriptive incident name;
- reporting officer;
- preparing officer;
- category;
- date; and
- location.

### 13.3 Relationship filters

Keep one Reports destination. Use filters:

- All incidents
- I am a reporting officer
- I prepared for another officer

The interface explains the relationship in plain language. `Prepared for Others` means the current employee created the canonical report for another reporting officer; it is not a separate copy.

### 13.4 Incident workspace tabs

- Overview
- Officer Reports
- Copy to Records
- Required Paperwork
- Notes & Facts
- History

## 14. Incident outputs

The interface distinguishes three output types.

### 14.1 Printable digital documents

Examples:

- 005/409;
- cover letter;
- incident-specific checklists; and
- approved additional digital forms.

Actions:

- View;
- edit permitted fields;
- print;
- download Word; and
- download PDF when supported.

### 14.2 Copy-to-records text

Examples:

- Supervisor Summary; and
- Disciplinary Supplement.

Actions:

- Review;
- edit;
- copy clean text.

These outputs never show Print or Download Word actions. The copy button uses the complete label, for example `Copy Supervisor Summary`. Successful copy changes the control to a checkmark and `Copied`, and copies plain text without HTML formatting.

### 14.3 Physical paperwork reminders

Example:

- Chain of Custody carbon-copy form.

The app must not generate, print, or download a replacement. The incident displays:

- `PHYSICAL CARBON-COPY FORM REQUIRED`;
- where the approved form is obtained;
- confirmed information the officer will need to handwrite;
- `View Completion Guidance`; and
- `Mark Physical Form Completed`.

The completion acknowledgment records actor and time. It is not an incident status.

## 15. Required Paperwork packet

### 15.1 Groups

- Required by checklist
- Recommended for this incident
- Additional forms

### 15.2 Required forms

Checklist rules add these automatically. They cannot be casually removed. When a form truly does not apply, the employee chooses `Mark Not Applicable` and provides a reason.

Every required item explains why it was selected, for example:

> Required because the confirmed incident category is Inmate Fight/Assault.

### 15.3 Recommended forms

Suggested from category and confirmed facts. The officer may add or remove them.

### 15.4 Additional forms

The officer opens Forms Library in a selection drawer and adds an approved form without leaving the incident.

### 15.5 Form viewer

Clicking a digital form opens a document workspace:

- paper-accurate preview;
- zoom;
- page navigation;
- form-completeness inspector;
- automatically populated fields;
- missing fields;
- provenance or source explanation;
- Edit Fields;
- Print; and
- Download.

The preview should look like a real sheet resting on the workspace through restrained paper shadow and page depth.

### 15.6 Population rule

```text
Field Notes
→ structured extraction
→ officer review and gap answers
→ confirmed facts
→ digital form instance
```

Raw notes do not directly overwrite official fields. Unknown values remain visibly incomplete or marked for supplementation. A form never receives an invented value merely to become printable.

### 15.7 Packet actions

- Preview Packet
- Print Packet
- Download Packet
- Print one item
- Download one item

Before printing, show:

- included documents;
- manual physical tasks;
- missing fields;
- warnings; and
- `Print anyway` versus `Return and complete`.

## 16. Forms Library

### 16.1 Purpose

Provide blank, fillable, and printable forms independent of a particular incident.

### 16.2 Categories

- Frequently Used
- Daily Paperwork
- Incident Reports
- PREA
- Evidence and Chain of Custody
- Supervisor Paperwork
- Movement and Gate Forms
- Weekly Paperwork
- Monthly Paperwork
- Checklists and Reference Guides

### 16.3 Form card information

- official form name;
- brief purpose;
- when it is used;
- blank, fillable, printable, or physical-only;
- revision/version date;
- preview;
- print;
- download; and
- add to current incident, when supported.

### 16.4 Multi-form actions

- select several forms;
- preview selected;
- print selected;
- download selected; and
- clear selection.

Physical carbon-copy forms remain guidance/reminder entries and cannot be digitally printed as substitutes.

## 17. Account

Available to every signed-in employee.

Contents:

- name;
- employee number;
- rank;
- shift;
- role;
- session-persistence state;
- active device/session summaries;
- Change PIN;
- Sign out of this device; and
- Sign out everywhere.

Official staff identity fields are read-only to the employee.

## 18. Administrator experience

### 18.1 Operational Command Center

Admin Overview may be denser than the officer dashboard but must retain the same shell and design language.

Primary sections:

- Today’s Paperwork;
- Incidents Needing Attention;
- Account Conditions;
- System Availability;
- Recent Administrative Activity; and
- quick links.

`Today’s Paperwork` shows the current shift’s Assignment Roster and Uniform Inspection first, with clear completion or last-saved information.

### 18.2 All Incidents

This replaces the phrase `All Reports`.

Admin capabilities:

- search every authorized incident;
- filter by incident/report identifiers, officers, dates, category, facility/location, shift, status, last editor, and modified date;
- open all attached officer reports and paperwork;
- edit with visible admin attribution;
- review and restore revisions;
- correct ownership;
- export documents; and
- apply records-management actions.

Opening another employee’s incident displays a persistent banner explaining that access and changes are attributed to the administrator.

### 18.3 Accounts & Staff

This replaces and expands the old standalone Roster page.

It combines:

- staff roster;
- account linkage;
- employee number;
- name;
- rank;
- shift;
- role;
- active/inactive roster status;
- account active/deactivated/locked state;
- temporary PIN issuance/reset;
- session revocation; and
- account unlock.

The personal Account page does not replace roster management; Accounts & Staff does.

### 18.4 Audit Log

Read-only, paginated accountability and troubleshooting view.

Example event families:

- sign-in success/failure;
- lockout;
- report/incident view;
- edit/save;
- print/export;
- copy-to-records action when policy requires;
- revision restore;
- ownership correction;
- physical-form completion acknowledgment;
- account creation;
- PIN reset;
- role change;
- session revocation;
- Review Lab handoff; and
- authorization denial.

Columns:

- time;
- actor;
- action;
- target;
- result; and
- request reference.

Details exclude full report narratives, readable PINs, session tokens, credentials, and unsafe infrastructure information.

### 18.5 System Health

Shows safe summaries:

- browser client version compatibility;
- API;
- database;
- AI classification/extraction/generation;
- Policy Expert;
- job queue;
- backups; and
- current degraded-service notices.

It is diagnostic, not an infrastructure control panel.

## 19. Administrator Paperwork Center

Top-level tabs:

- Daily
- Weekly
- Monthly

Tabs use a raised, high-quality fixture with a clear selected state and keyboard navigation.

## 20. Daily Paperwork

### 20.1 Core records

- Shift Assignment Roster
- Uniform Inspection Log
- NCU Days Count

These are browser-fillable, saved by date/shift, reopenable, and print-accurate.

### 20.2 Additional daily records from the reference workbook

- Daily Walk-Through Metal Detector Testing
- Daily Perimeter Check List
- Daily Random Searches
- Handheld Metal Detector Sign-Out

These are also browser-fillable and printable. Saving them by date/shift prevents accidental loss and allows reopening, but they remain operational paperwork rather than incident reports.

### 20.3 Shift Assignment Roster

The interactive editor modernizes data entry while preserving the printed structure.

Header and operational sections:

- unit title;
- shift;
- date;
- captain;
- leave time and type of leave;
- Shift Personnel;
- Housing Zones;
- Zones 1–5;
- Sergeant;
- Initial Officer;
- Rotation Officer;
- housing and service-area posts;
- Extra Assignments;
- Alternate Shift Supervisor;
- Shift Briefing Minutes;
- Roll Call;
- Uniform Inspection;
- Security Equipment Accounted For;
- Guests at Shift Briefing;
- Captain;
- Lieutenant;
- Duty Warden;
- lieutenant signature; and
- date.

Behavior:

- load active staff from Accounts & Staff;
- search/select staff;
- drag or keyboard-reorder assignments;
- copy the previous roster;
- rotate assignments when an approved rotation template is selected;
- show coverage warnings without auto-reassigning people;
- record leave reason;
- add briefing notes;
- save by date and shift;
- preview the official print form; and
- print one-page or approved multipage output.

Real employee data comes only from the production staff service.

### 20.4 Uniform Inspection Log

Preserve fields:

- Name
- Shirt
- Pants
- Shoes
- Cap
- Coat
- I.D.
- Hair
- Nails
- Comments
- inspecting staff
- shift
- date

Approved values:

- S — Satisfactory
- N/I — Needs Improvement
- U — Unsatisfactory
- NONE — not used today

Behavior:

- load staff from the selected Assignment Roster;
- efficient keyboard or tap entry;
- bulk-mark a column satisfactory, followed by exceptions;
- required comment for unsatisfactory values;
- inspector signature/name;
- save, preview, and print.

### 20.5 Daily Walk-Through Metal Detector Testing

Preserve:

- date;
- detectors #1–#11;
- seven test positions;
- P/F result per detector and position;
- tested by;
- comments/corrective action;
- per-detector location/identifier guidance;
- reviewed by; and
- distribution note.

The web version uses a matrix with sticky detector headers and requires a corrective-action note for a failed test.

### 20.6 Daily Perimeter Check List

Preserve grouped sections:

- Doors;
- Outside Doors;
- Fence & Gates;
- S/U result columns;
- Senstar Test;
- Pipe Chases;
- Manholes;
- Metal Detector;
- Fence and Alleyways;
- inspected by;
- signature;
- date/time; and
- supervisor signature.

The application must preserve the full source location list and print layout.

### 20.7 Daily Random Searches

Preserve:

- North 1;
- North 2;
- South 1;
- South 2;
- four officer blocks per section;
- Date;
- Time;
- I/M Last Name;
- ADC#;
- Bks#–Rack#; and
- Contraband found/Disposition.

The editor may use repeated structured rows while the print view reproduces the source blocks.

### 20.8 Handheld Metal Detector Sign-Out

Preserve:

- units D1–D9;
- Staff Name;
- Area of Assignment;
- Shift Supervisor; and
- Date.

## 21. Weekly Paperwork

Weekly remains a curated print library in release one.

Capabilities:

- preview;
- select multiple;
- print selected;
- download selected; and
- search.

No digital completion workflow or persistence is added until a specific weekly form requires it.

## 22. Monthly Paperwork

Monthly is a curated print library in release one. Month and shift may be selected and prefilled into the preview before printing, but completed monthly entries are not stored digitally in the first release.

### 22.1 Windows, Bars & Doors Check Log

One row for each day 1–31 with:

- Date;
- Exterior Bks. Windows;
- All Inmate Housing Windows;
- Housing Doors;
- All Cell Bars;
- Officer’s Signature;
- note that bars are checked with a rubber mallet; and
- Comments.

### 22.2 Use of Chemical Agents Log

Fields:

- month;
- shift supervisor;
- Date;
- Staff;
- Inmate Name / #;
- Conforms To Policy;
- Medical Attention;
- Supervisor;
- COS Review / Date; and
- Warden Review / Date.

### 22.3 Contraband Search Log — standard area rotation

Fields:

- Month;
- Shift;
- Date/Time;
- Area Searched;
- Contraband Found;
- Searching Officers;
- Disposition of Contraband; and
- Additional Comments.

Preserve the source standard area schedule.

### 22.4 Contraband Search Log — expanded area rotation

The same fields with the expanded source schedule including areas such as Chapel, Entrance Building, Laundry, Inmate Barbershop, and Inside Maintenance.

Both variants remain visible until an administrator explicitly identifies one as obsolete. They receive descriptive names rather than `Contraband Log` and `Contraband Log (2)`.

### 22.5 Monthly packet actions

- Preview a form;
- print a form;
- select several;
- preview monthly packet; and
- print monthly packet.

## 23. Print system

### 23.1 General requirements

- Dedicated print templates, not screenshots of app UI.
- Correct page size, orientation, margins, line weight, and pagination.
- Browser print preview and server-generated output should agree closely.
- Application chrome hidden.
- Fields remain legible in grayscale.
- Blank values print blank or with an approved completion marker.
- Print date and actor are not inserted into official forms unless the form requires them.

### 23.2 Visual regression

Maintain reference screenshots or rendered fixtures for:

- NCU Days Count;
- Shift Assignment Roster;
- Uniform Inspection;
- Metal Detector Testing;
- Perimeter Checklist;
- Random Searches;
- Handheld Detector Sign-Out;
- Windows/Bars/Doors;
- Chemical Agents;
- both Contraband Search logs; and
- incident digital forms.

Reference fixtures must contain fictional staff and incident information only.

## 24. Frontend architecture

### 24.1 Recommended stack

Create a new application under:

```text
frontend/web/
├── src/
│   ├── app/
│   ├── api/
│   ├── components/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── incidents/
│   │   ├── reports/
│   │   ├── paperwork/
│   │   ├── forms-library/
│   │   ├── policy/
│   │   ├── account/
│   │   └── administration/
│   ├── print/
│   ├── styles/
│   └── test/
├── package.json
├── tsconfig.json
└── vite.config.ts
```

Use:

- React;
- TypeScript;
- Vite;
- React Router;
- accessible native or headless primitives;
- one consistent SVG icon family;
- CSS variables and focused component styles;
- CSS/WAAPI or a small motion library; and
- generated visual assets only where they add real value.

Do not use a generic component theme as the final visual design. Build reusable primitives from the approved design system.

### 24.2 Deployment

Vite builds static assets into a directory served by Flask/Cloud Run. Flask remains the trusted backend. Existing Jinja pages remain available as a fallback during migration and are retired only after web parity and rollout approval.

### 24.3 Browser authentication

Do not store access or renewal tokens in `localStorage`.

Add a browser-session adapter that reuses existing identity, session, authorization, audit, and rate-limit services:

- employee number and PIN submitted over HTTPS;
- server creates/rotates the underlying authenticated session;
- browser receives an opaque HttpOnly, Secure, SameSite cookie;
- JavaScript receives only safe profile/session state;
- server enforces role and record authorization for every request;
- logout, PIN change, role change, deactivation, and revocation invalidate the session.

The Access `/api/v1` bearer contract remains unchanged.

### 24.4 API and service reuse

The web application calls focused JSON endpoints backed by the same service layer used by Access and existing APIs. Frontend code must not duplicate:

- incident authorization;
- report ownership;
- revisions;
- AI job behavior;
- checklist rules;
- form requirements;
- anti-fabrication validation;
- policy search;
- staff identity; or
- audit rules.

### 24.5 New domain resources

Implementation planning should define APIs and persistence for:

- CountSheetRecord;
- DailyAssignmentRoster;
- UniformInspectionRecord;
- DailyMetalDetectorTest;
- DailyPerimeterCheck;
- DailyRandomSearchLog;
- DailyDetectorSignOut;
- FormTemplate;
- FormInstance;
- IncidentPacketItem; and
- PhysicalPaperworkAcknowledgment.

Monthly and weekly print-only templates do not require completed-record persistence in release one.

## 25. Save, recovery, and network behavior

- Autosave incident and fillable paperwork after a short idle period.
- Show Saved, Saving, Unsaved changes, Reconnecting, and Save failed—work preserved.
- A network failure never clears visible fields.
- Disable duplicate submissions while a request is pending.
- Use idempotency keys for modifying operations.
- Preserve local in-memory edits on retry.
- Warn before leaving a page with unconfirmed unsaved changes.
- Do not persist report narratives, PINs, or sensitive data in unencrypted localStorage.
- Resume background AI jobs by server job ID.
- Print or copy failure never marks content as saved or complete.

## 26. Accessibility and usability

- Meet WCAG 2.2 AA contrast and interaction expectations.
- Full keyboard navigation.
- Logical focus order.
- Visible focus rings.
- Minimum 44px touch targets for primary controls.
- No color-only status meaning.
- Screen-reader labels for every icon-only action.
- Data tables expose proper headers.
- Count-sheet row/column context is announced.
- Print controls announce the selected document.
- Copy buttons announce success.
- Reduced-motion mode.
- Test at 1366×768 and Windows scaling from 100% through 150%.
- Support current desktop browsers and usable mobile layouts.

## 27. Error handling

Use plain, actionable language.

Examples:

- `We could not save yet. Your work is still visible. Check the connection and try again.`
- `This incident number is already in use.`
- `Two required facts are still missing before reports can be generated.`
- `The official Chain of Custody form must be completed by hand.`
- `This document is copy-only and is not intended for printing.`
- `The count does not reconcile. The totals differ by 2.`

Every server error may expose a request ID, but never raw stack traces, gateway HTML, secrets, or internal infrastructure details.

## 28. Testing strategy

### 28.1 Component and unit tests

- navigation and role visibility;
- incident-number formatting/validation;
- automatic workflow progress;
- count-sheet calculations and reconciliation;
- form requirement grouping;
- clean-text copy;
- Chain of Custody action restrictions;
- print-only weekly/monthly behavior;
- daily form validation;
- save state; and
- reduced motion.

### 28.2 API contract tests

- browser session lifecycle;
- authorization matrix;
- incident ownership/preparer relationships;
- admin access;
- idempotency;
- revision conflicts;
- form-instance population;
- physical-task acknowledgment; and
- daily paperwork access.

### 28.3 Visual and print regression

Desktop, tablet, and mobile screenshots for primary product screens, plus print snapshots for every official template.

### 28.4 End-to-end paths

1. Sign in → Home → Start New Incident → generate → review → view populated form → print.
2. Open incident → edit Supervisor Summary → copy clean text.
3. Required Chain of Custody reminder → view guidance → acknowledge physical completion.
4. Home → Open Count Sheet → enter numbers → reconcile → save → print.
5. Admin → Daily → copy prior roster → edit assignments → load uniform inspection → print both.
6. Admin → Monthly → select required monthly forms → preview packet → print.
7. Admin → All Incidents → open another officer’s incident → visible attribution → revision-safe edit.
8. Admin → Accounts & Staff → reset PIN → session revocation.
9. Admin → Audit → find the corresponding actions.

## 29. Rollout

1. Build the shared web shell and individual browser authentication.
2. Deliver officer Home, Reports incident library, and Account.
3. Deliver New Report and incident Document Studio on existing `/api/v1` services.
4. Deliver Required Paperwork, copy-only outputs, and physical reminders.
5. Deliver Forms Library and NCU Days Count.
6. Deliver Admin Overview, All Incidents, and Accounts & Staff.
7. Deliver Paperwork Center Daily.
8. Deliver Weekly and Monthly print libraries.
9. Deliver Audit, Health, and Review Lab entry.
10. Run pilot beside the existing Jinja website and Access client.
11. Retire shared-code browser routes only after verified parity, training, rollback readiness, and user approval.

## 30. Implementation decomposition

This master design is intentionally broader than one implementation plan. It defines the complete browser product contract and must be delivered through focused workstreams:

1. **Web foundation and visual system**
   - browser session adapter;
   - React/TypeScript/Vite shell;
   - responsive navigation;
   - design tokens, dimensional controls, motion, accessibility, and print foundation;
   - feature flag and legacy fallback.

2. **Incident workspace**
   - Reports incident library;
   - New Report six-step workflow;
   - Document Studio;
   - officer reports;
   - copy-to-records outputs;
   - required/recommended/additional paperwork;
   - form viewer; and
   - physical paperwork reminders.

3. **Officer utility workspace**
   - officer Home;
   - NCU Days Count;
   - Forms Library;
   - Policy Expert integration; and
   - personal Account.

4. **Administrator command center**
   - Admin Overview;
   - All Incidents;
   - Accounts & Staff;
   - Audit Log;
   - System Health; and
   - Review Lab entry.

5. **Daily Paperwork Center**
   - Assignment Roster;
   - Uniform Inspection;
   - Metal Detector Testing;
   - Perimeter Check;
   - Random Searches; and
   - Detector Sign-Out.

6. **Weekly/monthly print center and rollout**
   - weekly template library;
   - monthly supplied templates;
   - packet selection and print;
   - visual/print regression;
   - pilot; and
   - legacy retirement.

Each workstream receives a focused implementation plan and review gate. The web foundation must land first. Incident workspace and officer utilities may then proceed in parallel where backend dependencies allow.

## 31. Visual concept and design-review gate

Before production UI code is accepted, create coordinated high-fidelity concepts for:

1. Officer Home desktop and mobile;
2. NCU Days Count data-entry and print-preview states;
3. Incident Document Studio with Required Paperwork inspector;
4. Forms Library;
5. Admin Overview and Daily/Weekly/Monthly Paperwork Center; and
6. populated form viewer and copy-to-records interaction.

The concepts must use one coherent Light Precision Workspace system and must show real workflow density, not marketing-only screens. They become the visual implementation contract after user approval. Browser implementation is compared directly against the accepted concepts at desktop, tablet, and mobile sizes.

## 32. Acceptance criteria

1. The officer shell contains exactly Home, New Report, Reports, Policy Expert, Forms Library, and Account.
2. The officer home page presents Start New Incident as the dominant action and includes a prominent Open Count Sheet action.
3. The count sheet reproduces the source areas and columns, calculates totals, detects reconciliation differences, saves, reopens, and prints accurately.
4. Incidents are organized by official `YYYY-MM-NNN` number and descriptive name.
5. Officers do not manually manage record status.
6. Required digital forms open as populated, printable document previews based on confirmed facts.
7. Supervisor Summary and Disciplinary Supplement are editable, clean-text copy experiences without Print or Word-download actions.
8. Chain of Custody is represented only as a physical carbon-copy requirement and completion reminder.
9. Admin Paperwork Center contains Daily, Weekly, and Monthly tabs.
10. Daily includes the exact core roster and uniform-inspection structures plus the other supplied daily logs.
11. Monthly includes Windows/Bars/Doors, Chemical Agents, and both Contraband Search schedules as preview-and-print forms.
12. Accounts & Staff replaces the old roster-management page; personal Account remains separate.
13. Admin All Incidents and Audit Log behave as specified and are server-authorized.
14. The normal interface is light, modern, premium, approachable, and uses dimensional design selectively.
15. Motion is polished, brief, purposeful, and reduced-motion compliant.
16. No uploaded workbook, real staff identity, phone number, or historical operational entry is committed or exposed in test/demo data.
17. Existing Access and backend behavior remain available throughout pilot rollout.
