from pathlib import Path

import yaml


SPEC = Path("openapi/web-v1.yaml")
AUTH_PATHS = {
    "/auth/session",
    "/auth/login",
    "/auth/renew",
    "/auth/logout",
}
PAPERWORK_PATHS = {
    "/paperwork",
    "/paperwork/count-sheets/structure",
    "/paperwork/count-sheets",
    "/paperwork/count-sheets/{record_id}",
    "/paperwork/count-sheets/{record_id}/revisions",
    "/paperwork/count-sheets/{record_id}/restore",
    "/paperwork/count-sheets/{record_id}/actions",
}
DAILY_PAPERWORK_PATHS = {
    "/admin/paperwork/daily",
    "/admin/paperwork/daily/{kind}",
    "/admin/paperwork/daily/{kind}/template",
    "/admin/paperwork/daily/{kind}/copy-previous",
    "/admin/paperwork/daily/{kind}/{record_id}",
    "/admin/paperwork/daily/{kind}/{record_id}/revisions",
    "/admin/paperwork/daily/{kind}/{record_id}/restore",
    "/admin/paperwork/daily/{kind}/{record_id}/actions",
    "/admin/paperwork/daily/assignment-roster/{record_id}/uniform-inspection",
}
PRINT_TEMPLATE_PATHS = {
    "/print-templates",
    "/print-templates/{template_code}",
    "/print-templates/packet",
    "/print-templates/actions",
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


def test_web_openapi_exposes_closed_revisioned_count_sheet_surface():
    document = _spec()

    assert PAPERWORK_PATHS <= set(document["paths"])
    request_schema = document["components"]["schemas"]["SaveCountSheetRequest"]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "schema_version",
        "work_date",
        "shift",
        "payload",
        "base_revision_number",
        "reason",
    }
    assert set(request_schema["properties"]) == set(request_schema["required"])
    action_schema = document["components"]["schemas"]["PaperworkActionRequest"]
    assert action_schema == {
        "type": "object",
        "additionalProperties": False,
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["preview", "print", "download_pdf"],
            }
        },
    }
    assert "delete" not in document["paths"][
        "/paperwork/count-sheets/{record_id}"
    ]


def test_web_openapi_exposes_closed_administrator_daily_paperwork_surface():
    document = _spec()

    assert DAILY_PAPERWORK_PATHS <= set(document["paths"])
    request_schema = document["components"]["schemas"]["SaveDailyPaperworkRequest"]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "schema_version",
        "work_date",
        "shift",
        "payload",
        "base_revision_number",
        "reason",
    }
    copy_schema = document["components"]["schemas"]["CopyPreviousDailyRequest"]
    assert copy_schema["additionalProperties"] is False
    assert set(copy_schema["required"]) == {"target_work_date", "shift"}


def test_web_openapi_exposes_read_only_print_template_library_surface():
    document = _spec()

    assert PRINT_TEMPLATE_PATHS <= set(document["paths"])
    packet = document["components"]["schemas"]["PrintTemplatePacketRequest"]
    assert packet["additionalProperties"] is False
    assert set(packet["required"]) == {"period", "template_codes", "prefill"}
    assert set(packet["properties"]) == set(packet["required"])


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
