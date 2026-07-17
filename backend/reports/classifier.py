"""Incident classifier — determines type, forms needed, persons, charges."""
import json
import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.prompts import CLASSIFIER_PROMPT, build_classifier_prompt

vertexai.init(project=PROJECT_ID, location=LOCATION)


def classify_incident(notes: str) -> dict:
    """Classify field notes into structured incident data."""
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

    # Parse JSON from response
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json\n"):
            text = text[5:]

    try:
        result = json.loads(text)
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
    except json.JSONDecodeError:
        return {
            "incident_type": "general_incident",
            "forms_required": ["005_409"],
            "persons_involved": [],
            "charges_applicable": [],
            "charge_descriptions": {},
            "facility": "Unknown",
            "shift": "Unknown",
            "raw_classification": text,
        }
