"""Report generator v3 — structured facts only, never raw notes.

Uses prompts_v2.py which receives extraction slots (narrative_facts, quotes,
per-officer actions) + auto_content sentences. Every header field is rendered
by code from slots — the model writes narrative prose ONLY.
"""
import os
import logging
from google import genai
from google.genai import types
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.prompts_v2 import (
    FIRST_PERSON_PROMPT,
    SUPERVISOR_SUMMARY_PROMPT,
    DISCIPLINARY_PROMPT,
    COVER_LETTER_PROMPT,
)

logger = logging.getLogger(__name__)

MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", LOCATION)

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=PROJECT_ID, location=MODEL_LOCATION)
    return _client


def _generate(system_prompt: str, user_prompt: str) -> str:
    response = _get_client().models.generate_content(
        model=GENERATION_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return response.text


def _clean_time(s: str) -> str:
    """Strip 'approximately'/'approx'/'~' prefixes from time values
    so they don't duplicate the prompt's built-in 'at approximately'."""
    import re
    return re.sub(r'^(approximately|approx\.?|~)\s*', '', s.strip(), flags=re.I)


def _fmt(val, default="[NOT IN NOTES]") -> str:
    v = str(val) if val else ""
    if not v or v.lower() in ("none", "[not in notes]", "null"):
        return default
    return v


def _auto_for(report_type: str, auto_content: list[dict] | None) -> str:
    """Collect auto_content sentences targeted at this report type."""
    if not auto_content:
        return ""
    lines = []
    for ac in auto_content:
        if report_type in ac.get("insert_into", []):
            lines.append(ac["text"])
    return "\n".join(lines) if lines else "(none)"


def _narrative_facts_str(slots: dict) -> str:
    facts = slots.get("narrative_facts", [])
    if not facts:
        return "(none)"
    return "\n".join(f"- {f}" for f in facts)


def _quotes_str(slots: dict) -> str:
    quotes = slots.get("quotes", [])
    if not quotes:
        return "(none)"
    return "\n".join(f'"{q}"' for q in quotes)


def _reporter_actions_str(slots: dict, reporter_index: int = 0) -> str:
    persons = slots.get("persons", [])
    staff = [p for p in persons if p.get("role") == "security_staff"]
    if staff and reporter_index < len(staff):
        actions = staff[reporter_index].get("actions", [])
    else:
        actions = []
    if not actions:
        return "(no actions attributed to this officer in the notes)"
    return "\n".join(f"- {a}" for a in actions)


def _opening_actor(slots: dict) -> str:
    rank = _fmt(slots.get("rank"), "")
    first = _fmt(slots.get("officer_first"), "")
    last = _fmt(slots.get("officer_last"), "")
    return f"{rank} {first} {last}".strip() or "the reporting officer"


def _esc(s: str) -> str:
    """Escape braces so they survive .format() — needed because narrative
    data may contain {Last}, {First}, ADC#{number}, etc."""
    return s.replace("{", "{{").replace("}", "}}")


def _clean_report(text: str) -> str:
    """Post-process AI-generated report to fix common mistakes."""
    import re
    # "Sgt." → "Sgt", "Cpl." → "Cpl", etc. (only when followed by space/name)
    text = re.sub(r'\b(Sgt|Cpl|Lt|Cpt)\.(\s)', r'\1\2', text)
    # Ampersands between names → "and"
    text = re.sub(r'(\w)\s*&\s*(\w)', r'\1 and \2', text)
    # "placed hand restraints onto" → "applied hand restraints to"
    text = re.sub(r'placed hand restraints onto', 'applied hand restraints to', text)
    return text


# ── Per-report generators (all receive structured data ONLY) ──────


def generate_first_person(slots: dict, auto_content: list[dict] | None = None,
                          reporter_index: int = 0) -> str:
    prompt = FIRST_PERSON_PROMPT.format(
        rank=_fmt(slots.get("rank")),
        officer_first=_fmt(slots.get("officer_first")),
        officer_last=_fmt(slots.get("officer_last")),
        date=_fmt(slots.get("date")),
        time=_clean_time(_fmt(slots.get("time"), "")),
        reporter_actions=_esc(_reporter_actions_str(slots, reporter_index)),
        narrative_facts=_esc(_narrative_facts_str(slots)),
        quotes=_esc(_quotes_str(slots)),
        auto_content=_esc(_auto_for("first_person", auto_content)),
    )
    return _clean_report(_generate(prompt, prompt))  # system=user for single-message flow


def generate_supervisor_summary(slots: dict, auto_content: list[dict] | None = None) -> str:
    prompt = SUPERVISOR_SUMMARY_PROMPT.format(
        date=_fmt(slots.get("date")),
        time=_fmt(slots.get("time")),
        opening_actor=_opening_actor(slots),
        narrative_facts=_esc(_narrative_facts_str(slots)),
        quotes=_esc(_quotes_str(slots)),
        auto_content=_esc(_auto_for("supervisor_summary", auto_content)),
    )
    return _clean_report(_generate(prompt, prompt))


def generate_cover_letter(slots: dict, auto_content: list[dict] | None = None) -> str:
    prompt = COVER_LETTER_PROMPT.format(
        rank=_fmt(slots.get("rank")),
        officer_first=_fmt(slots.get("officer_first")),
        officer_last=_fmt(slots.get("officer_last")),
        date=_fmt(slots.get("date")),
        time=_fmt(slots.get("time")),
        narrative_facts=_esc(_narrative_facts_str(slots)),
        auto_content=_esc(_auto_for("cover_letter", auto_content)),
    )
    return _clean_report(_generate(prompt, prompt))


def generate_disciplinary(slots: dict, first_person_report: str,
                          auto_content: list[dict] | None = None) -> str:
    charges = slots.get("charges", "")
    prompt = DISCIPLINARY_PROMPT.format(
        rank=_fmt(slots.get("rank")),
        officer_first=_fmt(slots.get("officer_first")),
        officer_last=_fmt(slots.get("officer_last")),
        first_person_report=_esc(first_person_report or ""),
        charges=charges or "None",
    )
    return _generate(prompt, prompt)


def generate_all_reports(slots: dict, category: str = "",
                         auto_content: list[dict] | None = None,
                         reporter_actions: str = "") -> dict:
    """Generate all report types from structured slots.

    Args:
        slots: Extraction slots (narrative_facts, quotes, persons, etc.)
        category: Incident category name
        auto_content: Resolved auto_content sentences from validate.py
        reporter_actions: Pre-formatted reporter actions (if already built)

    Returns:
        dict with keys: cover_letter, first_person, supervisor_summary,
                        disciplinary (if charges present)
    """
    reports = {}

    try:
        reports["first_person"] = generate_first_person(slots, auto_content)
    except Exception:
        logger.error("First person report generation failed", exc_info=True)
        reports["first_person"] = "[Error generating first person report]"

    try:
        reports["supervisor_summary"] = generate_supervisor_summary(slots, auto_content)
    except Exception:
        logger.error("Supervisor summary generation failed", exc_info=True)
        reports["supervisor_summary"] = "[Error generating supervisor summary]"

    try:
        reports["cover_letter"] = generate_cover_letter(slots, auto_content)
    except Exception:
        logger.error("Cover letter generation failed", exc_info=True)
        reports["cover_letter"] = "[Error generating cover letter]"

    charges = slots.get("charges", "")
    if charges and charges not in ("None", ""):
        try:
            reports["disciplinary"] = generate_disciplinary(
                slots, reports.get("first_person", ""), auto_content
            )
        except Exception:
            logger.error("Disciplinary supplement generation failed", exc_info=True)
            reports["disciplinary"] = "[Error generating disciplinary supplement]"

    return reports
