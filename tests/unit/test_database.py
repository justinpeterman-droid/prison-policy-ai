import pytest

from backend.persistence import database


def test_session_scope_rolls_back_and_closes(monkeypatch):
    calls = []

    class FakeSession:
        def commit(self):
            calls.append("commit")

        def rollback(self):
            calls.append("rollback")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(database, "_session_factory", lambda: FakeSession())
    with pytest.raises(ValueError, match="stop"):
        with database.session_scope():
            raise ValueError("stop")
    assert calls == ["rollback", "close"]
