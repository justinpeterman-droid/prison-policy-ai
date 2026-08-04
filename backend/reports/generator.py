"""Report generator v3 — structured facts only, never raw notes.

Uses prompts_v2.py which receives extraction slots (narrative_facts, quotes,
per-officer actions) + auto_content sentences. Every header field is rendered
by code from slots — the model writes narrative prose ONLY.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
from backend.pipeline.config import PROJECT_ID, PRO_MODEL, MODEL_LOCATION
from backend.pipeline.retry import with_retries
from backend.reports.prompts_v2 import (
    REPORT_STYLE_SYSTEM,
    FIRST_PERSON_PROMPT,
    SUPERVISOR_SUMMARY_PROMPT,
    DISCIPLINARY_PROMPT,
    COVER_LETTER_PROMPT,
)
from backend.reports.name_fixer import enforce_naming

logger = logging.getLogger(__name__)

# Report prose is a structured, rule-bound task — keep it low-temperature so the
# required sentences and opening formulas are followed and output is stable
# run-to-run (extraction is temp=0; generation just needs a little room to read
# naturally).
GENERATION_TEMPERATURE = 0.25

# A report generation that hangs is worse than one that fails: the officer sits
# on a spinner with no idea whether to wait or start over.
GENERATION_TIMEOUT_MS = 120_000

_thread_local = threading.local()


def _get_client() -> genai.Client:
    """Return a per-thread genai.Client — httpx clients are not thread-safe."""
    client = getattr(_thread_local, 'client', None)
    if client is None:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=MODEL_LOCATION)
        _thread_local.client = client
    return client


def _generate(system_prompt: str, user_prompt: str, describe: str = "report generation") -> str:
    def _call():
        response = _get_client().models.generate_content(
            model=PRO_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=GENERATION_TEMPERATURE,
                http_options=types.HttpOptions(timeout=GENERATION_TIMEOUT_MS),
            ),
        )
        return response.text

    return with_retries(_call, describe=describe)


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
    # Rank abbreviations KEEP their period ("Sgt.", "Cpl.") — they are
    # abbreviations, and every real report writes them that way. This used to
    # strip the period, rewriting correct output into something the officers
    # don't write. See templates/gold_reports/STYLE_RULINGS.md ruling 2.
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
    return _clean_report(_generate(REPORT_STYLE_SYSTEM, prompt))


def generate_supervisor_summary(slots: dict, auto_content: list[dict] | None = None) -> str:
    prompt = SUPERVISOR_SUMMARY_PROMPT.format(
        date=_fmt(slots.get("date")),
        time=_fmt(slots.get("time")),
        opening_actor=_opening_actor(slots),
        narrative_facts=_esc(_narrative_facts_str(slots)),
        quotes=_esc(_quotes_str(slots)),
        auto_content=_esc(_auto_for("supervisor_summary", auto_content)),
    )
    return _clean_report(_generate(REPORT_STYLE_SYSTEM, prompt))


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
    return _clean_report(_generate(REPORT_STYLE_SYSTEM, prompt))


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
    return _generate(REPORT_STYLE_SYSTEM, prompt)


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
                        disciplinary (if charges present), plus `_errors` —
                        the report keys that failed, so the caller can surface
                        the failure instead of letting an error placeholder
                        pass for a finished report.
    """
    reports: dict = {}
    errors: list[str] = []

    def _run(key: str, label: str, fn):
        """Generate one report, recording failure rather than raising."""
        try:
            return key, enforce_naming(fn(), slots), None
        except Exception:
            logger.error("%s generation failed", label, exc_info=True)
            return key, f"[Error generating {label.lower()}]", key

    # first_person, supervisor_summary and cover_letter are independent of one
    # another, so run them concurrently — previously this was four sequential
    # round-trips on the Pro tier, which reads as a hung page. disciplinary is
    # sequenced afterwards because it takes the finished first-person report as
    # its factual source.
    jobs = [
        ("first_person", "First person report",
         lambda: generate_first_person(slots, auto_content)),
        ("supervisor_summary", "Supervisor summary",
         lambda: generate_supervisor_summary(slots, auto_content)),
        ("cover_letter", "Cover letter",
         lambda: generate_cover_letter(slots, auto_content)),
    ]

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for key, text, failed in pool.map(lambda j: _run(*j), jobs):
            reports[key] = text
            if failed:
                errors.append(failed)

    charges = slots.get("charges", "")
    if charges and charges not in ("None", ""):
        key, text, failed = _run(
            "disciplinary", "Disciplinary supplement",
            lambda: generate_disciplinary(
                slots, reports.get("first_person", ""), auto_content))
        reports[key] = text
        if failed:
            errors.append(failed)

    logger.info("Generated %d report(s) in %.1fs (%d failed)",
                len(reports), time.monotonic() - started, len(errors))
    if errors:
        reports["_errors"] = errors
    return reports
