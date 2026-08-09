# Security Hardening for Issues 66 and 67

## Purpose

This change closes two verified security gaps in the first of three remediation
pull requests:

- Issue #66: a missing `ACCESS_CODE` silently falls back to a public, known
  credential.
- Issue #67: report provenance snippets copied from field notes enter
  `innerHTML` without escaping.

The pull request must remain limited to fail-closed access-code configuration,
safe provenance rendering, their regression tests, and the deployment guidance
needed to operate the new behavior.

## Goals

- Make an omitted `ACCESS_CODE` a startup configuration error.
- Preserve the existing explicit `ACCESS_CODE=""` local-development bypass.
- Preserve the current shared-code login and cookie behavior when a non-empty
  code is configured.
- Render provenance excerpts as text even when field notes contain HTML.
- Prove both fixes with focused regression tests and the complete test suite.

## Non-goals

- Replacing shared-code authentication with user accounts or signed sessions.
- Changing `ADMIN_CODE`, cookie structure, login routing, or authorization tiers.
- Adding a Content Security Policy or refactoring every `innerHTML` call.
- Changing report extraction, provenance matching, or report content.
- Deploying the application as part of this pull request.

## Design

### Fail-closed access-code configuration

`backend.pipeline.config.ACCESS_CODE` will use `os.getenv("ACCESS_CODE")`
without a default. This preserves three distinct states:

1. `None`: the variable was omitted. Application startup must fail with a clear
   `RuntimeError` that names `ACCESS_CODE` but contains no credential value.
2. `""`: the operator explicitly disabled the authentication gate for local
   development or an isolated test.
3. A non-empty string: the existing shared-code authentication behavior remains
   active.

Validation belongs at the start of `create_app()`, before blueprints, model
configuration, or request hooks are initialized. Keeping the check in the app
factory lets configuration modules remain importable by scripts and tests while
ensuring no web process can serve requests with an omitted value.

Tests that create the Flask app must choose an authentication state explicitly.
Existing tests that already monkeypatch `backend.webapp.app.ACCESS_CODE` remain
valid. Shared fixtures that rely on the old implicit default will set an
explicit value appropriate to the behavior under test.

The README and deployment instructions will state that production must provide
`ACCESS_CODE` through an environment variable or secret binding. They will also
document that an explicitly empty value is a local-only opt-out, not a safe
production default.

### Safe provenance rendering

`compute_provenance()` intentionally returns source excerpts copied from the
original field notes. The backend will keep returning those excerpts unchanged;
provenance is data, and changing it there would blur the boundary between stored
content and presentation encoding.

The provenance panel in `backend/webapp/templates/reports.html` inserts each
excerpt into HTML text content. The existing `esc()` helper is correct for that
text context, so the sink will render `esc(cleanSource)` instead of
`cleanSource`. The fuzzy-match prefix and existing panel markup remain static.

This fix is deliberately scoped to the verified text-content sink. It does not
claim that the same helper is safe for JavaScript strings, URLs, or HTML
attributes.

## Data Flow

1. An officer submits field notes.
2. Extraction computes structured slots.
3. `compute_provenance()` returns raw source excerpts so the API faithfully
   represents the notes.
4. The browser receives the provenance JSON.
5. The provenance renderer escapes each excerpt for HTML text content before
   assigning the assembled markup to `innerHTML`.
6. Text such as `<img src=x onerror=alert(1)>` appears literally and cannot
   create an element or event handler.

## Error Handling

- Omitted `ACCESS_CODE`: `create_app()` raises a deterministic startup error.
  The process does not bind a port or serve an open application.
- Explicitly empty `ACCESS_CODE`: startup succeeds and retains the existing
  warning that authentication is disabled.
- Provenance values that are empty or missing continue through the current
  inferred-value rendering branch.
- Escaping accepts values through the existing string-producing provenance
  contract; no new network or model failure modes are introduced.

## Testing

Focused authentication tests will verify:

- omitted `ACCESS_CODE` causes startup to fail for the expected reason;
- explicit `ACCESS_CODE=""` starts successfully with authentication disabled;
- a configured non-empty code retains the current login gate.

The provenance regression test will use a malicious note excerpt containing an
HTML element with an event handler. It will verify both sides of the boundary:
the API/provenance layer preserves the original source text, and the template
routes the browser value through `esc()` at the HTML sink.

After focused tests pass, the complete `python -m pytest -q` suite must pass.
The working tree must contain only files belonging to issues #66 and #67.

## Rollout

Before deployment, verify that the Cloud Run service has an `ACCESS_CODE`
environment or secret binding without printing its value. Deploy the pull
request normally only after that preflight succeeds. A deployment without the
binding is expected to fail startup, which is the intended fail-closed result.

## Acceptance Criteria

- No repository-known fallback access code remains.
- Missing and explicitly empty configuration have distinct, tested behavior.
- The existing authenticated flow still passes its tests.
- Raw field-note markup cannot become DOM elements in the provenance panel.
- Deployment guidance describes the required production configuration.
- The full test suite passes with no new warnings introduced by this change.
