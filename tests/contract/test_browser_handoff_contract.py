from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _openapi():
    with (ROOT / "openapi" / "access-v1.yaml").open(encoding="utf-8") as source:
        return yaml.safe_load(source)


def test_openapi_defines_admin_issue_and_public_redeem_contracts():
    document = _openapi()
    paths = document["paths"]
    assert "/api/v1/admin/review-lab-handoffs" in paths
    assert "/api/browser-handoffs/redeem" in paths
    redeem = paths["/api/browser-handoffs/redeem"]["post"]
    assert redeem["security"] == []
    token = document["components"]["schemas"]["BrowserHandoffRedeemRequest"]["properties"]["token"]
    assert token["writeOnly"] is True


def test_fragment_landing_never_persists_or_exposes_handoff_token():
    script = (ROOT / "backend" / "webapp" / "static" / "js" / "access-handoff.js").read_text(encoding="utf-8")
    assert "window.location.hash" in script
    assert "history.replaceState" in script
    assert script.index("history.replaceState") < script.index("fetch(")
    assert "localStorage" not in script
    assert "sessionStorage" not in script
    assert "console." not in script
    assert "?token=" not in script


def test_landing_page_is_static_and_loads_only_the_handoff_script():
    page = (ROOT / "backend" / "webapp" / "templates" / "access_handoff.html").read_text(encoding="utf-8")
    assert "access-handoff.js" in page
    assert "{{ request" not in page
    assert "window.location" not in page
