"""PostgreSQL browser contracts for durable incident workflow jobs."""
from tests.support.web_browser import authenticate_browser, browser_headers


def test_browser_submits_and_reopens_durable_incident_job(
    db_session,
    db_session_factory,
    api_client,
    fictional_reporting_incident,
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

    submitted = api_client.post(
        f"/api/web/v1/incidents/{fictional_reporting_incident.id}/jobs/classify",
        json={
            "base_revision_number": fictional_reporting_incident.current_revision_number
        },
        headers=browser_headers(
            "request_web_job_submit",
            idempotency_key="web-job-submit-0001",
        ),
    )
    assert submitted.status_code == 202
    data = submitted.get_json()["data"]
    assert data["incident_id"] == str(fictional_reporting_incident.id)
    assert data["job_type"] == "classify"
    assert data["state"] == "queued"

    status = api_client.get(
        f"/api/web/v1/jobs/{data['job_id']}",
        headers=browser_headers("request_web_job_status"),
    )
    assert status.status_code == 200
    assert status.get_json()["data"]["job_id"] == data["job_id"]


def test_browser_rejects_unknown_job_type_without_creating_work(
    db_session,
    db_session_factory,
    api_client,
    fictional_reporting_incident,
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

    response = api_client.post(
        f"/api/web/v1/incidents/{fictional_reporting_incident.id}/jobs/invented",
        json={
            "base_revision_number": fictional_reporting_incident.current_revision_number
        },
        headers=browser_headers(
            "request_web_job_unknown",
            idempotency_key="web-job-unknown-0001",
        ),
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
