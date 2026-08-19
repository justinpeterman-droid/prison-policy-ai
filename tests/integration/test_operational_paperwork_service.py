from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from backend.paperwork.contracts import (
    OperationalPaperworkContentV1,
    PaperworkIdentity,
    SaveOperationalPaperworkRequest,
)
from backend.paperwork.service import (
    PaperworkNotAllowed,
    PaperworkRevisionConflict,
    create_operational_paperwork,
    get_operational_paperwork,
    list_operational_paperwork_revisions,
    restore_operational_paperwork,
    save_operational_paperwork,
)
from backend.webapp.api_v1.middleware import Actor


def _actor(account):
    return Actor(
        account.id,
        account.staff_member_id,
        uuid4(),
        account.role,
        account.auth_version,
        account.must_change_pin,
    )


def _identity(paperwork_type="ncu_days_count"):
    return PaperworkIdentity(
        paperwork_type=paperwork_type,
        record_date=date(2026, 8, 19),
        shift="A Shift",
        record_key="primary",
    )


def _content(total):
    return OperationalPaperworkContentV1(fields={
        "housing_total": total,
        "out_of_housing_total": 2,
        "reconciliation_difference": 0,
    })


def test_count_sheet_create_save_restore_and_idempotent_replay(
    db_session,
    fictional_staff_and_accounts,
):
    actor = _actor(fictional_staff_and_accounts.user)
    fixed = datetime(2026, 8, 19, 15, 0, tzinfo=UTC)

    created = create_operational_paperwork(
        db_session,
        actor,
        identity=_identity(),
        content=_content(40),
        idempotency_key="paperwork-create-fictional-001",
        request_id="request_paperwork_create_001",
        client_version="1.0.0",
        now=fixed,
    )
    replay = create_operational_paperwork(
        db_session,
        actor,
        identity=_identity(),
        content=_content(40),
        idempotency_key="paperwork-create-fictional-001",
        request_id="request_paperwork_create_001_replay",
        client_version="1.0.0",
        now=fixed,
    )

    assert replay.record.id == created.record.id
    assert created.revision_number == 1
    assert created.content["fields"]["housing_total"] == 40

    saved = save_operational_paperwork(
        db_session,
        actor,
        record_id=created.record.id,
        request_model=SaveOperationalPaperworkRequest(
            content=_content(41),
            base_revision_number=1,
            reason="manual_save",
        ),
        idempotency_key="paperwork-save-fictional-001",
        request_id="request_paperwork_save_001",
        client_version="1.0.0",
        now=datetime(2026, 8, 19, 15, 5, tzinfo=UTC),
    )
    assert saved.revision_number == 2
    assert saved.content["fields"]["housing_total"] == 41

    with pytest.raises(PaperworkRevisionConflict) as error:
        save_operational_paperwork(
            db_session,
            actor,
            record_id=created.record.id,
            request_model=SaveOperationalPaperworkRequest(
                content=_content(42),
                base_revision_number=1,
                reason="autosave",
            ),
            idempotency_key="paperwork-save-fictional-stale",
            request_id="request_paperwork_save_stale",
            client_version="1.0.0",
        )
    assert error.value.current_revision_number == 2

    restored = restore_operational_paperwork(
        db_session,
        actor,
        record_id=created.record.id,
        source_revision_number=1,
        base_revision_number=2,
        idempotency_key="paperwork-restore-fictional-001",
        request_id="request_paperwork_restore_001",
        client_version="1.0.0",
        now=datetime(2026, 8, 19, 15, 10, tzinfo=UTC),
    )
    assert restored.revision_number == 3
    assert restored.content["fields"]["housing_total"] == 40

    loaded = get_operational_paperwork(
        db_session,
        actor,
        record_id=created.record.id,
    )
    assert loaded.revision_number == 3
    revisions = list_operational_paperwork_revisions(
        db_session,
        actor,
        record_id=created.record.id,
    )
    assert [revision.revision_number for revision in revisions] == [1, 2, 3]
    assert revisions[-1].reason == "restored"


def test_daily_admin_paperwork_is_not_available_to_officer_accounts(
    db_session,
    fictional_staff_and_accounts,
):
    user_actor = _actor(fictional_staff_and_accounts.user)
    admin_actor = _actor(fictional_staff_and_accounts.admin)

    with pytest.raises(PaperworkNotAllowed):
        create_operational_paperwork(
            db_session,
            user_actor,
            identity=_identity("assignment_roster"),
            content=OperationalPaperworkContentV1(fields={}),
            idempotency_key="paperwork-user-roster-denied",
            request_id="request_user_roster_denied",
            client_version="1.0.0",
        )

    created = create_operational_paperwork(
        db_session,
        admin_actor,
        identity=_identity("assignment_roster"),
        content=OperationalPaperworkContentV1(fields={}),
        idempotency_key="paperwork-admin-roster-created",
        request_id="request_admin_roster_created",
        client_version="1.0.0",
    )
    assert created.record.paperwork_type == "assignment_roster"
