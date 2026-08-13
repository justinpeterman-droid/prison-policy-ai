from backend.webapp import app as app_mod


EXPECTED_KEYS = {
    "release_version",
    "latest_client_version",
    "minimum_client_version",
    "minimum_server_version",
    "api_version",
    "release_notes",
    "read_only_required",
    "review_lab_origin",
    "field_notes_max_characters",
}


def configured_client(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://app:test@localhost/access_test"
    )
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("RELEASE_VERSION", "1.4.0")
    monkeypatch.setenv("LATEST_CLIENT_VERSION", "1.4.0")
    monkeypatch.setenv("MINIMUM_CLIENT_VERSION", "1.2.0")
    monkeypatch.setenv("MINIMUM_SERVER_VERSION", "1.2.0")
    monkeypatch.setenv("API_VERSION", "v1")
    monkeypatch.setenv("RELEASE_NOTES", "Fictional reviewed release.")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://review.example.gov")
    return app_mod.create_app().test_client()


def test_public_client_policy_has_exact_nine_safe_fields(monkeypatch):
    response = configured_client(monkeypatch).get("/api/v1/client-policy")
    assert response.status_code == 200
    policy = response.get_json()["data"]
    assert set(policy) == EXPECTED_KEYS
    assert policy["field_notes_max_characters"] == 30_000
    assert type(policy["field_notes_max_characters"]) is int


def test_public_client_policy_exposes_only_safe_origin(monkeypatch):
    policy = (
        configured_client(monkeypatch).get("/api/v1/client-policy").get_json()["data"]
    )
    assert policy["minimum_server_version"] == "1.2.0"
    assert policy["api_version"] == "v1"
    assert policy["review_lab_origin"] == "https://review.example.gov"
    assert "/access-handoff" not in policy["review_lab_origin"]
    assert "#" not in policy["review_lab_origin"]
    assert "?" not in policy["review_lab_origin"]
    for forbidden in ("package_url", "signer", "bucket", "token", "credential"):
        assert forbidden not in policy
