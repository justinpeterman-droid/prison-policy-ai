# Prison Policy AI — Project Vision

## What We're Building

Two AI-powered tools for Arkansas Department of Correction (ADC) staff, deployed on Google Cloud and accessible from any browser — including work computers behind firewalls.

---

## System A: Policy Knowledge Expert

**Ask any policy question → AI answers with citations from real ADC policy documents.**

- 90+ NCU and SD policies indexed in Vertex AI RAG Engine
- Gemini 2.5 Flash generates answers grounded in retrieved policy text
- Every answer cites the exact policy section(s) used
- Chat-style interface — ask naturally, get precise answers

**Status:** ✅ Deployed and working  
**URL:** `https://prison-policy-ai-403037827694.us-central1.run.app`

---

## System B: Report Writing Assistant (In Development)

**Paste field notes → AI classifies the incident, generates required reports, and fills official templates.**

### Pipeline

```
Field Notes → Classifier → Report Router → Template Filler → Completed Documents
```

### 1. Classifier
Reads raw officer field notes and determines:
- **Incident category** (Use of Force, PREA, Disciplinary, Medical, General, etc.)
- **Which report forms are required** per ADC incident package requirements
- **Which disciplinary charges apply** (from AR Inmate Disciplinary Manual)

### 2. Report Generator
Produces three or more report types:

| Report | Voice | Delivery Format |
|---|---|---|
| **Supervisor Summary** | 3rd person | Copyable text |
| **First Person Report** | 1st person (officer's voice) | Copyable text |
| **005/409 Incident Form** | Narrative + metadata | Filled DOC template |
| **Disciplinary Supplement** | Derived from 1st person report | Text with charge lines |

### 3. Template Filler
- Retrieves the correct DOC/DOCX template from the template library
- Fills metadata fields: officer name, ADC#, date, time, location, inmate names
- Inserts AI-generated narrative into the correct field
- For disciplinary: strips non-court information, adds charge line from inmate manual
- Outputs completed, formatted document ready to file

### Incident Categories

| Category | Forms Required |
|---|---|
| Use of Force | 005/409, Photo/Video documentation |
| Major Disciplinary | 005/409, Major Disciplinary Form, Chain of Custody |
| Contraband | 005/409, Confiscation Form, Chain of Custody |
| PREA | 005/409, PREA Step Checklist, PREA Cover |
| Medical Emergency | 005/409 |
| Escape/Walkaway | 005/409, Photo documentation |
| General Incident | 005/409 |

---

## Homepage Design

```
┌────────────────────────────────────────────┐
│          ADC Policy Assistant              │
│                                            │
│  ┌──────────────┐   ┌──────────────────┐  │
│  │ 📋 Policy    │   │ 📝 Report        │  │
│  │ Knowledge    │   │ Writing          │  │
│  │ Expert       │   │ Assistant        │  │
│  │              │   │                  │  │
│  │ Search ADC   │   │ Paste notes →    │  │
│  │ policies     │   │ completed forms  │  │
│  └──────────────┘   └──────────────────┘  │
└────────────────────────────────────────────┘
```

- **Policy Expert**: Chat interface with policy search, citation display
- **Report Assistant**: One-page form — paste notes → one click → classified + reports generated + template filled

---

## Technology Stack

| Layer | Technology |
|---|---|
| AI Model | Gemini 2.5 Flash (Vertex AI) |
| RAG Engine | Vertex AI RAG (Serverless mode) |
| Embeddings | text-embedding-005 (768-dim) |
| PDF Extraction | PyMuPDF (fitz) |
| OCR | Gemini 2.5 Flash vision |
| Web Framework | Flask + Gunicorn |
| Frontend | HTML/CSS + Claude's React forms app |
| Deployment | Cloud Run (serverless, HTTPS, auto-scaling) |
| Storage | Google Cloud Storage (policy chunks, DOC templates) |
| Project | gen-lang-client-0968389176, us-central1 |

---

## Firewall Strategy

The app runs entirely on Google Cloud. Staff open `https://...run.app` in any browser.
Corporate firewalls pass standard HTTPS traffic. No VPN, no install, no open ports.

---

## Data Pipeline

```
PDF → PyMuPDF extract → Human review → Chunk (512 tokens, 64 overlap) → 
  GCS upload → Vertex AI RAG import → text-embedding-005 → Gemini 2.5 Flash query
```

- **236 PDFs ingested**, 90 with extractable text (NCU + SD policies)
- **146 scanned PDFs** (Post Orders) need OCR — pending
- **1,736 chunks** indexed in RAG
- **2,772 Q&A training examples** from correctional policy writing guide

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

## What Claude Should Work On

See `.godplans/PLAN.mdx` for the full 20-task plan. Priority for Claude:

1. **OCR remaining documents** — 146 Post Orders + 35-page disciplinary manual
2. **Classifier refinement** — map all incident types to required forms
3. **Template filler** — DOC field injection (currently stubbed, needs `python-docx`)
4. **Report page styling** — professional layout matching ADC forms aesthetic
5. **Error handling** — loading states, retry logic, user feedback

---

## Contact

- Justin Peterman — `justinpeterman@hometownserenity.com`
- Hermes agent sessions: search "prison policy" or "ADC"
