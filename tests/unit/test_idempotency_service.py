"""Unit coverage for how AI job submission uses ID-06 idempotency primitives.

This does not duplicate or redefine ID-06's own idempotency tests
(`tests/integration/test_identity_idempotency.py`) -- it tests only the
canonical-request construction `backend.jobs.service.submit_job` feeds into
the shared `backend.identity.idempotency.request_digest`/`claim_idempotency`
functions, which is pure and needs no database.
"""
from uuid import uuid4

import pytest

# Warms up `backend.webapp.api_v1` (which imports `backend.reports.persistence`
# by way of its own `incidents`/`reports` blueprints) before anything imports
# `backend.jobs.service`. `backend.jobs.service` also depends on
# `backend.reports.persistence`, and that module's pre-existing import chain
# only resolves cleanly when `backend.webapp.api_v1` has already been loaded
# first; importing `backend.jobs.service` cold otherwise hits a genuine
# circular import that exists independent of this task (confirmed by the
# same failure importing `backend.reports.persistence` alone, first, in a
# fresh interpreter). Every other test file that reaches this module reaches
# it after `tests/integration/conftest.py` has already imported
# `backend.webapp.api_v1.middleware`, so only this standalone unit module
# needs the explicit warm-up.
import backend.webapp.api_v1  # noqa: F401

from backend.identity.idempotency import FORBIDDEN_REFERENCE_KEYS, request_digest
from backend.jobs.service import JOB_TYPES, SubmitJobCommand, _canonical_request


def test_canonical_request_digest_is_stable_for_the_same_payload():
    incident_id = uuid4()
    first = request_digest(_canonical_request(incident_id, "classify", 1))
    second = request_digest(_canonical_request(incident_id, "classify", 1))
    assert first == second


def test_canonical_request_digest_changes_with_base_revision_number():
    incident_id = uuid4()
    original = request_digest(_canonical_request(incident_id, "classify", 1))
    changed = request_digest(_canonical_request(incident_id, "classify", 2))
    assert original != changed


def test_canonical_request_digest_changes_with_job_type():
    incident_id = uuid4()
    classify = request_digest(_canonical_request(incident_id, "classify", 1))
    extract = request_digest(_canonical_request(incident_id, "extract", 1))
    assert classify != extract


def test_canonical_request_digest_changes_with_incident_id():
    first = request_digest(_canonical_request(uuid4(), "classify", 1))
    second = request_digest(_canonical_request(uuid4(), "classify", 1))
    assert first != second


def test_canonical_request_is_json_safe_and_order_independent():
    """`request_digest` sorts keys, so field order in the payload cannot matter."""
    incident_id = uuid4()
    payload = _canonical_request(incident_id, "generate", 3)
    reordered = {key: payload[key] for key in reversed(list(payload))}
    assert request_digest(payload) == request_digest(reordered)


def test_canonical_request_never_carries_a_forbidden_reference_key():
    """The idempotency response reference must never carry sensitive keys.

    The request payload passed to `request_digest` for job submission is
    smaller than -- and disjoint from -- ID-06's forbidden reference-key
    list, so it can never smuggle a token/PIN/report-text field through.
    """
    payload = _canonical_request(uuid4(), "disciplinary", 7)
    assert not (set(payload) & FORBIDDEN_REFERENCE_KEYS)


@pytest.mark.parametrize("job_type", sorted(JOB_TYPES))
def test_submit_job_command_accepts_every_approved_job_type(job_type):
    command = SubmitJobCommand(incident_id=uuid4(), job_type=job_type)
    assert command.job_type == job_type


def test_job_types_are_exactly_the_four_approved_values():
    assert JOB_TYPES == frozenset({"classify", "extract", "generate", "disciplinary"})
