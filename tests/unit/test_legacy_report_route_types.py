from types import SimpleNamespace

from flask import Flask, jsonify

from backend.webapp.routes import reports as reports_route


CLASSIFICATION = {
    "incident_type": "fictional_incident",
    "label": "Fictional incident",
    "charges_applicable": [],
    "charge_descriptions": {},
    "persons_involved": [
        {
            "role": "reporting_officer",
            "name": "Example, Alex",
            "employee_number": "FICT-001",
            "rank": "Officer",
        }
    ],
}
EXTRACTION = {
    "slots": {
        "narrative_facts": ["A fictional event occurred."],
        "officer_first": "Alex",
        "officer_last": "Example",
    },
    "auto_content": [{"insert_into": ["first_person"], "text": "Fictional context."}],
}


def _client(monkeypatch):
    app = Flask(__name__)
    app.config["IDENTITY_SETTINGS"] = SimpleNamespace(enabled=False)
    app.register_blueprint(reports_route.reports_bp)
    monkeypatch.setattr(reports_route, "classify_incident", lambda _notes: dict(CLASSIFICATION))
    monkeypatch.setattr(
        reports_route.report_service,
        "extract_incident_notes",
        lambda _notes, _category, _provider: dict(EXTRACTION),
    )

    def generate(slots, category, auto_content):
        if (
            slots != EXTRACTION["slots"]
            or category != "fictional_incident"
            or auto_content != EXTRACTION["auto_content"]
        ):
            raise TypeError("legacy route did not honor the structured generator contract")
        return {"first_person": "I documented a fictional event."}

    monkeypatch.setattr(reports_route, "generate_all_reports", generate)
    return app.test_client()


def test_legacy_combined_route_adapts_notes_to_structured_generator_contract(monkeypatch):
    response = _client(monkeypatch).post("/api/reports", json={"notes": "Fictional field notes."})

    assert response.status_code == 200
    assert response.get_json()["reports"] == {"first_person": "I documented a fictional event."}


def test_legacy_download_route_adapts_notes_to_structured_generator_contract(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(reports_route, "_send_filled", lambda metadata: jsonify(metadata))

    response = client.post("/api/reports/download", json={"notes": "Fictional field notes."})

    assert response.status_code == 200
    assert response.get_json()["narrative"] == "I documented a fictional event."
