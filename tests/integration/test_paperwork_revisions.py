from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.identity.browser_sessions import BrowserActor
from backend.paperwork.models import PaperworkKind
from backend.paperwork.schemas import SavePaperworkRequest
from backend.paperwork.service import (
    PaperworkNotFound,
    PaperworkRevisionConflict,
    get_paperwork_record,
    get_paperwork_revision,
    list_paperwork_records,
    list_paperwork_revisions,
    restore_paperwork_record,
    save_paperwork_record,
)
from backend.persistence.models.paperwork import PaperworkRecord, PaperworkRevision
from backend.persistence.models.security import AuditEvent


FIXED = datetime(2026, 8, 19, 16, 0, tzinfo=UTC)


def _actor(account):
    return BrowserActor(
        account_id=account.id,
        staff_member_id=account.staff_member_id,
        session_id=uuid4(),
        role=account.role,
        auth_version=account.auth_version,
        must_change_pin=account.must_change_pin,
    )


def _request(*, value: int, base: int | None, reason="manual_save"):
    return SavePaperworkRequest.model_validate({
        "schema_version": 1,
        "work_date": date(2026, 8, 19),
        "shift": "A",
        "payload": {
            "cells": {"Fictional Area": {"1": value}},
            "operational": {"on_site": value},
        },
        "base_revision_number": base,
        "reason": reason,
    })


def test_create_update_replay_conflict_and_restore_are_revisioned_atomically(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    owner = _actor(accounts.user)

    created = save_paperwork_record(
        db_session,
        owner,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=_request(value=4, base=None),
        idempotency_key="paperwork-create-0001",
        request_id="request_paperwork_create_0001",
        client_version="1.0.0",
        now=FIXED,
    )
    replayed = save_paperwork_record(
        db_session,
        owner,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=_request(value=4, base=None),
        idempotency_key="paperwork-create-0001",
        request_id="request_paperwork_create_replay",
        client_version="1.0.0",
        now=FIXED + timedelta(seconds=1),
    )

    assert replayed.record_id == created.record_id
    assert replayed.current_revision_number == 1
    assert db_session.scalar(select(PaperworkRecord).where(
        PaperworkRecord.id == created.record_id
    )) is not None
    assert len(list(db_session.scalars(select(PaperworkRevision).where(
        PaperworkRevision.record_id == created.record_id
    )).all())) == 1

    updated = save_paperwork_record(
        db_session,
        owner,
        record_id=created.record_id,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=_request(value=7, base=1, reason="autosave"),
        idempotency_key="paperwork-save-0002",
        request_id="request_paperwork_save_0002",
        client_version="1.0.0",
        now=FIXED + timedelta(minutes=1),
    )

    assert updated.current_revision_number == 2
    assert updated.payload["cells"]["Fictional Area"]["1"] == 7
    second = get_paperwork_revision(
        db_session,
        owner,
        created.record_id,
        2,
    )
    assert second.reason == "autosave"
    assert second.changed_fields == {
        "paths": ["payload.cells", "payload.operational"]
    }

    with pytest.raises(PaperworkRevisionConflict) as conflict:
        save_paperwork_record(
            db_session,
            owner,
            record_id=created.record_id,
            kind=PaperworkKind.COUNT_SHEET,
            request_model=_request(value=8, base=1),
            idempotency_key="paperwork-stale-0003",
            request_id="request_paperwork_stale_0003",
            client_version="1.0.0",
            now=FIXED + timedelta(minutes=2),
        )
    assert conflict.value.current_revision_number == 2

    restored = restore_paperwork_record(
        db_session,
        owner,
        record_id=created.record_id,
        source_revision_number=1,
        idempotency_key="paperwork-restore-0004",
        request_id="request_paperwork_restore_0004",
        client_version="1.0.0",
        now=FIXED + timedelta(minutes=3),
    )

    assert restored.current_revision_number == 3
    assert restored.payload["cells"]["Fictional Area"]["1"] == 4
    revisions = list_paperwork_revisions(
        db_session,
        owner,
        created.record_id,
        limit=10,
    )
    assert [revision.revision_number for revision in revisions.items] == [1, 2, 3]
    assert revisions.items[-1].reason == "restored"

    events = list(db_session.scalars(
        select(AuditEvent)
        .where(AuditEvent.target_id == created.record_id)
        .order_by(AuditEvent.occurred_at, AuditEvent.id)
    ).all())
    assert [event.action for event in events] == [
        "paperwork.created",
        "paperwork.saved",
        "paperwork.restored",
    ]
    assert all("payload" not in repr(event.details).lower() for event in events)
    assert events[1].details["changed_fields"] == [
        "payload.cells",
        "payload.operational",
    ]


def test_owner_admin_and_unrelated_access_are_enforced(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    owner = _actor(accounts.user)
    unrelated = _actor(accounts.unrelated)
    admin = _actor(accounts.admin)

    created = save_paperwork_record(
        db_session,
        owner,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=_request(value=3, base=None),
        idempotency_key="paperwork-access-0001",
        request_id="request_paperwork_access_0001",
        client_version="1.0.0",
        now=FIXED,
    )

    assert get_paperwork_record(
        db_session,
        owner,
        created.record_id,
    ).record_id == created.record_id
    assert get_paperwork_record(
        db_session,
        admin,
        created.record_id,
    ).record_id == created.record_id
    with pytest.raises(PaperworkNotFound):
        get_paperwork_record(db_session, unrelated, created.record_id)

    owner_page = list_paperwork_records(
        db_session,
        owner,
        kind=PaperworkKind.COUNT_SHEET,
        limit=10,
    )
    unrelated_page = list_paperwork_records(
        db_session,
        unrelated,
        kind=PaperworkKind.COUNT_SHEET,
        limit=10,
    )
    admin_page = list_paperwork_records(
        db_session,
        admin,
        kind=PaperworkKind.COUNT_SHEET,
        limit=10,
    )

    assert [item.record_id for item in owner_page.items] == [created.record_id]
    assert unrelated_page.items == ()
    assert [item.record_id for item in admin_page.items] == [created.record_id]

    admin_updated = save_paperwork_record(
        db_session,
        admin,
        record_id=created.record_id,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=_request(value=5, base=1),
        idempotency_key="paperwork-admin-0002",
        request_id="request_paperwork_admin_0002",
        client_version="1.0.0",
        now=FIXED + timedelta(minutes=1),
    )
    assert admin_updated.current_revision_number == 2
    assert admin_updated.last_editor_staff_member_id == admin.staff_member_id
