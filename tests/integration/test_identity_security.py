def test_browser_session_cookie_is_not_an_access_bearer(api_client, db_session):
    response = api_client.get(
        "/api/v1/me",
        headers={
            "Authorization": "Bearer fictional-browser-cookie-not-valid",
            "X-Client-Version": "1.0.0",
        },
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


def test_legacy_cookie_cannot_authenticate_access_api(api_client, db_session):
    api_client.set_cookie("access_code", "fictional-legacy-admin-code")
    response = api_client.get(
        "/api/v1/me",
        headers={"X-Client-Version": "1.0.0"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"
