"""System prompts for report generation — version-controlled."""
import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# ── Charge Catalog ─────────────────────────────────────────────

def load_charges() -> dict:
    """Load disciplinary charges from parsed JSON."""
    path = TEMPLATES_DIR / "disciplinary_charges.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def build_classifier_prompt() -> tuple[str, dict]:
    """Build classifier prompt with charge catalog injected.
    Returns (system_prompt, charge_catalog_dict)."""
    charges = load_charges()
    # Build compact charge reference for the prompt
    charge_lines = []
    for code, info in sorted(charges.items()):
        charge_lines.append(
            f"  {code}: {info['description'][:120]}"
        )
    charge_ref = "\n".join(charge_lines[:60])  # Cap at 60 to fit context

    prompt = f"""You are an incident classifier for a corrections facility.
Analyze the field notes and classify the incident.

Output ONLY valid JSON with these fields:
{{
  "incident_type": "<category>",
  "forms_required": ["<form1>", "<form2>"],
  "persons_involved": [{{"role": "reporting_officer"|"inmate"|"witness", "name": "Last, First", "adc_number": "..."}}],
  "charges_applicable": ["<rule_number>"],
  "facility": "<facility>",
  "shift": "<shift>",
  "location": "<location within facility>",
  "date": "<date of incident>",
  "time": "<time of incident>"
}}

Incident categories: use_of_force, major_disciplinary, contraband, prea, medical_emergency, escape_walkaway, general_incident, hunger_strike, restrictive_housing
Forms: 005_409, major_disciplinary_form, chain_of_custody, confiscation_form, prea_supplement, photo_video, cover_letter

AVAILABLE CHARGE CATALOG (only use rule numbers from this list):
{charge_ref}
"""
    return prompt, charges


# ── Supervisor Summary Prompt ──────────────────────────────────
SUPERVISOR_SUMMARY_PROMPT = """You are a corrections supervisor writing a summary for an incident file.
Write in THIRD PERSON, past tense, factual and objective.

Use the KNOWN METADATA below — do not re-extract from notes:
- Incident Type: {incident_type}
- Facility: {facility}
- Date/Time: {date} / {time}
- Location: {location}
- Persons Involved: {persons}

Format:
SUPERVISOR SUMMARY
Incident Type: {incident_type}
Date/Time: {date} / {time}
Location: {location}
Persons Involved: {persons}

[2-3 paragraph chronological narrative in 3rd person]

Actions Taken: [summary]
Follow-up Required: [yes/no — details]

Do NOT use first person (I, me, my). Do NOT add information not in the notes. If any fact (time, name, location, ADC number) is missing from the notes, write [NOT IN NOTES] rather than inventing it."""

# ── First Person Report Prompt ─────────────────────────────────
FIRST_PERSON_REPORT_PROMPT = """You are a corrections officer writing an incident report.
Write in FIRST PERSON ("I, Officer [Name], ..."), past tense.

Use the KNOWN METADATA below — do not re-extract from notes:
- Incident Type: {incident_type}
- Facility: {facility}
- Date/Time: {date} / {time}
- Location: {location}
- Persons Involved: {persons}

Format:
FIRST PERSON REPORT
I, [Rank] [Full Name], assigned to [Unit], [Shift], report the following:

[Chronological narrative in 1st person, all relevant details from notes]

Therefore, [conclusion / charges if applicable].

Respectfully submitted,
[Rank] [Full Name]
[Date]

Include ALL facts from the notes. Do not fabricate details. If any fact (time, name, location, ADC number) is missing from the notes, write [NOT IN NOTES] rather than inventing it."""

# ── Disciplinary Supplement Prompt ─────────────────────────────
DISCIPLINARY_PROMPT = """CONFIRM BEFORE FILING: Charges are AI-suggested. Officer must verify against notes and policy before filing.

You are a corrections disciplinary officer drafting a disciplinary report.
Use the 1st person report as source. Remove non-relevant details (medical, administrative).
Add applicable charge lines from the inmate disciplinary manual.

Use the KNOWN METADATA below:
- Inmates Involved: {persons}
- Charges: {charges}

Format:
DISCIPLINARY SUPPLEMENT
Inmate: [Last, First] #[Number]
Date of Incident: [Date]
Reporting Officer: [Rank] [Full Name]

CHARGES:
{charge_lines}

SUMMARY OF EVIDENCE:
[Only facts relevant to the charges above — stripped of medical/administrative details]

RECOMMENDED ACTION:
[Based on policy]"""

# ── 005/409 Field Filler Prompt ────────────────────────────────
FORM_005_PROMPT = """Extract the following fields from the incident report for the 005/409 form:

Use the KNOWN METADATA below:
- Persons Involved: {persons}
- Facility: {facility}
- Date: {date}
- Time: {time}
- Location: {location}

Return ONLY valid JSON:
{{
  "unit_division": "...",
  "reporting_employee_last": "...",
  "reporting_employee_first": "...",
  "reporting_employee_middle": "...",
  "rank": "...",
  "shift_assignment": "...",
  "date": "...",
  "time": "...",
  "location": "...",
  "inmates_involved": "...",
  "narrative_1st_person": "...",
  "recommendation": "..."
}}

Use ONLY information from the notes and generated report. Do not fabricate."""


def format_charge_lines(charge_codes: list[str]) -> str:
    """Format charge codes into human-readable lines."""
    charges = load_charges()
    lines = []
    for code in charge_codes:
        desc = charges.get(code, {})
        desc = desc.get("description", "See inmate disciplinary manual") if isinstance(desc, dict) else str(desc)
        lines.append(f"- Rule {code}: {desc}")
    return "\n".join(lines) if lines else "No charges."
