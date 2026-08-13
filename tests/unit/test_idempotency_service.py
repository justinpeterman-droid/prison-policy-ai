"""Unit contracts for canonical AI-job idempotency input."""

from uuid import UUID

import pytest

from backend.identity.idempotency import request_digest
from backend.jobs.service import SubmitJobCommand
from backend.persistence.models.jobs import AiJob


INCIDENT_ID = UUID("00000000-0000-4000-8000-000000000611")
REPORT_ID = UUID("00000000-0000-4000-8000-000000000612")


def test_submit_command_canonical_payload_is_stable_and_content_free():
    command = SubmitJobCommand(
        incident_id=INCIDENT_ID,
        job_type="generate",
        report_id=REPORT_ID,
    )

    canonical = command.canonical_payload(base_revision_number=7)

    assert canonical == {
        "base_revision_number": 7,
        "incident_id": str(INCIDENT_ID),
        "job_type": "generate",
        "report_id": str(REPORT_ID),
    }
    assert request_digest(canonical) == request_digest(
        {
            "report_id": str(REPORT_ID),
            "job_type": "generate",
            "incident_id": str(INCIDENT_ID),
            "base_revision_number": 7,
        }
    )


@pytest.mark.parametrize("job_type", ["classify", "extract", "generate", "disciplinary"])
def test_submit_command_accepts_only_the_four_public_job_types(job_type):
    command = SubmitJobCommand(incident_id=INCIDENT_ID, job_type=job_type)
    assert command.canonical_payload(base_revision_number=1)["job_type"] == job_type


def test_submit_command_rejects_unknown_job_type_and_invalid_base_revision():
    with pytest.raises(ValueError, match="job type"):
        SubmitJobCommand(incident_id=INCIDENT_ID, job_type="unknown")

    command = SubmitJobCommand(incident_id=INCIDENT_ID, job_type="classify")
    for value in (0, -1, True, "1"):
        with pytest.raises(ValueError, match="base revision"):
            command.canonical_payload(base_revision_number=value)


@pytest.mark.parametrize(
    "unsafe_reference",
    [
        {"content": "Fictional report content."},
        {"provider": {"prompt": "Fictional prompt."}},
        {"reports": [{"report_id": str(REPORT_ID), "revision_number": 1, "raw": {}}]},
    ],
)
def test_ai_job_mapping_rejects_non_contract_result_references(unsafe_reference):
    job = AiJob()

    with pytest.raises(ValueError, match="result reference"):
        job.result_reference = unsafe_reference
