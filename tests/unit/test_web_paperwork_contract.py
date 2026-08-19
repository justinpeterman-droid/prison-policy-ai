from pathlib import Path

import yaml


REQUIRED_PATHS = {
    "/paperwork",
    "/paperwork/{paperwork_id}",
    "/paperwork/{paperwork_id}/revisions",
    "/paperwork/{paperwork_id}/revisions/{revision_number}",
    "/paperwork/{paperwork_id}/restore",
}


def test_browser_paperwork_route_is_registered():
    root = Path("backend/webapp/web_api")
    assert (root / "paperwork.py").is_file()
    registration = (root / "__init__.py").read_text(encoding="utf-8")
    assert "from backend.webapp.web_api.paperwork import paperwork_bp" in registration
    assert (
        'register_blueprint(paperwork_bp, url_prefix="/paperwork")'
        in registration
    )


def test_openapi_publishes_revisioned_paperwork_surface():
    document = yaml.safe_load(
        Path("openapi/web-v1.yaml").read_text(encoding="utf-8")
    )
    assert REQUIRED_PATHS <= set(document["paths"])
    schemas = document["components"]["schemas"]
    assert {
        "OperationalPaperwork",
        "OperationalPaperworkCreateRequest",
        "OperationalPaperworkSaveRequest",
        "OperationalPaperworkRevision",
    } <= set(schemas)


def test_paperwork_writes_require_browser_session_and_csrf_in_spec():
    document = yaml.safe_load(
        Path("openapi/web-v1.yaml").read_text(encoding="utf-8")
    )
    for path, method in (
        ("/paperwork", "post"),
        ("/paperwork/{paperwork_id}", "patch"),
        ("/paperwork/{paperwork_id}/restore", "post"),
    ):
        operation = document["paths"][path][method]
        parameters = operation.get("parameters", [])
        assert any(
            item.get("$ref") == "#/components/parameters/CsrfHeader"
            for item in parameters
        )
