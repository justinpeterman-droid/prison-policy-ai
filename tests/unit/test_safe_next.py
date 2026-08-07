"""The post-login redirect target.

`next` is attacker-controllable — it arrives on the query string of a URL
anyone can hand a logged-out officer. These tests pin the two properties that
matter: a legitimate deep link survives login, and nothing else does.
"""
import pytest

from backend.webapp.app import _safe_next


@pytest.mark.parametrize("value", [
    "//evil.com",                    # protocol-relative — browsers treat as absolute
    "////evil.com",
    "https://evil.com",
    "http://a@evil.com/",            # userinfo trick
    "javascript:alert(1)",
    "/\\evil.com",                   # backslash, normalized to a slash by browsers
    "\t/\\evil.com",
    "/nope",                         # a real relative path, but not one of ours
    "/static/../../etc/passwd",
    "",
    None,
])
def test_hostile_or_unknown_targets_collapse_to_home(value):
    assert _safe_next(value) == "/"


@pytest.mark.parametrize("value", ["/", "/chat", "/reports", "/roster"])
def test_known_pages_are_preserved(value):
    assert _safe_next(value) == value


def test_the_demo_deep_link_survives_login():
    """The whole reason the redirect carries a query string at all: without
    this, a logged-out 'Try a demo' click lands on a blank /reports."""
    assert _safe_next("/reports?demo=1") == "/reports?demo=1"
    assert _safe_next("/reports?demo=use_of_force_oc") == "/reports?demo=use_of_force_oc"


def test_only_the_demo_parameter_rides_along():
    assert _safe_next("/reports?demo=1&next=//evil.com") == "/reports?demo=1"
    assert _safe_next("/chat?q=anything") == "/chat"


def test_a_malformed_demo_value_is_dropped_not_echoed():
    assert _safe_next("/reports?demo=<script>alert(1)</script>") == "/reports"
    assert _safe_next("/reports?demo=" + "a" * 41) == "/reports"


def test_demo_is_not_smuggled_onto_another_page():
    assert _safe_next("/roster?demo=1") == "/roster"
