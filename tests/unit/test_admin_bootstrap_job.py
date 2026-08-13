import hashlib
import json
from uuid import UUID

import pytest

from backend.jobs.admin_bootstrap import load_bootstrap_request


class Reader:
    def __init__(self, payload): self.payload = payload
    def read_exact(self, *, bucket, object_name, max_bytes): return self.payload


def test_bootstrap_request_requires_hash_schema_and_matching_opaque_path():
    operation = "00000000-0000-4000-8000-000000000001"
    body = json.dumps({"schema_version": 1, "operation_id": operation, "staff_member_id": "00000000-0000-4000-8000-000000000002", "approval_reference": "fictional-approval-reference"}).encode()
    request = load_bootstrap_request(Reader(body), request_uri=f"gs://fixture-config/admin-bootstrap-requests/{operation}.json", expected_sha256=hashlib.sha256(body).hexdigest(), expected_bucket="fixture-config")
    assert request.operation_id == UUID(operation)
    with pytest.raises(ValueError):
        load_bootstrap_request(Reader(body), request_uri="gs://fixture-config/other.json", expected_sha256=hashlib.sha256(body).hexdigest(), expected_bucket="fixture-config")
