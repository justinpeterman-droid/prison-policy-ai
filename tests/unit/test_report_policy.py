"""Owner, preparer, unrelated-user, and Admin record-policy matrix."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.reports.policy import can_edit_report, can_export_report, can_read_report


@pytest.fixture
def identities():
    return SimpleNamespace(owner=uuid4(), preparer=uuid4(), unrelated=uuid4())


def _actor(staff_id, role="user"):
    return SimpleNamespace(staff_member_id=staff_id, role=role)


def _report(identities):
    return SimpleNamespace(
        reporting_staff_member_id=identities.owner,
        prepared_by_staff_member_id=identities.preparer,
    )


@pytest.mark.parametrize("policy", [can_read_report, can_edit_report, can_export_report])
def test_owner_and_preparer_are_authorized(policy, identities):
    report = _report(identities)
    assert policy(_actor(identities.owner), report) is True
    assert policy(_actor(identities.preparer), report) is True


@pytest.mark.parametrize("policy", [can_read_report, can_edit_report, can_export_report])
def test_unrelated_user_is_denied(policy, identities):
    assert policy(_actor(identities.unrelated), _report(identities)) is False


@pytest.mark.parametrize("policy", [can_read_report, can_edit_report, can_export_report])
def test_admin_is_authorized_without_client_owned_relationship(policy, identities):
    assert policy(_actor(identities.unrelated, role="admin"), _report(identities)) is True


@pytest.mark.parametrize("policy", [can_read_report, can_edit_report, can_export_report])
def test_client_supplied_role_like_report_attributes_do_not_grant_access(policy, identities):
    report = _report(identities)
    report.owner_staff_member_id = identities.unrelated
    report.actor_role = "admin"
    assert policy(_actor(identities.unrelated), report) is False
