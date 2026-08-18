# Browser Authentication Session Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browser-safe authentication layer that reuses the existing employee-number/PIN identity system while keeping access and renewal credentials out of React JavaScript.

**Architecture:** Add a same-origin Flask browser-auth blueprint that calls the existing identity services and stores credentials in Secure, HttpOnly, SameSite cookies. Browser-auth middleware resolves/renews the same server-side actor used by `/api/v1`; state-changing browser requests require CSRF tokens. No separate user database or authorization logic is introduced.

**Tech Stack:** Flask, existing `backend.identity` services, PostgreSQL 17, pytest, secure cookies, CSRF double-submit/header token.

**Spec:** `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`

## Global Constraints

- Preserve the existing 4-8 alphanumeric PIN contract.
- Employee/device/network rate limiting and lockout remain enabled.
- React must never receive or persist the renewal token.
- Sensitive authenticated responses must be `Cache-Control: no-store`.
- Shared codes cannot authorize identity-backed APIs.

---

### Task 1: Add browser-auth configuration and cookie primitives

**Files:**
- Create: `backend/webapp/browser_auth/config.py`
- Create: `backend/webapp/browser_auth/cookies.py`
- Create: `tests/unit/test_browser_auth_cookies.py`

**Interfaces:**
- Produces: `BrowserAuthSettings.from_env(env)`, `set_session_cookies(response, pair, csrf_token, settings)`, `clear_session_cookies(response, settings)`.

- [ ] **Step 1: Write failing cookie tests**

```python
def test_session_cookies_are_http_only_and_secure(app):
    response = app.response_class()
    set_session_cookies(response, pair=fake_pair(), csrf_token="csrf", settings=test_settings())
    headers = response.headers.getlist("Set-Cookie")
    assert any("HttpOnly" in h and "Secure" in h and "SameSite=Lax" in h for h in headers)
    assert all("renewal" not in h.lower() or "HttpOnly" in h for h in headers)
```

- [ ] **Step 2: Run test and confirm failure**

Run: `python -m pytest tests/unit/test_browser_auth_cookies.py -q`
Expected: FAIL because the browser-auth package does not exist.

- [ ] **Step 3: Implement settings and cookie helpers**

Define cookie names with a `__Host-` prefix in HTTPS production, `Path=/`, no `Domain`, `Secure`, `HttpOnly` for access/renewal, and a separate readable CSRF cookie. Local test settings may disable `Secure` explicitly.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/unit/test_browser_auth_cookies.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/browser_auth tests/unit/test_browser_auth_cookies.py
git commit -m "feat(auth): add secure browser session cookies"
```

### Task 2: Add login, logout, profile, and PIN-change browser routes

**Files:**
- Create: `backend/webapp/browser_auth/routes.py`
- Modify: `backend/webapp/app.py`
- Create: `tests/unit/test_browser_auth_routes.py`

**Interfaces:**
- Produces endpoints: `POST /web-auth/login`, `POST /web-auth/logout`, `POST /web-auth/change-pin`, `GET /web-auth/session`.
- Reuses: `backend.identity.sessions.login`, `change_pin`, `revoke_session` and existing account/audit services.

- [ ] **Step 1: Write failing login/session tests**

```python
def test_browser_login_returns_profile_without_tokens(client, identity_fixture):
    response = client.post("/web-auth/login", json={
        "employee_number": "1001", "pin": "1234",
        "device_id": "browser-test-1", "device_label": "Safari on iPhone",
        "persistent": False,
    })
    body = response.get_json()
    assert response.status_code == 200
    assert "profile" in body["data"]
    assert "access_token" not in str(body)
    assert "renewal_token" not in str(body)
```

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/unit/test_browser_auth_routes.py -q`
Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement thin route adapters**

Call the same identity service functions used by `/api/v1/auth.py`; translate successful `SessionTokenPair` values into cookies and return only safe session/profile metadata. Reuse existing generic invalid-credential messages and rate-limit behavior.

- [ ] **Step 4: Run focused and existing auth tests**

Run: `python -m pytest tests/unit/test_browser_auth_routes.py tests/unit/test_auth_middleware.py tests/integration/test_auth_rate_limits.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/browser_auth/routes.py backend/webapp/app.py tests/unit/test_browser_auth_routes.py
git commit -m "feat(auth): add browser login and session routes"
```

### Task 3: Add automatic access renewal and actor bridging

**Files:**
- Create: `backend/webapp/browser_auth/middleware.py`
- Modify: `backend/webapp/api_v1/middleware.py` only if a small shared actor helper is required
- Create: `tests/unit/test_browser_session_auth.py`

**Interfaces:**
- Produces: `resolve_browser_actor()` and renewal logic that validates the renewal cookie against the same device ID/session semantics as Access.
- Consumes: existing token/session validation functions.

- [ ] **Step 1: Write failing renewal tests**

```python
def test_expired_access_cookie_renews_with_valid_renewal(client, browser_session):
    browser_session.expire_access_only()
    response = client.get("/web-auth/session")
    assert response.status_code == 200
    assert response.headers.getlist("Set-Cookie")


def test_revoked_session_cannot_be_renewed(client, revoked_browser_session):
    response = client.get("/web-auth/session")
    assert response.status_code == 401
```

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/unit/test_browser_session_auth.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement renewal**

Read access/renewal cookies server-side; when access is expired but renewal remains valid, call the existing renew-session service using the browser's device identifier. Rotate credentials using the existing session semantics and replace cookies atomically.

- [ ] **Step 4: Run auth/session suites**

Run: `python -m pytest tests/unit/test_browser_session_auth.py tests/integration/test_session_rotation.py tests/integration/test_session_concurrency.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/browser_auth/middleware.py backend/webapp/api_v1/middleware.py tests/unit/test_browser_session_auth.py
git commit -m "feat(auth): bridge browser cookies to identity sessions"
```

### Task 4: Enforce CSRF and no-store security policy

**Files:**
- Create: `backend/webapp/browser_auth/security.py`
- Modify: `backend/webapp/app.py`
- Create: `tests/security/test_browser_auth_security.py`

**Interfaces:**
- Produces: CSRF validation for unsafe browser-authenticated methods and `Cache-Control: no-store` on authenticated/sensitive responses.

- [ ] **Step 1: Write failing CSRF/cache tests**

```python
def test_authenticated_post_rejects_missing_csrf(authenticated_client):
    response = authenticated_client.post("/web-api/reports", json={})
    assert response.status_code == 403


def test_authenticated_response_is_no_store(authenticated_client):
    response = authenticated_client.get("/web-auth/session")
    assert "no-store" in response.headers["Cache-Control"]
```

- [ ] **Step 2: Run security test**

Run: `python -m pytest tests/security/test_browser_auth_security.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement security hooks**

Require `X-CSRF-Token` to match the browser CSRF cookie using constant-time comparison for POST/PUT/PATCH/DELETE browser-authenticated routes. Add no-store headers to login/session/account/report/admin/policy responses handled through the browser adapter.

- [ ] **Step 4: Run security and full auth tests**

Run: `python -m pytest tests/security/test_browser_auth_security.py tests/unit/test_browser_auth_cookies.py tests/unit/test_browser_auth_routes.py tests/unit/test_browser_session_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/browser_auth/security.py backend/webapp/app.py tests/security/test_browser_auth_security.py
git commit -m "feat(auth): protect browser sessions with csrf"
```

### Task 5: Add same-origin browser API proxy/adapter boundary

**Files:**
- Create: `backend/webapp/web_api/__init__.py`
- Create: `backend/webapp/web_api/session_context.py`
- Create: `tests/unit/test_web_api_isolation.py`

**Interfaces:**
- Produces a browser-only route namespace `/web-api/*` whose handlers resolve a browser actor then call domain/service functions or shared `/api/v1` implementation helpers without exposing bearer credentials.

- [ ] **Step 1: Write isolation tests**

```python
def test_shared_access_code_cannot_call_web_api(legacy_code_client):
    assert legacy_code_client.get("/web-api/me").status_code == 401


def test_browser_actor_role_is_server_derived(officer_browser_client):
    response = officer_browser_client.get("/web-api/me")
    assert response.get_json()["data"]["role"] == "officer"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/unit/test_web_api_isolation.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement the boundary**

Register `/web-api` only when identity is enabled. Resolve the actor exclusively from browser-auth cookies/session state; never accept role/account/report ownership from request JSON or headers.

- [ ] **Step 4: Run isolation/security suite**

Run: `python -m pytest tests/unit/test_web_api_isolation.py tests/security/test_browser_auth_security.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/web_api tests/unit/test_web_api_isolation.py
git commit -m "feat(web): add authenticated browser api boundary"
```
