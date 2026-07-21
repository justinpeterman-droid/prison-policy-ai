# Prison Policy AI — Project Vision

## What We're Building

Two AI-powered tools for Arkansas Department of Correction (ADC) staff, deployed on Google Cloud and accessible from any browser — including work computers behind firewalls.

---

## System A: Policy Knowledge Expert

**Ask any policy question → AI answers with citations from real ADC policy documents.**

- 90+ NCU and SD policies indexed in Vertex AI RAG Engine
- Gemini 3.5 Flash generates answers grounded in retrieved policy text
- Every answer cites the exact policy section(s) used
- Chat-style interface — ask naturally, get precise answers

**Status:** ✅ Deployed and working
**URL:** `https://prison-policy-ai-403037827694.us-central1.run.app`

---

## System B: Report Writing Assistant

**Paste field notes → AI classifies, extracts structured facts, identifies gaps, generates reports, and fills official DOCX templates.**

### Pipeline (v2 — Three Steps)

```
Field Notes
    │ POST /api/reports/classify
    ▼
Classifier → incident_type (7 BMU categories)
    │ officer confirms/overrides
    ▼ POST /api/reports/extract
Extraction (Gemini, temp=0, response_schema) → structured slots
    │ find_gaps() → deterministic validation, no AI
    │ Missing Information panel → officer answers gaps
    ▼ POST /api/reports/generate
Generator → 4 report types from structured facts + auto_content
    │ invented_facts() scan → fabricated ADC#s/dates flagged
    ▼ POST /api/reports/download
Template Filler → filled 005/409 DOCX
```

### 1. Classifier
Reads raw officer field notes and determines:
- **Incident category** — 7 BMU categories (contraband, inmate_fight, staff_assault, forced_cell_movement, prea, incident_no_disciplinary, other_rule_violation)
- Disciplinary charges validated against the real charge catalog
- Officer confirms or overrides with one tap; dropdown to change

### 2. Extraction + Validation
Gemini extracts structured slots at temp=0 with response_schema:
- **All slots nullable** — null = "not stated in notes"
- `find_gaps()` (deterministic Python — NO AI) finds unanswered required fields
- Gap questions rendered from `incident_checklist_v2.json` (pre-written data)
- Answer types: choice (dropdown + Other), yes_no (buttons), text (input)
- Every field has an "Unknown" button
- UNKNOWN values render as ⚠ `[TO BE SUPPLEMENTED: ...]` in output
- Yes/No never blocks — "No" just leaves the checklist box unchecked

### 3. Report Generator
Four report types from **structured facts only** (never raw notes):

| Report | Voice | Delivery Format |
|---|---|---|
| **First Person Report** | 1st person (officer's voice) | Copyable text + DOCX |
| **Supervisor Summary** | 3rd person | Copyable text |
| **Cover Letter** | Formal | Copyable text |
| **Disciplinary Supplement** | Derived from 1st person | Text with charge lines |

- `auto_content` sentences inserted by CODE: enemy alert cross-reference, footage-attached line, restraint line, escort line
- Fights always document: who applied restraints, who escorted, destination (usually RH)
- **Per-officer reports**: each security staff member gets their own 005 with correct header
- `invented_facts()` scan: any ADC#, time, or date not in the source gets yellow-highlighted
- Quotes verbatim and uncensored (evidence)
- Medical events hedged ("appeared to have a seizure")

### 4. Template Filler
- Reads `005_template_v3.docx` — exact ADC replica (navy blue, Times New Roman)
- Fills all `{{placeholders}}` from slot values
- `officer_middle` renamed to `employee_number` (005 header middle spot = employee #)
- Writer/Reviewer signatures auto-filled
- Output: completed DOCX ready to file

### Incident Categories (BMU)

| Category | Slug | Forms Required |
|---|---|---|
| Inmate on Inmate Fight/Assault | `inmate_fight` | 005/409, Cover Letter, Disciplinary |
| Staff Assault | `staff_assault` | 005/409, Cover Letter |
| Contraband | `contraband` | 005/409, Confiscation Form, Chain of Custody |
| Forced Cell Movement | `forced_cell_movement` | 005/409, Cover Letter |
| PREA | `prea` | 005/409, PREA Checklist, PREA Cover |
| General Incident (No Disciplinary) | `incident_no_disciplinary` | 005/409 |
| Other Rule Violation | `other_rule_violation` | 005/409, Cover Letter |

---

## Homepage Design

```
┌────────────────────────────────────────────┐
│           Policy AI Assistant              │
│                                            │
│  ┌──────────────┐   ┌──────────────────┐  │
│  │ 📋 Policy    │   │ 📝 Report        │  │
│  │ Knowledge    │   │ Writing          │  │
│  │ Expert       │   │ Assistant        │  │
│  │              │   │                  │  │
│  │ Search ADC   │   │ Paste notes →    │  │
│  │ policies     │   │ completed forms  │  │
│  └──────────────┘   └──────────────────┘  │
│                                            │
│  Two tools. One workflow.                  │
└────────────────────────────────────────────┘
```

Theme: Linear dark — navy hero, gold accents, cream cards. No ADC branding.

---

## Technology Stack

| Layer | Technology |
|---|---|
| AI Model | Gemini 3.5 Flash (Vertex AI) |
| RAG Engine | Vertex AI RAG (Serverless mode) |
| Embeddings | text-embedding-004 (768-dim) |
| PDF Extraction | PyMuPDF (fitz) |
| OCR | Gemini Flash vision |
| Web Framework | Flask + Gunicorn (1 worker, 8 threads) |
| Frontend | Jinja2 templates + vanilla CSS/JS |
| Forms App | React (standalone in `frontend/forms/`) |
| DOCX Filling | python-docx |
| Deployment | Cloud Run (Docker, HTTPS, auto-scaling) |
| Storage | Google Cloud Storage (policy chunks, templates) |
| Project | gen-lang-client-0968389176, us-central1 |

---

## Firewall Strategy

The app runs entirely on Google Cloud. Staff open `https://...run.app` in any browser.
Corporate firewalls pass standard HTTPS traffic. No VPN, no install, no open ports.

---

## Data Pipeline

```
PDF → PyMuPDF extract → Human review → Chunk → GCS upload →
  Vertex AI RAG import → text-embedding-004 → Gemini 3.5 Flash query
```

- **236 PDFs ingested**, 90 with extractable text (NCU + SD policies)
- **146 scanned PDFs** (Post Orders) need OCR — pending
- **1,736 chunks** indexed in RAG
- **2,772 Q&A training examples** from correctional policy writing guide

---

## Anti-Fabrication Guardrails

1. **temp=0 + response_schema** on extraction — zero hallucination
2. **All slots nullable** — nulls force gap questions, Gemini cannot "fill in"
3. **invented_facts()** — regex scan for ADC#s/dates/times not in source → yellow highlight
4. **UNKNOWN markers** — `⚠ [TO BE SUPPLEMENTED: ...]` bold in output
5. **Charge catalog validation** — charges not in `disciplinary_charges.json` are dropped
6. **Generator receives structured facts only** — never raw notes

---

## Frontend Forms (by Claude)

6 fillable/printable ADC forms built in React:

1. Shift Supervisor Paperwork Checklist
2. PREA Incident After Action Review Cover
3. Abuse of PREA Hotline Warning
4. Gate Pass Step Chart
5. Chain of Custody/Evidence Form
6. PREA Step by Step Checklist

---

## What's Next

See `.godplans/PLAN.mdx` for the full task list. Remaining priorities:

1. **OCR 146 Post Orders** — batch process with Gemini vision
2. **Report history** — SQLite DB for generated reports
3. **Cloud IAP authentication** — restrict to authorized users
4. **Cloud Monitoring** — latency, error rate, cost tracking
5. **Rate limiting** — per-IP, per-endpoint

---

## Contact

- Justin Peterman — `justinpeterman@hometownserenity.com`
- Repo: `https://github.com/justinpeterman-droid/prison-policy-ai`
- Live: `https://prison-policy-ai-403037827694.us-central1.run.app`
