"""Report generation endpoint."""
from flask import Blueprint, render_template, request, jsonify, send_file
from backend.reports.classifier import classify_incident
from backend.reports.generator import generate_all_reports
from backend.reports.filler import fill_template
import tempfile

reports_bp = Blueprint("reports", __name__)


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
        # Step 1: Classify
        classification = classify_incident(notes)

        # Step 2: Generate all required reports
        reports = generate_all_reports(notes, classification)

        return jsonify({
            "incident_type": classification.get("incident_type"),
            "forms_required": classification.get("forms_required", []),
            "charges": classification.get("charges_applicable", []),
            "reports": reports,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/download", methods=["POST"])
def reports_download():
    """Generate + fill 005/409 form, return as DOC."""
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    if not notes:
        return jsonify({"error": "No field notes provided"}), 400

    try:
        classification = classify_incident(notes)
        reports = generate_all_reports(notes, classification)

        # Use first person report as narrative for the form
        narrative = reports.get("first_person", "")
        metadata = {
            "narrative": narrative,
            "incident_type": classification.get("incident_type", "general"),
            "charges": classification.get("charges_applicable", []),
        }

        output = fill_template(metadata)

        if output.get("text"):
            # Fallback: return text if no DOC
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500
