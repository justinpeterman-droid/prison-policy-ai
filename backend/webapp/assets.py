"""Static-asset delivery: content-versioned URLs, cache headers, and gzip.

Three things were costing every page load more than they needed to:

1. Flask was answering `/static/*` with `Cache-Control: no-cache`, so the browser
   revalidated every asset on every navigation. With the nav mark on all five
   pages that is a round-trip per page just to be told "not modified".
2. Nothing was compressed. `reports.html` is ~85KB of markup on the wire.
3. Asset URLs were unversioned, so the only safe cache policy *was* a short one.

`asset_url()` fixes (3) by stamping each URL with a hash of the file's bytes,
which then makes the year-long immutable policy in (1) safe: a changed file gets
a new URL, so a stale cache entry is unreachable rather than merely unlikely.
"""
from __future__ import annotations

import gzip
import hashlib
import re
from pathlib import Path

from flask import Flask, request

# Text types worth compressing. Images, video, PDFs and woff2 are already
# compressed — re-gzipping them burns CPU to make bytes marginally bigger.
COMPRESSIBLE = {
    "text/html",
    "text/css",
    "text/plain",
    "text/xml",
    "application/json",
    "application/javascript",
    "text/javascript",
    "image/svg+xml",
}

# Below this, the gzip header costs more than the compression saves.
MIN_COMPRESS_BYTES = 1024

# Versioned URLs are content-addressed, so they can be cached hard.
IMMUTABLE_MAX_AGE = 31_536_000  # 1 year
# Unversioned ones still need to be re-checked reasonably often.
DEFAULT_STATIC_MAX_AGE = 3600  # 1 hour

# Vite names production assets with a content hash (for example,
# ``assets/index-3f7ae12c.js``). Unlike the legacy ``?v=`` convention, the
# filename itself proves freshness, so it gets the same immutable policy.
VITE_HASHED_ASSET = re.compile(r"(?:^|/)[^/]+-[A-Za-z0-9_-]{8,}\.[^/]+$")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()[:8]


def _has_immutable_asset_name(filename: str) -> bool:
    """Return whether a static filename is content-addressed by Vite."""
    return bool(VITE_HASHED_ASSET.search(filename))


def init_assets(app: Flask) -> None:
    """Wire versioned asset URLs, cache headers and gzip into `app`."""
    static_dir = Path(app.static_folder)
    # Hashes are computed once per process. The container is immutable in
    # production, so re-stat-ing on every request would buy nothing; in debug we
    # recompute so a designer editing CSS sees it without a restart.
    cache: dict[str, str] = {}

    def asset_url(filename: str) -> str:
        """`/static/<filename>?v=<content-hash>` — safe to cache forever."""
        if app.debug or filename not in cache:
            path = static_dir / filename
            if not path.is_file():
                # Missing file: fall back to the plain URL rather than raising, so
                # a bad asset name is a broken image and not a 500 on every page.
                app.logger.warning("asset_url: no such static file %r", filename)
                return f"/static/{filename}"
            cache[filename] = _hash_file(path)
        return f"/static/{filename}?v={cache[filename]}"

    app.jinja_env.globals["asset_url"] = asset_url

    @app.after_request
    def _cache_and_compress(response):
        if request.path.startswith("/static/"):
            # A ?v= hash means the URL changes whenever the bytes do, so the
            # response can be cached hard. Without one, stay conservative.
            if request.args.get("v") or _has_immutable_asset_name(request.path):
                response.headers["Cache-Control"] = (
                    f"public, max-age={IMMUTABLE_MAX_AGE}, immutable"
                )
            else:
                response.headers["Cache-Control"] = (
                    f"public, max-age={DEFAULT_STATIC_MAX_AGE}"
                )

        return _compress(response)

    def _compress(response):
        # Vary regardless of whether we compressed this particular response:
        # the same URL can produce both encodings, and a shared cache needs to
        # keep them apart.
        response.headers.add("Vary", "Accept-Encoding")

        if "gzip" not in request.headers.get("Accept-Encoding", "").lower():
            return response
        if response.status_code < 200 or response.status_code >= 300:
            return response
        if "Content-Encoding" in response.headers:
            return response
        if response.mimetype not in COMPRESSIBLE:
            return response

        # send_file() streams in passthrough mode; reading the body would
        # otherwise raise. These are small text files, so buffering is fine.
        response.direct_passthrough = False
        data = response.get_data()
        if len(data) < MIN_COMPRESS_BYTES:
            return response

        compressed = gzip.compress(data, compresslevel=6)
        if len(compressed) >= len(data):
            return response

        response.set_data(compressed)
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed))
        # The body is no longer the bytes the ETag was computed from.
        if "ETag" in response.headers:
            etag = response.headers["ETag"].strip('"')
            response.headers["ETag"] = f'"{etag}-gzip"'
        return response
