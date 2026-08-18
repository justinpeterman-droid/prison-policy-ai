# Guided Operations Web Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the secure browser session adapter, React/TypeScript application shell, Light Precision Workspace design system, responsive navigation, build pipeline, and legacy-safe preview route required by every Guided Operations web feature.

**Architecture:** Flask continues to own authentication, authorization, sessions, audit, and all server data. A new `/api/web/v1` blueprint resolves opaque credentials from HttpOnly cookies and exposes safe profile/session state; a Vite SPA is served under `/workspace` during pilot, with a feature flag that later supports primary-route cutover without removing the legacy Jinja pages.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, Alembic, PostgreSQL 17, React, TypeScript, Vite, React Router, TanStack Query, Zod, Vitest, React Testing Library, MSW, Playwright, CSS variables, and native CSS/WAAPI motion.

**Spec:** `docs/superpowers/specs/2026-08-18-guided-operations-web-frontend-design.md`

## Global Constraints

- The browser app is light-first and uses the approved Light Precision Workspace visual direction.
- Production UI implementation begins only after coordinated high-fidelity concepts are approved.
- Officer navigation is exactly Home, New Report, Reports, Policy Expert, Forms Library, and Account.
- The Access `/api/v1` bearer contract is unchanged.
- Browser access and renewal tokens never enter JavaScript, browser storage, rendered HTML, logs, or API bodies.
- Cookie-authenticated mutations require a session-bound CSRF token, same-origin validation, and idempotency when applicable.
- The legacy shared-code Jinja website remains available during preview and pilot.
- All sample identities and data are fictional.
- No uploaded workbook or real operational record is committed.
- WCAG 2.2 AA, keyboard operation, visible focus, reduced motion, and 44px primary touch targets are release gates.

---

## File Map

```text
frontend/web/
  package.json
  package-lock.json
  tsconfig.json
  vite.config.ts
  playwright.config.ts
  index.html
  src/
    main.tsx
    vite-env.d.ts
    app/App.tsx
    app/providers.tsx
    app/router.tsx
    app/route-guards.tsx
    api/client.ts
    api/errors.ts
    api/query-keys.ts
    api/schemas.ts
    components/layout/AppShell.tsx
    components/layout/Sidebar.tsx
    components/layout/TopBar.tsx
    components/feedback/AppErrorBoundary.tsx
    components/feedback/ConnectionStatus.tsx
    components/primitives/Button.tsx
    components/primitives/Surface.tsx
    components/primitives/Spinner.tsx
    features/auth/api.ts
    features/auth/AuthProvider.tsx
    features/auth/LoginPage.tsx
    features/auth/PinChangePage.tsx
    features/dashboard/HomePlaceholderPage.tsx
    styles/tokens.css
    styles/typography.css
    styles/motion.css
    styles/global.css
    styles/print.css
    test/setup.ts
    test/server.ts
    test/handlers.ts
  tests/e2e/auth-shell.spec.ts

backend/identity/browser_sessions.py
backend/persistence/models/browser.py
backend/persistence/models/__init__.py
backend/webapp/web_api/__init__.py
backend/webapp/web_api/context.py
backend/webapp/web_api/middleware.py
backend/webapp/web_api/auth.py
backend/webapp/web_api/responses.py
backend/webapp/routes/web_app.py
backend/webapp/app.py
backend/webapp/static/web/

migrations/versions/20260818_0006_browser_sessions.py
openapi/web-v1.yaml
Dockerfile
.dockerignore
.gitignore

scripts/check_web_build.py
tests/contract/test_web_v1_openapi.py
tests/integration/test_web_auth.py
tests/security/test_web_cookie_security.py
tests/unit/test_browser_sessions.py
tests/unit/test_web_app_routes.py
tests/unit/test_web_csrf.py
```

## Shared Interfaces Produced by This Plan

```python
@dataclass(frozen=True)
class BrowserActor:
    account_id: UUID
    staff_member_id: UUID
    session_id: UUID
    role: Literal["user", "admin"]
    auth_version: int
    must_change_pin: bool

@dataclass(frozen=True)
class BrowserCookiePair:
    access_token: str
    renewal_token: str
    csrf_token: str
    access_expires_at: datetime
    renewal_expires_at: datetime
    persistent: bool


def create_browser_session(...) -> tuple[BrowserActor, BrowserCookiePair]: ...
def renew_browser_session(...) -> tuple[BrowserActor, BrowserCookiePair]: ...
def resolve_browser_actor(...) -> BrowserActor: ...
def revoke_browser_session(...) -> None: ...
def validate_browser_csrf(...) -> None: ...
```

The SPA consumes this safe envelope:

```ts
export interface SessionProfile {
  accountId: string;
  staffId: string;
  sessionId: string;
  employeeNumber: string;
  displayName: string;
  rank: string | null;
  shift: string | null;
  role: "user" | "admin";
  mustChangePin: boolean;
}

export interface BrowserSessionState {
  authenticated: boolean;
  profile: SessionProfile | null;
  csrfToken: string | null;
}
```

### Task 1: Create and approve the visual concept pack

**Files:**
- Create: `docs/design/guided-operations/README.md`
- Create: `docs/design/guided-operations/officer-home-desktop.png`
- Create: `docs/design/guided-operations/officer-home-mobile.png`
- Create: `docs/design/guided-operations/app-shell-desktop.png`
- Create: `docs/design/guided-operations/app-shell-mobile.png`
- Create: `docs/design/guided-operations/component-fixtures.png`

**Interfaces:**
- Consumes: approved master design specification.
- Produces: the visual implementation contract for Tasks 9–12.

- [ ] **Step 1: Generate coordinated concepts**

Create the five named images using one Light Precision Workspace system. The component fixture sheet must show the raised gold primary button, ceramic secondary button, navigation selected state, tab fixture, save-state fixture, paper surface, input, select, checkbox, modal, and reduced-motion equivalent.

- [ ] **Step 2: Record exact visual tokens**

Create `docs/design/guided-operations/README.md` with this structure:

```markdown
# Guided Operations Visual Contract

## Approved screens
- `officer-home-desktop.png`
- `officer-home-mobile.png`
- `app-shell-desktop.png`
- `app-shell-mobile.png`
- `component-fixtures.png`

## Locked palette
- Canvas: `#F4F6F5`
- Surface: `#FFFFFF`
- Raised surface: `#FAFBFC`
- Inset surface: `#E9EEF1`
- Primary navy: `#1B2E45`
- Secondary slate: `#58728A`
- Muted gold: `#B58A3B`
- Gold highlight: `#D8B66A`
- Primary text: `#17212D`
- Secondary text: `#627080`
- Border: `#D7DEE4`
- Focus: `#2E6FA3`

## Locked behavior
- Primary controls travel 2px on press.
- Navigation transitions finish within 240ms.
- Reduced motion removes transform travel.
- Officer navigation contains exactly six items.
```

- [ ] **Step 3: Review the complete concept pack with the user**

Do not begin Task 2 until the user explicitly approves the concept pack or requested revisions have been incorporated.

- [ ] **Step 4: Commit**

```bash
git add docs/design/guided-operations
git commit -m "design: approve guided operations visual contract"
```

### Task 2: Scaffold the React/TypeScript/Vite application and test harness

**Files:**
- Create: `frontend/web/**`
- Modify: `.gitignore`
- Test: `frontend/web/src/app/App.test.tsx`

**Interfaces:**
- Consumes: Task 1 visual contract.
- Produces: `npm run build`, `npm run test`, `npm run test:e2e`, and `npm run typecheck`.

- [ ] **Step 1: Generate the project**

Run from the repository root:

```bash
npm create vite@latest frontend/web -- --template react-ts
cd frontend/web
npm install react-router-dom @tanstack/react-query zod
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event msw playwright @playwright/test eslint eslint-plugin-react-hooks eslint-plugin-react-refresh axe-core
```

- [ ] **Step 2: Replace package scripts**

Set the scripts in `frontend/web/package.json` to:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint ."
  }
}
```

- [ ] **Step 3: Configure Vitest**

Add to `frontend/web/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/static/web/",
  plugins: [react()],
  build: {
    outDir: "../../backend/webapp/static/web",
    emptyOutDir: true,
    manifest: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
```

- [ ] **Step 4: Write the failing smoke test**

Create `frontend/web/src/app/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { App } from "./App";

it("renders the Guided Operations application", () => {
  render(<App />);
  expect(screen.getByText("Standard Logistics & Unit Tools")).toBeInTheDocument();
});
```

- [ ] **Step 5: Run the test and verify failure**

```bash
npm run test -- src/app/App.test.tsx
```

Expected: FAIL because `App` does not yet export the required application title.

- [ ] **Step 6: Add the minimal App component**

```tsx
export function App() {
  return <main>Standard Logistics & Unit Tools</main>;
}
```

- [ ] **Step 7: Verify the scaffold**

```bash
npm run typecheck
npm run test
npm run build
```

Expected: all commands pass and `backend/webapp/static/web/.vite/manifest.json` exists.

- [ ] **Step 8: Ignore local artifacts and commit**

Append to `.gitignore`:

```text
frontend/web/node_modules/
frontend/web/playwright-report/
frontend/web/test-results/
backend/webapp/static/web/
```

Then commit:

```bash
git add frontend/web .gitignore
git commit -m "build: scaffold guided operations web client"
```

### Task 3: Add deterministic frontend build integration to Docker and local checks

**Files:**
- Modify: `Dockerfile`
- Modify: `.dockerignore`
- Create: `scripts/check_web_build.py`
- Test: `tests/unit/test_web_build_contract.py`

**Interfaces:**
- Consumes: `frontend/web/package-lock.json` and `npm run build`.
- Produces: `/app/backend/webapp/static/web/index.html` and hashed assets in the runtime image.

- [ ] **Step 1: Write the failing build-contract test**

Create `tests/unit/test_web_build_contract.py`:

```python
from pathlib import Path


def test_dockerfile_builds_and_copies_web_assets():
    text = Path("Dockerfile").read_text(encoding="utf-8")
    assert "FROM node:" in text
    assert "npm ci" in text
    assert "npm run build" in text
    assert "COPY --from=web-build" in text
```

- [ ] **Step 2: Run the test and verify failure**

```bash
python -m pytest tests/unit/test_web_build_contract.py -v
```

Expected: FAIL because the Dockerfile has no Node build stage.

- [ ] **Step 3: Convert Dockerfile to a multi-stage build**

Use this structure:

```dockerfile
FROM node:lts-slim AS web-build
WORKDIR /src
COPY frontend/web/package.json frontend/web/package-lock.json ./frontend/web/
RUN cd frontend/web && npm ci
COPY frontend/web/ ./frontend/web/
RUN cd frontend/web && npm run build

FROM python:3.14-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY --from=web-build /src/backend/webapp/static/web/ /app/backend/webapp/static/web/
COPY templates/ /app/templates/
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
COPY scripts/dispatch_outbox.py /app/scripts/dispatch_outbox.py
ENV PORT=8080
ENV PYTHONPATH=/app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 300 --pythonpath /app "backend.webapp.app:create_app()"
```

- [ ] **Step 4: Add a local manifest check**

Create `scripts/check_web_build.py`:

```python
from pathlib import Path
import json

root = Path("backend/webapp/static/web")
index = root / "index.html"
manifest = root / ".vite" / "manifest.json"
if not index.is_file() or not manifest.is_file():
    raise SystemExit("web build is missing index.html or manifest.json")
value = json.loads(manifest.read_text(encoding="utf-8"))
if not isinstance(value, dict) or not value:
    raise SystemExit("web manifest is empty")
print("web build verified")
```

- [ ] **Step 5: Verify build and image**

```bash
cd frontend/web && npm ci && npm run build && cd ../..
python scripts/check_web_build.py
docker build -t prison-policy-ai:web-foundation .
```

Expected: all commands succeed.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile .dockerignore scripts/check_web_build.py tests/unit/test_web_build_contract.py
git commit -m "build: package guided operations web assets"
```

### Task 4: Add browser-session persistence and migration

**Files:**
- Create: `backend/persistence/models/browser.py`
- Modify: `backend/persistence/models/__init__.py`
- Create: `migrations/versions/20260818_0006_browser_sessions.py`
- Test: `tests/unit/test_browser_session_model.py`
- Test: `tests/integration/test_browser_session_migration.py`

**Interfaces:**
- Consumes: `AccessSession.id`.
- Produces: `BrowserSessionBinding` keyed one-to-one by session ID.

- [ ] **Step 1: Write the failing model test**

```python
from backend.persistence.models.browser import BrowserSessionBinding


def test_browser_session_binding_table_contract():
    table = BrowserSessionBinding.__table__
    assert table.name == "browser_session_bindings"
    assert table.c.session_id.primary_key
    assert table.c.csrf_token_hash.nullable is False
    assert table.c.csrf_token_hash.type.length == 32
```

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_browser_session_model.py -v
```

Expected: FAIL because the model does not exist.

- [ ] **Step 3: Implement the model**

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


class BrowserSessionBinding(Base):
    __tablename__ = "browser_session_bindings"
    __table_args__ = (
        CheckConstraint("octet_length(csrf_token_hash) = 32", name="browser_csrf_hash_length"),
    )

    session_id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    csrf_token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Step 4: Add the migration**

The migration must create the table exactly as the model defines and use revision metadata:

```python
revision = "20260818_0006"
down_revision = "20260812_0005"
```

- [ ] **Step 5: Verify migration lifecycle**

```bash
python -m pytest tests/unit/test_browser_session_model.py tests/integration/test_browser_session_migration.py -v
alembic upgrade head
alembic downgrade 20260812_0005
alembic upgrade head
```

Expected: tests pass and the migration completes upgrade/downgrade/upgrade.

- [ ] **Step 6: Commit**

```bash
git add backend/persistence/models migrations/versions/20260818_0006_browser_sessions.py tests/unit/test_browser_session_model.py tests/integration/test_browser_session_migration.py
git commit -m "feat: add browser session bindings"
```

### Task 5: Implement browser-session domain services and CSRF validation

**Files:**
- Create: `backend/identity/browser_sessions.py`
- Test: `tests/unit/test_browser_sessions.py`
- Test: `tests/unit/test_web_csrf.py`

**Interfaces:**
- Consumes: existing `login`, `renew_session`, `resolve_access_session`, and `revoke_session` services.
- Produces: the shared browser-session interfaces in this plan header.

- [ ] **Step 1: Write failing service tests**

Cover these exact behaviors:

```python
def test_create_browser_session_returns_actor_and_cookie_pair(): ...
def test_renew_rotates_access_renewal_and_csrf_values(): ...
def test_resolve_browser_actor_rejects_expired_access_token(): ...
def test_validate_browser_csrf_accepts_matching_token(): ...
def test_validate_browser_csrf_rejects_mismatch(): ...
def test_revoke_browser_session_revokes_underlying_access_session(): ...
```

Use fictional account/staff fixtures and assert that only SHA-256 digests are persisted.

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_browser_sessions.py tests/unit/test_web_csrf.py -v
```

Expected: FAIL because `backend.identity.browser_sessions` does not exist.

- [ ] **Step 3: Implement credential helpers**

```python
from secrets import token_urlsafe
from hashlib import sha256


def issue_csrf_token() -> tuple[str, bytes]:
    raw = token_urlsafe(32)
    return raw, sha256(raw.encode("ascii")).digest()


def hash_csrf_token(raw: str) -> bytes:
    if not 32 <= len(raw) <= 256 or not raw.isascii():
        raise ValueError("csrf token is invalid")
    return sha256(raw.encode("ascii")).digest()
```

- [ ] **Step 4: Implement the public services**

The implementation must call the existing identity services, create or rotate `BrowserSessionBinding`, return `BrowserActor`, and never log readable credentials.

```python
def validate_browser_csrf(db: Session, *, session_id: UUID, supplied_token: str) -> None:
    binding = db.get(BrowserSessionBinding, session_id)
    if binding is None or not compare_digest(binding.csrf_token_hash, hash_csrf_token(supplied_token)):
        raise BrowserCsrfInvalid("Request verification failed.")
```

- [ ] **Step 5: Verify tests**

```bash
python -m pytest tests/unit/test_browser_sessions.py tests/unit/test_web_csrf.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/identity/browser_sessions.py tests/unit/test_browser_sessions.py tests/unit/test_web_csrf.py
git commit -m "feat: add secure browser session service"
```

### Task 6: Create the `/api/web/v1` envelope, request context, and middleware

**Files:**
- Create: `backend/webapp/web_api/__init__.py`
- Create: `backend/webapp/web_api/context.py`
- Create: `backend/webapp/web_api/responses.py`
- Create: `backend/webapp/web_api/middleware.py`
- Modify: `backend/webapp/app.py`
- Test: `tests/unit/test_web_api_responses.py`
- Test: `tests/security/test_web_cookie_security.py`

**Interfaces:**
- Consumes: `BrowserActor`, Flask request context, existing audit writer.
- Produces: `current_browser_actor`, `current_web_db_session`, `require_browser_session`, `require_web_role`, and `require_web_csrf`.

- [ ] **Step 1: Write failing response and middleware tests**

Assert:

```python
def test_web_success_envelope_contains_request_id_server_time_and_api_version(): ...
def test_missing_access_cookie_returns_authentication_required(): ...
def test_mutation_rejects_missing_origin(): ...
def test_mutation_rejects_cross_site_fetch(): ...
def test_mutation_rejects_missing_csrf_header(): ...
def test_admin_guard_rejects_user_actor(): ...
```

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_web_api_responses.py tests/security/test_web_cookie_security.py -v
```

- [ ] **Step 3: Implement the response envelope**

```python
def success(data: object, status: int = 200):
    return jsonify({
        "data": data,
        "request_id": g.request_id,
        "server_time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "api_version": "web-v1",
    }), status
```

Implement matching `failure` with stable code, safe message, retryable flag, details, request ID, and server time.

- [ ] **Step 4: Implement cookie authentication**

`require_browser_session` must:

1. read `slut_web_access`;
2. open one `session_scope()` context;
3. resolve the actor through `resolve_browser_actor`;
4. attach actor and DB session to `g`;
5. reject required-PIN-change routes except `/auth/change-pin`, `/auth/logout`, and `/auth/logout-all`; and
6. close the DB context in blueprint teardown.

- [ ] **Step 5: Implement CSRF and origin checks**

`require_web_csrf` must require:

```text
Origin == request.host_url without trailing slash
Sec-Fetch-Site in {same-origin, same-site}
X-CSRF-Token matches the session-bound digest
```

Local tests may omit `Sec-Fetch-Site` only when `app.testing` is true and must still supply a valid Origin and CSRF token.

- [ ] **Step 6: Register the blueprint only when identity is enabled**

In `create_app()`:

```python
if identity_settings.enabled:
    from backend.webapp.web_api import web_api_bp
    app.register_blueprint(web_api_bp)
```

- [ ] **Step 7: Run tests and commit**

```bash
python -m pytest tests/unit/test_web_api_responses.py tests/security/test_web_cookie_security.py -v
git add backend/webapp/web_api backend/webapp/app.py tests/unit/test_web_api_responses.py tests/security/test_web_cookie_security.py
git commit -m "feat: add browser web API middleware"
```

### Task 7: Add browser authentication, renewal, profile, PIN, and session routes

**Files:**
- Create: `backend/webapp/web_api/auth.py`
- Modify: `backend/webapp/web_api/__init__.py`
- Create: `openapi/web-v1.yaml`
- Test: `tests/integration/test_web_auth.py`
- Test: `tests/contract/test_web_v1_openapi.py`

**Interfaces:**
- Consumes: Tasks 4–6 and existing identity services.
- Produces: `/api/web/v1/auth/*` and `/api/web/v1/me`.

- [ ] **Step 1: Write failing integration tests**

Test this lifecycle:

```text
POST /api/web/v1/auth/login
GET  /api/web/v1/me
POST /api/web/v1/auth/renew
GET  /api/web/v1/auth/sessions
POST /api/web/v1/auth/change-pin
DELETE /api/web/v1/auth/sessions/{session_id}
POST /api/web/v1/auth/logout-all
```

Assert that login JSON contains no access or renewal token and `Set-Cookie` includes `HttpOnly`, `SameSite=Lax`, bounded paths, and `Secure` under HTTPS.

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/integration/test_web_auth.py -v
```

- [ ] **Step 3: Implement cookie helpers**

```python
ACCESS_COOKIE = "slut_web_access"
RENEWAL_COOKIE = "slut_web_renewal"
DEVICE_COOKIE = "slut_web_device"
CSRF_COOKIE = "slut_web_csrf"


def apply_browser_cookies(response, pair: BrowserCookiePair, *, device_id: str, secure: bool):
    response.set_cookie(ACCESS_COOKIE, pair.access_token, httponly=True, secure=secure, samesite="Lax", path="/")
    response.set_cookie(RENEWAL_COOKIE, pair.renewal_token, httponly=True, secure=secure, samesite="Lax", path="/api/web/v1/auth")
    response.set_cookie(DEVICE_COOKIE, device_id, httponly=True, secure=secure, samesite="Lax", path="/")
    response.set_cookie(CSRF_COOKIE, pair.csrf_token, httponly=False, secure=secure, samesite="Lax", path="/")
    return response
```

Use explicit max ages derived from the returned expiration values.

- [ ] **Step 4: Implement closed request bodies**

Login accepts exactly:

```json
{"employee_number":"E1001","pin":"A12345","persistent":true}
```

Renew accepts an empty body and reads renewal/device cookies. Responses return profile and expiry metadata only.

- [ ] **Step 5: Implement OpenAPI contract**

`openapi/web-v1.yaml` must define every route, cookie security scheme, CSRF header, success envelope, stable errors, and closed request schemas.

- [ ] **Step 6: Verify contract and lifecycle**

```bash
python -m pytest tests/integration/test_web_auth.py tests/contract/test_web_v1_openapi.py tests/security/test_web_cookie_security.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/webapp/web_api/auth.py backend/webapp/web_api/__init__.py openapi/web-v1.yaml tests/integration/test_web_auth.py tests/contract/test_web_v1_openapi.py
git commit -m "feat: add browser authentication API"
```

### Task 8: Add SPA preview routing and legacy-safe feature flags

**Files:**
- Create: `backend/webapp/routes/web_app.py`
- Modify: `backend/webapp/app.py`
- Modify: `backend/identity/config.py`
- Test: `tests/unit/test_web_app_routes.py`

**Interfaces:**
- Consumes: built SPA assets.
- Produces: preview routes under `/workspace` and `WEB_APP_MODE=off|preview|primary`.

- [ ] **Step 1: Write failing route tests**

```python
def test_preview_mode_serves_spa_under_workspace(client): ...
def test_preview_mode_preserves_legacy_home_reports_and_chat(client): ...
def test_unknown_workspace_path_returns_spa_for_client_routing(client): ...
def test_missing_web_build_returns_safe_503(client): ...
def test_off_mode_returns_404_for_workspace(client): ...
```

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tests/unit/test_web_app_routes.py -v
```

- [ ] **Step 3: Add validated configuration**

`IdentitySettings` or a focused web setting must parse:

```text
WEB_APP_MODE=off|preview|primary
```

Any other value raises at startup. Default is `off`.

- [ ] **Step 4: Implement the SPA route**

```python
web_app_bp = Blueprint("web_app", __name__)

@web_app_bp.get("/workspace")
@web_app_bp.get("/workspace/<path:client_path>")
def workspace(client_path: str = ""):
    if current_app.config["WEB_APP_MODE"] == "off":
        abort(404)
    index = Path(current_app.static_folder) / "web" / "index.html"
    if not index.is_file():
        return "The web workspace is temporarily unavailable.", 503
    return send_file(index)
```

Primary-route cutover is reserved for the rollout plan; preview mode must not collide with current `/`, `/chat`, or `/reports` routes.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/unit/test_web_app_routes.py -v
git add backend/webapp/routes/web_app.py backend/webapp/app.py backend/identity/config.py tests/unit/test_web_app_routes.py
git commit -m "feat: serve web workspace behind preview flag"
```

### Task 9: Implement the typed frontend API client and authentication provider

**Files:**
- Create: `frontend/web/src/api/client.ts`
- Create: `frontend/web/src/api/errors.ts`
- Create: `frontend/web/src/api/schemas.ts`
- Create: `frontend/web/src/api/query-keys.ts`
- Create: `frontend/web/src/features/auth/api.ts`
- Create: `frontend/web/src/features/auth/AuthProvider.tsx`
- Create: `frontend/web/src/test/handlers.ts`
- Create: `frontend/web/src/test/server.ts`
- Test: `frontend/web/src/features/auth/AuthProvider.test.tsx`

**Interfaces:**
- Consumes: Task 7 HTTP contract.
- Produces: `apiRequest<T>()`, `useAuth()`, `login()`, `renew()`, and `logout()`.

- [ ] **Step 1: Write failing AuthProvider tests**

Test unauthenticated bootstrap, authenticated profile load, one renewal attempt after `authentication_required`, transient renewal failure preserving profile, and definitive rejection clearing profile.

- [ ] **Step 2: Implement strict schemas**

```ts
import { z } from "zod";

export const sessionProfileSchema = z.object({
  account_id: z.string().uuid(),
  staff_id: z.string().uuid(),
  session_id: z.string().uuid(),
  employee_number: z.string().min(1),
  display_name: z.string().min(1),
  rank: z.string().nullable(),
  shift: z.string().nullable(),
  role: z.enum(["user", "admin"]),
  must_change_pin: z.boolean(),
}).strict();
```

Every API response is parsed before state changes.

- [ ] **Step 3: Implement the request client**

`apiRequest` must:

- use `credentials: "same-origin"`;
- add `Accept: application/json`;
- add `Content-Type` only for JSON bodies;
- add `X-Client-Version` from `__APP_VERSION__`;
- add `X-Request-ID` from `crypto.randomUUID()`;
- read `slut_web_csrf` and add `X-CSRF-Token` for mutations;
- parse the safe error envelope; and
- never log bodies or cookie values.

- [ ] **Step 4: Implement exactly one renewal retry**

Use an in-memory shared renewal promise so concurrent 401 responses trigger one `POST /api/web/v1/auth/renew`. Retry the original request once after successful renewal and never recurse.

- [ ] **Step 5: Verify tests**

```bash
cd frontend/web
npm run test -- src/features/auth/AuthProvider.test.tsx
npm run typecheck
```

- [ ] **Step 6: Commit**

```bash
git add frontend/web/src/api frontend/web/src/features/auth frontend/web/src/test
git commit -m "feat: add typed browser auth client"
```

### Task 10: Build login, required-PIN-change, and route guards

**Files:**
- Create: `frontend/web/src/features/auth/LoginPage.tsx`
- Create: `frontend/web/src/features/auth/PinChangePage.tsx`
- Create: `frontend/web/src/app/route-guards.tsx`
- Test: `frontend/web/src/features/auth/LoginPage.test.tsx`
- Test: `frontend/web/src/app/route-guards.test.tsx`

**Interfaces:**
- Consumes: `useAuth()`.
- Produces: `RequireSession`, `RequirePinChanged`, and `RequireRole`.

- [ ] **Step 1: Write failing interaction tests**

Assert employee number, 4–8 character PIN, Keep me signed in, disabled submit while pending, safe invalid-credential copy, temporary PIN redirect, and preservation of the requested route after login.

- [ ] **Step 2: Implement LoginPage**

The form uses labels, autocomplete values `username` and `current-password`, no branding terms prohibited on the public login screen, and one primary `Sign In` action.

- [ ] **Step 3: Implement route guards**

```tsx
export function RequireSession({ children }: { children: React.ReactNode }) {
  const { state } = useAuth();
  if (state.status === "loading") return <FullPageSpinner label="Checking your session" />;
  if (state.status === "anonymous") return <Navigate to="/workspace/login" replace />;
  return <>{children}</>;
}
```

`RequireRole` must render a not-found route for unauthorized users rather than exposing admin navigation.

- [ ] **Step 4: Verify tests and commit**

```bash
cd frontend/web
npm run test -- src/features/auth/LoginPage.test.tsx src/app/route-guards.test.tsx
npm run typecheck
git add src/features/auth src/app/route-guards.tsx
git commit -m "feat: add web login and route guards"
```

### Task 11: Build the responsive application shell and locked navigation

**Files:**
- Create: `frontend/web/src/app/providers.tsx`
- Create: `frontend/web/src/app/router.tsx`
- Create: `frontend/web/src/components/layout/AppShell.tsx`
- Create: `frontend/web/src/components/layout/Sidebar.tsx`
- Create: `frontend/web/src/components/layout/TopBar.tsx`
- Create: `frontend/web/src/features/dashboard/HomePlaceholderPage.tsx`
- Modify: `frontend/web/src/app/App.tsx`
- Test: `frontend/web/src/components/layout/AppShell.test.tsx`

**Interfaces:**
- Consumes: auth state and React Router.
- Produces: shared shell slots for all later plans.

- [ ] **Step 1: Write failing navigation tests**

Assert the six officer items in exact order, admin section only for role `admin`, current-user block, current-route `aria-current="page"`, keyboard drawer operation, Escape close, and focus return.

- [ ] **Step 2: Define route objects**

```ts
const officerNav = [
  ["Home", "/workspace/home"],
  ["New Report", "/workspace/new-report"],
  ["Reports", "/workspace/reports"],
  ["Policy Expert", "/workspace/policy-expert"],
  ["Forms Library", "/workspace/forms"],
  ["Account", "/workspace/account"],
] as const;
```

Do not add extra officer navigation entries.

- [ ] **Step 3: Implement responsive shell**

Desktop uses a fixed 248px sidebar and top utility bar. Tablet uses a 72px icon rail. Mobile uses a modal drawer with inert background, focus trap, Escape handling, and route-change close.

- [ ] **Step 4: Add route placeholders**

Each future route renders a plain titled placeholder inside the real shell. This proves routing without inventing feature UI before its plan.

- [ ] **Step 5: Verify tests and commit**

```bash
cd frontend/web
npm run test -- src/components/layout/AppShell.test.tsx
npm run typecheck
git add src/app src/components/layout src/features/dashboard/HomePlaceholderPage.tsx
git commit -m "feat: add guided operations application shell"
```

### Task 12: Implement Light Precision Workspace tokens and dimensional primitives

**Files:**
- Create: `frontend/web/src/styles/tokens.css`
- Create: `frontend/web/src/styles/typography.css`
- Create: `frontend/web/src/styles/motion.css`
- Create: `frontend/web/src/styles/global.css`
- Create: `frontend/web/src/styles/print.css`
- Create: `frontend/web/src/components/primitives/Button.tsx`
- Create: `frontend/web/src/components/primitives/Surface.tsx`
- Create: `frontend/web/src/components/primitives/Spinner.tsx`
- Test: `frontend/web/src/components/primitives/Button.test.tsx`

**Interfaces:**
- Consumes: Task 1 visual contract.
- Produces: `Button`, `Surface`, and shared CSS tokens used by every later plan.

- [ ] **Step 1: Write failing primitive tests**

Assert button variants, disabled state, pending label, icon label requirement, and no motion class when reduced motion is enabled.

- [ ] **Step 2: Define exact token variables**

```css
:root {
  --color-canvas: #f4f6f5;
  --color-surface: #ffffff;
  --color-raised: #fafbfc;
  --color-inset: #e9eef1;
  --color-navy: #1b2e45;
  --color-slate: #58728a;
  --color-gold: #b58a3b;
  --color-gold-highlight: #d8b66a;
  --color-text: #17212d;
  --color-text-muted: #627080;
  --color-border: #d7dee4;
  --color-focus: #2e6fa3;
  --radius-control: 11px;
  --shadow-control: 0 5px 0 #7f5d22, 0 10px 20px rgb(27 46 69 / 14%);
  --duration-control: 150ms;
  --duration-navigation: 220ms;
  --duration-panel: 300ms;
}
```

- [ ] **Step 3: Implement the raised primary control**

The primary button uses the approved gold gradient, 2px press travel, compressed active shadow, explicit 44px minimum height, visible focus, and no full-pill radius.

- [ ] **Step 4: Implement reduced-motion override**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 1ms !important;
  }
  .raised-control:active { transform: none; }
}
```

- [ ] **Step 5: Compare browser render to approved fixtures**

Capture the shell and buttons at the concept dimensions. Record at least five comparison points in `docs/design/guided-operations/README.md`: palette, button depth, sidebar width, type hierarchy, and focus treatment. Fix every unapproved difference.

- [ ] **Step 6: Verify and commit**

```bash
cd frontend/web
npm run test -- src/components/primitives/Button.test.tsx
npm run typecheck
git add src/styles src/components/primitives docs/design/guided-operations/README.md
git commit -m "feat: add light precision design system"
```

### Task 13: Add safe error boundaries, connection state, and query defaults

**Files:**
- Create: `frontend/web/src/components/feedback/AppErrorBoundary.tsx`
- Create: `frontend/web/src/components/feedback/ConnectionStatus.tsx`
- Modify: `frontend/web/src/app/providers.tsx`
- Test: `frontend/web/src/components/feedback/ConnectionStatus.test.tsx`
- Test: `frontend/web/src/components/feedback/AppErrorBoundary.test.tsx`

**Interfaces:**
- Consumes: TanStack Query network state and safe API errors.
- Produces: reusable error and connection UI.

- [ ] **Step 1: Write failing tests**

Assert Online, Reconnecting, and Offline text; no color-only meaning; safe retry; request ID display; and no rendering of raw stack or HTML.

- [ ] **Step 2: Configure query defaults**

Use:

```ts
new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: 15_000, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
});
```

Feature modules explicitly opt into bounded retries only for safe reads.

- [ ] **Step 3: Implement safe error copy**

Unknown errors render:

```text
We could not complete that action. Your visible work has not been cleared.
```

When a request ID exists, show `Reference: <request-id>`.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend/web
npm run test -- src/components/feedback
npm run typecheck
git add src/components/feedback src/app/providers.tsx
git commit -m "feat: add web connection and error states"
```

### Task 14: Add end-to-end, accessibility, security, and documentation gates

**Files:**
- Create: `frontend/web/playwright.config.ts`
- Create: `frontend/web/tests/e2e/auth-shell.spec.ts`
- Create: `frontend/web/tests/e2e/accessibility.spec.ts`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `.github/workflows/tests.yml`
- Test: all foundation tests.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: a verified foundation ready for the Incident Workspace and Officer Utilities plans.

- [ ] **Step 1: Configure Playwright**

Use Chromium desktop 1366×768, tablet 1024×768, and mobile 390×844 projects. The test server runs Flask with `WEB_APP_MODE=preview`, identity test fixtures, and built web assets.

- [ ] **Step 2: Add the authenticated shell E2E path**

```ts
test("employee signs in and sees the locked officer navigation", async ({ page }) => {
  await page.goto("/workspace/login");
  await page.getByLabel("Employee number").fill("E1001");
  await page.getByLabel("PIN").fill("A12345");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("navigation")).toContainText("Home");
  await expect(page.getByRole("navigation")).toContainText("Forms Library");
});
```

- [ ] **Step 3: Add accessibility assertions**

Run axe-core against login, desktop shell, mobile drawer, and required-PIN-change page; fail on serious or critical violations. Also verify keyboard-only navigation and reduced-motion media emulation.

- [ ] **Step 4: Add CI commands**

The workflow runs:

```bash
cd frontend/web
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
cd ../..
python -m pytest tests/unit/test_web_* tests/integration/test_web_auth.py tests/contract/test_web_v1_openapi.py tests/security/test_web_cookie_security.py -v
```

- [ ] **Step 5: Document local commands and preview URL**

README and AGENTS must state:

```text
npm ci --prefix frontend/web
npm run build --prefix frontend/web
WEB_APP_MODE=preview ACCESS_CODE="" PYTHONPATH=. python backend/webapp/app.py
Open http://localhost:8080/workspace/login
```

- [ ] **Step 6: Run the complete foundation verification twice**

```bash
cd frontend/web && npm ci && npm run lint && npm run typecheck && npm run test && npm run build && npm run test:e2e && cd ../..
python -m pytest tests/unit tests/contract tests/security -q
```

Run the same sequence a second time. Both runs must pass.

- [ ] **Step 7: Self-review against the spec**

Confirm:

- exactly six officer nav items;
- no dark-first page;
- no tokens in JavaScript;
- legacy routes preserved;
- secure cookie flags;
- CSRF and origin protection;
- desktop/tablet/mobile behavior;
- reduced motion;
- fictional fixtures only; and
- approved concept fidelity.

- [ ] **Step 8: Commit**

```bash
git add frontend/web/playwright.config.ts frontend/web/tests README.md AGENTS.md .github/workflows/tests.yml
git commit -m "test: verify guided operations web foundation"
```

## Foundation Completion Gate

The Incident Workspace, Officer Utilities, Admin Command Center, and Paperwork plans may begin only when:

- every task above is committed;
- the approved concept pack is present;
- all foundation checks pass twice;
- `/api/v1` contract tests remain unchanged and green;
- browser auth security tests pass;
- `/workspace` preview does not alter `/`, `/chat`, `/reports`, `/roster`, or `/review-lab`; and
- the user approves the rendered foundation shell at desktop and mobile sizes.
