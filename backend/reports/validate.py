"""Deterministic validation — the rule loop. No AI anywhere in this file.

Takes the extraction JSON + confirmed category, returns:
  * gaps      — questions to render on the Missing Information screen
                (question text, answer_type, options, blocking flag — all
                 read verbatim from incident_checklist_v2.json)
  * checklist — every form for the category with its checked/unchecked state
  * auto_content — resolved template sentences code must insert per report
  * markers   — [TO BE SUPPLEMENTED: ...] entries for anything answered UNKNOWN
"""
import json
import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
CHECKLIST_PATH = TEMPLATES_DIR / "incident_checklist_v2.json"

UNKNOWN = "UNKNOWN"
OTHER_OPTION = "Other (type your own)"


def load_checklist() -> dict:
    return json.loads(CHECKLIST_PATH.read_text())


def _get_category(checklist: dict, name: str) -> dict:
    for cat in checklist["categories"]:
        if cat["name"] == name:
            return cat
    raise KeyError(f"Unknown incident category: {name}")


def _condition_met(cond: str, slots: dict) -> bool:
    """Evaluate the tiny condition language used in the checklist file.
    Supports: always | <slot> == true/false | <slot> == 'Value' | <slot> != null
    """
    cond = cond.strip()
    if cond == "always":
        return True
    m = re.match(r"^(\w+)\s*(==|!=)\s*(.+)$", cond)
    if not m:
        return False
    slot, op, raw = m.groups()
    val = slots.get(slot)
    raw = raw.strip()
    if raw == "null":
        target = None
    elif raw in ("true", "false"):
        target = (raw == "true")
        val = bool(val) if isinstance(val, bool) else (
            str(val).lower() in ("yes", "true", "1") if val is not None else None)
    else:
        target = raw.strip("'\"")
    return (val == target) if op == "==" else (val != target)


def _options_for(rule: dict, checklist: dict) -> list[str] | None:
    if rule.get("answer_type") != "choice":
        return None
    opts = rule.get("options") or checklist["shared_option_sets"].get(
        rule.get("options_ref", ""), [])
    return list(opts) + [OTHER_OPTION]


def _active_rules(category: dict, checklist: dict, slots: dict) -> list[dict]:
    rules = checklist.get("universal_rules", []) + category.get("rules", [])
    return [r for r in rules if _condition_met(r.get("if", "always"), slots)]


def find_gaps(category_name: str, slots: dict) -> dict:
    """The core loop. A slot needs asking when it is null (never answered).
    UNKNOWN is an answer — it stops the asking and becomes a marker instead.
    """
    checklist = load_checklist()
    category = _get_category(checklist, category_name)

    gaps, markers = [], []

    # required_slots without a dedicated rule get a plain text question
    for slot in category.get("required_slots", []):
        val = slots.get(slot)
        if val is None and not any(r["require"] == slot
                                   for r in category.get("rules", [])):
            gaps.append({"slot": slot, "blocking": True, "answer_type": "text",
                         "question": slot.replace("_", " ").capitalize() + "?"})
        elif val == UNKNOWN:
            markers.append(slot)

    for rule in _active_rules(category, checklist, slots):
        slot = rule["require"]
        val = slots.get(slot)
        if val is None:
            gaps.append({
                "slot": slot,
                "blocking": rule.get("blocking", True),
                "answer_type": rule.get("answer_type", "text"),
                "question": rule["question"],
                "options": _options_for(rule, checklist),
            })
        elif val == UNKNOWN:
            markers.append(slot)

    return {
        "gaps": gaps,
        "blocking_remaining": sum(1 for g in gaps if g["blocking"]),
        "markers": [f"[TO BE SUPPLEMENTED: {m.replace('_', ' ')}]"
                    for m in markers],
        "checklist": _checklist_state(category, slots),
        "auto_content": _resolve_auto_content(category, slots),
    }


def _checklist_state(category: dict, slots: dict) -> list[dict]:
    """Checked/unchecked box per required form. Yes/no answers drive the box;
    'No' never blocks — it just stays unchecked (per BMU practice)."""
    yes = {r["require"] for r in category.get("rules", [])
           if r.get("answer_type") == "yes_no"
           and str(slots.get(r["require"], "")).lower() in ("yes", "true")}
    form_slot = {
        "witness_statements": "witness_statements_collected",
        "enemy_alert_form": "enemy_alert_filed",
        "photo_video": "photo_video_obtained",
        "confiscation_f401": "confiscation_form_completed",
        "officer_accident_report": "officer_accident_report_completed",
        "accident_report_form": "accident_report_completed",
        "prea_checklist": "prea_checklist_completed",
    }
    out = []
    for form in category["forms_required"]:
        slot = next((s for f, s in form_slot.items() if f in form), None)
        out.append({"form": form,
                    "checked": slot in yes if slot else None})
    return out


def _resolve_auto_content(category: dict, slots: dict) -> list[dict]:
    """Fill each auto_content template whose condition is met. Unfilled
    placeholders render as visible [NEEDED: ...] markers — never dropped."""
    resolved = []
    for item in category.get("auto_content", []):
        if not _condition_met(item.get("condition", "always"), slots):
            continue
        text = re.sub(
            r"\{(\w+)\}",
            lambda m: str(slots.get(m.group(1))
                          if slots.get(m.group(1)) not in (None, UNKNOWN)
                          else f"[NEEDED: {m.group(1).replace('_', ' ')}]"),
            item["template"])
        resolved.append({"id": item["id"],
                         "insert_into": item["insert_into"],
                         "text": text})
    return resolved


def invented_facts(output_text: str, notes: str, answers: dict) -> list[str]:
    """Hard check: every ADC#, time, and date in generated text must appear in
    the officer's input (notes or gap answers). Returns suspicious tokens."""
    source = (notes + " " + " ".join(str(v) for v in answers.values())).lower()
    tokens = set(re.findall(r"ADC#\s?\d+|\d{1,2}[:/-]\d{2}(?:[/-]\d{2,4})?(?:\s?[ap]\.?m\.?)?",
                            output_text, re.I))
    return [t for t in tokens
            if re.sub(r"\s", "", t.lower()) not in re.sub(r"\s", "", source)]
