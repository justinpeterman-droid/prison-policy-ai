# Sanitized Operational Paperwork Structures

**Date:** 2026-08-18  
**Status:** Authoritative implementation reference  
**Related design:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Purpose

This document records the approved, non-sensitive structure of the supplied daily, count-sheet, and monthly workbooks. It allows the browser application and print templates to reproduce the operational forms without committing the uploaded workbooks or any real staff names, employee numbers, equipment identifiers, telephone numbers, handwritten entries, historical dates, or operational narratives.

The labels and ordering below are the source of truth for the first web release. A later form revision must be reviewed as a versioned template change rather than silently changing these structures.

## Data-safety rules

- Use fictional identities in tests, screenshots, demos, and documentation.
- Resolve current employees by stable staff UUID at runtime.
- Store a bounded display-name snapshot only where a saved print record must retain what appeared at that time.
- Do not copy equipment numbers from the source workbook. Current equipment identifiers are optional record fields with blank defaults.
- Do not copy historical dates, shift minutes, leave entries, signatures, or completed inspection results.
- Do not commit the source `.xls` or `.xlsx` files.

---

# 1. Shift Assignment Roster

## 1.1 Document header and operational fields

The print document includes:

- North Central Unit
- Shift Assignment Roster
- Shift
- Date
- Captain
- Shift Personnel
- Housing Zones
- Initial Officer
- Rotation Officer
- Leave Time (Type of Leave)
- Extra Assignments
- Alternate Shift Supervisor
- Shift Briefing Minutes
- Roll Call
- Uniform Inspection
- Assigned to post and dismissed
- Security Equipment Accounted For
  - Digital Camera
  - Video Camera (Go PRO)
  - 9 Metal Detector Wands
- Guests at Shift Briefing
- Captain
- Lieutenant
- Duty Warden
- Lieutenant Signature
- Date
- Priority-one staffing warning
- `CGPS = Cross Gender Pat Searches`
- `NOA = No Officer Available`
- Distribution footer:
  - Assistant Warden
  - Major
  - Building Captain
  - Control Center
  - Human Resources
  - Training Officer
  - Shift Supervisor
  - File

The priority-one warning states that P1 posts must be staffed in accordance with unit policy or post orders unless otherwise directed by the Warden or Duty Warden, and deviations require notification of the Duty Warden.

## 1.2 Zone and post order

### Zone 1 — Bks 8-14 Hallway and Service Area

Supervisor label: **South Hall Sergeant**

1. Bks 8 Control Booth — P1
2. Bks 9-10 Control Booth — P1
3. Bks 9-10 Desk — P2
4. Bks 11-12 Control Booth — P1
5. Bks 13-14 Control Booth — P1
6. South Tower Officer — P1
7. East Tower Officer — P1
8. South Hall Rover — P2

### Zone 2 — Bks 1-7 Hallway and Service Area

Supervisor label: **North Hall Sergeant**

1. Bks 1 Control Booth — P1
2. Bks 2-3 Control Booth — P1
3. Bks 4-5 Control Booth — P1
4. Bks 4-5 Desk — P2
5. Bks 6-7 Control Booth — P1
6. North Tower Officer — P1
7. West Tower Officer — P1
8. School Security Officer — P1
9. North Hall Rover — P2

### Zone 3 — Isolation and Service Area

Supervisor label: **Isolation Sergeant**

1. Isolation Officer #1 — P1
2. Isolation Officer #2 — P1
3. Rover — P2

### Zone 4 — Front Entrance and Service Area

Supervisor label: **Front Entrance Sergeant**

1. Master Control #1 — P1
2. Master Control #2 — P2
3. Infirmary Officer — P1
4. Outside Rover — P1
5. Biometrics Officer Lobby — P2
6. Rover — P2

### Zone 5 — Sally Port and Service Area

Supervisor label: **Sergeant**

1. Boiler Room — no P1/P2 designation shown on the supplied form

## 1.3 Assignment state

Every supervisor/post cell uses an explicit state:

```text
unassigned
assigned
no_officer_available
```

`no_officer_available` prints `NOA`. It is not represented as a null assignment because null means the field has not been completed.

Initial and Rotation assignments are independent columns. Duplicate warnings are calculated separately for each column. The application never moves an employee automatically.

---

# 2. Uniform Inspection Log

## 2.1 Header

- North Central Unit
- Uniform Inspection Log
- Date
- Shift

## 2.2 Columns

1. Name
2. Shirt
3. Pants
4. Shoes
5. Cap
6. Coat
7. I.D.
8. Hair
9. Nails
10. Comments

## 2.3 Allowed values

```text
S     Satisfactory
N/I   Needs Improvement
U     Unsatisfactory
NONE  Item not used or not applicable during this inspection
```

An Unsatisfactory value requires a comment. The print document includes:

- Staff Conducting Inspection
- Distribution line

The default row list is derived from the selected Assignment Roster and contains each selected employee once.

---

# 3. Daily Walk-Through Metal Detector Testing

## 3.1 Header and columns

- Daily Walk-Through Metal Detector Testing
- Date
- Detector #1 through Detector #11
- Tested by
- Comments, including Corrective Action Taken
- Reviewed By
- Distribution line

## 3.2 Test-position order

1. Inner left leg, pointing down
2. Centered on front of body, pointing down
3. Left side of body, pointing down
4. Center of back, pointing down
5. Center of back, pointing left
6. Under left arm, pointing down
7. Centered on top of head, pointing forward

## 3.3 Allowed results

```text
P  Pass
F  Fail
blank  Not yet tested
```

Any Fail requires a corrective-action comment before save. Each detector has optional runtime fields:

- location
- equipment identifier

Both default blank. No source equipment identifier is committed.

---

# 4. Perimeter Check List

Each check uses:

```text
S  Satisfactory
U  Unsatisfactory
blank  Not yet checked
```

## 4.1 Doors

1. Isolation NW Corridor Exit
2. Isolation SW Corridor Exit
3. Isolation To Exercise Yard
4. 1 Barracks Exit Door
5. South Hall Exit Doors
6. 2 Barracks Exit Door
7. 3 Barracks Exit Door
8. 4 Barracks Exit Door
9. 5 Barracks Exit Door
10. Inf. Meeting Room Exit Door
11. Infirmary Ward Exit Door
12. Visitation East Exit Door
13. Visitation North Exit Door
14. Gym Exit East Door
15. 6 Barracks Exit Door
16. 7 Barracks Exit Door
17. 8 Barracks Exit Door
18. North Hall Exit Doors
19. 9 Barracks Exit Door
20. 10 Barracks Exit Door
21. School Exit West Door
22. ODR Exit Door
23. Kitchen To Dock

Additional checks in this group:

24. Senstar Test
25. Pipe Chases

## 4.2 Outside Doors

1. 1 Barracks Mech Room
2. 2 & 3 Barracks Mech Room
3. 4 & 5 Barracks Mech Room
4. Administration Mech Room
5. Visitation Mech Room
6. 6 Barracks Mech Room
7. 7 & 8 Barracks Mech Room
8. 9 & 10 Barracks Mech Room
9. Maintenance Office
10. Telephone Room
11. Kitchen Dock Storage Room
12. 11 & 12 Barracks Mech Room
13. 13 & 14 Barracks Mech Room
14. 11 Barracks Exit Door
15. 12 Barracks Exit Door
16. 13 Barracks Exit Door
17. 14 Barracks Exit Door

Additional checks in this group:

18. Manholes
19. Metal Detector

## 4.3 Fence & Gates

1. West Tower Bull Pen & Inner Fence Gate
2. Sally Port To South Yard Gate
3. Isolation To Sally Port Gate
4. Isolation To South Yard Gate
5. South Yard Construction Gate
6. South Tower To South Yard Drive-Thru Gate
7. South Tower To South Yard Gate
8. South Tower Outside Maintenance Gate
9. South Tower To S.E. Yard Gate
10. South Tower To S.E. Drive-Thru Gate
11. Front Entrance To S.E. Yard Gate
12. East Tower Inner Fence
13. Front Entrance Inner Fence
14. Front Entrance To N.E. Yard Gate
15. North Tower To N.E. Yard Drive-Thru Gate
16. North Tower To N.E. Yard Gate
17. North Tower Outside Maintenance Gate
18. North Tower To North Yard Gate
19. North Tower To N.W. Drive-Thru Gate

Additional checks in this group:

20. Sally Port Inner Fence Gate
21. Fence And Alleyways

## 4.4 Sign-off fields

- Perimeter Inspected by
- Signature
- Date / Time
- Senstar Inspected by
- Shift Supervisor's Signature
- Date / Time

---

# 5. Random Searches Log

## 5.1 Sections

1. North 1
2. North 2
3. South 1
4. South 2

Each section contains four repeated officer blocks.

## 5.2 Fields per block

- Officer
- Date
- Time
- Individual Last Name
- Individual Number
- Barracks / Rack
- Contraband Found and Disposition

The browser editor stores staff by stable staff UUID and preserves the selected display name for the saved print revision.

---

# 6. Handheld Metal Detector Sign-Out

## 6.1 Unit order

```text
D1
D2
D3
D4
D5
D6
D7
D8
D9
```

## 6.2 Fields per unit

- Staff Member
- Area of Assignment
- Shift Supervisor
- Date

---

# 7. North Central Unit Count Sheet

## 7.1 Housing columns

```text
1
2
3
4
5
6
7
8
9
10
11
12
13
14
Iso
Inf
Total
```

## 7.2 Area row order

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

## 7.3 Totals and operational fields

- Out of Hsg Area by housing column
- In Hsg Area by housing column
- Unit Total by housing column
- On Site
- Gate Pass
- Transfers
- Court
- Hospital
- Furlough
- Other
- Operational Total
- Reconciliation Difference
- Count Started
- Count Ended
- Date

Court, Hospital, and Furlough retain the source reminder `See Attached Form`.

All input values are blank or non-negative whole numbers. The application calculates totals and displays the signed reconciliation difference; it never inserts a balancing value.

---

# 8. Weekly Paperwork

No approved weekly forms were supplied for release one.

The Weekly tab displays:

> No weekly forms have been published.

No example or speculative weekly form is included.

---

# 9. Monthly Paperwork

All release-one monthly documents use letter landscape print geometry.

## 9.1 Windows, Bars & Doors Check Log

Header fields:

- Month
- Shift

Rows:

- Day 1 through Day 31

Columns:

1. Date
2. Exterior Bks. Windows
3. All Inmate Housing Windows
4. Housing Doors
5. All Cell Bars
6. Officer's Signature

Footer:

- `All bars will be checked with a rubber mallet.`
- Comments

## 9.2 Use of Chemical Agents Log

Header fields:

- Month
- Shift Supervisor

Columns:

1. Date
2. Staff
3. Inmate Name / #
4. Conforms To Policy
5. Medical Attention
6. Supervisor

Review areas:

- COS Review / Date
- Warden Review / Date

## 9.3 Contraband Search Log — Standard Area Rotation

Header fields:

- Month
- Shift

Columns:

1. Date / Time
2. Area Searched
3. Contraband Found
4. Searching Officers
5. Disposition of Contraband

Footer:

- Additional Comments

Schedule cycle, in order:

1. Gym
2. School
3. Front Office / Barber Shop
4. Boiler Room
5. Kitchen and ODR
6. Laundry Press Area / Main Showers

The print definition repeats this cycle in source order to fill its approved row count.

## 9.4 Contraband Search Log — Expanded Area Rotation

Header fields and columns match the standard log.

Schedule cycle, in order:

1. Gym
2. Chapel
3. Entrance Building
4. School
5. Front Office / Barbershop
6. Boiler Room
7. Kitchen / ODR
8. Laundry
9. Inmate Barbershop
10. Inside Maintenance

The print definition repeats this cycle in source order to fill its approved row count.

## 9.5 Release-one behavior

- Month and shift may be prefilled in the browser.
- Shift Supervisor may be prefilled for the Chemical Agents log.
- Completed monthly row entries are not saved in release one.
- Users may preview one form, print one form, or select and print a packet.
- Both contraband schedules remain available.
