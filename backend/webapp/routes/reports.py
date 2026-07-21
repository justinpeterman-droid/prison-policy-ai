"""Report generation endpoints — v2 three-step pipeline."""
import logging
import re
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from backend.reports.classifier import classify_incident
from backend.reports.generator import generate_all_reports
from backend.reports.filler import fill_template

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)

# Per BMU practice, medical detail is not written onto the 005 — the injury
# and treatment lines reference the separate report. Inmate injuries point to
# the Infirmary Report; officer injuries point to the officer's Medical Report.
SEE_INFIRMARY = "See Infirmary Report"
SEE_MEDICAL = "See Medical Report"
# Present lines that aren't separately stated point back to the involved lists.
SEE_ABOVE = "See Above"
FIRST_NAME_NEEDED = "[FIRST NAME NEEDED]"

# Incidents that, by their nature, involve an inmate going to medical — the
# medical disposition pre-selects "Seen by Infirmary staff" (still changeable).
MEDICAL_SEEN_CATEGORIES = {
    "inmate_fight", "staff_assault", "forced_cell_movement", "prea",
}
# Medical dispositions that mean an inmate actually went to/was offered medical
# (so EXTENT OF INJURY TO INMATE reads "See Infirmary Report" rather than N/A).
MEDICAL_INJURY_DISPOSITIONS = {
    "Seen by Infirmary staff",
    "Refused medical (Refuse box checked)",
    "Sent by ambulance to outside facility",
}
# Categories/signals where the inmate used force on the officer, so the
# officer injury/treatment lines reference the officer's Medical Report.
OFFICER_FORCE_CATEGORIES = {"staff_assault"}
# Fights/assaults: the inmate is always ultimately placed in Restrictive
# Housing (after the infirmary if they were treated first).
FIGHT_RH_CATEGORIES = {"inmate_fight", "staff_assault"}
RESTRICTIVE_HOUSING = "Restrictive Housing"


def _titlecase(value):
    """Capitalize each word of a name so hand-typed 'john' becomes 'John'."""
    if not value:
        return value
    return " ".join(w[:1].upper() + w[1:] if w else w for w in str(value).split())


def _to_12h(value):
    """Normalize a time to 12-hour 'H:MMam/pm' (BMU convention).

    Accepts 24-hour ('2200', '22:00'), 12-hour ('10:00pm', '10:00 PM'), and a
    leading 'approximately'/'~'. Returns the bare 12-hour time (no
    'approximately' — the narrative prompt adds that). Unparseable input is
    returned unchanged so nothing is ever lost."""
    if not value:
        return value
    core = re.sub(r'^(approximately|approx\.?|~)\s*', '', str(value).strip(),
                  flags=re.I).strip()
    m = re.match(r'^(\d{1,2}):?(\d{2})\s*([ap])\.?\s*m\.?$', core, re.I)
    if m:  # already 12-hour, just canonicalize
        return f"{int(m.group(1))}:{m.group(2)}{m.group(3).lower()}m"
    m = re.match(r'^(\d{1,2}):?(\d{2})$', core)
    if m:  # 24-hour
        h, mm = int(m.group(1)), m.group(2)
        if 0 <= h <= 23:
            ap = 'am' if h < 12 else 'pm'
            return f"{h % 12 or 12}:{mm}{ap}"
    return value


def _format_shift(value):
    """Roster stores a single-letter shift code ('A'..'F'); reports write it as
    'A Shift'. Anything already spelled out is left as-is."""
    if not value:
        return value
    s = str(value).strip()
    if len(s) == 1 and s.isalpha():
        return f"{s.upper()} Shift"
    return s


def _apply_gap_defaults(category: str, gaps: list) -> None:
    """Pre-select sensible defaults on gap widgets so the officer confirms
    rather than fills. Defaults are suggestions only — every one stays
    editable, and none of them block generation."""
    for g in gaps:
        slot = g.get("slot")
        if slot == "medical_disposition":
            g["default"] = ("Seen by Infirmary staff"
                            if category in MEDICAL_SEEN_CATEGORIES
                            else "N/A - no injuries reported")
        elif slot == "drug_test_disposition":
            g["default"] = "N/A"
        elif slot == "escort_destination" and category in FIGHT_RH_CATEGORIES:
            # Fights end in Restrictive Housing (via the infirmary if treated).
            g["default"] = "Infirmary, then Restrictive Housing"


def _today() -> str:
    """Current date in the MM-DD-YYYY form officers use in the notes."""
    return datetime.now().strftime("%m-%d-%Y")


def _is_first_person_unnamed(notes: str, slots: dict) -> bool:
    """Detect notes that use first-person ('I'/'me') but no officer name extracted."""
    has_first_person = bool(re.search(r'\bI\b|\bme\b|\bmy\b', notes, re.I))
    last = slots.get("officer_last")
    first = slots.get("officer_first")
    unnamed = not last or not first or last == "None" or first == "None"
    return has_first_person and unnamed


def _build_incident_number(last3) -> str:
    """Compose YYYY-MM-### from the officer's 3-digit log number."""
    digits = "".join(ch for ch in str(last3 or "") if ch.isdigit())[-3:]
    return f"{datetime.now():%Y-%m}-{digits.zfill(3)}" if digits else ""


def _format_inmates(slots: dict) -> str:
    parts = []
    for p in slots.get("persons", []):
        if p.get("role") != "inmate" or not p.get("last"):
            continue
        first = _titlecase(p.get("first")) or FIRST_NAME_NEEDED
        parts.append(f"Inmate {_titlecase(p.get('last', ''))}, {first} "
                     f"ADC#{p.get('adc_number') or 'UNKNOWN'}")
    return ", ".join(parts)


def _inmates_missing_first(slots: dict) -> list:
    """Inmates named by last name but with no first name — each one needs a
    gap question, and if still blank at generation, a supplement marker."""
    return [p.get("last") for p in slots.get("persons", [])
            if p.get("role") == "inmate" and p.get("last") and not p.get("first")]


def _apply_first_name_answers(slots: dict, answers: dict) -> None:
    """Fold 'inmate_first::<Last>' gap answers back into the persons list."""
    for key, val in answers.items():
        if not (isinstance(key, str) and key.startswith("inmate_first::") and val):
            continue
        last = key.split("::", 1)[1]
        for p in slots.get("persons", []):
            if (p.get("role") == "inmate" and p.get("last") == last
                    and not p.get("first")):
                p["first"] = _titlecase(val)


def _format_employees(slots: dict) -> str:
    return ", ".join(
        f"{p.get('rank', '')} {_titlecase(p.get('first', ''))} "
        f"{_titlecase(p.get('last', ''))}".strip()
        for p in slots.get("persons", [])
        if p.get("role") == "security_staff" and p.get("last")
    )


def _find_person(classification: dict, role: str) -> dict:
    """Find first person with given role from classification."""
    for p in classification.get("persons_involved", []):
        if p.get("role") == role:
            return p
    return {}


def _parse_name(full_name: str) -> tuple[str, str, str]:
    """Parse 'Last, First' or 'Last, First Middle' into components."""
    if not full_name:
        return "", "", ""
    parts = full_name.split(",", 1)
    last = parts[0].strip()
    first = ""
    middle = ""
    if len(parts) > 1:
        given = parts[1].strip().split()
        first = given[0] if given else ""
        middle = " ".join(given[1:]) if len(given) > 1 else ""
    return last, first, middle


@reports_bp.route("/reports")
def reports_page():
    return render_template("reports.html")


# ── v2 three-step pipeline ──────────────────────────────────────

@reports_bp.route("/api/reports/classify", methods=["POST"])
def reports_classify():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "").strip()
    if not notes:
        return jsonify({"error": "No field notes provided"}), 400
    try:
        classification = classify_incident(notes)
        logger.info("Classify → %s, %d charges", classification.get("incident_type"),
                    len(classification.get("charges_applicable", [])))
        return jsonify({
            "incident_type": classification.get("incident_type"),
            "label": classification.get("label", ""),
            # AI-suggested charges from the disciplinary handbook — the officer
            # confirms/edits these; they are not applied until generate.
            "charges": classification.get("charges_applicable", []),
            "charge_descriptions": classification.get("charge_descriptions", {}),
        })
    except Exception as e:
        logger.exception("Classification failed")
        return jsonify({"error": "Classification failed", "detail": str(e)}), 500


@reports_bp.route("/api/reports/extract", methods=["POST"])
def reports_extract():
    from backend.reports.extraction import extract_slots
    from backend.reports.validate import find_gaps
    from backend.reports.schema import security_staff

    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "").strip()
    category = data.get("category", "").strip()
    if not notes or not category:
        return jsonify({"error": "notes and category required"}), 400
    try:
        slots = extract_slots(notes, category)

        # If the notes never stated a date, today's is safe — don't ask for it.
        if not slots.get("date"):
            slots["date"] = _today()
        # All reports use 12-hour time; convert whatever the notes stated.
        if slots.get("time"):
            slots["time"] = _to_12h(slots["time"])

        # ── Staff roster resolution ──
        from backend.reports.roster import resolve_staff_from_persons
        persons = slots.get("persons", [])
        roster_gaps = []
        if persons:
            resolved_persons, roster_gaps = resolve_staff_from_persons(persons)
            slots["persons"] = resolved_persons
            # Also fill officer_* slots from the first reporting officer match,
            # including the shift assignment (which comes from the roster).
            for p in resolved_persons:
                if p.get("role") == "security_staff" and p.get("_roster_match"):
                    slots.setdefault("officer_last", p.get("last", ""))
                    slots.setdefault("officer_first", p.get("first", ""))
                    slots.setdefault("rank", p.get("rank", ""))
                    slots.setdefault("employee_number", p.get("employee_number", ""))
                    if p.get("shift") and not slots.get("shift_assignment"):
                        slots["shift_assignment"] = _format_shift(p.get("shift"))
                    break

        # The involved lists come from the extracted persons — don't ask for
        # them again as a Missing-Information question.
        if not slots.get("inmates_involved") and any(
                p.get("role") == "inmate" and p.get("last")
                for p in slots.get("persons", [])):
            slots["inmates_involved"] = _format_inmates(slots)
        if not slots.get("employees_involved") and any(
                p.get("role") == "security_staff" and p.get("last")
                for p in slots.get("persons", [])):
            slots["employees_involved"] = _format_employees(slots)

        gap_result = find_gaps(category, slots)
        gaps = gap_result.get("gaps", [])
        # Merge roster gaps
        if roster_gaps:
            gaps = gaps + roster_gaps
        # Shift assignment comes from the unit roster — if it couldn't be
        # resolved, ask for it (non-blocking, like the other checklist items).
        if not slots.get("shift_assignment"):
            gaps.append({"slot": "shift_assignment", "blocking": False,
                         "answer_type": "text",
                         "question": "Shift assignment? (from the unit roster)"})
        # Notes use first-person ("I"/"me") but no officer name was extracted —
        # must ask who the reporting officer is before generating.
        if _is_first_person_unnamed(notes, slots):
            gaps.insert(0, {"slot": "officer_name", "blocking": True,
                            "answer_type": "text",
                            "question": "Who is the reporting officer? "
                                        "(name not found in the notes)"})
        # An inmate named only by last name needs a first name — ask per inmate.
        for last in _inmates_missing_first(slots):
            gaps.append({"slot": f"inmate_first::{last}", "blocking": False,
                         "answer_type": "text",
                         "question": f"First name for Inmate {last}? "
                                     f"(leave blank if unknown)"})
        gap_result["gaps"] = gaps
        gap_result["blocking_remaining"] = sum(1 for g in gaps if g.get("blocking"))
        # Pre-select suggested defaults (medical disposition, drug test).
        _apply_gap_defaults(category, gaps)
        officers = security_staff(slots)
        logger.info("Extract → %d gaps (%d blocking), %d officers",
                    len(gap_result.get("gaps", [])),
                    gap_result.get("blocking_remaining", 0),
                    len(officers))
        return jsonify({
            "slots": slots,
            "gaps": gap_result.get("gaps", []),
            "blocking_remaining": gap_result.get("blocking_remaining", 0),
            "markers": gap_result.get("markers", []),
            "checklist": gap_result.get("checklist", []),
            "auto_content": gap_result.get("auto_content", []),
            "officers": officers,
        })
    except Exception as e:
        logger.exception("Extraction failed")
        return jsonify({"error": "Extraction failed", "detail": str(e)}), 500


@reports_bp.route("/api/reports/generate", methods=["POST"])
def reports_generate():
    from backend.reports.schema import bind_reporter, security_staff
    from backend.reports.validate import find_gaps, invented_facts

    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "").strip()
    category = data.get("category", "").strip()
    slots = data.get("slots", {})
    answers = data.get("answers", {})
    charges = data.get("charges")  # officer-confirmed charge codes (list)
    reporter_index = int(data.get("reporter_index", 0))

    if not notes or not category:
        return jsonify({"error": "notes and category required"}), 400
    try:
        # Merge gap answers into slots
        slots = dict(slots)
        slots.update(answers)
        # Fold any first-name answers back into the inmate records.
        _apply_first_name_answers(slots, answers)

        # ── Deterministic BMU defaults (before auto_content resolves) ──
        # Date: if the notes never stated one, today's date is safe to use.
        if not slots.get("date"):
            slots["date"] = _today()
        # All reports use 12-hour time.
        if slots.get("time"):
            slots["time"] = _to_12h(slots["time"])
        # Incident number: officer supplies only the last 3 digits; the
        # year and month are prefixed automatically.
        last3 = slots.get("incident_number_last3") or answers.get("incident_number_last3")
        if last3 and not slots.get("incident_number"):
            slots["incident_number"] = _build_incident_number(last3)
        # Inmate drug test defaults to N/A unless the officer chose otherwise.
        if not slots.get("drug_test_disposition"):
            slots["drug_test_disposition"] = "N/A"
        # Officer-confirmed charges win over anything extracted.
        if isinstance(charges, list) and charges:
            slots["charges"] = ", ".join(charges)

        # Fights/assaults always end in Restrictive Housing — after the
        # infirmary if the inmate was treated first.
        if category in FIGHT_RH_CATEGORIES:
            dest = (slots.get("escort_destination") or "").strip()
            if not dest:
                slots["escort_destination"] = RESTRICTIVE_HOUSING
            elif "restrictive" not in dest.lower():
                slots["escort_destination"] = (
                    f"Infirmary, then {RESTRICTIVE_HOUSING}"
                    if "infirmary" in dest.lower() else RESTRICTIVE_HOUSING)

        # Re-resolve auto_content with answered slots
        gap_result = find_gaps(category, slots)
        auto_content = gap_result.get("auto_content", [])
        markers = list(gap_result.get("markers", []))
        # Any inmate still missing a first name at generation is flagged so the
        # officer's attention is drawn to it on the "Review before filing" card.
        for last in _inmates_missing_first(slots):
            markers.append(f"[TO BE SUPPLEMENTED: first name for Inmate {last}]")

        # Bind reporter
        officers = security_staff(slots)
        reporter = None
        if officers and reporter_index < len(officers):
            reporter = officers[reporter_index]
            slots = bind_reporter(slots, reporter)
        elif reporters := [p for p in slots.get("persons", [])
                          if p.get("role") == "security_staff"]:
            reporter = reporters[0]
            slots = bind_reporter(slots, reporter)

        # Sanitize null/None officer names — only when ALL fields are null.
        # Don't touch slots that already have real data or partial data.
        officer_last = slots.get("officer_last")
        officer_first = slots.get("officer_first")
        null_last = not officer_last or str(officer_last).lower() in ("none", "[not in notes]")
        null_first = not officer_first or str(officer_first).lower() in ("none", "[not in notes]")
        if null_last or null_first:
            if not null_last:
                # Have last name but no first — leave as-is, gap asks for first
                pass
            elif not null_first:
                # Have first name but no last — odd case, leave as-is
                pass
            else:
                # Both null — leave as-is. The gap question asks for the name.
                # Reports won't generate with [NOT IN NOTES] officer names.
                pass

        # Shift assignment: use the bound officer's roster shift (a letter like
        # 'B') rendered as 'B Shift', else normalize whatever was answered.
        if reporter and reporter.get("shift"):
            slots["shift_assignment"] = _format_shift(reporter["shift"])
        elif slots.get("shift_assignment"):
            slots["shift_assignment"] = _format_shift(slots["shift_assignment"])

        reports = generate_all_reports(slots, category, auto_content=auto_content)

        # ── 005 injury / present line logic (deterministic) ──
        # Inmate injury/treatment can only read "See Infirmary Report" or "N/A".
        inmate_hurt = slots.get("medical_disposition") in MEDICAL_INJURY_DISPOSITIONS
        inmate_injury_line = SEE_INFIRMARY if inmate_hurt else "N/A"
        # Officer injury/treatment reads "See Medical Report" only when the
        # inmate used force on the officer; otherwise N/A.
        officer_force = (category in OFFICER_FORCE_CATEGORIES
                         or bool(slots.get("officer_injuries"))
                         or str(slots.get("staff_injured", "")).lower()
                         in ("yes", "true"))
        officer_injury_line = SEE_MEDICAL if officer_force else "N/A"

        form005 = {
            "unit_division": "BMU",
            "officer_last": slots.get("officer_last") or "",
            "officer_first": slots.get("officer_first") or "",
            "employee_number": slots.get("employee_number") or "",
            "rank": slots.get("rank") or "",
            "shift_assignment": slots.get("shift_assignment") or "",
            "date": slots.get("date") or "",
            "time": slots.get("time") or "",
            "location": slots.get("location") or "",
            "inmates_involved": _format_inmates(slots),
            "employees_involved": _format_employees(slots),
            # Present lines default to "See Above" (the involved lists) unless
            # the notes named separate people who were present.
            "inmates_present": slots.get("inmates_present") or SEE_ABOVE,
            "employees_present": slots.get("employees_present") or SEE_ABOVE,
            "others_present": slots.get("others_present") or SEE_ABOVE,
            # Medical detail lives in the infirmary/medical report, not the 005.
            "inmate_injuries": inmate_injury_line,
            "inmate_treatment": inmate_injury_line,
            "officer_injuries": officer_injury_line,
            "officer_treatment": officer_injury_line,
            "recommendation": reports.get("recommendation", ""),
            "narrative": reports.get("first_person", ""),
            "reporting_employee_signature": f"{slots.get('officer_first', '')} {slots.get('officer_last', '')}".strip(),
            "supervisor_signature": "",
        }

        all_text = " ".join(v for v in reports.values() if isinstance(v, str))
        flags = invented_facts(all_text, notes, answers)

        logger.info("Generate → %d reports, %d invented-fact flags, %d markers",
                    len(reports), len(flags), len(markers))
        return jsonify({
            "reports": reports,
            "form005": form005,
            "flags": flags,
            "markers": markers,
            "officers": officers,
        })
    except Exception as e:
        logger.exception("Report generation failed")
        return jsonify({"error": "Report generation failed", "detail": str(e)}), 500


@reports_bp.route("/api/reports", methods=["POST"])
def reports_api():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "").strip()
    if not notes:
        return jsonify({"error": "No field notes provided"}), 400

    logger.info("Report generation requested — notes length: %d chars", len(notes))

    try:
        classification = classify_incident(notes)
        logger.info("Classification complete — type: %s, charges: %d",
                     classification.get("incident_type"),
                     len(classification.get("charges_applicable", [])))

        reports = generate_all_reports(notes, classification)

        # Extract officer info for preview
        officer = _find_person(classification, "reporting_officer")
        last, first, middle = _parse_name(officer.get("name", ""))

        # Extract inmates
        inmates = [
            p for p in classification.get("persons_involved", [])
            if p.get("role") == "inmate"
        ]
        inmate_names = ", ".join(i.get("name", "") for i in inmates)

        return jsonify({
            "incident_type": classification.get("incident_type"),
            "label": classification.get("label", classification.get("incident_type", "")),
            "forms_required": classification.get("forms_required", []),
            "charges": classification.get("charges_applicable", []),
            "charge_descriptions": classification.get("charge_descriptions", {}),
            "persons": classification.get("persons_involved", []),
            # Flattened metadata for UI preview
            "metadata": {
                "officer_last": last,
                "officer_first": first,
                "employee_number": officer.get("employee_number", ""),
                "rank": officer.get("rank", ""),
                "facility": classification.get("facility", ""),
                "shift": classification.get("shift", ""),
                "location": classification.get("location", ""),
                "date": classification.get("date", ""),
                "time": classification.get("time", ""),
                "inmates_involved": inmate_names,
            },
            "reports": reports,
        })
    except Exception as e:
        logger.exception("Report generation failed")
        return jsonify({"error": "Report generation failed", "detail": str(e)}), 500


def _send_filled(metadata: dict):
    """Fill the 005 template and return it as a DOCX (or text fallback)."""
    output = fill_template(metadata)

    if output.get("text"):
        return jsonify({
            "format": "text",
            "content": output["text"],
            "message": "DOC template not available — text report returned"
        })

    return send_file(
        output["path"],
        as_attachment=True,
        download_name="Incident_Report_Form.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@reports_bp.route("/api/reports/download", methods=["POST"])
def reports_download():
    """Fill the incident report form and return it as DOCX.

    Preferred path: the client sends `metadata` — the already-generated
    (and possibly officer-corrected) field values + narrative — so the
    document matches exactly what was reviewed on screen, with no second
    LLM pass. Legacy path: raw `notes` re-runs the full pipeline.
    """
    data = request.get_json(silent=True) or {}

    metadata = data.get("metadata")
    if isinstance(metadata, dict) and metadata:
        metadata = {k: str(v) for k, v in metadata.items() if isinstance(k, str)}
        logger.info("Document download from reviewed metadata — %d fields", len(metadata))
        try:
            return _send_filled(metadata)
        except Exception as e:
            logger.exception("Document fill failed")
            return jsonify({"error": "Document generation failed", "detail": str(e)}), 500

    notes = data.get("notes", "").strip()
    if not notes:
        return jsonify({"error": "No field notes provided"}), 400

    logger.info("Document download requested — notes length: %d chars", len(notes))

    try:
        classification = classify_incident(notes)
        reports = generate_all_reports(notes, classification)

        narrative = reports.get("first_person", "")
        officer = _find_person(classification, "reporting_officer")
        last, first, middle = _parse_name(officer.get("name", ""))

        inmates = [
            p for p in classification.get("persons_involved", [])
            if p.get("role") == "inmate"
        ]
        inmate_names = ", ".join(i.get("name", "") for i in inmates)

        metadata = {
            "officer_last": last,
            "officer_first": first,
            "employee_number": officer.get("employee_number", ""),
            "rank": officer.get("rank", ""),
            "unit_division": classification.get("facility", ""),
            "shift_assignment": classification.get("shift", ""),
            "date": classification.get("date", ""),
            "time": classification.get("time", ""),
            "location": classification.get("location", ""),
            "inmates_involved": inmate_names,
            "narrative": narrative,
            "officer_signature": f"{first} {last}".strip(),
        }

        return _send_filled(metadata)
    except Exception as e:
        logger.exception("Document download failed")
        return jsonify({"error": "Document generation failed", "detail": str(e)}), 500
