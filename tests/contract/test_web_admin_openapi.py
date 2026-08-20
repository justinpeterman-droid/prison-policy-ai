from pathlib import Path

import yaml


SPEC = Path("openapi/web-v1.yaml")
ADMIN_PATHS = {
    "/admin/elevation",
    "/admin/step-up",
    "/admin/overview",
    "/admin/incidents",
    "/admin/incidents/{incident_id}",
    "/admin/incidents/{incident_id}/records-status",
    "/admin/incidents/{incident_id}/restore",
    "/admin/reports/{report_id}/transfer",
    "/admin/staff",
    "/admin/staff/{staff_id}",
    "/admin/accounts",
    "/admin/accounts/{account_id}",
    "/admin/accounts/{account_id}/reset-pin",
    "/admin/accounts/{account_id}/unlock",
    "/admin/accounts/{account_id}/sessions",
    "/admin/accounts/{account_id}/revoke-sessions",
    "/admin/audit",
    "/admin/audit/{event_id}",
    "/admin/health",
    "/admin/review-lab-handoffs",
}


def _spec():
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def test_web_openapi_publishes_closed_admin_surface():
    document = _spec()
    assert ADMIN_PATHS <= set(document["paths"])

    elevation = document["components"]["schemas"]["AdminElevationRequest"]
    assert elevation["additionalProperties"] is False
    assert set(elevation["required"]) == {"pin"}
    assert set(elevation["properties"]) == {"pin"}

    step_up = document["components"]["schemas"]["AdminStepUpRequest"]
    assert step_up["additionalProperties"] is False
    assert set(step_up["required"]) == {"pin", "purpose"}
    assert set(step_up["properties"]) == {"pin", "purpose"}


def test_admin_openapi_never_defines_readable_step_up_credentials():
    text = SPEC.read_text(encoding="utf-8").lower()
    assert "step_up_token" not in text
    assert "admin_step_up_cookie" not in text
    assert "pin_hash" not in text
