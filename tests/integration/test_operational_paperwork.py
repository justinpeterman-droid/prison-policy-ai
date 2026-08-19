from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.paperwork.service import (
    OperationalPaperworkNotFound,
    OperationalPaperworkRevisionConflict,
    create_operational_paperwork,
    get_operational_paperwork,
    list_operational_paperwork,
    list_operational_paperwork_revisions,
    restore_operational_paperwork,
    save_operational_paperwork,
)
from backend.persistence.models.security import AuditEvent
from backend.webapp.api_v1.middleware import Actor


def _actor(account, *, role=None):
    return Actor(
        account.id,
        account.staff_member_id,
        uuid4(),
        role or account.role,
        account.auth_version,
        account.must_change_pin,
    )


def _content(count=12):
    return {
        "schema_version": 1,
        "rows": [
            {
                "row_id": "fictional_housing_a",
                "label": "Fictional Housing A",
                "count": count,
            }
        ],
        "expected_total": 12,
        "actual_total": count,
        "difference": count - 12,
    }


def _create(db_session, accounts, identity_fixed_now):
    return create_operational_paperwork(
        db_session,
        _actor(accounts.user),
        paperwork_type="ncu_days_count",
        record_date="2026-08-19",
        shift="A",
        content=_content(),
        idempotency_key="paperwork-create-fictional-0001",
        request_id="request_fictional_paperwork_create_1",
        client_version="1.0.0",
        now=identity_fixed_now,
    )


def test_create_read_list_and_authorization(
    db_session,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    accounts = fictional_staff_and_accounts
    created = _create(db_session, accounts, identity_fixed_now)
    db_session.flush()

    current = get_operational_paperwork(
        db_session,
        _actor(accounts.user),
        created.paperwork.id,
    )
    assert current.revision_number == 1
    assert current.content["actual_total"] == 12

    page = list_operational_paperwork(
        db_session,
        _actor(accounts.user),
        paperwork_type="ncu_days_count",
    )
    assert [item.paperwork.id for item in page.items] == [created.paperwork.id]

    with pytest.raises(OperationalPaperworkNotFound):
        get_operational_paperwork(
            db_session,
            _actor(accounts.unrelated),
            created.paperwork.id,
        )

    admin_view = get_operational_paperwork(
        db_session,
        _actor(accounts.admin, role="admin"),
        created.paperwork.id,
    )
    assert admin_view.paperwork.id == created.paperwork.id


def test_save_rejects_stale_revision_and_preserves_immutable_history(
    db_session,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    accounts = fictional_staff_and_accounts
    created = _create(db_session, accounts, identity_fixed_now)
    owner = _actor(accounts.user)

    saved = save_operational_paperwork(
        db_session,
        owner,
        created.paperwork.id,
        content=_content(11),
        base_revision_number=1,
        reason="autosave",
        status=None,
        idempotency_key="paperwork-save-fictional-0001",
        request_id="request_fictional_paperwork_save_1",
        client_version="1.0.0",
        now=identity_fixed_now,
    )
    db_session.flush()

    assert saved.revision_number == 2
    assert saved.content["difference"] == -1

    with pytest.raises(OperationalPaperworkRevisionConflict) as error:
        save_operational_paperwork(
            db_session,
            owner,
            created.paperwork.id,
            content=_content(10),
            base_revision_number=1,
            reason="manual_save",
            status=None,
            idempotency_key="paperwork-save-fictional-stale",
            request_id="request_fictional_paperwork_save_stale",
            client_version="1.0.0",
            now=identity_fixed_now,
        )
    assert error.value.current_revision_number == 2

    revisions = list_operational_paperwork_revisions(
        db_session,
        owner,
        created.paperwork.id,
    )
    assert [item.revision.revision_number for item in revisions] == [1, 2]
    assert revisions[0].revision.snapshot["actual_total"] == 12
    assert revisions[1].revision.snapshot["actual_total"] == 11


def test_save_replay_returns_original_revision_without_duplicate_audit(
    db_session,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    accounts = fictional_staff_and_accounts
    owner = _actor(accounts.user)
    created = _create(db_session, accounts, identity_fixed_now)
    arguments = dict(
        content=_content(11),
        base_revision_number=1,
        reason="manual_save",
        status="completed",
        idempotency_key="paperwork-save-fictional-replay",
        request_id="request_fictional_paperwork_save_replay",
        client_version="1.0.0",
        now=identity_fixed_now,
    )

    first = save_operational_paperwork(
        db_session,
        owner,
        created.paperwork.id,
        **arguments,
    )
    db_session.flush()
    replay = save_operational_paperwork(
        db_session,
        owner,
        created.paperwork.id,
        **arguments,
    )
    db_session.flush()

    assert replay.revision_number == first.revision_number == 2
    assert replay.current_revision_number == first.current_revision_number == 2
    assert replay.status == "completed"
    audits = list(db_session.scalars(select(AuditEvent).where(
        AuditEvent.action == "operational_paperwork.saved",
        AuditEvent.target_id == created.paperwork.id,
    )).all())
    assert len(audits) == 1
    serialized = repr(audits[0].details)
    assert "rows" not in serialized
    assert "Fictional Housing A" not in serialized


def test_restore_creates_a_new_revision_instead_of_rewriting_history(
    db_session,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    accounts = fictional_staff_and_accounts
    owner = _actor(accounts.user)
    created = _create(db_session, accounts, identity_fixed_now)
    save_operational_paperwork(
        db_session,
        owner,
        created.paperwork.id,
        content=_content(9),
        base_revision_number=1,
        reason="manual_save",
        status=None,
        idempotency_key="paperwork-save-before-restore",
        request_id="request_fictional_paperwork_before_restore",
        client_version="1.0.0",
        now=identity_fixed_now,
    )

    restored = restore_operational_paperwork(
        db_session,
        owner,
        created.paperwork.id,
        revision_number=1,
        idempotency_key="paperwork-restore-fictional-0001",
        request_id="request_fictional_paperwork_restore_1",
        client_version="1.0.0",
        now=identity_fixed_now,
    )
    db_session.flush()

    assert restored.revision_number == 3
    assert restored.content["actual_total"] == 12
    revisions = list_operational_paperwork_revisions(
        db_session,
        owner,
        created.paperwork.id,
    )
    assert [item.revision.reason for item in revisions] == [
        "manual_save",
        "manual_save",
        "restored",
    ]
