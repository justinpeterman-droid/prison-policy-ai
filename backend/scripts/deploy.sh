#!/bin/bash
# Deploy backend to Cloud Run
set -e
cd "$(dirname "$0")/.."
gcloud run deploy prison-policy-ai \
  --source . \
  --region us-central1 \
  --project gen-lang-client-0968389176 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 120

gcloud run services describe prison-policy-ai \
  --region us-central1 \
  --format="value(status.url)"
