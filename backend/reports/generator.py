"""Report generator — produces all required report texts."""
import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.prompts import (
    SUPERVISOR_SUMMARY_PROMPT,
    FIRST_PERSON_REPORT_PROMPT,
    DISCIPLINARY_PROMPT,
    FORM_005_PROMPT,
    format_charge_lines,
)

vertexai.init(project=PROJECT_ID, location=LOCATION)


def _generate(system_prompt: str, user_prompt: str) -> str:
    model = GenerativeModel(
        model_name=GENERATION_MODEL,
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_prompt)
    return response.text


def generate_supervisor_summary(notes: str, classification: dict) -> str:
    """Generate 3rd-person supervisor summary."""
    context = f"Field Notes:\n{notes}\n\nClassification: {classification.get('incident_type')}"
    return _generate(SUPERVISOR_SUMMARY_PROMPT, context)


def generate_first_person(notes: str, classification: dict) -> str:
    """Generate 1st-person officer report."""
    context = f"Field Notes:\n{notes}\n\nClassification: {classification.get('incident_type')}"
    return _generate(FIRST_PERSON_REPORT_PROMPT, context)


def generate_disciplinary(notes: str, first_person_report: str,
                          classification: dict) -> str:
    """Generate disciplinary supplement with charge lines."""
    charges = classification.get("charges_applicable", [])
    charge_text = format_charge_lines(charges)
    prompt = DISCIPLINARY_PROMPT.replace("{charge_lines}", charge_text)
    context = (
        f"Field Notes:\n{notes}\n\n"
        f"First Person Report:\n{first_person_report}\n\n"
        f"Charges: {', '.join(charges)}"
    )
    return _generate(prompt, context)


def generate_all_reports(notes: str, classification: dict) -> dict:
    """Generate all required reports in one call. Returns dict of report texts."""
    reports = {}

    reports["supervisor_summary"] = generate_supervisor_summary(
        notes, classification
    )
    reports["first_person"] = generate_first_person(
        notes, classification
    )

    charges = classification.get("charges_applicable", [])
    if charges:
        reports["disciplinary"] = generate_disciplinary(
            notes, reports["first_person"], classification
        )

    return reports
