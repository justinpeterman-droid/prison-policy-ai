# Release Cleanup and Documentation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean the current release candidate, resolve the known deployment/reliability defects, reconcile documentation with the actual architecture, and prepare a trustworthy integration-to-main release.

**Architecture:** Work from `integration/access-cloud-run-rp02`; do not make feature changes here. Fix the three known reliability/deployment issues with regression tests, then update release documentation and prepare a gated integration-to-main PR. Branch protection is a GitHub settings action and must be completed before production rollout.

**Tech Stack:** Python 3.14, Flask, pytest, GitHub Actions, Docker/Cloud Run, Markdown.

**Spec:** `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`

## Global Constraints

- PostgreSQL 17 remains the integration-test floor.
- Preserve the existing anti-fabrication report pipeline and `/api/v1` contracts.
- Do not remove shared-code legacy access in this plan; final removal belongs to the cutover plan.
- Do not merge the release candidate to `main` until all required checks are green.

---

### Task 1: Fix root-source Cloud Run deployment (#69)

**Files:**
- Modify: `backend/scripts/deploy.sh`
- Modify: deployment instructions in `README.md` or current runbook
- Create/Test: `tests/unit/test_deploy_script.py`

**Interfaces:**
- Consumes: repository root containing `Dockerfile`, `backend/`, and top-level assets.
- Produces: a deploy script that always passes the repository root to `gcloud run deploy --source`.

- [ ] **Step 1: Write the failing regression test**

```python
from pathlib import Path


def test_deploy_script_uses_repository_root():
    text = Path("backend/scripts/deploy.sh").read_text()
    assert 'REPO_ROOT=' in text
    assert '--source "$REPO_ROOT"' in text
    assert 'cd "$SCRIPT_DIR"' not in text
```

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest tests/unit/test_deploy_script.py -q`
Expected: FAIL against the current script.

- [ ] **Step 3: Implement the root-safe script**

Use the script directory only to derive the root:

```bash
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
gcloud run deploy "$SERVICE_NAME" --source "$REPO_ROOT" "$@"
```

Keep existing project/region flags intact.

- [ ] **Step 4: Run the focused test and shell syntax check**

Run: `python -m pytest tests/unit/test_deploy_script.py -q && bash -n backend/scripts/deploy.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/deploy.sh tests/unit/test_deploy_script.py
git commit -m "fix(deploy): deploy Cloud Run from repository root"
```

### Task 2: Add a finite GitHub feedback timeout (#72)

**Files:**
- Modify: `backend/webapp/routes/feedback.py`
- Modify/Test: `tests/unit/test_feedback_ratelimit.py`

**Interfaces:**
- Consumes: `FEEDBACK_GITHUB_TIMEOUT_SECONDS`, default `10`.
- Produces: finite `urllib.request.urlopen(..., timeout=seconds)` behavior and a safe timeout response.

- [ ] **Step 1: Add failing tests**

```python
def test_feedback_uses_finite_timeout(monkeypatch, client):
    seen = {}
    def fake_urlopen(req, timeout):
        seen["timeout"] = timeout
        raise TimeoutError()
    monkeypatch.setattr("backend.webapp.routes.feedback.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    response = client.post("/api/feedback", json={"comment": "x", "url": "https://example.test"})
    assert seen["timeout"] == 10
    assert response.status_code == 503
```

- [ ] **Step 2: Run the focused tests**

Run: `python -m pytest tests/unit/test_feedback_ratelimit.py -q`
Expected: FAIL because no timeout is passed and timeout is not classified separately.

- [ ] **Step 3: Implement timeout parsing and handling**

```python
def _github_timeout_seconds() -> float:
    raw = os.environ.get("FEEDBACK_GITHUB_TIMEOUT_SECONDS", "10")
    try:
        return min(max(float(raw), 1.0), 30.0)
    except ValueError:
        return 10.0
```

Call `urlopen(req, timeout=_github_timeout_seconds())`; catch `TimeoutError` and `urllib.error.URLError` whose reason is a timeout, log category `feedback_github_timeout`, and return `503` with a retryable generic message.

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest tests/unit/test_feedback_ratelimit.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/routes/feedback.py tests/unit/test_feedback_ratelimit.py
git commit -m "fix(feedback): bound GitHub request time"
```

### Task 3: Remove temporary DOCX files after legacy download (#71)

**Files:**
- Modify: `backend/webapp/routes/reports.py`
- Modify/Test: `tests/unit/test_filler_boxes.py` or create `tests/unit/test_report_download_cleanup.py`

**Interfaces:**
- Consumes: temporary paths created by the legacy report filler.
- Produces: response cleanup registered with Flask `after_this_request` only for files owned by the route.

- [ ] **Step 1: Write a failing cleanup test**

```python
def test_download_deletes_generated_temp_file(client, monkeypatch, tmp_path):
    output = tmp_path / "generated.docx"
    output.write_bytes(b"docx")
    monkeypatch.setattr("backend.webapp.routes.reports.fill_template", lambda *a, **k: output)
    response = client.post("/api/reports/download", json={"metadata": {}})
    response.get_data()
    assert not output.exists()
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/unit/test_report_download_cleanup.py -q`
Expected: FAIL because the generated pathname remains.

- [ ] **Step 3: Register response cleanup**

Use `after_this_request` and delete only the route-created temp path:

```python
@after_this_request
def _cleanup(response):
    try:
        output_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove generated report file", exc_info=True)
    return response
```

Do not delete caller-provided paths used by lower-level filler tests or services.

- [ ] **Step 4: Run cleanup and report tests**

Run: `python -m pytest tests/unit/test_report_download_cleanup.py tests/unit/test_filler_boxes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/webapp/routes/reports.py tests/unit/test_report_download_cleanup.py
git commit -m "fix(reports): clean temporary download files"
```

### Task 4: Rewrite current-state documentation

**Files:**
- Modify: `README.md`
- Modify: `HANDOFF.md`
- Modify: `docs/access-cloud-run-implementation-checklist.md`
- Create: `docs/architecture/unified-platform.md`

**Interfaces:**
- Consumes: approved web companion spec and current integration-branch status.
- Produces: one consistent description of Access + web + `/api/v1` + PostgreSQL + Cloud Run.

- [ ] **Step 1: Add documentation assertions**

Create `tests/unit/test_current_docs.py`:

```python
from pathlib import Path


def test_readme_describes_unified_clients():
    text = Path("README.md").read_text()
    for phrase in ["Microsoft Access", "React", "/api/v1", "PostgreSQL 17"]:
        assert phrase in text


def test_handoff_does_not_reference_obsolete_prs():
    text = Path("HANDOFF.md").read_text()
    assert "PR #22" not in text
    assert "PR #23" not in text
```

- [ ] **Step 2: Run the documentation tests**

Run: `python -m pytest tests/unit/test_current_docs.py -q`
Expected: FAIL on stale content.

- [ ] **Step 3: Rewrite the docs**

README sections must be: Product, Architecture, Clients, Backend/API, Local testing, Release process, Security model, Current roadmap. `HANDOFF.md` must contain only current external/manual gates. `docs/architecture/unified-platform.md` must link the approved design and show client/data flow.

- [ ] **Step 4: Run docs tests and link checks used by the repo**

Run: `python -m pytest tests/unit/test_current_docs.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md HANDOFF.md docs/access-cloud-run-implementation-checklist.md docs/architecture/unified-platform.md tests/unit/test_current_docs.py
git commit -m "docs: refresh unified platform documentation"
```

### Task 5: Validate the release candidate and prepare integration-to-main PR

**Files:**
- Modify only if tests expose defects.
- GitHub settings: protect `main` before production rollout.

**Interfaces:**
- Consumes: cleaned integration branch.
- Produces: evidence for a release PR to `main`.

- [ ] **Step 1: Run static and unit gates**

Run the repository's locked Ruff/mypy/unit/contract/security commands from `backend-quality.yml`.
Expected: all PASS.

- [ ] **Step 2: Run PostgreSQL 17 integration and migration lifecycle**

Run the existing PostgreSQL integration suite and `scripts/verify_migration.py` against PostgreSQL 17.
Expected: all PASS, excluding documented opt-in skips only.

- [ ] **Step 3: Run container/security gates**

Run the same container build, SBOM, vulnerability, and signature checks required by the release workflows.
Expected: all PASS.

- [ ] **Step 4: Configure branch protection**

In GitHub repository settings, require pull requests and required release/status checks for `main`, and disallow force pushes. Record the exact required-check names in `docs/operations/github-environment-policy.md`.

- [ ] **Step 5: Open the release PR**

Create `integration/access-cloud-run-rp02 -> main` with a checklist containing exact test run IDs/results and an explicit statement that the web-companion feature itself is not yet part of this merge unless separately implemented.
