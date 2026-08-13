"""Incident classifier — determines type, forms needed, persons, charges."""

import json
import re
import logging
from google import genai
from google.genai import types
from backend.pipeline.config import PROJECT_ID, FAST_MODEL, MODEL_LOCATION
from backend.pipeline.retry import with_retries
from backend.reports.prompts import build_classifier_prompt
from backend.reports.schema import load_checklist

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "contraband",
    "inmate_fight",
    "staff_assault",
    "forced_cell_movement",
    "prea",
    "incident_no_disciplinary",
    "use_of_force",
    "medical_emergency",
    "other_rule_violation",
}

# Grammar-constrain the classifier the same way extraction is constrained.
# Without this the model returned free-form text that had to be regex-scraped
# for JSON, and any parse failure silently became `other_rule_violation` —
# the wrong category then drives the wrong checklist, the wrong gap questions,
# and the wrong report. The enum makes an invalid category unrepresentable.
CLASSIFIER_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "incident_type": {"type": "STRING", "enum": sorted(VALID_CATEGORIES)},
        "persons_involved": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "role": {
                        "type": "STRING",
                        "enum": [
                            "reporting_officer",
                            "inmate",
                            "security_staff",
                            "witness",
                        ],
                    },
                    "name": {
                        "type": "STRING",
                        "nullable": True,
                        "description": "Last, First",
                    },
                    "rank": {
                        "type": "STRING",
                        "nullable": True,
                        "description": "Cpl. / Sgt. / Lt. / Cpt. — staff only",
                    },
                    "adc_number": {
                        "type": "STRING",
                        "nullable": True,
                        "description": "inmates only, digits",
                    },
                },
                "required": ["role"],
            },
        },
        "charges_applicable": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "code": {
                        "type": "STRING",
                        "description": "rule number from the charge catalog",
                    },
                    "inmate": {
                        "type": "STRING",
                        "nullable": True,
                        "description": "last name of the inmate charged",
                    },
                    "description": {"type": "STRING", "nullable": True},
                },
                "required": ["code"],
            },
        },
        "facility": {"type": "STRING", "nullable": True},
        "shift": {"type": "STRING", "nullable": True},
        "location": {"type": "STRING", "nullable": True},
        "date": {"type": "STRING", "nullable": True},
        "time": {"type": "STRING", "nullable": True},
    },
    "required": ["incident_type", "persons_involved", "charges_applicable"],
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


# Classification is a short call; fail fast rather than stalling the wizard.
CLASSIFY_TIMEOUT_MS = 60_000

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True, project=PROJECT_ID, location=MODEL_LOCATION
        )
    return _client


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
    system_prompt, charge_catalog = build_classifier_prompt()

    prompt = (
        f"Classify this incident from the field notes:\n\n"
        f"---\n{notes}\n---\n\n"
        f"Use the charge catalog below to select applicable rule numbers.\n"
        f"Return ONLY valid JSON."
    )

    def _call():
        return _get_client().models.generate_content(
            model=FAST_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=CLASSIFIER_RESPONSE_SCHEMA,
                # Classification is a decision, not prose — the same category
                # every time for the same notes.
                temperature=0.0,
                http_options=types.HttpOptions(timeout=CLASSIFY_TIMEOUT_MS),
            ),
        )

    response = with_retries(_call, describe="incident classification")

    # Robust JSON extraction from model response
    text = _extract_json_from_response(response.text)

    try:
        result = json.loads(text)
        # Constrain to the valid categories (belt and braces — the response
        # schema enum should already make an invalid one impossible)
        if result.get("incident_type") not in VALID_CATEGORIES:
            logger.warning(
                "Classifier returned invalid category %r — defaulting to other_rule_violation",
                result.get("incident_type"),
            )
            result["incident_type"] = "other_rule_violation"
        # Always add the human-readable label
        result["label"] = _category_label(result["incident_type"])
        # Normalize charges: support both old (list of strings) and new (list of objects)
        raw_charges = result.get("charges_applicable", [])
        normalized_charges = []
        for c in raw_charges:
            if isinstance(c, str):
                # Old format: just a code string
                if c in charge_catalog:
                    normalized_charges.append(
                        {
                            "code": c,
                            "inmate": "",
                            "description": charge_catalog[c]["description"],
                        }
                    )
            elif isinstance(c, dict):
                code = c.get("code", "")
                if code in charge_catalog:
                    normalized_charges.append(
                        {
                            "code": code,
                            "inmate": c.get("inmate", ""),
                            "description": c.get("description")
                            or charge_catalog[code]["description"],
                        }
                    )
        result["charges_applicable"] = normalized_charges
        # Fill in charge descriptions from catalog (backward compat for UI)
        result["charge_descriptions"] = {
            c["code"]: c["description"] for c in normalized_charges
        }
        return result
    except (json.JSONDecodeError, KeyError) as e:
        # With response_schema this should be unreachable. If it ever fires,
        # the officer is about to get the wrong checklist and the wrong gap
        # questions, so make it loud and mark the result as degraded rather
        # than passing off a guess as a real classification.
        logger.error(
            "Classification JSON parse failed despite response_schema: "
            "%s — falling back to other_rule_violation",
            e,
        )
        return {
            "incident_type": "other_rule_violation",
            "label": _category_label("other_rule_violation"),
            "persons_involved": [],
            "charges_applicable": [],
            "charge_descriptions": {},
            "facility": "Benny Magness Unit",
            "shift": "Unknown",
            # Signals "this is a fallback, not a real classification" — the
            # officer should double-check the incident type before continuing.
            "classification_degraded": True,
            "raw_classification": text,
        }
