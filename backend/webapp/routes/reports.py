"""Report generation endpoint."""
import tempfile
import os
import logging
from flask import Blueprint, render_template, request, jsonify, send_file
from backend.reports.classifier import classify_incident
from backend.reports.generator import generate_all_reports
from backend.reports.filler import fill_template

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)


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


@reports_bp.route("/api/reports", methods=["POST"])
def reports_api():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    if not notes:
        return jsonify({"error": "No field notes provided"}), 400

    try:
        classification = classify_incident(notes)
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
            "forms_required": classification.get("forms_required", []),
            "charges": classification.get("charges_applicable", []),
            "charge_descriptions": classification.get("charge_descriptions", {}),
            "persons": classification.get("persons_involved", []),
            # Flattened metadata for UI preview
            "metadata": {
                "officer_last": last,
                "officer_first": first,
                "officer_middle": middle,
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
    except Exception:
        logger.exception("Report generation failed")
        return jsonify({"error": "Report generation failed. Please try again."}), 500


@reports_bp.route("/api/reports/download", methods=["POST"])
def reports_download():
    """Generate + fill incident report form, return as DOCX."""
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    if not notes:
        return jsonify({"error": "No field notes provided"}), 400

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
            "officer_middle": middle,
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
    except Exception:
        logger.exception("Document download failed")
        return jsonify({"error": "Document generation failed. Please try again."}), 500
