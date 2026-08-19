"""PostgreSQL browser contracts for populated and physical incident paperwork."""
from datetime import date, time

from backend.reports.persistence import save_incident_record
from backend.webapp.api_v1.schemas.reporting import SaveIncidentRequest
from tests.support.web_browser import authenticate_browser, browser_headers


def _reviewed_incident(
    db_session,
    user_actor,
    incident,
    *,
    category: str,
    gap_answers: dict[str, str],
    extracted_facts: dict[str, object] | None = None,
):
    request = SaveIncidentRequest(
        incident_number="2026-08-029",
        incident_name="Fictional Barracks 4 Incident",
        incident_date=date(2026, 8, 19),
        incident_time=time(14, 30),
        facility="Fictional Unit",
        shift="A",
        location="Barracks 4",
        category=category,
        field_notes="Fictional reviewed incident notes.",
        classification={"category": category},
        extracted_facts=extracted_facts or {},
        gap_answers=gap_answers,
        charges=[],
        validation={"facts_reviewed": True},
        warnings=[],
        base_revision_number=incident.current_revision_number,
        reason="manual_save",
    )
    view = save_incident_record(
        db_session,
        user_actor,
        incident.id,
        request,
        f"fixture-reviewed-{category}",
        request_id=f"request_fixture_reviewed_{category}",
        client_version="1.0.0",
    )
    db_session.flush()
    return view


def test_digital_packet_populates_previews_edits_and_records_print(
    db_session,
    db_session_factory,
    api_client,
    fictional_reporting_incident,
    fictional_staff_and_accounts,
    user_actor,
    monkeypatch,
):
    reviewed = _reviewed_incident(
        db_session,
        user_actor,
        fictional_reporting_incident,
        category="incident_no_disciplinary",
        extracted_facts={
            "inmates_involved": "Fictional inmate TEST-0001",
            "inmate_injuries": "Minor fictional abrasion",
        },
        gap_answers={
            "medical_disposition": "Seen by Infirmary staff",
            "treatment_location": "Fictional Infirmary",
            "photo_video_obtained": "No",
            "drug_test_disposition": "N/A",
        },
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.user,
    )

    rebuilt = api_client.post(
        f"/api/web/v1/incidents/{reviewed.incident.id}/packet/rebuild",
        json={"incident_revision_number": reviewed.revision_number},
        headers=browser_headers("request_web_packet_rebuild"),
    )
    assert rebuilt.status_code == 200
    items = rebuilt.get_json()["data"]["items"]
    medical = next(
        item for item in items
        if item["template_code"] == "medical_documentation_checklist"
    )
    assert medical["presentation"] == "document"
    assert "print" in medical["allowed_actions"]

    populated = api_client.post(
        f"/api/web/v1/packet-items/{medical['packet_item_id']}/populate",
        json={"incident_revision_number": reviewed.revision_number},
        headers=browser_headers("request_web_form_populate"),
    )
    assert populated.status_code == 200
    form = populated.get_json()["data"]
    assert form["source_incident_revision_number"] == reviewed.revision_number
    assert form["populated_fields"]["incident_number"] == "2026-08-029"

    preview = api_client.get(
        f"/api/web/v1/form-instances/{form['form_instance_id']}/preview",
        headers=browser_headers("request_web_form_preview"),
    )
    assert preview.status_code == 200
    assert preview.get_json()["data"]["fields"]["location"] == "Barracks 4"

    saved = api_client.patch(
        f"/api/web/v1/form-instances/{form['form_instance_id']}",
        json={
            "manual_fields": {"treatment_location": "Fictional Infirmary"},
            "source_incident_revision_number": reviewed.revision_number,
        },
        headers=browser_headers("request_web_form_manual_save"),
    )
    assert saved.status_code == 200
    assert saved.get_json()["data"]["manual_fields"] == {
        "treatment_location": "Fictional Infirmary"
    }

    printed = api_client.post(
        "/api/web/v1/document-actions",
        json={
            "incident_id": str(reviewed.incident.id),
            "incident_revision_number": reviewed.revision_number,
            "packet_item_id": medical["packet_item_id"],
            "action": "print",
        },
        headers=browser_headers("request_web_form_print"),
    )
    assert printed.status_code == 201
    assert printed.get_json()["data"]["action"] == "print"


def test_physical_chain_of_custody_has_guidance_acknowledgment_and_no_print(
    db_session,
    db_session_factory,
    api_client,
    fictional_reporting_incident,
    fictional_staff_and_accounts,
    user_actor,
    monkeypatch,
):
    reviewed = _reviewed_incident(
        db_session,
        user_actor,
        fictional_reporting_incident,
        category="contraband",
        extracted_facts={"contraband_is_suspected_drugs": True},
        gap_answers={
            "medical_disposition": "N/A - no injuries reported",
            "photo_video_obtained": "No",
            "drug_test_disposition": "N/A",
            "evidence_description": "Fictional sealed evidence package",
            "recovery_location": "Fictional locker 4",
        },
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.user,
    )

    rebuilt = api_client.post(
        f"/api/web/v1/incidents/{reviewed.incident.id}/packet/rebuild",
        json={"incident_revision_number": reviewed.revision_number},
        headers=browser_headers("request_web_physical_rebuild"),
    )
    assert rebuilt.status_code == 200
    item = next(
        value for value in rebuilt.get_json()["data"]["items"]
        if value["template_code"] == "chain_of_custody_physical"
    )
    assert item["presentation"] == "physical"
    assert item["allowed_actions"] == []

    guidance = api_client.get(
        f"/api/web/v1/packet-items/{item['packet_item_id']}/physical",
        headers=browser_headers("request_web_physical_guidance"),
    )
    assert guidance.status_code == 200
    guidance_data = guidance.get_json()["data"]
    assert guidance_data["warning"] == "PHYSICAL CARBON-COPY FORM REQUIRED"
    assert "print" not in guidance_data["allowed_actions"]
    assert "download_word" not in guidance_data["allowed_actions"]

    acknowledged = api_client.post(
        f"/api/web/v1/packet-items/{item['packet_item_id']}/physical/acknowledgment",
        json={"note": "Fictional carbon-copy form completed by hand."},
        headers=browser_headers("request_web_physical_acknowledge"),
    )
    assert acknowledged.status_code == 200
    assert acknowledged.get_json()["data"]["packet_item_id"] == item["packet_item_id"]

    refreshed = api_client.get(
        f"/api/web/v1/packet-items/{item['packet_item_id']}/physical",
        headers=browser_headers("request_web_physical_refreshed"),
    )
    assert refreshed.get_json()["data"]["acknowledgment"] is not None

    cleared = api_client.delete(
        f"/api/web/v1/packet-items/{item['packet_item_id']}/physical/acknowledgment",
        headers=browser_headers("request_web_physical_clear"),
    )
    assert cleared.status_code == 200
    assert cleared.get_json()["data"] == {"cleared": True}
