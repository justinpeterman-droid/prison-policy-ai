"""Regression tests for temporary legacy report-download files."""

from pathlib import Path

import pytest
from flask import Flask

from backend.reports.filler import fill_template
from backend.webapp.routes import reports


def _request_context():
    app = Flask(__name__)
    app.config.update(TESTING=True)
    return app.test_request_context("/api/reports/download", method="POST")


def test_fill_template_marks_generated_path_as_temporary():
    result = fill_template({"narrative": "fictional report"})
    path = Path(result["path"])
    try:
        assert result["temporary"] is True
        assert path.exists()
    finally:
        path.unlink(missing_ok=True)


def test_fill_template_marks_caller_path_as_not_temporary(tmp_path):
    output_path = tmp_path / "caller-owned.docx"

    result = fill_template(
        {"narrative": "fictional report"},
        output_path=output_path,
    )

    assert result["temporary"] is False
    assert output_path.exists()


def test_send_filled_removes_owned_temp_file(monkeypatch, tmp_path):
    output_path = tmp_path / "route-owned.docx"
    output_path.write_bytes(b"fictional-docx")
    monkeypatch.setattr(
        reports,
        "fill_template",
        lambda metadata: {"path": str(output_path), "temporary": True},
    )

    with _request_context():
        response = reports._send_filled({"narrative": "fictional report"})
        response.direct_passthrough = False
        assert response.get_data() == b"fictional-docx"

    assert not output_path.exists()


def test_send_filled_preserves_caller_owned_path(monkeypatch, tmp_path):
    output_path = tmp_path / "caller-owned.docx"
    output_path.write_bytes(b"fictional-docx")
    monkeypatch.setattr(
        reports,
        "fill_template",
        lambda metadata: {"path": str(output_path), "temporary": False},
    )

    with _request_context():
        response = reports._send_filled({"narrative": "fictional report"})
        response.direct_passthrough = False
        assert response.get_data() == b"fictional-docx"

    assert output_path.exists()


def test_send_filled_removes_owned_temp_file_when_response_fails(monkeypatch, tmp_path):
    output_path = tmp_path / "route-owned.docx"
    output_path.write_bytes(b"fictional-docx")
    monkeypatch.setattr(
        reports,
        "fill_template",
        lambda metadata: {"path": str(output_path), "temporary": True},
    )

    def fail_send_file(*args, **kwargs):
        raise RuntimeError("response construction failed")

    monkeypatch.setattr(reports, "send_file", fail_send_file)

    with _request_context(), pytest.raises(RuntimeError, match="response construction failed"):
        reports._send_filled({"narrative": "fictional report"})

    assert not output_path.exists()
