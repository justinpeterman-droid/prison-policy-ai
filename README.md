# Prison Policy AI

Dual-purpose ADC corrections operations tool. Built with Python/Flask + Vertex AI RAG.

## Structure

```
├── backend/          ← Python API + pipeline
│   ├── pipeline/     ← PDF extraction, chunking, RAG indexing, querying
│   ├── reports/      ← Classifier, report generator, DOC template filler
│   ├── webapp/       ← Flask app (homepage, chat, reports API)
│   └── scripts/      ← Deploy and utility scripts
├── frontend/         ← Client-side apps
│   └── forms/        ← Fillable/printable ADC form replicas (React)
├── templates/        ← DOC templates + structured data
│   ├── 005.doc       ← 005/409 Incident Report form
│   ├── checklist.json← Incident checklist categories
│   └── charges.json  ← Disciplinary charge codes
├── .godplans/        ← Master plan
└── data/             ← Data directories (gitignored):
    ├── pdfs/         ← Source PDFs
    ├── extracted/    ← Raw text
    ├── reviewed/     ← Approved text
    ├── chunks/       ← Chunked JSONL
    └── field-notes/  ← Training data
```

## Quick Start

```bash
pip install -r backend/requirements.txt
cp .env.example .env  # fill in GCP project details
python -m backend.webapp.app
```

## Deployment

```bash
gcloud run deploy prison-policy-ai --source backend/ --region us-central1
```

## License

Internal use — Arkansas Department of Corrections.
