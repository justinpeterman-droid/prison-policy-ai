# Web Cutover and Shared-Code Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the completed React Officer/Admin companion to the primary web product, prove cross-client parity, retire shared access/admin codes, and release through controlled production gates.

**Architecture:** Keep legacy Flask pages restricted during pilot acceptance, then switch `/` to the compiled React application and remove the old shared-code authentication/configuration entirely. Recovery remains through documented Admin bootstrap/operations procedures, not a permanent universal credential.

**Tech Stack:** React/Vite, Flask, PostgreSQL 17, Playwright, pytest, Docker/Cloud Run, Terraform/GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`

## Global Constraints

- Do not cut over until both Officer and Admin parity acceptance passes.
- A report created in one client must retain the same report/revision identity in the other.
- Shared-code legacy access must not reach identity-backed APIs during pilot.
- Final production has no `ACCESS_CODE` or `ADMIN_CODE` fallback.
- Production release must pass the repository's full backend, database, container, security, and supply-chain gates.

---

### Task 1: Enforce restricted legacy coexistence during pilot

**Files:**
- Modify: `backend/webapp/app.py`
- Modify: `backend/webapp/routes/reports.py`
- Create: `tests/security/test_legacy_identity_isolation.py`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: legacy shared-code cookie gate and identity-enabled configuration.
- Produces: legacy pages limited to explicitly approved transient fallback behavior; no `/api/v1` or `/web-api` access from shared codes.

- [ ] **Step 1: Write failing isolation tests**

```python
def test_access_code_cannot_reach_identity_backed_api(legacy_access_client):
    assert legacy_access_client.get("/web-api/me").status_code == 401
    assert legacy_access_client.get("/api/v1/reports").status_code in {401, 403}


def test_admin_code_does_not_become_identity_admin(legacy_admin_client):
    assert legacy_admin_client.get("/web-api/admin/overview").status_code == 401
```

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/security/test_legacy_identity_isolation.py -q`
Expected: FAIL if any shared-code path leaks into identity-backed authorization.

- [ ] **Step 3: Implement explicit isolation**

Keep legacy cookie checks scoped only to legacy Flask page/routes. Identity `/api/v1`, `/web-auth`, and `/web-api` require individual identity sessions and ignore legacy access/admin cookies.

- [ ] **Step 4: Re-run security tests**

Run: `python -m pytest tests/security/test_legacy_identity_isolation.py tests/unit/test_legacy_report_route_types.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/app.py backend/webapp/routes/reports.py tests/security/test_legacy_identity_isolation.py HANDOFF.md
git commit -m "security: isolate legacy shared-code access"
```

### Task 2: Add cross-client Access/web acceptance tests and runbook

**Files:**
- Create: `docs/runbooks/web-access-cross-client-acceptance.md`
- Create: `tests/acceptance/test_cross_client_contract.py`
- Extend: Access test fixtures/helpers only as required for fictional test environment.

**Interfaces:**
- Produces: repeatable evidence that Access and web operate on identical accounts/reports/revisions.

- [ ] **Step 1: Add contract assertions for shared identity/report IDs**

```python
def test_web_and_access_use_same_report_identity(api_client, fictional_officer):
    created = api_client.create_report(actor=fictional_officer)
    assert api_client.get_report_as_access(created["id"])["id"] == created["id"]
    assert api_client.get_report_as_web(created["id"])["revision"] == created["revision"]
```

This harness may use the common API fixture to emulate the two client credentials; the Windows acceptance runbook separately verifies the real Access UI.

- [ ] **Step 2: Run the contract test**

Run: `python -m pytest tests/acceptance/test_cross_client_contract.py -q`
Expected: PASS only when both client adapters target the same API records.

- [ ] **Step 3: Write the manual Windows/browser acceptance matrix**

The runbook must cover: create in web/read in Access; create in Access/read in web; concurrent edit conflict; Admin edit attribution; deactivated account denied in both; PIN change reflected in both; session revocation; export parity.

- [ ] **Step 4: Execute against fictional test accounts**

Record exact environment, Access version/bitness, web build SHA, API build SHA, report IDs, and pass/fail results in the release evidence artifact rather than committing credentials or sensitive values.

- [ ] **Step 5: Commit**

```bash
git add docs/runbooks/web-access-cross-client-acceptance.md tests/acceptance/test_cross_client_contract.py
git commit -m "test: add cross-client acceptance contract"
```

### Task 3: Make React the primary application route

**Files:**
- Modify: `backend/webapp/app.py`
- Modify: `Dockerfile`
- Modify/create: build workflow steps for `web-client`
- Create: `tests/unit/test_spa_serving.py`

**Interfaces:**
- Consumes: `web-client/dist/` build output.
- Produces: `/` and non-API SPA routes served from React build while `/health`, `/api/v1`, `/web-auth`, `/web-api` remain backend routes.

- [ ] **Step 1: Write failing SPA route tests**

```python
def test_root_serves_react_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'<div id="root"></div>' in response.data


def test_api_is_not_shadowed_by_spa(client):
    response = client.get("/api/v1/client-policy")
    assert response.status_code != 200 or response.is_json
```

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/unit/test_spa_serving.py -q`
Expected: FAIL while legacy home owns `/`.

- [ ] **Step 3: Implement SPA serving/build packaging**

Build `web-client` before the Python runtime image is finalized; copy only `dist/`. Flask serves `index.html` for known SPA paths after API/static/auth route matching. Add immutable caching for content-hashed JS/CSS and `no-store` for `index.html`.

- [ ] **Step 4: Run frontend build, Flask tests, and container build**

Run: `cd web-client && npm ci && npm run build && cd .. && python -m pytest tests/unit/test_spa_serving.py -q` plus the repository container-build gate.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/app.py Dockerfile web-client tests/unit/test_spa_serving.py .github/workflows
git commit -m "feat(web): serve React as primary application"
```

### Task 4: Remove legacy Flask UI and shared-code authentication

**Files:**
- Modify: `backend/webapp/app.py`
- Modify: `backend/pipeline/config.py`
- Delete: legacy-only templates/static/routes after confirming no React or API dependency
- Modify: deployment/Terraform secret configuration
- Create: `tests/security/test_shared_code_removed.py`

**Interfaces:**
- Produces: production application with individual identity login only.

- [ ] **Step 1: Write failing removal tests**

```python
def test_shared_code_config_is_not_part_of_production_auth():
    import backend.pipeline.config as config
    assert not hasattr(config, "ADMIN_CODE")
    assert not hasattr(config, "ACCESS_CODE")


def test_code_query_parameter_does_not_authenticate(client):
    response = client.get("/?code=anything")
    assert b"signed in" not in response.data.lower()
```

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/security/test_shared_code_removed.py -q`
Expected: FAIL before retirement.

- [ ] **Step 3: Remove the old credential path**

Delete shared-code matching/cookies/login behavior and legacy-only route registrations. Remove `ACCESS_CODE`/`ADMIN_CODE` from runtime secret/env wiring. Keep current Admin bootstrap/recovery jobs/runbooks as the supported recovery path.

- [ ] **Step 4: Run full auth/security regression suite**

Run: `python -m pytest tests/unit/test_auth_middleware.py tests/integration/test_identity_security.py tests/security -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A backend web-client tests infra docs
git commit -m "refactor(web): retire shared-code legacy application"
```

### Task 5: Update final documentation and issue state

**Files:**
- Modify: `README.md`
- Modify: `HANDOFF.md`
- Modify: `docs/access-cloud-run-implementation-checklist.md`
- Modify: `docs/architecture/unified-platform.md`
- Modify: current roadmap/vision document

**Interfaces:**
- Produces: docs describing only the shipped React + Access + shared `/api/v1` platform and current remaining gates.

- [ ] **Step 1: Add final-state docs test**

```python
def test_docs_do_not_present_shared_codes_as_supported_auth():
    from pathlib import Path
    combined = "\n".join(Path(p).read_text() for p in ["README.md", "HANDOFF.md"])
    assert "shared access code" not in combined.lower()
    assert "employee number" in combined.lower()
```

- [ ] **Step 2: Run docs test**

Run: `python -m pytest tests/unit/test_current_docs.py -q`
Expected: FAIL until documentation is finalized.

- [ ] **Step 3: Rewrite final-state documentation**

Document Officer/Admin web capabilities, Access companion role, individual login, session controls, centralized report ownership/revisions, production deployment, recovery/bootstrap, and remaining rollout gates. Close/supersede stale planning issues only after their unresolved requirements are represented in current docs/issues.

- [ ] **Step 4: Re-run docs tests**

Run: `python -m pytest tests/unit/test_current_docs.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md HANDOFF.md docs tests/unit/test_current_docs.py
git commit -m "docs: document unified production web platform"
```

### Task 6: Full release gate and production cutover

**Files:**
- No code changes unless a gate reveals a defect.
- Release evidence/runbooks only.

**Interfaces:**
- Produces: GO/FIX/BLOCK decision for production.

- [ ] **Step 1: Run web quality gates**

Run: `cd web-client && npm ci && npm test && npm run build && npm run test:e2e`
Expected: PASS for Officer/Admin and responsive viewport projects.

- [ ] **Step 2: Run backend/database gates**

Run locked Ruff/mypy, unit, contract, PostgreSQL 17 integration, migration lifecycle, security, and policy/report evaluation gates exactly as defined by CI/release docs.
Expected: PASS.

- [ ] **Step 3: Run container/supply-chain gates**

Build the actual production image and execute SBOM, vulnerability, signature/Rekor, workflow pin, and sensitive-output gates.
Expected: PASS.

- [ ] **Step 4: Run cross-client test-environment acceptance**

Execute `docs/runbooks/web-access-cross-client-acceptance.md` using only fictional data. Any ownership, revision, auth, or attribution mismatch is BLOCK.

- [ ] **Step 5: Deploy test, then production through controlled workflow**

Verify health, sign-in, Officer flow, Admin flow, Policy Expert, export, audit, and session revocation after deployment. Remove old shared-code secrets only after the new revision is verified healthy.

- [ ] **Step 6: Record release evidence and mark gates**

Update the implementation ledger with exact deployed revision/build SHA and acceptance evidence. Gate status must distinguish code complete, test accepted, and production deployed.
