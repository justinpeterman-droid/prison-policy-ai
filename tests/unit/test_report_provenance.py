"""Tests for the centralized provenance fingerprints.

Review Lab already had this behavior inline. The point of moving it is that one
helper now answers "which models and prompts produced this text" for reports,
exports, and Review Lab alike — so the Review Lab output must not shift by a
single key while that move happens.
"""

import re

import pytest

from backend.pipeline.config import FAST_MODEL, MODEL_LOCATION, PRO_MODEL
from backend.reports import review_schema
from backend.reports.provenance import (
    PROVENANCE_SOURCES,
    collect_provenance,
    file_sha256,
)


SHA256 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_KEYS = {
    "fast_model",
    "pro_model",
    "model_location",
    "classification_prompt_sha256",
    "generation_prompt_sha256",
    "checklist_sha256",
    "template_sha256",
    "cloud_run_revision",
    "source_commit",
}


def test_provenance_keys_are_exact():
    assert set(collect_provenance()) == EXPECTED_KEYS


def test_provenance_reports_the_configured_model_tiers():
    provenance = collect_provenance()

    assert provenance["fast_model"] == FAST_MODEL
    assert provenance["pro_model"] == PRO_MODEL
    assert provenance["model_location"] == MODEL_LOCATION


@pytest.mark.parametrize(
    "key",
    [
        "classification_prompt_sha256",
        "generation_prompt_sha256",
        "checklist_sha256",
        "template_sha256",
    ],
)
def test_fingerprints_are_sha256_digests(key):
    assert SHA256.fullmatch(collect_provenance()[key])


def test_fingerprints_track_the_real_source_files():
    provenance = collect_provenance()

    assert provenance["classification_prompt_sha256"] == file_sha256(
        PROVENANCE_SOURCES["classification"]
    )
    assert provenance["template_sha256"] == file_sha256(PROVENANCE_SOURCES["template"])


def test_fingerprint_changes_when_a_source_file_changes(tmp_path, monkeypatch):
    original = tmp_path / "prompt.py"
    original.write_text("PROMPT = 'fictional first'\n", encoding="utf-8")
    monkeypatch.setitem(PROVENANCE_SOURCES, "classification", original)
    first = collect_provenance()["classification_prompt_sha256"]

    original.write_text("PROMPT = 'fictional second'\n", encoding="utf-8")
    second = collect_provenance()["classification_prompt_sha256"]

    assert first != second


def test_deployment_identity_is_server_owned_and_nullable(monkeypatch):
    monkeypatch.delenv("K_REVISION", raising=False)
    monkeypatch.delenv("SOURCE_COMMIT", raising=False)
    absent = collect_provenance()

    assert absent["cloud_run_revision"] is None
    assert absent["source_commit"] is None

    monkeypatch.setenv("K_REVISION", "revision-151")
    monkeypatch.setenv("SOURCE_COMMIT", "deadbeef")
    present = collect_provenance()

    assert present["cloud_run_revision"] == "revision-151"
    assert present["source_commit"] == "deadbeef"


def test_review_lab_consumes_the_shared_helper():
    """Review Lab must not keep a private copy of the hashing behavior."""
    source = review_schema.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()

    assert "from backend.reports.provenance import" in text
    assert "hashlib" not in text


def test_review_lab_fingerprints_match_the_shared_helper():
    fingerprints = review_schema._prompt_fingerprints()

    assert set(fingerprints) == {"classification", "generation", "checklist", "charges"}
    for name, digest in fingerprints.items():
        assert digest == file_sha256(PROVENANCE_SOURCES[name])
