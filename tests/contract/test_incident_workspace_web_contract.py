"""Release contract for the remaining Guided Operations Incident Workspace."""
from pathlib import Path

import yaml


SPEC = Path("openapi/web-v1.yaml")


REQUIRED_PATHS = {
    "/staff",
    "/incidents",
    "/incidents/{incident_id}",
    "/incidents/{incident_id}/revisions",
    "/incidents/{incident_id}/revisions/{revision_number}",
    "/incidents/{incident_id}/restore",
    "/incidents/{incident_id}/reports",
    "/incidents/{incident_id}/jobs/{job_type}",
    "/jobs/{job_id}",
    "/reports/{report_id}",
    "/reports/{report_id}/revisions",
    "/reports/{report_id}/revisions/{revision_number}",
    "/reports/{report_id}/restore",
    "/reports/{report_id}/export-docx",
    "/incidents/{incident_id}/packet",
    "/incidents/{incident_id}/packet/rebuild",
    "/incidents/{incident_id}/packet/additional",
    "/packet-items/{packet_item_id}",
    "/packet-items/{packet_item_id}/populate",
    "/packet-items/{packet_item_id}/physical",
    "/packet-items/{packet_item_id}/physical/acknowledgment",
    "/form-instances/{form_instance_id}",
    "/form-instances/{form_instance_id}/preview",
    "/document-actions",
}

HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}


def test_openapi_exposes_the_complete_cookie_authenticated_incident_workspace():
    document = yaml.safe_load(SPEC.read_text(encoding="utf-8"))

    assert REQUIRED_PATHS <= set(document["paths"])
    for path in REQUIRED_PATHS:
        for method, operation in document["paths"][path].items():
            if method not in HTTP_METHODS:
                continue
            assert isinstance(operation, dict)
            assert "operationId" in operation


def test_browser_route_modules_exist_and_are_registered():
    root = Path("backend/webapp/web_api")
    for name in ("reports.py", "jobs.py", "forms.py", "staff.py"):
        assert (root / name).is_file()

    registry = (root / "__init__.py").read_text(encoding="utf-8")
    for blueprint in ("reports_bp", "jobs_bp", "forms_bp", "staff_bp"):
        assert blueprint in registry
