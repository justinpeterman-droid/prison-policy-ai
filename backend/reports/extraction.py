"""Extraction pass — the ONLY place Gemini reads the raw notes.

Output is grammar-constrained by response_schema (schema.py), so it always
parses. The model's job is extraction only: it fills slots from the notes and
returns null for anything not stated. It never writes report prose here.
"""
import json
import logging
import os
import re
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from backend.pipeline.config import PROJECT_ID, LOCATION, GENERATION_MODEL
from backend.reports.schema import build_response_schema, load_checklist

logger = logging.getLogger(__name__)

# Model may need a different location than the app default (e.g. gemini-3.5-flash
# is global-only while RAG/corpus lives in us-central1).
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", LOCATION)
vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)

EXTRACTION_SYSTEM = """You extract facts from a corrections officer's field notes.
Rules:
- Output values ONLY for facts the notes state. Anything not stated = null.
- NEVER guess, infer, or invent names, ADC numbers, dates, times, or events.
- NAMES: Always extract as Last, First. Officers often write 'First Last'
  (e.g. 'Harry Vagina'). Detect this and output last='Vagina', first='Harry'.
  Common first names (Harry, James, Michael, etc.) followed by a surname are
  a strong signal the order is flipped. If ambiguous, prefer Last, First.
- INJURIES: NEVER reproduce racial slurs or profanity. Describe injuries
  clinically: 'fat lip' → 'swollen lip', 'black eye' → 'periorbital
  contusion', 'busted lip' → 'lip laceration'. Classify into standard
  categories: 'minor facial swelling', 'periorbital contusion', 'minor
  lacerations', 'contusions', 'abrasions'. Multiple minor injuries →
  'minor injuries to the facial area'.
- persons[].actions: list what the notes attribute to THAT person only.
- narrative_facts: the events in chronological order, one plain factual
  sentence each, faithful to the notes. No embellishment, no conclusions.
- quotes: verbatim inmate statements. If they contain slurs/profanity,
  keep the quote but prefix with [QUOTE CONTAINS OFFENSIVE LANGUAGE].
- Times: format as 'H:MMam' or 'H:MMpm'. Fix obvious typos (e.g.
  '7:22AAm' → '7:22am'). If unparseable, leave as-is."""

# ── Field labels for the trace UI ──
FIELD_LABELS = {
    "date": "Date", "time": "Time", "location": "Location",
    "unit_division": "Unit/Division", "shift_assignment": "Shift",
    "officer_last": "Officer (last)", "officer_first": "Officer (first)",
    "rank": "Rank", "employee_number": "Employee #",
    "inmate_injuries": "Inmate injuries", "officer_injuries": "Officer injuries",
    "inmate_treatment": "Inmate treatment", "officer_treatment": "Officer treatment",
    "others_present": "Others present",
    "weapon_involved": "Weapon involved", "drug_type": "Drug type",
    "force_type": "Force type", "chemical_agent": "Chemical agent",
    "cell_number": "Cell number",
}


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


def _safe_str(v):
    """Return a clean string for matching; skip None/empty/boolean/list objects."""
    if v is None:
        return None
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (list, dict)):
        return None  # complex — skip span matching
    s = str(v).strip()
    if not s or s in ("N/A", "UNKNOWN", "None", "null"):
        return None
    return s


def _find_span(notes: str, notes_lower: str, value: str, vl: str) -> str | None:
    """Find the best matching span in notes for a given value string.

    Tries: exact match then word-level match.
    Returns a short surrounding context snippet, or None.
    """
    # 1) Exact substring match (case-insensitive)
    idx = notes_lower.find(vl)
    if idx >= 0:
        snippet = notes[idx:idx + len(value)]
        # Grab a little context
        start = max(0, idx - 20)
        end = min(len(notes), idx + len(value) + 30)
        ctx = notes[start:end].strip()
        if start > 0:
            ctx = "\u2026" + ctx
        if end < len(notes):
            ctx = ctx + "\u2026"
        # Bold the match
        ctx_highlighted = ctx.replace(snippet, f"**{snippet}**")
        return ctx_highlighted

    # 2) Try matching individual words (e.g. "Justin" matches "Sgt Justin Peterman")
    words = [w for w in re.split(r"[\s,.;:]+", vl) if len(w) > 2]
    if words:
        for word in words:
            idx = notes_lower.find(word)
            if idx >= 0:
                start = max(0, idx - 15)
                end = min(len(notes), idx + len(word) + 25)
                ctx = notes[start:end].strip()
                if start > 0:
                    ctx = "\u2026" + ctx
                if end < len(notes):
                    ctx = ctx + "\u2026"
                return f"~{ctx}"

    return None


def compute_provenance(notes: str, slots: dict) -> list[dict]:
    """Post-hoc: find where each slot value appears in the original notes.

    Returns a list of {label, value, source_snippet} for non-null slot values
    that could be anchored to the notes. Values without a match are still
    listed (source_snippet is null) so the UI can show them as AI-inferred.
    """
    entries: list[dict] = []
    notes_lower = notes.lower()
    seen_values: set[str] = set()

    # Collect flat slot keys
    flat_slots: list[tuple[str, str]] = []

    # Top-level slots
    for key, val in slots.items():
        if key in ("persons", "narrative_facts", "quotes", "actions",
                   "incident_type"):
            continue
        sv = _safe_str(val)
        if sv:
            label = FIELD_LABELS.get(key, key.replace("_", " ").title())
            flat_slots.append((label, sv))

    # Persons
    for person in slots.get("persons", []):
        name_parts = []
        for f in ("rank", "first", "last"):
            v = _safe_str(person.get(f))
            if v:
                name_parts.append(v)
        if name_parts:
            full = " ".join(name_parts)
            role = person.get("role", "person")
            label = f"{role.replace('_', ' ').title()}: {full}"
            flat_slots.append((label, full))

        adc = _safe_str(person.get("adc_number") or person.get("employee_number"))
        if adc:
            name = person.get("last", "") or person.get("first", "") or ""
            label = f"{name} ADC#" if name else "ADC#"
            flat_slots.append((label, adc))

        for inj in (person.get("injuries") or []):
            if isinstance(inj, str) and inj.strip():
                flat_slots.append(("Injury noted", inj.strip()))

        for act in (person.get("actions") or []):
            if isinstance(act, str) and act.strip():
                flat_slots.append(("Action", act.strip()))

    # Narrative facts
    for fact in (slots.get("narrative_facts") or []):
        sv = _safe_str(fact)
        if sv:
            flat_slots.append(("Narrative fact", sv))

    # Match each value to a span in the notes
    for label, value in flat_slots:
        vl = value.lower()
        # Deduplicate identical values
        dedup_key = f"{label}:{vl}"
        if dedup_key in seen_values:
            continue
        seen_values.add(dedup_key)

        source = _find_span(notes, notes_lower, value, vl)
        entries.append({
            "label": label,
            "value": value,
            "source": source,
        })

    return entries
