# Report Workstation — Refined UI Spec

## Three-Column Layout (keep)

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠️ AI-Generated — Verify against ADC Policy before filing   │
├──────────────┬───────────────────────────┬───────────────────┤
│  INPUT (35%) │  LIVE PREVIEW (50%)       │  CONTROLS (15%)   │
│              │                           │                   │
│ [Paste notes]│  ┌─────────────────────┐  │ Classified as:    │
│              │  │ ARKANSAS DEPARTMENT │  │ USE OF FORCE      │
│ [Generate]──→│  │ OF CORRECTION       │  │                   │
│              │  │ 005/409 FORM        │  │ Forms required:   │
│ Generated:   │  │                     │  │ • 005/409         │
│ ┌──────────┐ │  │ Unit: [filled]      │  │ • Photo/Video     │
│ │Supervisor│ │  │ Officer: [filled]   │  │                   │
│ │Summary   │ │  │ Date: [filled]      │  │ Reports:          │
│ │  [📋]    │ │  │                     │  │ • Supervisor Sum  │
│ ├──────────┤ │  │ NARRATIVE:          │  │ • 1st Person      │
│ │1st Person│ │  │ [1st person report] │  │ • Disciplinary    │
│ │Report    │ │  │                     │  │                   │
│ │  [📋]    │ │  │ RECOMMENDATION:     │  │ [Print All]       │
│ ├──────────┤ │  │ [filled]            │  │ [Download DOC]    │
│ │Disc. Supp│ │  │                     │  │                   │
│ │(if appl) │ │  │ SIGNATURE: ____     │  │                   │
│ │  [📋]    │ │  └─────────────────────┘  │                   │
│ └──────────┘ │                           │                   │
└──────────────┴───────────────────────────┴───────────────────┘
```

## Changes from Original Mock

### 1. Report Boxes → Match Our Pipeline

| Mock (Old) | Our Pipeline (New) |
|---|---|
| "Brief Summary" | **Supervisor Summary** (3rd person, past tense) |
| "Incident Narrative" | **First Person Report** (1st person, "I, Officer...") |
| "Disciplinary Report" | **Disciplinary Supplement** (only if charges exist, includes charge codes) |

### 2. Preview → Show Real 005/409 Layout

The center preview should replicate the actual 005/409 form fields:
- UNIT/DIVISION
- REPORTING EMPLOYEE (Last, First, Middle)
- RANK + SHIFT ASSIGNMENT
- DATE + TIME + LOCATION
- INMATE(S) INVOLVED (Name + ADC#)
- NARRATIVE (the 1st person report)
- RECOMMENDATION
- SIGNATURE DATE

### 3. Controls Column → Classifier Feedback First

Before showing report boxes, show the classifier output:
- **Incident Type** badge (colored)
- **Forms Required** list
- **Charges Identified** (if any)

Then the template selector (for printing different form layouts):
- 005/409 Incident Report
- Major Disciplinary Form (if applicable)
- Chain of Custody (if evidence)
- PREA Supplement (if PREA)

### 4. States

| State | What shows |
|---|---|
| **Empty** | Textarea with placeholder example |
| **Loading** | Spinner replacing Generate button, skeleton cards |
| **Error** | Red banner: "Classification failed — check notes and retry" |
| **Success** | Classifier badge + report boxes + filled preview |
| **No charges** | Disciplinary box hidden or marked "Not applicable" |

### 5. API Integration

Replace mock `handleGenerate` with real call:
```
POST /api/reports  { notes: "..." }
→ {
    incident_type: "use_of_force",
    forms_required: ["005_409", "photo_video"],
    charges: ["10-1"],
    reports: {
      supervisor_summary: "...",
      first_person: "...",
      disciplinary: "..."
    }
  }
```

### 6. Preview Form Selection

The right column form selector should switch the center preview between different form layouts:
- **005/409** (default) — shows the filled incident report
- **Disciplinary** — shows the Major Disciplinary Form layout
- **Chain of Custody** — shows evidence tracking layout
- **PREA** — shows PREA supplement layout

Each form layout is a different HTML template that fills fields from the same report data.

## Implementation Notes

- Use the same dark theme palette as our homepage (`--bg:#0f0f1a`, `--card:#1a1a2e`, `--accent:#4a6cf7`)
- The copy button should copy report text only, not the form layout
- Print button should print the selected form layout (CSS `@media print`)
- Keep it vanilla HTML/CSS/JS — no React needed (consistent with our Flask stack)
- The preview paper size should match real 8.5×11 proportions
