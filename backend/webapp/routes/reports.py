"""Report generation endpoints — v2 three-step pipeline."""
import logging
from flask import Blueprint, render_template, request, jsonify, send_file
from backend.reports.classifier import classify_incident
from backend.reports.generator import generate_all_reports
from backend.reports.filler import fill_template

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)


def _format_inmates(slots: dict) -> str:
    return ", ".join(
        f"Inmate {p.get('last', '')}, {p.get('first', '')} ADC#{p.get('adc_number', 'UNKNOWN')}"
        for p in slots.get("persons", [])
        if p.get("role") == "inmate" and p.get("last")
    )


def _format_employees(slots: dict) -> str:
    return ", ".join(
        f"{p.get('rank', '')} {p.get('first', '')} {p.get('last', '')}".strip()
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
        logger.info("Classify → %s", classification.get("incident_type"))
        return jsonify({
            "incident_type": classification.get("incident_type"),
            "label": classification.get("label", ""),
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
        gap_result = find_gaps(category, slots)
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
    reporter_index = int(data.get("reporter_index", 0))

    if not notes or not category:
        return jsonify({"error": "notes and category required"}), 400
    try:
        # Merge gap answers into slots
        slots = dict(slots)
        slots.update(answers)

        # Re-resolve auto_content with answered slots
        gap_result = find_gaps(category, slots)
        auto_content = gap_result.get("auto_content", [])

        # Bind reporter
        officers = security_staff(slots)
        if officers and reporter_index < len(officers):
            slots = bind_reporter(slots, officers[reporter_index])
        elif reporters := [p for p in slots.get("persons", [])
                          if p.get("role") == "security_staff"]:
            slots = bind_reporter(slots, reporters[0])

        reports = generate_all_reports(slots, category, auto_content=auto_content)

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
            "inmate_injuries": slots.get("inmate_injuries") or "",
            "officer_injuries": slots.get("officer_injuries") or "",
        }

        all_text = " ".join(v for v in reports.values() if isinstance(v, str))
        flags = invented_facts(all_text, notes, answers)

        logger.info("Generate → %d reports, %d invented-fact flags", len(reports), len(flags))
        return jsonify({
            "reports": reports,
            "form005": form005,
            "flags": flags,
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
