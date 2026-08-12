"""Conflict-safe employee report HTTP saves against PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select

from backend.persistence.models.reporting import Report, ReportRevision
from backend.persistence.models.security import IdempotencyRecord
from tests.support.reporting import fictional_report_content


@pytest.fixture(autouse=True)
def _fixed_auth_clock(monkeypatch, identity_fixed_now):
    from datetime import datetime, timedelta
    import backend.webapp.api_v1.middleware as middleware

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)


def test_two_saves_from_the_same_base_yield_one_success_and_one_safe_conflict(
    db_session, db_session_factory, api_client, owner_bearer_headers, shared_report,
):
    report_id = shared_report.id
    db_session.commit()
    barrier = Barrier(2)
    app = api_client.application

    def save(number):
        headers = owner_bearer_headers | {
            "Idempotency-Key": f"report-concurrent-{number:04d}",
            "X-Request-ID": f"request-report-concurrent-{number:04d}",
            "If-Match": '"1"',
        }
        barrier.wait()
        with app.test_client() as client:
            return client.patch(
                f"/api/v1/reports/{report_id}", headers=headers,
                json={
                    "base_revision_number": 1,
                    "content": fictional_report_content(
                        f"Fictional simultaneous edit {number}."),
                    "reason": "manual_save",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(save, (1, 2)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    details = conflict.json["error"]["details"]
    assert conflict.json["error"]["code"] == "revision_conflict"
    assert details["current_revision_number"] == 2
    assert set(details) == {
        "current_revision_number", "current_editor_display_name",
        "current_edited_at", "changed_fields",
    }
    assert details["current_editor_display_name"] == "Officer Alex Example"
    assert details["changed_fields"] == ["narrative"]
    assert "content" not in details and "narrative" not in details
    with db_session_factory() as verification:
        report = verification.get(Report, report_id)
        assert report.current_revision_number == 2
        assert verification.scalar(select(func.count()).select_from(ReportRevision).where(
            ReportRevision.report_id == report_id)) == 2
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "report.save")) == 1


def test_if_match_and_body_base_must_agree_before_any_write(
    db_session, db_session_factory, api_client, owner_bearer_headers, shared_report,
):
    report_id = shared_report.id
    db_session.commit()
    response = api_client.patch(
        f"/api/v1/reports/{report_id}",
        headers=owner_bearer_headers | {
            "Idempotency-Key": "report-if-match-mismatch-0001",
            "If-Match": '"7"',
        },
        json={
            "base_revision_number": 1,
            "content": fictional_report_content("Fictional mismatched edit."),
            "reason": "manual_save",
        },
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    with db_session_factory() as verification:
        assert verification.get(Report, report_id).current_revision_number == 1
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord).where(
            IdempotencyRecord.action == "report.save")) == 0
