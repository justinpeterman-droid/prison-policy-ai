"""Incident classifier — determines type, forms needed, persons, charges."""
import json
import os
import re
import logging
import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.prompts import build_classifier_prompt
from backend.reports.schema import load_checklist

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "contraband", "inmate_fight", "staff_assault", "forced_cell_movement",
    "prea", "incident_no_disciplinary", "other_rule_violation",
}

def _category_label(incident_type: str) -> str:
    try:
        cl = load_checklist()
        for cat in cl.get("categories", []):
            if cat["name"] == incident_type:
                return cat["label"]
    except Exception:
        pass
    return incident_type.replace("_", " ").title()

# Model may need a different location than the app default (e.g. gemini-3.5-flash
# is global-only while RAG/corpus lives in us-central1).
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", LOCATION)
vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)


def _extract_json_from_response(text: str) -> str:
    """Extract JSON from a model response that may contain markdown fences or commentary."""
    # Strip wrapping ``` fences (multi-line and inline)
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    # Try to find JSON object between first { and last }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def classify_incident(notes: str) -> dict:
    """Classify field notes into structured incident data."""
    # Re-init in case another module changed vertexai's global location.
    vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)

    system_prompt, charge_catalog = build_classifier_prompt()

    model = GenerativeModel(
        model_name=GENERATION_MODEL,
        system_instruction=system_prompt,
    )

    prompt = (
        f"Classify this incident from the field notes:\n\n"
        f"---\n{notes}\n---\n\n"
        f"Use the charge catalog below to select applicable rule numbers.\n"
        f"Return ONLY valid JSON."
    )

    response = model.generate_content(prompt)

    # Robust JSON extraction from model response
    text = _extract_json_from_response(response.text)

    try:
        result = json.loads(text)
        # Constrain to the 7 valid categories
        if result.get("incident_type") not in VALID_CATEGORIES:
            logger.warning("Classifier returned invalid category %r — defaulting to other_rule_violation",
                           result.get("incident_type"))
            result["incident_type"] = "other_rule_violation"
        # Always add the human-readable label
        result["label"] = _category_label(result["incident_type"])
        # Validate charges against catalog
        result["charges_applicable"] = [
            c for c in result.get("charges_applicable", [])
            if c in charge_catalog
        ]
        # Fill in charge descriptions from catalog
        result["charge_descriptions"] = {
            c: charge_catalog[c]["description"]
            for c in result["charges_applicable"]
        }
        return result
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Classification JSON parse failed: %s — raw: %.300s", e, text)
        return {
            "incident_type": "other_rule_violation",
            "label": _category_label("other_rule_violation"),
            "persons_involved": [],
            "charges_applicable": [],
            "charge_descriptions": {},
            "facility": "Benny Magness Unit",
            "shift": "Unknown",
            "raw_classification": text,
        }
