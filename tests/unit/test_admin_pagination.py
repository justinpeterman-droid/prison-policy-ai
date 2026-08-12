from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from backend.identity.accounts import page_from_rows


def test_admin_page_caps_at_one_hundred_and_emits_unsigned_keyset_cursor():
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    rows = [SimpleNamespace(id=uuid4(), created_at=now + timedelta(seconds=index))
            for index in range(101)]
    page = page_from_rows(rows, 100)
    assert len(page.items) == 100
    assert set(page.next_cursor) == {"created_at", "id"}
