from backend.persistence.models.browser import BrowserSessionBinding


def test_browser_session_binding_table_contract():
    table = BrowserSessionBinding.__table__

    assert table.name == "browser_session_bindings"
    assert table.c.session_id.primary_key
    assert table.c.session_id.nullable is False
    assert table.c.csrf_token_hash.nullable is False
    assert table.c.csrf_token_hash.type.length == 32
    assert table.c.created_at.nullable is False
    assert table.c.rotated_at.nullable is False


def test_browser_session_binding_cascades_with_identity_session():
    foreign_keys = list(BrowserSessionBinding.__table__.c.session_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "sessions.id"
    assert foreign_keys[0].ondelete == "CASCADE"
