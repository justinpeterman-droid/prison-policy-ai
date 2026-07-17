"""Report generator — produces all required report texts."""
import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.prompts import (
    SUPERVISOR_SUMMARY_PROMPT,
    FIRST_PERSON_REPORT_PROMPT,
    DISCIPLINARY_PROMPT,
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


def _format_persons(persons: list[dict]) -> str:
    """Format persons list for prompt injection."""
    if not persons:
        return "None listed"
    return ", ".join(
        f"{p.get('name', 'Unknown')} ({p.get('role', 'unknown')}, ADC #{p.get('adc_number', 'N/A')})"
        for p in persons
    )


def _fmt(val, default="Unknown") -> str:
    """Format a value with fallback."""
    return str(val) if val else default


def generate_supervisor_summary(notes: str, classification: dict) -> str:
    """Generate 3rd-person supervisor summary."""
    prompt = SUPERVISOR_SUMMARY_PROMPT.format(
        incident_type=_fmt(classification.get("incident_type")),
        facility=_fmt(classification.get("facility")),
        date=_fmt(classification.get("date")),
        time=_fmt(classification.get("time")),
        location=_fmt(classification.get("location")),
        persons=_format_persons(classification.get("persons_involved", [])),
    )
    return _generate(prompt, notes)


def generate_first_person(notes: str, classification: dict) -> str:
    """Generate 1st-person officer report."""
    prompt = FIRST_PERSON_REPORT_PROMPT.format(
        incident_type=_fmt(classification.get("incident_type")),
        facility=_fmt(classification.get("facility")),
        date=_fmt(classification.get("date")),
        time=_fmt(classification.get("time")),
        location=_fmt(classification.get("location")),
        persons=_format_persons(classification.get("persons_involved", [])),
    )
    return _generate(prompt, notes)


def generate_disciplinary(notes: str, first_person_report: str,
                          classification: dict) -> str:
    """Generate disciplinary supplement with charge lines."""
    charges = classification.get("charges_applicable", [])
    charge_text = format_charge_lines(charges)

    # Build the prompt with charge_lines and metadata pre-filled
    prompt = DISCIPLINARY_PROMPT.format(
        persons=_format_persons(classification.get("persons_involved", [])),
        charges=", ".join(charges) if charges else "None",
        charge_lines=charge_text,
    )
    return _generate(prompt, f"{notes}\n\nFirst Person Report:\n{first_person_report}")


def generate_all_reports(notes: str, classification: dict) -> dict:
    """Generate all required reports. Returns dict with partial results on failure."""
    reports = {}

    try:
        reports["supervisor_summary"] = generate_supervisor_summary(
            notes, classification
        )
    except Exception:
        reports["supervisor_summary"] = "[Error generating supervisor summary]"

    try:
        reports["first_person"] = generate_first_person(
            notes, classification
        )
    except Exception:
        reports["first_person"] = "[Error generating first person report]"

    charges = classification.get("charges_applicable", [])
    if charges:
        try:
            reports["disciplinary"] = generate_disciplinary(
                notes, reports.get("first_person", ""), classification
            )
        except Exception:
            reports["disciplinary"] = "[Error generating disciplinary supplement]"

    return reports
