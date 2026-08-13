"""Route-neutral adapters over the existing report pipeline.

The adapters preserve the legacy browser payloads while allowing the Access
worker to inject a SQL-backed staff provider. They do not change prompts,
retrieval, validation, generation, repair, or fabrication checks.
"""

import json
import logging
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from backend.reports.classifier import classify_incident
from backend.reports.extraction import compute_provenance, extract_slots
from backend.reports.filler import designation_boxes
from backend.reports.gap_answers import build_incident_number, merge_gap_answers
from backend.reports.generator import (
    generate_all_reports,
    generate_disciplinary_only,
    has_charges,
)
from backend.reports.report_validator import repair_all, summarize, validate_all
from backend.reports.roster import FileStaffProvider, StaffProvider, SqlStaffProvider
from backend.reports.roster import resolve_staff_from_persons
from backend.reports.schema import bind_reporter, security_staff
from backend.reports.validate import find_gaps, invented_facts


logger = logging.getLogger(__name__)
_LOCATION_MAP_PATH = Path(__file__).parents[2] / "templates" / "location_map.json"

MSF_REFERENCE = "MSF 205"
SEE_ABOVE = "Same as above"
FIRST_NAME_NEEDED = "[FIRST NAME NEEDED]"
MEDICAL_SEEN_CATEGORIES = {
    "inmate_fight",
    "staff_assault",
    "forced_cell_movement",
    "prea",
    "use_of_force",
    "medical_emergency",
}
MEDICAL_INJURY_DISPOSITIONS = {
    "Seen by Infirmary staff",
    "Refused medical (Refuse box checked)",
    "Sent by ambulance to outside facility",
}
OFFICER_FORCE_CATEGORIES = {"staff_assault", "use_of_force"}
FIGHT_RH_CATEGORIES = {"inmate_fight", "staff_assault", "use_of_force"}
RESTRICTIVE_HOUSING = "Restrictive Housing"
RESUMABLE_REPORT_KEYS = (
    "first_person",
    "supervisor_summary",
    "cover_letter",
    "investigation",
)


@lru_cache(maxsize=1)
def _load_location_map() -> dict:
    try:
        return json.loads(_LOCATION_MAP_PATH.read_text())
    except Exception:
        logger.warning("Could not load location_map.json; skipping normalization")
        return {}


def _normalize_location(value):
    if not value:
        return value
    location_map = _load_location_map()
    if not location_map:
        return value
    lowered = str(value).strip().lower()
    if lowered in location_map:
        return location_map[lowered]
    best = None
    for slang, formal in location_map.items():
        if slang in lowered and (best is None or len(slang) > len(best[0])):
            best = (slang, formal)
    if best:
        return str(value).replace(best[0], best[1]).replace(best[0].title(), best[1])
    return value


def _titlecase(value):
    if not value:
        return value
    return " ".join(
        word[:1].upper() + word[1:] if word else word for word in str(value).split()
    )


def _to_12h(value):
    if not value:
        return value
    core = re.sub(
        r"^(approximately|approx\.?|~)\s*",
        "",
        str(value).strip(),
        flags=re.I,
    ).strip()
    match = re.match(r"^(\d{1,2}):?(\d{2})\s*([ap])\.?\s*m\.?$", core, re.I)
    if match:
        return f"{int(match.group(1))}:{match.group(2)} {match.group(3).lower()}m"
    match = re.match(r"^(\d{1,2}):?(\d{2})$", core)
    if match:
        hour, minute = int(match.group(1)), match.group(2)
        if 0 <= hour <= 23:
            suffix = "am" if hour < 12 else "pm"
            return f"{hour % 12 or 12}:{minute} {suffix}"
    return value


def _validate_and_clean_time(value):
    if not value:
        return value, False
    raw = str(value).strip()
    if re.match(r"^\d{1,2}:?\d{2}\s*[ap]\.?m\.?$", raw, re.I):
        return _to_12h(raw), True
    if re.match(r"^\d{3,4}$", raw):
        hour, minute = int(raw[:-2]), raw[-2:]
        if 0 <= hour <= 23 and 0 <= int(minute) <= 59:
            return _to_12h(f"{hour}:{minute}"), True
        return raw, False
    cleaned = re.sub(r"\s*[a-zA-Z]+$", "", raw).strip()
    match = re.match(r"^(\d{1,2}):?(\d{2})$", cleaned)
    if match:
        hour, minute = int(match.group(1)), match.group(2)
        if 1 <= hour <= 12 and 0 <= int(minute) <= 59:
            suffix_match = re.search(r"([ap])", raw, re.I)
            suffix = suffix_match.group(1).lower() + "m" if suffix_match else "am"
            return _to_12h(f"{hour}:{minute}{suffix}"), True
        return raw, False
    approximate = re.match(r"^(approximately|approx\.?|~)\s+(.+)", raw, re.I)
    if approximate:
        inner, valid = _validate_and_clean_time(approximate.group(2))
        if valid:
            return inner, True
    return raw, False


def _to_form_time(value):
    if not value:
        return value
    normalized = _to_12h(value)
    match = re.match(r"^(\d{1,2}):(\d{2})\s*([ap])m$", str(normalized).strip(), re.I)
    if not match:
        return value
    return f"APX. {int(match.group(1))}:{match.group(2)} {match.group(3).upper()}M"


def _format_shift(value):
    if not value:
        return value
    rendered = str(value).strip()
    return (
        f"{rendered.upper()} Shift"
        if len(rendered) == 1 and rendered.isalpha()
        else rendered
    )


def _today() -> str:
    return datetime.now().strftime("%m-%d-%Y")


def _is_first_person_unnamed(notes: str, slots: dict) -> bool:
    first_person = bool(re.search(r"\bI\b|\bme\b|\bmy\b", notes, re.I))
    last, first = slots.get("officer_last"), slots.get("officer_first")
    return first_person and (not last or not first or last == "None" or first == "None")


def _build_incident_number(last3, incident_date=None) -> str:
    return build_incident_number(last3, incident_date)


def _format_inmates(slots: dict) -> str:
    values = []
    for person in slots.get("persons", []):
        if person.get("role") != "inmate" or not person.get("last"):
            continue
        first = _titlecase(person.get("first")) or FIRST_NAME_NEEDED
        values.append(
            f"Inmate {_titlecase(person.get('last', ''))}, {first} "
            f"ADC#{person.get('adc_number') or 'UNKNOWN'}"
        )
    return ", ".join(values)


def _inmates_missing_first(slots: dict) -> list:
    return [
        person.get("last")
        for person in slots.get("persons", [])
        if person.get("role") == "inmate"
        and person.get("last")
        and not person.get("first")
    ]


def _apply_first_name_answers(slots: dict, answers: dict) -> None:
    for key, value in answers.items():
        if not (isinstance(key, str) and key.startswith("inmate_first::") and value):
            continue
        last = key.split("::", 1)[1]
        for person in slots.get("persons", []):
            if (
                person.get("role") == "inmate"
                and person.get("last") == last
                and not person.get("first")
            ):
                person["first"] = _titlecase(value)


def _format_employees(slots: dict) -> str:
    return ", ".join(
        f"{person.get('rank', '')} {_titlecase(person.get('first', ''))} "
        f"{_titlecase(person.get('last', ''))}".strip()
        for person in slots.get("persons", [])
        if person.get("role") == "security_staff" and person.get("last")
    )


def _parse_name(full_name: str) -> tuple[str, str, str]:
    if not full_name:
        return "", "", ""
    parts = full_name.split(",", 1)
    last = parts[0].strip()
    given = parts[1].strip().split() if len(parts) > 1 else []
    return (
        last,
        given[0] if given else "",
        " ".join(given[1:]) if len(given) > 1 else "",
    )


def _parse_rank(full_name: str) -> str:
    if not full_name:
        return ""
    ranks = [
        "Cpt.",
        "Lt.",
        "Sgt.",
        "Cpl.",
        "Ofc.",
        "Officer",
        "Capt.",
        "Captain",
        "Lieutenant",
        "Sergeant",
        "Corporal",
        "Major",
        "Maj.",
        "Col.",
        "Colonel",
        "Warden",
        "Deputy Warden",
    ]
    abbreviations = {
        "Corporal": "Cpl.",
        "Sergeant": "Sgt.",
        "Captain": "Cpt.",
        "Lieutenant": "Lt.",
        "Colonel": "Col.",
        "Major": "Maj.",
        "Officer": "Ofc.",
    }
    for rank in sorted(ranks, key=len, reverse=True):
        if full_name.startswith(rank) or full_name.startswith(
            rank.lower().capitalize()
        ):
            return abbreviations.get(rank, rank)
    return ""


def _apply_gap_defaults(category: str, gaps: list) -> None:
    for gap in gaps:
        slot = gap.get("slot")
        if slot == "medical_disposition":
            gap["default"] = (
                "Seen by Infirmary staff"
                if category in MEDICAL_SEEN_CATEGORIES
                else "N/A - no injuries reported"
            )
        elif slot == "drug_test_disposition":
            gap["default"] = "N/A"
        elif slot == "escort_destination" and category in FIGHT_RH_CATEGORIES:
            gap["default"] = "Infirmary, then Restrictive Housing"


def classify_incident_notes(notes: str) -> dict:
    classification = classify_incident(notes)
    return {
        "incident_type": classification.get("incident_type"),
        "label": classification.get("label", ""),
        "charges": classification.get("charges_applicable", []),
        "charge_descriptions": classification.get("charge_descriptions", {}),
    }


def extract_incident_notes(
    notes: str,
    category: str,
    staff_provider: StaffProvider,
) -> dict:
    slots = extract_slots(notes, category)
    if not slots.get("date"):
        slots["date"] = _today()
    if slots.get("location"):
        slots["location"] = _normalize_location(slots["location"])
    if slots.get("time"):
        cleaned, valid = _validate_and_clean_time(slots["time"])
        slots["time"] = cleaned if valid else _to_12h(slots["time"])

    roster_gaps: list[dict] = []
    persons = slots.get("persons", [])
    if persons:
        persons, roster_gaps = resolve_staff_from_persons(
            persons, staff_provider=staff_provider
        )
        slots["persons"] = persons
        for person in persons:
            if person.get("role") == "security_staff" and person.get("_roster_match"):
                slots.setdefault("officer_last", person.get("last", ""))
                slots.setdefault("officer_first", person.get("first", ""))
                slots.setdefault("rank", person.get("rank", ""))
                slots.setdefault("employee_number", person.get("employee_number", ""))
                if person.get("shift") and not slots.get("shift_assignment"):
                    slots["shift_assignment"] = _format_shift(person["shift"])
                break

    if not slots.get("inmates_involved") and any(
        person.get("role") == "inmate" and person.get("last")
        for person in slots.get("persons", [])
    ):
        slots["inmates_involved"] = _format_inmates(slots)
    if not slots.get("employees_involved") and any(
        person.get("role") == "security_staff" and person.get("last")
        for person in slots.get("persons", [])
    ):
        slots["employees_involved"] = _format_employees(slots)

    gap_result = find_gaps(category, slots)
    gaps = list(gap_result.get("gaps", [])) + roster_gaps
    if not slots.get("shift_assignment"):
        gaps.append(
            {
                "slot": "shift_assignment",
                "blocking": False,
                "answer_type": "text",
                "question": "Shift assignment? (from the unit roster)",
            }
        )
    if _is_first_person_unnamed(notes, slots):
        gaps.insert(
            0,
            {
                "slot": "officer_name",
                "blocking": True,
                "answer_type": "text",
                "question": "Who is the reporting officer? (name not found in the notes)",
            },
        )
    for last in _inmates_missing_first(slots):
        gaps.append(
            {
                "slot": f"inmate_first::{last}",
                "blocking": False,
                "answer_type": "text",
                "question": f"First name for Inmate {last}? (leave blank if unknown)",
            }
        )
    _apply_gap_defaults(category, gaps)
    return {
        "slots": slots,
        "gaps": gaps,
        "blocking_remaining": sum(1 for gap in gaps if gap.get("blocking")),
        "markers": gap_result.get("markers", []),
        "checklist": gap_result.get("checklist", []),
        "auto_content": gap_result.get("auto_content", []),
        "officers": security_staff(slots),
        "provenance": compute_provenance(notes, slots),
    }


def _prepare_generation(data: dict, staff_provider: StaffProvider) -> dict:
    notes = data.get("notes", "").strip()
    category = data.get("category", "").strip()
    answers = data.get("answers", {})
    slots = merge_gap_answers(dict(data.get("slots", {})), answers)
    _apply_first_name_answers(slots, answers)

    add_from_gap = getattr(staff_provider, "add_from_gap_answer", None)
    for key, value in answers.items():
        if key.startswith("officer_identity_") and value and add_from_gap is not None:
            add_from_gap(key.replace("officer_identity_", ""), str(value))
        elif key.startswith("officer_fields_") and value:
            hint = key.replace("officer_fields_", "")
            for person in slots.get("persons", []):
                if person.get("role") == "security_staff" and (
                    person.get("last", "").lower() == hint.lower()
                    or person.get("name", "").lower() == hint.lower()
                ):
                    person["first"] = _titlecase(str(value))
                    break

    if not slots.get("date"):
        slots["date"] = _today()
    if slots.get("time"):
        slots["time"] = _to_12h(slots["time"])
    last_three = slots.get("incident_number_last3") or answers.get(
        "incident_number_last3"
    )
    if last_three and not slots.get("incident_number"):
        slots["incident_number"] = _build_incident_number(
            last_three, incident_date=slots.get("date")
        )
    if not slots.get("drug_test_disposition"):
        slots["drug_test_disposition"] = "N/A"
    charges = data.get("charges")
    if isinstance(charges, list) and charges:
        slots["charges"] = ", ".join(charges)
    if category in FIGHT_RH_CATEGORIES:
        destination = (slots.get("escort_destination") or "").strip()
        if not destination:
            slots["escort_destination"] = RESTRICTIVE_HOUSING
        elif "restrictive" not in destination.lower():
            slots["escort_destination"] = (
                f"Infirmary, then {RESTRICTIVE_HOUSING}"
                if "infirmary" in destination.lower()
                else RESTRICTIVE_HOUSING
            )

    gap_result = find_gaps(category, slots)
    auto_content = gap_result.get("auto_content", [])
    markers = list(gap_result.get("markers", []))
    for last in _inmates_missing_first(slots):
        markers.append(f"[TO BE SUPPLEMENTED: first name for Inmate {last}]")

    officers = security_staff(slots)
    reporter = None
    reporter_index = int(data.get("reporter_index", 0))
    if officers and reporter_index < len(officers):
        reporter = officers[reporter_index]
        slots = bind_reporter(slots, reporter)
    officer_name = answers.get("officer_name", "")
    if officer_name:
        name = str(officer_name).strip()
        rank = _parse_rank(name)
        if rank:
            name = name[len(rank) :].strip()
        if "," in name:
            last, first, _middle = _parse_name(name)
        else:
            parts = name.split()
            last, first = (parts[-1], parts[0]) if len(parts) > 1 else (parts[0], "")
        if last:
            slots["officer_last"] = last
        if first:
            slots["officer_first"] = first
        if rank:
            slots["rank"] = rank
    elif reporters := [
        person
        for person in slots.get("persons", [])
        if person.get("role") == "security_staff"
    ]:
        slots = bind_reporter(slots, reporters[0])
        reporter = reporters[0]

    if reporter and reporter.get("shift"):
        slots["shift_assignment"] = _format_shift(reporter["shift"])
    elif slots.get("shift_assignment"):
        slots["shift_assignment"] = _format_shift(slots["shift_assignment"])
    return {
        "notes": notes,
        "category": category,
        "slots": slots,
        "answers": answers,
        "auto_content": auto_content,
        "markers": markers,
        "officers": officers,
    }


def _finalize_generation(reports: dict, ctx: dict) -> dict:
    reports = dict(reports)
    generation_errors = reports.pop("_errors", [])
    reports, repaired = repair_all(reports)
    slots, category = ctx["slots"], ctx["category"]
    inmate_hurt = slots.get("medical_disposition") in MEDICAL_INJURY_DISPOSITIONS
    inmate_injury = MSF_REFERENCE if inmate_hurt else "N/A"
    officer_force = (
        category in OFFICER_FORCE_CATEGORIES
        or bool(slots.get("officer_injuries"))
        or str(slots.get("staff_injured", "")).lower() in ("yes", "true")
    )
    officer_injury = MSF_REFERENCE if officer_force else "N/A"
    form005 = {
        **designation_boxes(category),
        "unit_division": "BMU",
        "officer_last": slots.get("officer_last") or "",
        "officer_first": slots.get("officer_first") or "",
        "employee_number": slots.get("employee_number") or "",
        "rank": slots.get("rank") or "",
        "shift_assignment": slots.get("shift_assignment") or "",
        "date": slots.get("date") or "",
        "time": _to_form_time(slots.get("time")) or "",
        "location": slots.get("location") or "",
        "inmates_involved": _format_inmates(slots),
        "employees_involved": _format_employees(slots),
        "inmates_present": slots.get("inmates_present") or SEE_ABOVE,
        "employees_present": slots.get("employees_present") or SEE_ABOVE,
        "others_present": slots.get("others_present") or "N/A",
        "inmate_injuries": inmate_injury,
        "inmate_treatment": inmate_injury,
        "officer_injuries": officer_injury,
        "officer_treatment": officer_injury,
        "recommendation": reports.get("recommendation", ""),
        "narrative": reports.get("first_person", ""),
        "reporting_employee_signature": (
            f"{slots.get('officer_first', '')} {slots.get('officer_last', '')}".strip()
        ),
        "supervisor_signature": "",
    }
    all_text = " ".join(value for value in reports.values() if isinstance(value, str))
    derived = [slots.get("time"), slots.get("date"), slots.get("incident_number")]
    flags = invented_facts(all_text, ctx["notes"], ctx["answers"], allow=derived)
    style = summarize(
        validate_all(
            reports,
            officer={
                "rank": slots.get("rank"),
                "first": slots.get("officer_first"),
                "last": slots.get("officer_last"),
            },
            notes=ctx["notes"],
            auto_content=ctx["auto_content"],
            allow=derived,
            answers=ctx["answers"],
        )
    )
    return {
        "generation_errors": generation_errors,
        "reports": reports,
        "form005": form005,
        "flags": flags,
        "markers": ctx["markers"],
        "officers": ctx["officers"],
        "style": style,
        "repaired": repaired,
    }


def _generate_report_set(
    payload: dict,
    *,
    staff_provider: StaffProvider,
    generate_all=generate_all_reports,
    charges_present=has_charges,
) -> dict:
    context = _prepare_generation(payload, staff_provider)
    defer = bool(payload.get("defer_disciplinary"))
    reports = generate_all(
        context["slots"],
        context["category"],
        auto_content=context.get("auto_content"),
        include_disciplinary=not defer,
    )
    result = _finalize_generation(reports, context)
    result["disciplinary_deferred"] = bool(defer and charges_present(context["slots"]))
    return result


def generate_report_set(payload: dict, *, staff_provider: StaffProvider) -> dict:
    return _generate_report_set(
        payload,
        staff_provider=staff_provider,
        generate_all=generate_all_reports,
        charges_present=has_charges,
    )


def _generate_disciplinary_report(
    payload: dict,
    *,
    staff_provider: StaffProvider,
    generate_only=generate_disciplinary_only,
) -> dict:
    context = _prepare_generation(payload, staff_provider)
    prior = payload.get("reports") or {}
    reports = {
        key: value
        for key, value in prior.items()
        if key in RESUMABLE_REPORT_KEYS and isinstance(value, str)
    }
    reports.update(
        generate_only(
            context["slots"],
            reports.get("first_person", ""),
            context["auto_content"],
        )
    )
    result = _finalize_generation(reports, context)
    result["disciplinary_deferred"] = False
    return result


def generate_disciplinary_report(
    payload: dict, *, staff_provider: StaffProvider
) -> dict:
    return _generate_disciplinary_report(
        payload,
        staff_provider=staff_provider,
        generate_only=generate_disciplinary_only,
    )


__all__ = [
    "FileStaffProvider",
    "SqlStaffProvider",
    "StaffProvider",
    "classify_incident_notes",
    "extract_incident_notes",
    "generate_report_set",
    "generate_disciplinary_report",
]
