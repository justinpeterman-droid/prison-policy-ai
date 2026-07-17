"""Report generation endpoint."""
from flask import Blueprint, render_template, request, jsonify
from backend.reports.classifier import classify_incident
from backend.reports.generator import generate_all_reports

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
