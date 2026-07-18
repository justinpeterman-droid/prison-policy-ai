"""Extraction pass — the ONLY place Gemini reads the raw notes.

Output is grammar-constrained by response_schema (schema.py), so it always
parses. The model's job is extraction only: it fills slots from the notes and
returns null for anything not stated. It never writes report prose here.
"""
import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.schema import build_response_schema, load_checklist

logger = logging.getLogger(__name__)
vertexai.init(project=PROJECT_ID, location=LOCATION)

EXTRACTION_SYSTEM = """You extract facts from a corrections officer's field notes.
Rules:
- Output values ONLY for facts the notes state. Anything not stated = null.
- NEVER guess, infer, or invent names, ADC numbers, dates, times, or events.
- Copy names/ADC#s exactly as written, even if misspelled (they are corrected later).
- persons[].actions: list what the notes attribute to THAT person only.
- narrative_facts: the events in chronological order, one plain factual
  sentence each, faithful to the notes. No embellishment, no conclusions.
- quotes: any verbatim inmate statements, exactly as written, uncensored."""


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
