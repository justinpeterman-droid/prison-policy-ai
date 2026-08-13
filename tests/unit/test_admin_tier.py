"""Two-tier access: ACCESS_CODE opens the site, ADMIN_CODE also opens the roster.

Both codes go into the same login box. The roster carries real staff names and
employee numbers, so a regular user shouldn't just be blocked from it — they
shouldn't be able to tell it's there. Hence 404 rather than 403, and no nav link.
"""

import pytest

from backend.webapp import app as app_mod

REGULAR = "regular-code"
ADMIN = "admin-code"


@pytest.fixture
def tiered(monkeypatch):
    """An app with both tiers configured."""
    monkeypatch.setattr(app_mod, "ACCESS_CODE", REGULAR)
    monkeypatch.setattr(app_mod, "ADMIN_CODE", ADMIN)
    return app_mod.create_app()


def _client(app, code=None):
    c = app.test_client()
    if code is not None:
        c.set_cookie("access_code", code)
    return c


# ── The regular tier cannot see the roster ───────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/roster",
        "/api/roster",
        "/api/roster/lookup?q=x",
        "/review-lab",
        "/api/review-lab/submissions",
    ],
)
def test_regular_users_get_404_on_admin_paths(tiered, path):
    assert _client(tiered, REGULAR).get(path).status_code == 404


def test_regular_users_cannot_write_to_the_roster(tiered):
    c = _client(tiered, REGULAR)
    assert (
        c.post(
            "/api/roster/staff",
            json={"last": "X", "employee_number": "1", "shift": "A"},
        ).status_code
        == 404
    )
    assert c.put("/api/roster/staff/100411", json={"shift": "B"}).status_code == 404
    assert c.delete("/api/roster/staff/100411").status_code == 404


def test_the_rest_of_the_site_still_works_for_regular_users(tiered):
    c = _client(tiered, REGULAR)
    assert c.get("/").status_code == 200
    assert c.get("/reports").status_code == 200


@pytest.mark.parametrize("page", ["/", "/reports"])
def test_the_roster_link_is_hidden_from_regular_users(tiered, page):
    body = _client(tiered, REGULAR).get(page).get_data(as_text=True)
    assert "/roster" not in body


# ── The admin tier gets everything ───────────────────────────────────────


@pytest.mark.parametrize("path", ["/roster", "/api/roster"])
def test_admins_reach_the_roster(tiered, path):
    assert _client(tiered, ADMIN).get(path).status_code == 200


@pytest.mark.parametrize("page", ["/", "/reports"])
def test_the_roster_link_is_shown_to_admins(tiered, page):
    body = _client(tiered, ADMIN).get(page).get_data(as_text=True)
    assert "/roster" in body


# ── Login ────────────────────────────────────────────────────────────────


def test_either_code_logs_in(tiered):
    for code in (REGULAR, ADMIN):
        resp = tiered.test_client().post("/login", data={"code": code})
        assert resp.status_code == 302, code


def test_a_wrong_code_is_still_rejected(tiered):
    resp = tiered.test_client().post("/login", data={"code": "nope"})
    assert resp.status_code == 200
    assert "Invalid access code" in resp.get_data(as_text=True)


def test_the_cookie_records_which_tier_logged_in(tiered):
    """The stored value is what distinguishes the tiers later, so it has to be
    the submitted code — not a fixed one."""
    resp = tiered.test_client().post("/login", data={"code": ADMIN})
    assert ADMIN in resp.headers["Set-Cookie"]


def test_a_regular_login_aimed_at_the_roster_lands_on_the_home_page(tiered):
    """Rather than bouncing them straight into a 404 they can do nothing about."""
    resp = tiered.test_client().post("/login?next=/roster", data={"code": REGULAR})
    assert resp.headers["Location"] == "/"


def test_an_admin_login_aimed_at_the_roster_lands_there(tiered):
    resp = tiered.test_client().post("/login?next=/roster", data={"code": ADMIN})
    assert resp.headers["Location"] == "/roster"


def test_the_bookmarkable_code_link_carries_the_tier(tiered):
    c = tiered.test_client()
    resp = c.get("/roster?code=" + ADMIN)
    assert resp.status_code == 302
    assert ADMIN in resp.headers["Set-Cookie"]


def test_logged_out_users_are_redirected_not_404ed(tiered):
    """A 404 here would be misleading — they simply haven't logged in yet."""
    assert _client(tiered).get("/roster").status_code == 302


# ── Configuration edge cases ─────────────────────────────────────────────


def test_without_an_admin_code_the_roster_is_closed_to_everyone(monkeypatch):
    """Fail closed. An unset ADMIN_CODE must not silently mean 'everyone is an
    admin' — that would quietly undo the whole point of the tier."""
    monkeypatch.setattr(app_mod, "ACCESS_CODE", REGULAR)
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    app = app_mod.create_app()
    assert _client(app, REGULAR).get("/roster").status_code == 404
    assert _client(app, REGULAR).get("/api/roster").status_code == 404


def test_with_auth_disabled_entirely_the_roster_is_still_reachable(monkeypatch):
    """ACCESS_CODE="" turns the gate off for local work; losing the roster
    along with it would be a surprise, not a security win."""
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    app = app_mod.create_app()
    c = app.test_client()
    assert c.get("/roster").status_code == 200
    assert c.get("/api/roster").status_code == 200
    assert "/roster" in c.get("/").get_data(as_text=True)


def test_health_stays_open(tiered):
    assert tiered.test_client().get("/health").status_code == 200
