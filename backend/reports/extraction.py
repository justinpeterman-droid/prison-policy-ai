"""Extraction pass — the ONLY place Gemini reads the raw notes.

Output is grammar-constrained by response_schema (schema.py), so it always
parses. The model's job is extraction only: it fills slots from the notes and
returns null for anything not stated. It never writes report prose here.
"""
import json
import logging
import os
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.schema import build_response_schema, load_checklist

logger = logging.getLogger(__name__)

# Model may need a different location than the app default (e.g. gemini-3.5-flash
# is global-only while RAG/corpus lives in us-central1).
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", LOCATION)
vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)

EXTRACTION_SYSTEM = """You extract facts from a corrections officer's field notes.
Rules:
- Output values ONLY for facts the notes state. Anything not stated = null.
- NEVER guess, infer, or invent names, ADC numbers, dates, times, or events.
- NAMES: Always extract as Last, First. Officers often write 'First Last'
  (e.g. 'Harry Vagina'). Detect this and output last='Vagina', first='Harry'.
  Common first names (Harry, James, Michael, etc.) followed by a surname are
  a strong signal the order is flipped. If ambiguous, prefer Last, First.
- INJURIES: NEVER reproduce racial slurs or profanity. Describe injuries
  clinically: 'fat lip' → 'swollen lip', 'black eye' → 'periorbital
  contusion', 'busted lip' → 'lip laceration'. Classify into standard
  categories: 'minor facial swelling', 'periorbital contusion', 'minor
  lacerations', 'contusions', 'abrasions'. Multiple minor injuries →
  'minor injuries to the facial area'.
- persons[].actions: list what the notes attribute to THAT person only.
- narrative_facts: the events in chronological order, one plain factual
  sentence each, faithful to the notes. No embellishment, no conclusions.
- quotes: verbatim inmate statements. If they contain slurs/profanity,
  keep the quote but prefix with [QUOTE CONTAINS OFFENSIVE LANGUAGE].
- Times: format as 'H:MMam' or 'H:MMpm'. Fix obvious typos (e.g.
  '7:22AAm' → '7:22am'). If unparseable, leave as-is."""


def extract_slots(notes: str, category_name: str) -> dict:
    checklist = load_checklist()
    category = next(c for c in checklist["categories"]
                    if c["name"] == category_name)
    schema = build_response_schema(category, checklist)

    model = GenerativeModel(model_name=GENERATION_MODEL,
                            system_instruction=EXTRACTION_SYSTEM)
    response = model.generate_content(
        notes,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0,
        ),
    )
    slots = json.loads(response.text)
    logger.info("Extraction: %d persons, %d facts, nulls: %d",
                len(slots.get("persons", [])),
                len(slots.get("narrative_facts", [])),
                sum(1 for v in slots.values() if v is None))
    return slots
