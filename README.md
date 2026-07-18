# Prison Policy AI

AI-powered policy assistant for Arkansas Department of Correction staff. Two tools in one app:

- **📋 Policy Knowledge Expert** — Ask any ADC policy question, get answers with citations
- **📝 Report Writing Assistant** — Paste field notes → classified, reports generated, forms filled

**Deployed:** `https://prison-policy-ai-403037827694.us-central1.run.app`

---

## For Claude: Start Here

1. **Read `VISION.md`** — project overview, what we're building, what needs work
2. **Read `.godplans/PLAN.mdx`** — detailed plan with status per task
3. **Read `REPORT_ENGINE_SPEC.md`** — authoritative spec for the report engine v2 rebuild (single source of truth)
4. **Key files to understand:**
   - `backend/reports/classifier.py` — incident type detection (needs wiring to UI)
   - `backend/reports/generator.py` — field notes → reports (prompts need polish)
   - `backend/reports/filler.py` — DOC form filling (currently text stub, needs python-docx)
   - `backend/reports/prompts.py` — AI prompts for each report type
   - `backend/webapp/templates/home.html` — homepage (needs redesign)
   - `backend/webapp/templates/reports.html` — report page (needs professional layout)
5. **Templates to reference:**
   - `templates/incident_checklist_v2.json` — which forms per incident type
   - `templates/005.doc` — the official ADC incident report form
   - `frontend/forms/` — 6 fillable ADC forms built by Claude (React)
6. **Charges:** `templates/disciplinary_charges.json` — stub until disciplinary manual OCR completes

## Project Structure

```
backend/          ← Python: RAG pipeline, report engine, Flask webapp
frontend/forms/   ← Claude's React forms app (6 ADC forms)
templates/        ← DOC templates + parsed JSON data
.godplans/        ← Detailed implementation plan
```

## Quick Start

```bash
cd backend && pip install -r requirements.txt
cd webapp && python app.py  # → http://localhost:8080
```

## Deploy

```bash
cd backend && gcloud run deploy prison-policy-ai \
  --source . --region us-central1 \
  --project gen-lang-client-0968389176 \
  --allow-unauthenticated
```

---

*Built with Hermes Agent + Claude Code*
*GCP project: gen-lang-client-0968389176 | Region: us-central1*
