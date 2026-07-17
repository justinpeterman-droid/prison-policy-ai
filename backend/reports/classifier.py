"""Incident classifier — determines type, forms needed, persons, charges."""
import json
import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.prompts import CLASSIFIER_PROMPT

vertexai.init(project=PROJECT_ID, location=LOCATION)


def classify_incident(notes: str) -> dict:
    """Classify field notes into structured incident data."""
    model = GenerativeModel(
        model_name=GENERATION_MODEL,
        system_instruction=CLASSIFIER_PROMPT,
    )

    prompt = f"Classify this incident from the field notes:\n\n---\n{notes}\n---\n\nReturn ONLY valid JSON."

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
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "incident_type": "general_incident",
            "forms_required": ["005_409"],
            "persons_involved": [],
            "charges_applicable": [],
            "facility": "Unknown",
            "shift": "Unknown",
            "raw_classification": text,
        }
