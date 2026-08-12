import yaml


def test_admin_openapi_has_exact_elevation_and_account_operations():
    with open("openapi/access-v1.yaml", encoding="utf-8") as source:
        document = yaml.safe_load(source)
    paths = document["paths"]
    assert set(paths) >= {
        "/api/v1/auth/admin-step-up", "/api/v1/admin/staff",
        "/api/v1/admin/staff/{staff_id}", "/api/v1/admin/accounts",
        "/api/v1/admin/accounts/{account_id}",
        "/api/v1/admin/accounts/{account_id}/reset-pin",
        "/api/v1/admin/accounts/{account_id}/unlock",
        "/api/v1/admin/accounts/{account_id}/sessions",
        "/api/v1/admin/accounts/{account_id}/revoke-sessions",
    }
    assert document["components"]["parameters"]["XAdminStepUp"]["name"] == "X-Admin-Step-Up"


def test_admin_bodies_and_one_time_values_are_closed_and_purpose_scoped():
    with open("openapi/access-v1.yaml", encoding="utf-8") as source:
        schemas = yaml.safe_load(source)["components"]["schemas"]
    assert schemas["AdminStepUpRequest"]["additionalProperties"] is False
    assert schemas["AdminStepUpRequest"]["properties"]["pin"]["writeOnly"] is True
    assert "admin_center" not in schemas["SensitiveAdminPurpose"]["enum"]
    assert schemas["TemporaryPinFirstData"]["properties"]["temporary_pin"]["writeOnly"] is True
    assert schemas["TemporaryPinFirstData"]["additionalProperties"] is False
    assert schemas["TemporaryPinReplayData"]["additionalProperties"] is False
    branches = schemas["RevokeSessionsRequest"]["oneOf"]
    assert all(branch["additionalProperties"] is False for branch in branches)
