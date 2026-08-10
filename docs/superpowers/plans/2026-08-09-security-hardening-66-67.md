# Security Hardening 66-67 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make missing access-code configuration fail closed and prevent raw field-note provenance from executing as HTML.

**Architecture:** Keep authentication validation at the Flask app-factory boundary while preserving `None`, empty, and configured access-code states from the configuration module. Keep provenance raw in the API and apply context-specific escaping only at the browser HTML-text sink.

**Tech Stack:** Python 3.14, Flask 3, pytest, Jinja/vanilla JavaScript, Markdown, Google Cloud Run.

## Global Constraints

- Limit this pull request to issues #66 and #67.
- Preserve an explicit `ACCESS_CODE=""` as the local-development authentication bypass.
- Preserve the existing shared-code login, cookie, admin tier, and report-generation behavior.
- Do not refactor unrelated `innerHTML` sites or change provenance extraction.
- Do not deploy as part of implementation; deployment occurs only after PR review and an environment-binding preflight.
- Every production behavior change must follow red-green-refactor and the complete `python -m pytest -q` suite must pass.

---

## File Structure

- `backend/pipeline/config.py`: preserve the difference between an omitted and explicitly empty access-code environment variable.
- `backend/webapp/app.py`: reject omitted access-code configuration before the Flask app initializes.
- `backend/webapp/templates/reports.html`: escape provenance source excerpts at the HTML text-content sink.
- `tests/unit/test_access_code_config.py`: regression coverage for omitted, empty, and configured access-code states.
- `tests/unit/test_reports_template_security.py`: regression contract for raw provenance data and escaped template rendering.
- `README.md`: correct local startup instructions and document the required production secret binding.

### Task 1: Fail Closed When ACCESS_CODE Is Omitted

**Files:**
- Create: `tests/unit/test_access_code_config.py`
- Modify: `backend/pipeline/config.py:91-95`
- Modify: `backend/webapp/app.py:134-147`

**Interfaces:**
- Consumes: process environment variable `ACCESS_CODE`.
- Produces: `backend.pipeline.config.ACCESS_CODE: str | None`; `create_app() -> Flask` raises `RuntimeError` when the value is `None`.

- [ ] **Step 1: Write the failing configuration tests**

```python
"""Fail-closed ACCESS_CODE configuration tests."""
import os
import subprocess
import sys

import pytest

from backend.webapp import app as app_mod


def test_config_preserves_missing_access_code_as_none():
    env = os.environ.copy()
    env.pop("ACCESS_CODE", None)
    result = subprocess.run(
        [sys.executable, "-c",
         "from backend.pipeline.config import ACCESS_CODE; print(repr(ACCESS_CODE))"],
        env=env, capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "None"


def test_create_app_rejects_missing_access_code(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", None)
    with pytest.raises(RuntimeError, match="ACCESS_CODE must be configured"):
        app_mod.create_app()


def test_create_app_allows_explicitly_empty_access_code(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    app = app_mod.create_app()
    assert app.test_client().get("/").status_code == 200


def test_create_app_keeps_configured_access_code_gate(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "configured-code")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    app = app_mod.create_app()
    assert app.test_client().get("/").status_code == 302
```

- [ ] **Step 2: Run the focused tests and verify the expected failures**

Run: `python -m pytest tests/unit/test_access_code_config.py -q`

Expected: the first test reports that the missing environment variable resolved to the old `"slut"` fallback, and the second test reports that `RuntimeError` was not raised. The explicit-empty and configured-gate tests pass.

- [ ] **Step 3: Remove the public fallback from configuration**

Replace the access-code assignment in `backend/pipeline/config.py` with:

```python
# No default: omission is a deployment error. An explicitly empty value keeps
# the intentional local-development auth bypass.
ACCESS_CODE = os.getenv("ACCESS_CODE")
```

- [ ] **Step 4: Validate configuration at the app-factory boundary**

Add this before constructing `Flask(...)` in `create_app()`:

```python
if ACCESS_CODE is None:
    raise RuntimeError(
        "ACCESS_CODE must be configured; set it to a non-empty secret in "
        "production or explicitly set ACCESS_CODE='' for isolated local work."
    )
```

- [ ] **Step 5: Run focused and existing authentication tests**

Run: `python -m pytest tests/unit/test_access_code_config.py tests/unit/test_admin_tier.py tests/unit/test_safe_next.py -q`

Expected: all tests pass; no credential value appears in output.

- [ ] **Step 6: Commit the fail-closed behavior**

```bash
git add backend/pipeline/config.py backend/webapp/app.py tests/unit/test_access_code_config.py
git commit -m "fix(auth): require explicit access code configuration"
```

### Task 2: Escape Provenance Excerpts at the HTML Sink

**Files:**
- Create: `tests/unit/test_reports_template_security.py`
- Modify: `backend/webapp/templates/reports.html:926-936`

**Interfaces:**
- Consumes: provenance objects shaped as `{label, value, source}` from `compute_provenance(notes: str, slots: dict) -> list[dict]`.
- Produces: literal text inside `.trace-src`; no note-derived string can create DOM markup at that sink.

- [ ] **Step 1: Write the failing provenance-rendering regression test**

```python
"""Security contracts for report-template rendering."""
import json
from pathlib import Path
import re
import subprocess

from backend.reports.extraction import compute_provenance


TEMPLATE = (Path(__file__).resolve().parents[2]
            / "backend" / "webapp" / "templates" / "reports.html")


def _render_provenance_in_node(provenance: list[dict]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    esc_fn = re.search(r"function esc\(s\)\{[^\n]+\}", template).group(0)
    start = template.index("function renderProvenance(){")
    end = template.index("function setSourcesOpen(open){", start)
    render_fn = template[start:end]
    script = f"""
const elements = {{
  sourcesArea: {{style: {{}}}},
  sourcesCnt: {{textContent: ''}},
  tracePanel: {{innerHTML: ''}},
  sourcesToggle: {{}},
}};
global.document = {{
  getElementById: id => elements[id],
  createElement: () => ({{
    _value: '',
    set textContent(value) {{ this._value = String(value); }},
    get innerHTML() {{
      return this._value.replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }},
  }}),
}};
const _extractedData = {{provenance: {json.dumps(provenance)}}};
function setSourcesOpen() {{}}
{esc_fn}
{render_fn}
renderProvenance();
process.stdout.write(elements.tracePanel.innerHTML);
"""
    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True,
    )
    return result.stdout


def test_raw_provenance_is_escaped_at_html_text_sink():
    payload = '<img src=x onerror="alert(1)">'
    provenance = compute_provenance(
        f"Officer observed {payload}",
        {"narrative_facts": [payload]},
    )
    assert payload in provenance[0]["source"]

    rendered = _render_provenance_in_node(provenance)
    assert "<img" not in rendered
    assert "&lt;img" in rendered
```

- [ ] **Step 2: Run the focused test and verify it fails at the unsafe sink assertion**

Run: `python -m pytest tests/unit/test_reports_template_security.py -q`

Expected: FAIL because the rendered panel contains the raw `<img` element. The provenance assertion passes, proving the test reaches raw note-derived content.

- [ ] **Step 3: Apply text-context escaping at the verified sink**

Change the source interpolation in `renderProvenance()` to:

```javascript
?`<span class="trace-src${srcClass}">${fuzzy?'≈ ':''}${esc(cleanSource)}</span>`
```

- [ ] **Step 4: Run the focused rendering test**

Run: `python -m pytest tests/unit/test_reports_template_security.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the provenance fix**

```bash
git add backend/webapp/templates/reports.html tests/unit/test_reports_template_security.py
git commit -m "fix(reports): escape provenance excerpts before rendering"
```

### Task 3: Document Required Local and Production Configuration

**Files:**
- Modify: `README.md:75-91`
- Test: `tests/unit/test_access_code_config.py`

**Interfaces:**
- Consumes: the Task 1 three-state `ACCESS_CODE` contract.
- Produces: copy-pasteable root-level local startup commands and production guidance that requires an environment or Secret Manager binding.

- [ ] **Step 1: Update Quick Start to run from the repository root**

Replace the existing nested-directory commands with platform-specific examples that preserve absolute `backend.*` imports:

````markdown
## Quick Start

Install dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

For isolated local work, explicitly disable the shared-code gate and run the
application from the repository root:

```powershell
$env:ACCESS_CODE=""
python backend/webapp/app.py
```

```bash
ACCESS_CODE="" PYTHONPATH=. python backend/webapp/app.py
```
````

- [ ] **Step 2: Document the production requirement without exposing a secret**

Add immediately before the deployment command:

```markdown
Production requires `ACCESS_CODE` to be present. Bind it from Google Secret
Manager or set it in the service environment before deployment; never commit
the value or place it in shell history. An omitted value stops application
startup, while an explicitly empty value disables authentication and is only
appropriate for isolated local development.
```

Keep the existing root-level `gcloud run deploy --source .` command unchanged;
issue #69 owns deployment-script path corrections.

- [ ] **Step 3: Run the authentication tests after documenting the contract**

Run: `python -m pytest tests/unit/test_access_code_config.py tests/unit/test_admin_tier.py -q`

Expected: all tests pass.

- [ ] **Step 4: Commit the operating guidance**

```bash
git add README.md
git commit -m "docs: require access code configuration"
```

### Task 4: Full Verification and PR Preparation

**Files:**
- Verify only; no new production files.
- Compare branch scope against issues #66 and #67 and the approved design spec.

**Interfaces:**
- Consumes: all changes from Tasks 1-3.
- Produces: a verified branch ready to push and open as a pull request.

- [ ] **Step 1: Run formatting and diff checks**

Run: `git diff --check origin/main...HEAD`

Expected: no whitespace errors.

- [ ] **Step 2: Run the complete test suite**

Run: `python -m pytest -q`

Expected: every test passes; the existing Google dependency deprecation warning may remain, but this change introduces no new warning.

- [ ] **Step 3: Inspect the final scope**

Run these commands separately:

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git log --oneline origin/main..HEAD
```

Expected: only the design, plan, authentication configuration, app factory, report template, focused tests, and README are present. No roster, download, feedback, or deployment-script implementation belongs in this PR.

- [ ] **Step 4: Push and open the pull request**

Use the repository publish workflow to push `fix/security-hardening-66-67` and open a draft pull request with:

```markdown
## Summary
- fail startup when ACCESS_CODE is omitted while preserving the explicit local opt-out
- escape raw provenance excerpts at the report HTML sink
- document local and production configuration requirements

## Verification
- python -m pytest -q

Closes #66
Closes #67
```
