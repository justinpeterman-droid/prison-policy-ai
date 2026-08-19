"""PostgreSQL browser contracts for incident-scoped reports and copy policy."""
from backend.persistence.models.reporting import ReportType
from tests.support.web_browser import authenticate_browser, browser_headers


def test_browser_report_list_edit_history_and_restore(
    db_session,
    db_session_factory,
    api_client,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    monkeypatch,
):
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.user,
    )

    listed = api_client.get(
        f"/api/web/v1/incidents/{fictional_incident.id}/reports",
        headers=browser_headers("request_web_report_list"),
    )
    assert listed.status_code == 200
    item = listed.get_json()["data"]["items"][0]
    assert item["report_id"] == str(fictional_report.id)
    assert item["presentation"] == "document"
    assert "download_word" in item["allowed_actions"]

    detail = api_client.get(
        f"/api/web/v1/reports/{fictional_report.id}",
        headers=browser_headers("request_web_report_detail"),
    )
    assert detail.status_code == 200
    assert detail.get_json()["data"]["content"]["narrative"].startswith(
        "Fictional initial"
    )

    saved = api_client.patch(
        f"/api/web/v1/reports/{fictional_report.id}",
        json={
            "content": {
                "narrative": "Fictional revised first-person narrative.",
                "editable_fields": {},
                "validation": {"reviewed": True},
                "warnings": [],
            },
            "base_revision_number": 1,
            "reason": "manual_save",
        },
        headers=browser_headers(
            "request_web_report_save",
            idempotency_key="web-report-save-0001",
            if_match=1,
        ),
    )
    assert saved.status_code == 200
    assert saved.get_json()["data"]["current_revision_number"] == 2

    revisions = api_client.get(
        f"/api/web/v1/reports/{fictional_report.id}/revisions",
        headers=browser_headers("request_web_report_revisions"),
    )
    assert revisions.status_code == 200
    assert [
        item["revision_number"]
        for item in revisions.get_json()["data"]["items"]
    ] == [1, 2]

    restored = api_client.post(
        f"/api/web/v1/reports/{fictional_report.id}/restore",
        json={"revision_number": 1},
        headers=browser_headers(
            "request_web_report_restore",
            idempotency_key="web-report-restore-0001",
        ),
    )
    assert restored.status_code == 200
    assert restored.get_json()["data"]["current_revision_number"] == 3
    assert restored.get_json()["data"]["content"]["narrative"].startswith(
        "Fictional initial"
    )


def test_copy_to_records_reports_never_expose_print_or_download(
    db_session,
    db_session_factory,
    api_client,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    monkeypatch,
):
    fictional_report.report_type = ReportType.SUPERVISOR_SUMMARY
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.user,
    )

    detail = api_client.get(
        f"/api/web/v1/reports/{fictional_report.id}",
        headers=browser_headers("request_web_copy_report_detail"),
    )
    assert detail.status_code == 200
    data = detail.get_json()["data"]
    assert data["presentation"] == "copy_text"
    assert data["allowed_actions"] == ["copy_text", "edit"]

    copied = api_client.post(
        "/api/web/v1/document-actions",
        json={
            "incident_id": str(fictional_incident.id),
            "incident_revision_number": fictional_incident.current_revision_number,
            "report_id": str(fictional_report.id),
            "action": "copy_text",
        },
        headers=browser_headers("request_web_copy_report_action"),
    )
    blocked = api_client.post(
        "/api/web/v1/document-actions",
        json={
            "incident_id": str(fictional_incident.id),
            "incident_revision_number": fictional_incident.current_revision_number,
            "report_id": str(fictional_report.id),
            "action": "print",
        },
        headers=browser_headers("request_web_copy_report_print"),
    )

    assert copied.status_code == 201
    assert copied.get_json()["data"]["action"] == "copy_text"
    assert blocked.status_code == 409
    assert blocked.get_json()["error"]["code"] == "action_not_allowed"


def test_unrelated_browser_actor_cannot_open_report(
    db_session,
    db_session_factory,
    api_client,
    fictional_report,
    fictional_staff_and_accounts,
    monkeypatch,
):
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_staff_and_accounts.unrelated,
    )

    response = api_client.get(
        f"/api/web/v1/reports/{fictional_report.id}",
        headers=browser_headers("request_web_report_unrelated"),
    )

    assert response.status_code == 404
