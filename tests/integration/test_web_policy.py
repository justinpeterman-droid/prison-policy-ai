from sqlalchemy import select

from backend.persistence.models.security import AuditEvent
from backend.webapp.web_api import policy as web_policy
from tests.support.web_browser import authenticate_browser, browser_headers


def _answer(_question, history=None, **_kwargs):
    assert history is None
    return {
        "answer": "Fictional policy requires documented supervisory review [1].",
        "citations": [
            {
                "n": 1,
                "source": "Fictional Operations Policy",
                "text": "A supervisory review is documented before closure.",
            }
        ],
    }


def test_policy_expert_returns_citations_without_persisting_question_or_answer(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=fictional_owner_tokens.session_id,
        device_id="device-fictional-owner-0001",
    )
    monkeypatch.setattr(web_policy, "answer_question", _answer)

    response = api_client.post(
        "/api/web/v1/policy/questions",
        json={"question": "What fictional supervisory review is required?"},
        headers=browser_headers("request_policy_question_0001"),
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert data["answer"] == "Fictional policy requires documented supervisory review [1]."
    assert data["citations"] == [{
        "title": "Fictional Operations Policy",
        "excerpt": "A supervisory review is documented before closure.",
        "location": "Source passage 1",
    }]
    assert "field_notes" not in repr(data)
    assert "incident_id" not in repr(data)

    with db_session_factory() as session:
        event = session.scalar(select(AuditEvent).where(
            AuditEvent.action == "policy.question_answered",
            AuditEvent.actor_account_id == account.id,
        ))
        assert event is not None
        assert event.details["document_count"] == 1
        assert isinstance(event.details["latency_ms"], int)
        serialized = repr(event.details)
        assert "supervisory review" not in serialized.lower()
        assert "Fictional Operations Policy" not in serialized


def test_policy_expert_fails_closed_when_sources_are_missing(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=fictional_owner_tokens.session_id,
        device_id="device-fictional-owner-0001",
    )
    monkeypatch.setattr(
        web_policy,
        "answer_question",
        lambda *_args, **_kwargs: {
            "answer": "No approved source passage was available.",
            "citations": [],
        },
    )

    response = api_client.post(
        "/api/web/v1/policy/questions",
        json={"question": "What does the policy say?"},
        headers=browser_headers("request_policy_question_no_sources"),
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "policy_sources_unavailable"
    assert response.get_json()["error"]["retryable"] is False


def test_policy_expert_rejects_cross_site_or_extra_fields_before_provider_use(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=fictional_owner_tokens.session_id,
        device_id="device-fictional-owner-0001",
    )
    provider = monkeypatch.setattr(web_policy, "answer_question", _answer)
    del provider

    extra = api_client.post(
        "/api/web/v1/policy/questions",
        json={"question": "Fictional question?", "incident_id": "forbidden"},
        headers=browser_headers("request_policy_question_extra"),
    )
    assert extra.status_code == 400
    assert extra.get_json()["error"]["code"] == "validation_failed"

    headers = browser_headers("request_policy_question_cross_site")
    headers["Origin"] = "https://attacker.invalid"
    headers["Sec-Fetch-Site"] = "cross-site"
    cross_site = api_client.post(
        "/api/web/v1/policy/questions",
        json={"question": "Fictional question?"},
        headers=headers,
    )
    assert cross_site.status_code == 403
    assert cross_site.get_json()["error"]["code"] == "csrf_validation_failed"
