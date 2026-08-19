from pathlib import Path

import yaml


SPEC = Path("openapi/web-v1.yaml")
AUTH_PATHS = {
    "/auth/session",
    "/auth/login",
    "/auth/renew",
    "/auth/logout",
}


def _spec():
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def test_web_openapi_preserves_closed_authentication_surface():
    document = _spec()

    assert document["openapi"] == "3.1.0"
    assert AUTH_PATHS <= set(document["paths"])
    login = document["components"]["schemas"]["LoginRequest"]
    assert login["additionalProperties"] is False
    assert set(login["required"]) == {"employee_number", "pin", "persistent"}
    assert set(login["properties"]) == {"employee_number", "pin", "persistent"}


def test_web_session_responses_never_define_readable_identity_credentials():
    text = SPEC.read_text(encoding="utf-8").lower()
    profile = _spec()["components"]["schemas"]["SessionProfile"]["properties"]

    assert "access_token" not in text
    assert "renewal_token" not in text
    assert "pin_hash" not in text
    assert "csrf_token" not in profile
    assert "access_token" not in profile
    assert "renewal_token" not in profile


def test_web_security_scheme_is_an_opaque_cookie():
    scheme = _spec()["components"]["securitySchemes"]["BrowserSession"]

    assert scheme == {
        "type": "apiKey",
        "in": "cookie",
        "name": "slut_web_access",
    }
