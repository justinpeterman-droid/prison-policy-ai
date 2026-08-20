"""Run bounded, content-minimizing health checks through the managed hostname."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


def _json_get(base_url: str, path: str, timeout: float) -> dict:
    request = Request(urljoin(base_url.rstrip("/") + "/", path.lstrip("/")), headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned HTTP {response.status}")
        if response.headers.get_content_type() != "application/json":
            raise RuntimeError(f"{path} returned an unexpected content type")
        payload = response.read(65537)
        if len(payload) > 65536:
            raise RuntimeError(f"{path} response exceeded safe limit")
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise RuntimeError(f"{path} response was not an object")
        return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-release-version", required=True)
    parser.add_argument("--expected-api-version", default="v1")
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        print("smoke test requires a clean HTTPS managed origin", file=sys.stderr)
        return 1
    try:
        health = _json_get(args.base_url, "/health", args.timeout_seconds)
        if health.get("status") not in {"ok", "healthy"}:
            raise RuntimeError("health status is not healthy")
        policy = _json_get(args.base_url, "/api/v1/client-policy", args.timeout_seconds)
        data = policy.get("data", policy)
        if not isinstance(data, dict):
            raise RuntimeError("client policy data is invalid")
        if data.get("release_version") != args.expected_release_version or data.get("api_version") != args.expected_api_version:
            raise RuntimeError("client policy version projection mismatch")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"smoke test failed: {exc}", file=sys.stderr)
        return 1
    print("managed-origin smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
