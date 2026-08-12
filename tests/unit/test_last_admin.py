from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.identity.accounts import LastActiveAdminError, ensure_not_last_active_admin


def test_last_active_admin_cannot_be_removed():
    target = SimpleNamespace(id=uuid4(), role="admin", status="active")
    with pytest.raises(LastActiveAdminError):
        ensure_not_last_active_admin(target, [target], role="user", status="active")


def test_second_active_admin_allows_role_change():
    target = SimpleNamespace(id=uuid4(), role="admin", status="active")
    other = SimpleNamespace(id=uuid4(), role="admin", status="active")
    ensure_not_last_active_admin(target, [target, other], role="user", status="active")
