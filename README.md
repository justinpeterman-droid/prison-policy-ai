# Prison Policy AI

AI-powered policy assistant for Arkansas Department of Correction staff. Two tools in one app:

- **📋 Policy Knowledge Expert** — Ask any ADC policy question, get answers with citations
- **📝 Report Writing Assistant** — Paste field notes → classified, reports generated, forms filled

**Deployed:** `https://prison-policy-ai-403037827694.us-central1.run.app`

---

## Project Structure

```
prison-policy-ai/
├── backend/
│   ├── pipeline/              # RAG: extract, chunk, embed, query, import
│   ├── reports/               # v2 report engine (3-step pipeline)
│   │   ├── classifier.py      # Incident type detection (Gemini)
│   │   ├── extraction.py      # Slot extraction (Gemini, temp=0, schema-constrained)
│   │   ├── schema.py          # Slot schema, response_schema builder, reporter binding
│   │   ├── validate.py        # Gap detection, auto_content, invented_facts (NO AI)
│   │   ├── generator.py       # 4 report generators (structured facts only)
│   │   ├── prompts.py         # Classifier prompt + charge catalog loader
│   │   ├── prompts_v2.py      # v2 generation prompts (never see raw notes)
│   │   ├── filler.py          # DOCX template filling (python-docx)
│   │   └── roster.py          # Staff roster loader
│   ├── webapp/                # Flask + Gunicorn
│   │   ├── app.py             # App factory, cookie-based auth
│   │   ├── routes/chat.py     # Policy Q&A endpoint
│   │   ├── routes/reports.py  # v2 3-step: /classify, /extract, /generate, /download
│   │   ├── templates/         # home.html, chat.html, reports.html, login.html
│   │   └── static/            # CSS (Linear dark theme), fonts, seal.svg
│   ├── scripts/deploy.sh
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/forms/            # Claude's 6-form React app
├── templates/                 # DOCX templates + checklist/charges JSON + roster
├── .godplans/PLAN.mdx        # Detailed implementation plan
├── VISION.md                  # Project vision for collaborators
├── REPORT_ENGINE_SPEC.md      # v2 report engine specification
├── UI_SPEC.md                 # v2 UI specification
├── README.md
└── ideas.md                   # Raw idea dump
```

---

## Report Pipeline (v2 — Three Steps)

```
Field Notes
    │ POST /api/reports/classify
    ▼ Classifier (Gemini) → 7 BMU categories
    │ POST /api/reports/extract
    ▼ Extraction (Gemini, temp=0) → structured slots → find_gaps()
    │ officer fills Missing Information panel
    │ POST /api/reports/generate
    ▼ Generator → 4 reports from structured facts + auto_content
    │ POST /api/reports/download
    ▼ Template Filler → filled 005/409 DOCX
```

### Anti-Fabrication Guardrails

- Extraction at temp=0, schema-constrained — zero hallucination
- All slots nullable — nulls force gap questions, model cannot "fill in"
- `invented_facts()` scan — ADC#s/dates not in source → yellow highlight
- UNKNOWN values → ⚠ `[TO BE SUPPLEMENTED: ...]` markers
- Generator receives structured facts only — never raw notes
- Per-officer reports — each staff member's 005 shows only their actions

---

## Quick Start

```bash
cd backend && pip install -r requirements.txt
cd webapp && python app.py  # → http://localhost:8080
```

## Deploy

```bash
gcloud run deploy prison-policy-ai \
  --source . --region us-central1 \
  --project gen-lang-client-0968389176 \
  --allow-unauthenticated
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/reports/classifier.py` | Incident type detection (7 categories, charge validation) |
| `backend/reports/extraction.py` | Slot extraction from notes (temp=0, response_schema) |
| `backend/reports/validate.py` | Gap detection, auto_content, invented_facts (deterministic) |
| `backend/reports/generator.py` | 4 report generators (structured facts only) |
| `backend/reports/prompts_v2.py` | Generation prompts (receive facts, never raw notes) |
| `backend/reports/filler.py` | DOCX template filling (python-docx) |
| `backend/reports/schema.py` | Slot schema, reporter binding, staff extraction |
| `backend/webapp/routes/reports.py` | v2 3-step API endpoints |
| `templates/incident_checklist_v2.json` | Authoritative — 7 categories, rules, questions, auto_content |
| `templates/disciplinary_charges.json` | 61 extracted charges for classifier validation |
| `templates/005_template_v3.docx` | Exact ADC replica (navy blue, Times New Roman) |

---

*Built with Hermes Agent + Claude Code*
*GCP project: gen-lang-client-0968389176 | Region: us-central1*
