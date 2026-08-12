# Sequence 003 — ID-02: Common `/api/v1` Contract, Envelopes, Request IDs, Client Version, and Cookie Isolation

Copy everything below into a fresh Claude Code session opened for this repository.

---

Implement exactly Task ID-02, “Common `/api/v1` Contract, Envelopes, Request IDs, Client Version, and Cookie Isolation.” Work test-first, create one focused commit, and stop. Do not implement authentication or ID-03.

## Objective, outcome, and rationale

Create the authoritative versioned Flask API boundary, response/error envelope, request/client-version context, one privacy-safe structured request-event contract, signed pagination cursor, safe nine-field client-policy bootstrap including the release-one 30,000-character field-notes limit, and strict isolation between Access bearer traffic and the legacy shared-code browser gate. This contract is the wire foundation used by every later Access and backend task; drift here would force unsafe client workarounds.

## Repository and baseline

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed planning baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/id-02-api-v1-foundation`
- Required predecessor commit subject: `chore(identity): add database and migration foundation`

Preflight:

```powershell
git status --short --untracked-files=all
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if ($LASTEXITCODE -ne 0) { throw "Reviewed planning baseline is not an ancestor of HEAD." }
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s" | Select-String -SimpleMatch "chore(identity): add database and migration foundation"
git switch -c claude/id-02-api-v1-foundation
```

Require a clean tracked tree/index before branching from current reviewed `main`. Ignore only pre-existing untracked `.superpowers/`, which is user-owned and must not be touched or staged; stop for anything else. If reviewed `main` advanced, require the baseline as an ancestor, read and verify review of intervening plan/spec/prerequisite changes, and use current reviewed contracts. Stop for unreviewed/conflicting changes. Never reset or discard user work. Create the branch from current HEAD without force and stop if it unexpectedly exists.

## Required reading

1. `AGENTS.md`
2. Roadmap `docs/superpowers/plans/2026-08-12-access-cloud-run-program-roadmap.md`: Global Constraints, Shared Python Interfaces, Shared HTTP Rules, locked wire/error/version rules.
3. Identity plan `docs/superpowers/plans/2026-08-12-cloud-identity-foundation-implementation.md`: exact section `### Task ID-02: Common /api/v1 Contract, Envelopes, Request IDs, Client Version, and Cookie Isolation` through its divider, including exact test/code examples.
4. Identity and master approved specs.
5. Consume-only existing `backend/webapp/app.py`, legacy auth gate/config, and ID-01 configuration/database modules.

## Exact allowed files

- Modify: `backend/webapp/app.py:13-20,138-224`
- Create: `backend/webapp/api_v1/__init__.py`
- Create: `backend/webapp/api_v1/context.py`
- Create: `backend/webapp/api_v1/responses.py`
- Create: `backend/webapp/api_v1/errors.py`
- Create: `backend/webapp/api_v1/client_policy.py`
- Create: `backend/webapp/api_v1/pagination.py`
- Create: `openapi/access-v1.yaml`
- Create: `tests/unit/test_api_v1_responses.py`
- Create: `tests/unit/test_api_v1_isolation.py`
- Create: `tests/unit/test_client_policy.py`
- Create: `tests/contract/test_access_v1_openapi.py`

Consume-only: all required-reading paths and ID-01 outputs not listed above. No README, plan, spec, identity service, browser template, or legacy route edit is allowed.

## Locked interfaces and wire rules

- Produce `api_v1_bp`, `FIELD_NOTES_MAX_CHARACTERS: Final[int] = 30_000` in `client_policy.py`, `request_id() -> str`, `client_version() -> Version`, `request_event(*, action, result, status_code, error_code=None, dependency="none") -> dict[str, object]`, `ApiError`, `success(...)`, `failure(...)`, `require_compatible_write(view)`, and signed opaque cursor helpers.
- `ApiError.__init__(code, message, *, status, retryable=False, details=None)` is the only intentional `/api/v1` exception. Success/error envelopes and top-level keys must exactly match the roadmap, include `api_version: "v1"`, RFC 3339 UTC `server_time`, response `X-Request-ID`, and `Cache-Control: no-store`.
- Retain only `X-Request-ID` matching `[A-Za-z0-9_-]{8,64}`; otherwise generate a lowercase UUID and never reflect the invalid value.
- Every `/api/v1` call requires valid `X-Client-Version` except `GET /api/v1/client-policy`. Writes below the minimum return `409 client_upgrade_required`. Do not invent endpoint exemptions in this task.
- Client policy, later login, and later renewal are the only operations that will have OpenAPI `security: []`; create only client policy now.
- `GET /api/v1/client-policy` is safe/bootstrap-only. Its closed data object has exactly nine required fields: `release_version`, `latest_client_version`, `minimum_client_version`, `minimum_server_version`, `api_version`, `release_notes`, `read_only_required`, `review_lab_origin`, and integer `field_notes_max_characters`. That last field is exactly `30000`, sourced only from `FIELD_NOTES_MAX_CHARACTERS`; do not add an environment/version setting or `release/version.json` field. Use ID-01 validated settings for the version/origin fields and do not expose package URLs, internal hosts, credentials, secrets, or signing metadata.
- Emit one `request_event` per versioned API response through the common lifecycle. Its keys are exactly `request_id`, `action`, `result`, `latency_ms`, `latency_bucket`, `http_status_class`, `error_code`, `client_version`, and `dependency`. Use parsed/sanitized values and bounded stable codes; derive status class and bucket. Never serialize URL/path/query values, raw headers, request/response bodies, content, identity/actor/session/device/network data, tokens, or exception text. Request ID is correlation-only and not a metric label.
- Signed cursors contain only `created_at` and `id`, use the configured cursor signing key, and enforce page size 1–100.
- The legacy gate must delegate `/api/v1` to this blueprint. A legacy cookie cannot authenticate `/api/v1`; a bearer header cannot authenticate legacy pages. Do not accept either as a substitute.
- Stable errors include `validation_failed`, `client_upgrade_required`, and safe authentication-required behavior; do not create aliases.

## TDD procedure

1. Add the four failing test/contract files first, reproducing the plan’s exact envelope-key, request-ID, no-store, client-policy, OpenAPI 3.1, cookie-isolation, and bearer-isolation cases. In existing test files, assert the public policy has exactly the nine required keys, integer `field_notes_max_characters == 30000`, and no extra field; capture success/error request events, assert the exact nine event keys/stable derived values, and prove supplied fictional content/identity/token/header/query/path markers are absent.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_api_v1_responses.py tests/unit/test_api_v1_isolation.py tests/unit/test_client_policy.py tests/contract/test_access_v1_openapi.py -q
   ```

   Expected: failure because `backend.webapp.api_v1` and `openapi/access-v1.yaml` do not exist and `/api/v1/me` is intercepted by the shared-code gate.
3. Implement request context with monotonic timing, the exact safe `request_event` builder/emission path, exact envelopes, `ApiError` translation, and deterministic request-ID handling. Do not return HTML/stack traces for API errors or log a competing request shape.
4. Register the feature-gated blueprint and isolate the legacy gate. Add the test-only `/api/v1/me` behavior exactly as described in the plan without preempting later bearer middleware.
5. Implement client policy, version write guard, and signed cursor helpers with closed validation.
6. Create the OpenAPI 3.1 foundation, reusable headers/envelopes/errors/security scheme, fictional examples only, and `security: []` on client policy only.
7. Run green and legacy regressions:

   ```powershell
   python -m pytest tests/unit/test_api_v1_responses.py tests/unit/test_api_v1_isolation.py tests/unit/test_client_policy.py tests/contract/test_access_v1_openapi.py -q
   python -m pytest tests/unit/test_access_code_config.py tests/unit/test_admin_tier.py tests/unit/test_safe_next.py -q
   ```

   Expected: all pass; an `access_code` cookie gets `401 authentication_required` from `/api/v1/me`, while a bearer without the legacy cookie still gets the unchanged legacy login redirect from `/reports`.
8. Run `git diff --check`, review the diff, and enforce:

   ```powershell
   $allowed=@('backend/webapp/app.py','backend/webapp/api_v1/__init__.py','backend/webapp/api_v1/context.py','backend/webapp/api_v1/responses.py','backend/webapp/api_v1/errors.py','backend/webapp/api_v1/client_policy.py','backend/webapp/api_v1/pagination.py','openapi/access-v1.yaml','tests/unit/test_api_v1_responses.py','tests/unit/test_api_v1_isolation.py','tests/unit/test_client_policy.py','tests/contract/test_access_v1_openapi.py')
   $changed=@((git diff --name-only),(git diff --cached --name-only),(git ls-files --others --exclude-standard))|Sort-Object -Unique
   $unexpected=$changed|Where-Object{$_ -notin $allowed -and $_ -notlike '.superpowers/*'}
   if($unexpected){$unexpected;throw 'Changed-file allowlist violation.'}
   git diff --check
   $taskChanged=@($changed|Where-Object{$_ -in $allowed})
   if(-not $taskChanged){throw 'No allowlisted task changes to stage.'}
   git add -A -- $taskChanged
   $staged=@(git diff --cached --name-only)|Sort-Object -Unique
   $unexpectedStaged=$staged|Where-Object{$_ -notin $allowed}
   if($unexpectedStaged){$unexpectedStaged;throw 'Staged-file allowlist violation.'}
   git diff --cached --name-status
   git diff --cached --check
   ```

## Security, privacy, non-goals, and acceptance

Use fictional examples only. Never include real people, employee numbers, PINs, tokens, device IDs, reports, field notes, inmate identifiers, raw request bodies, database URLs, or secrets in examples/logs/errors. Do not add authentication, sessions, accounts, report APIs, Admin routes, browser handoff, deployment, or Access code. Do not refactor legacy route behavior beyond the exact isolation hook.

Acceptance requires: red-first evidence; exact envelopes and headers; safe request IDs; exactly one nine-key structured request-event contract with marker-redaction tests; the exact nine-field policy with integer `field_notes_max_characters: 30000` from one code constant; no environment/version source for that limit; validated version/cursor behavior; valid OpenAPI; disabled-feature behavior; cookie/bearer isolation in both directions; focused and legacy tests green; no unexpected files; `git diff --check` green; no sensitive material.

## Commit and handoff

```powershell
git commit -m "feat(api): add versioned Access API foundation"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff must report task/branch, start SHA and ancestry, commit SHA/subject, full file list, red result, every green command/result, OpenAPI/isolation review, security review, deviations, and residual risks.

Stop for missing ancestry/prerequisite, dirty unrelated work, conflicting reviewed instructions, required out-of-allowlist edits, unexpected legacy behavior, or any need for secrets/production. Never push, merge, deploy, apply, sign, publish, alter secrets, access production, delete data/resources, use destructive Git, or touch `.superpowers/`.
