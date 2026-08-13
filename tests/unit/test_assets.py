"""Tests for backend.webapp.assets — versioned URLs, cache headers, gzip.

These are worth pinning down because the failure modes are quiet and long-lived:
a wrong `immutable` header is a year-long stale-asset bug that no amount of
reloading clears, and a gzip bug corrupts the body rather than erroring.
"""

import gzip

import pytest

from flask import Flask

from backend.webapp.assets import (
    DEFAULT_STATIC_MAX_AGE,
    IMMUTABLE_MAX_AGE,
    MIN_COMPRESS_BYTES,
    init_assets,
)


@pytest.fixture
def app(tmp_path):
    """A minimal Flask app with a throwaway static dir."""
    static = tmp_path / "static"
    static.mkdir()
    (static / "small.css").write_text("a{color:red}")
    (static / "big.css").write_text("a{color:red}\n" * 400)
    (static / "pic.webp").write_bytes(b"\x00\xff" * 4000)

    application = Flask(__name__, static_folder=str(static))
    init_assets(application)

    @application.route("/page")
    def page():
        return "<html>" + ("x" * 5000) + "</html>"

    return application


@pytest.fixture
def client(app):
    return app.test_client()


GZIP = {"Accept-Encoding": "gzip"}


# ── versioned URLs ────────────────────────────────────────────────────────────


def test_asset_url_appends_content_hash(app):
    with app.app_context():
        url = app.jinja_env.globals["asset_url"]("small.css")
    assert url.startswith("/static/small.css?v=")
    assert len(url.split("v=")[1]) == 8


def test_asset_url_changes_when_bytes_change(app, tmp_path):
    asset_url = app.jinja_env.globals["asset_url"]
    with app.app_context():
        first = asset_url("small.css")
    # A fresh app picks up the new content; within one process the hash is
    # cached deliberately, since the container's files never change under it.
    (tmp_path / "static" / "small.css").write_text("a{color:blue}")
    other = Flask(__name__, static_folder=str(tmp_path / "static"))
    init_assets(other)
    with other.app_context():
        second = other.jinja_env.globals["asset_url"]("small.css")
    assert first != second


def test_asset_url_survives_missing_file(app):
    """A bad asset name should degrade to a broken image, not a 500 per page."""
    with app.app_context():
        url = app.jinja_env.globals["asset_url"]("nope.css")
    assert url == "/static/nope.css"


def test_asset_initialization_requires_a_static_folder():
    application = Flask(__name__, static_folder=None)

    with pytest.raises(
        RuntimeError, match="static asset delivery requires a configured static folder"
    ):
        init_assets(application)


# ── cache headers ─────────────────────────────────────────────────────────────


def test_versioned_static_is_immutable(client):
    resp = client.get("/static/small.css?v=deadbeef")
    assert resp.headers["Cache-Control"] == (
        f"public, max-age={IMMUTABLE_MAX_AGE}, immutable"
    )


def test_unversioned_static_gets_short_cache(client):
    """Without a content hash we can't prove freshness, so don't claim a year."""
    resp = client.get("/static/small.css")
    assert resp.headers["Cache-Control"] == f"public, max-age={DEFAULT_STATIC_MAX_AGE}"
    assert "immutable" not in resp.headers["Cache-Control"]


def test_html_is_not_given_a_static_cache_policy(client):
    """Pages must stay revalidated — only /static/ gets the long policy."""
    resp = client.get("/page")
    assert "immutable" not in resp.headers.get("Cache-Control", "")


# ── compression ───────────────────────────────────────────────────────────────


def test_html_is_gzipped_and_round_trips(client):
    resp = client.get("/page", headers=GZIP)
    assert resp.headers["Content-Encoding"] == "gzip"
    body = gzip.decompress(resp.get_data())
    assert body.startswith(b"<html>")
    assert len(resp.get_data()) < len(body)


def test_content_length_matches_compressed_body(client):
    """A stale Content-Length truncates the response in real clients."""
    resp = client.get("/page", headers=GZIP)
    assert int(resp.headers["Content-Length"]) == len(resp.get_data())


def test_no_gzip_when_client_does_not_ask(client):
    resp = client.get("/page")
    assert "Content-Encoding" not in resp.headers
    assert resp.get_data().startswith(b"<html>")


def test_small_bodies_are_left_alone(client):
    """Below the floor, the gzip header costs more than it saves."""
    resp = client.get("/static/small.css", headers=GZIP)
    assert len(resp.get_data()) < MIN_COMPRESS_BYTES
    assert "Content-Encoding" not in resp.headers


def test_large_css_is_compressed(client):
    resp = client.get("/static/big.css", headers=GZIP)
    assert resp.headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(resp.get_data()).startswith(b"a{color:red}")


def test_images_are_not_recompressed(client):
    """WebP is already compressed; gzipping it burns CPU for nothing."""
    resp = client.get("/static/pic.webp", headers=GZIP)
    assert "Content-Encoding" not in resp.headers


def test_vary_accept_encoding_always_set(client):
    """Without Vary, a shared cache can hand a gzipped body to a client that
    never asked for one."""
    for headers in (GZIP, {}):
        resp = client.get("/page", headers=headers)
        assert "Accept-Encoding" in resp.headers.get("Vary", "")


def test_etag_differs_between_encodings(client):
    """Same URL, two bodies — they must not share a validator."""
    plain = client.get("/static/big.css")
    zipped = client.get("/static/big.css", headers=GZIP)
    if "ETag" in plain.headers and "ETag" in zipped.headers:
        assert plain.headers["ETag"] != zipped.headers["ETag"]
