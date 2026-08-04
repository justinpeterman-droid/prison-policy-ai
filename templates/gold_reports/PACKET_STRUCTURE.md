# How a complete incident packet is assembled

Reconstructed from real filed packets (`20XX-02-041`, 18 pages; a 2023 use-of-force
packet, 49 pages). Recorded here because the app currently generates **loose
reports**, while what actually gets filed is an **assembled packet**. If packet
assembly is ever added to the project, this is the specification.

Nothing here is implemented yet. This is reference material.

---

## Assembly order

```
1.  Incident Checklist          ← unit-level cover sheet, category boxes ticked
2.  Cover Letter                ← one, third person, from the supervisor
3.  005/409 Form  (officer A)   ← one PER INVOLVED OFFICER
      └ 005 Continuation        ← only if the narrative overruns the box
4.  005/409 Form  (officer B)
5.  005/409 Form  (supervisor)
6.  Major Disciplinary Form     ← when charges are brought
7.  Witness Statements          ← inmate and/or staff
8.  Category-specific forms     ← per the checklist (see table below)
9.  Medical Report / refusal
10. Inmate Drug Test Form / refusal
11. Photographs / video footage log
```

## 1 · Incident Checklist

Page 1 of every packet. Titled **"North Central Unit Incident Checklist"**, with
`Date` and `Incident Number` at the top and a checkbox grid of seven categories.
This is the paper source for `templates/incident_checklist_v2.json`.

Signature lines: **Shift Lieutenant**, **Shift Captain**, **Chief of Security**.

### Forms required, by category (verbatim from the sheet)

| Category | Forms |
|---|---|
| **Introduction of Contraband** | Cover Letter · 005/409 · Major Disciplinary · Photograph/Video Footage · Chain of Custody · Confiscation Form F401 · Field Test Result Form · Medical Report [Refuse] · Inmate Drug Test [Refuse] · Money-Receipt from Business Office |
| **Inmate on Inmate Fight/Assault** | Cover Letter · 005/409 · Major Disciplinary · Photograph/Video Footage · Weapon-Chain of Custody/F401 · Witness Statements · Enemy Alert Form · Medical Report [Refuse] · Inmate Drug Test [Refuse] · Emergency Gate Pass if Treated Outside Unit |
| **Staff Assault/Battery** | Cover Letter · 005/409 · Major Disciplinary · Photograph/Video Footage · Injured Staff-Company Nurse (877) 854-6877 · Confirmation Number · Officer Accident Report · Weapon-Chain of Custody/F401 · Medical Report [Refuse] · Inmate Drug Test [Refuse] |
| **Forced Cell Movement** | Cover Letter · 005/409 · Major Disciplinary · Forced Cell Movement Information/Fact Sheet · Photograph/Video Footage · Chain of Custody · Medical Report [Refuse] · Inmate Drug Test [Refuse] · Emergency Gate Pass if Treated Outside Unit |
| **PREA/Sexual Misconduct** | Cover Letter · 005/409 · Major Disciplinary · PREA Checklist · Chain of Custody · Confiscation Form · Copy of Barracks Log · Copy of PREA Unannounced Log · Copy of Package to Internal Affairs Div. · Photograph/Video Footage · Medical Report [Refuse] · Inmate Drug Test [Refuse] |
| **Other Rule Violation** | Cover Letter · 005/409 · Major Disciplinary · Photograph/Video Footage · Chain of Custody · Confiscation Form F401 · Medical Report [Refuse] · Inmate Drug Test [Refuse] |
| **Incident w/o Disciplinary** | Cover Letter · 005/409 · Photograph/Video Footage · Witness Statements · Accident Report Form · Medical Report [Refuse] · Inmate Drug Test [Refuse] |

> ⚠️ **To verify:** this list should be diffed against `incident_checklist_v2.json`.
> The sheet is from **North Central Unit**; the app targets **BMU / Grimes**, so
> the form lists may legitimately differ by unit.

## 2 · Cover Letter

On unit letterhead (ADC seal, unit name, address, phone/fax, Warden's name).

```
To:   {recipient — e.g. "J. Sample CSO", or several: Warden, Dep. Warden, Major, Cpt.}
From: {Rank}. {First} {Last}, {Shift}-Shift
RE:   {incident number, e.g. 20XX-02-041}      ← sometimes "Use of Force Incident #20XX-07-126"
Date: {Month D, YYYY}

{third-person narrative of the incident}

{Rank}. {First} {Last}        ← author's name repeated on its own line
```

Written in **third person** about the involved officers, even though the author
is usually one of them. Signed by hand across the header block.

## 3 · 005/409 Form — one per involved officer

Header: `ADMINISTRATIVE REGULATIONS / STATE OF ARKANSAS / DEPARTMENT OF CORRECTION`,
`SUBJECT: Reporting of Incidents — 005; Use of Force — 409`, with checkboxes for
**Incident Report** vs **Use of Force**, and the unit name.

Fields, in order:

| Field | Convention |
|---|---|
| REPORTING EMPLOYEE | Last / First / Middle |
| RANK | spelled out (`Corporal`, `Sergeant`) |
| SHIFT ASSIGNMENT | single letter (`D`) |
| DATE / TIME / LOCATION | `02/15/22` · `APX. 9:50 PM` · `Zone 2- 7 Barracks` |
| INMATE(S) INVOLVED | `Last, First ADC# {number}` |
| EMPLOYEE(S) INVOLVED | the **other** officers — `Cpl. A. Doe, Sgt. B. Roe, ...` |
| INMATE(S) PRESENT | `Same as above` |
| EMPLOYEE(S) PRESENT | `Same as above` |
| OTHERS PRESENT/INVOLVED | `N/A` |
| EXTENT OF INJURY TO INMATE(S) | `MSF 205` |
| TREATMENT AFFORDED INMATE(S) | `MSF 205` |
| EXTENT OF INJURY TO OFFICER(S) | `N/A` |
| TREATMENT AFFORDED OFFICER(S) | `N/A` |
| STATEMENT OF FACTS | first-person narrative, ruled lines |

Then: `Signature of Reporting Employee` + Date · `Signature of Supervisor` + Date ·
`Reviewed by Warden/Center Supervisor` · `RECOMMENDATION:` ×2 (Assistant Director,
Director).

Footer: `ADCF-26`. Distribution: *Original to Assistant Director, then to Director,
then to inmate Institutional File.*

**Key confirmation:** each involved officer files their own 005, listing themselves
as REPORTING EMPLOYEE and the others as EMPLOYEE(S) INVOLVED. Times differ per
officer where they arrived at different points. This validates `bind_reporter()`.

## 4 · 005 Continuation page

Used when the narrative overruns the box. Different layout:

```
REPORT OF INCIDENTS- 005 USE OF FORCE –409 (CONTINUED)
DATE | TIME | LOCATION OF INCIDENT
OFFICER(S) INVOLVED (NAMES)
INMATE(S) INVOLVED (NAME & ADC #'S)
********** STATEMENT OF OFFICER **********
{narrative continues}
{signatures}
```

The charging closer typically lands here, at the very end of the narrative.

## 5 · Incident numbering

`YYYY-MM-###` — e.g. `20XX-02-041`, `20XX-07-126`. Handwritten across the top of
each page of the packet so loose pages can be re-associated.

This matches `_build_incident_number()` in `backend/webapp/routes/reports.py`.

---

## Gap analysis — what the app would need for full packet generation

| Packet element | App today |
|---|---|
| Incident Checklist cover sheet | ❌ not generated (data exists in `incident_checklist_v2.json`) |
| Cover Letter | ✅ generated |
| 005 per officer | ✅ generated + filled |
| 005 Continuation | ❌ no support — long narratives have nowhere to go |
| Major Disciplinary Form | ⚠️ narrative generated, form not filled |
| Witness Statements | ❌ not generated |
| Enemy Alert / Separation Form | ❌ not generated (seen in packets) |
| Confiscation F401 / Chain of Custody | ❌ not generated |
| Medical / Drug Test forms | ❌ not generated (disposition captured in slots) |
