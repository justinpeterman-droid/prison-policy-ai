"""Slot schema for incident report extraction.

Two levels:
  * INCIDENT slots — shared facts about the event (date, time, location, inmates...).
  * REPORTER slots — bound per generated 005. When the user taps another officer's
    button, the reporter block is re-bound to that officer, so the front of the 005
    (Reporting Officer name / rank / shift) changes to reflect them.

Also builds the Gemini response_schema so extraction output is guaranteed-valid JSON.
Every field is nullable: the model returns null for anything the notes don't state —
nulls are what drive the gap-question screen.
"""
import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
CHECKLIST_PATH = TEMPLATES_DIR / "incident_checklist_v2.json"


def load_checklist() -> dict:
    return json.loads(CHECKLIST_PATH.read_text())


# ── Reporter-level slots (swap per selected officer) ──────────────
REPORTER_SLOTS = ["officer_last", "officer_first", "employee_number",
                  "rank", "shift_assignment"]

_PERSON = {
    "type": "OBJECT",
    "properties": {
        "role": {"type": "STRING", "enum": ["inmate", "security_staff",
                                            "medical_staff", "other"]},
        "last": {"type": "STRING", "nullable": True},
        "first": {"type": "STRING", "nullable": True},
        "employee_number": {"type": "STRING", "nullable": True, "description": "staff employee # (goes in the 005 middle spot)"},
        "rank": {"type": "STRING", "nullable": True,
                 "description": "Cpl. / Sgt. / Lt. / Cpt. — staff only"},
        "adc_number": {"type": "STRING", "nullable": True,
                       "description": "inmates only, digits"},
        "actions": {"type": "ARRAY", "items": {"type": "STRING"},
                    "description": "actions/observations the notes attribute to THIS person, verbatim-faithful"},
        "injuries": {"type": "STRING", "nullable": True},
    },
    "required": ["role", "last", "actions"],
}


def build_response_schema(category: dict, checklist: dict) -> dict:
    """Gemini response_schema for one incident category.

    Core 005 slots + this category's required_slots + every slot any of its
    rules can require. All nullable — null means 'notes did not state this'.
    """
    props = {
        "incident_number": {"type": "STRING", "nullable": True},
        "unit_division": {"type": "STRING", "nullable": True},
        "date": {"type": "STRING", "nullable": True},
        "time": {"type": "STRING", "nullable": True,
                 "description": "as written, e.g. 'approximately 10:42pm'"},
        "location": {"type": "STRING", "nullable": True},
        "persons": {"type": "ARRAY", "items": _PERSON},
        "reporting_officer_index": {"type": "INTEGER", "nullable": True,
            "description": "index into persons of the officer writing these notes (the 'I')"},
        "inmate_injuries": {"type": "STRING", "nullable": True},
        "officer_injuries": {"type": "STRING", "nullable": True},
        "narrative_facts": {"type": "ARRAY", "items": {"type": "STRING"},
            "description": "chronological list of factual events from the notes, one per entry, no embellishment"},
        "quotes": {"type": "ARRAY", "items": {"type": "STRING"},
            "description": "verbatim statements/profanity to quote as evidence"},
    }

    extra = set(category.get("required_slots", []))
    for rule in category.get("rules", []) + checklist.get("universal_rules", []):
        extra.add(rule["require"])
    for slot in extra:
        if slot not in props:
            props[slot] = {"type": "STRING", "nullable": True}

    return {"type": "OBJECT", "properties": props,
            "required": ["persons", "narrative_facts"]}


def bind_reporter(slots: dict, person: dict) -> dict:
    """Return a copy of slots with the 005 reporter block bound to `person`.

    This is what makes the front page of the 005 change when another
    officer's report is generated.
    """
    out = dict(slots)
    out["officer_last"] = person.get("last") or None
    out["officer_first"] = person.get("first") or None
    out["employee_number"] = person.get("employee_number") or None
    out["rank"] = person.get("rank") or None
    out["shift_assignment"] = person.get("shift_assignment") or slots.get("shift_assignment")
    return out


def security_staff(extraction: dict) -> list[dict]:
    """All named security staff — one report button each in the UI."""
    return [p for p in extraction.get("persons", [])
            if p.get("role") == "security_staff"]
