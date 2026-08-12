# Sequence 019 — RP-10: Client Policy, Admin Overview/Audit/Health, Legacy Pilot Controls, and Full Verification

Copy everything below into a fresh Claude Code session.

---

Implement only RP-10, “Client policy, Admin overview/audit/health, legacy pilot controls, and full verification.” Work TDD-first, make one focused commit, hand off the complete backend gate evidence, and stop before infrastructure or Access work.

## Objective

Complete the backend contract with safe release compatibility, the exact nine-field public policy including the shared 30,000-character field-notes limit, bounded Admin overview/audit/health, sanitized operational signal producers, stepped-up deterministic audit CSV export, explicit legacy report pilot/restriction control, complete fictional OpenAPI examples, sensitive-log protection, and all backend verification gates. This is the handoff boundary before Cloud infrastructure and Access clients consume `/api/v1`.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-10-operations-legacy-controls`
- Predecessor on current reviewed `main`: `feat: export audited report revisions` and all ID/RP tasks reviewed/merged.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: export audited report revisions"
git switch -c claude/rp-10-operations-legacy-controls
```

Require clean tracked/index state; only untouched existing `.superpowers/` tolerated. Read every intervening reviewed plan/prerequisite change if main advanced; stop for unreviewed/conflicting changes. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; full roadmap global/shared/wire/version/error rules and Gates A/B.
- Report plan exact RP-10 section and Plan Acceptance Checklist.
- Deployment plan OP-08 consume-only for canonical `release/version.json` projection; approved report/deployment/master specs.
- Consume-only all ID/RP APIs/services/OpenAPI, legacy report routes/config, existing full tests.

## Exact allowed files

- Create: `backend/build_info.py`
- Modify: `backend/webapp/api_v1/client_policy.py`
- Create: `backend/webapp/api_v1/admin_audit.py`
- Create: `backend/webapp/api_v1/admin_health.py`
- Modify: `backend/webapp/api_v1/admin.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `backend/webapp/app.py`
- Modify: `backend/webapp/routes/reports.py`
- Modify: `backend/pipeline/config.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_build_info.py`
- Modify: `tests/unit/test_client_policy.py`
- Create: `tests/integration/test_admin_audit_health.py`
- Create: `tests/integration/test_legacy_pilot_controls.py`
- Modify: `tests/contract/test_access_v1_openapi.py`
- Create: `tests/security/test_sensitive_logging.py`

Consume-only: `release/version.json` (OP-08 owns it), plans/specs, prior API/services/tests. Do not edit release registry, infrastructure/workflows, Access, templates, README, or unrelated legacy behavior.

## Locked interfaces and wire rules

- Produce public GET client-policy; elevated Admin GET overview/audit-events/health; exact stepped-up POST audit-events/export; sanitized `dependency_health`, `queue_health`, `backup_restore_health`, and `client_upgrade_required` signals in existing allowed files; build metadata; exact `LEGACY_REPORT_MODE` control.
- `backend/build_info.py` exposes source commit, Cloud Run revision, current Alembic revision safely. Client policy reads validated runtime projection of canonical release registry: release/latest/minimum client/minimum server/API/release notes/public base URL.
- Closed public policy response has exactly nine required fields: release version, latest/minimum client, minimum server, API version, release notes, read-only-required, validated HTTPS origin-only Review Lab origin, and integer `field_notes_max_characters`. Preserve the ID-02 code constant value exactly `30000`; do not add it to an environment variable, `release/version.json`, or version projection. No package URL/signer/bucket/token/credential/internal host/handoff path. Local version defaults remain explicit development sentinels; production fails if a version sentinel or invalid notes/origin remains. Writes below minimum blocked; sign-in/read/export eligible per contract.
- Overview safe counts/actions. Audit list exact closed filters from plan, deterministic cursor default 50/max100, immutable safe details only; no device/network hashes or request content.
- Audit export requires `audit_export` step-up, idempotency, exact closed filters, CSV-only, reason <=500; max 10,000 in `(occurred_at,id)`, otherwise `audit_export_limit_exceeded`. Fixed safe columns exclude detail JSON/hashes/credential/report/inmate/free text. Exact binary headers; audit search/export with filter names/count only.
- Health returns only Operational/Degraded/Unavailable for approved components/metadata; never secrets, report content, infrastructure control, raw errors. Emit only the exact sanitized signal types `dependency_health` (stable dependency/result/latency bucket), `queue_health` (stable result/depth/oldest-age plus job-type/stage/result/latency buckets), `backup_restore_health` (stable result and recency buckets), and `client_upgrade_required` (stable result and parsed client version), reusing ID-02 safe event conventions where applicable. Never include request/report content, person/account/session/device/network identity, raw exception/SQL/query/host/secret values. OP-05 consumes these signals; RP-09 is not a health producer.
- `LEGACY_REPORT_MODE` values exactly `pilot_fallback|restricted`, default restricted; reject others. Pilot fallback preserves transient browser workflow with persistent warning but never Cloud SQL history. Restricted legacy classify/extract/generate/disciplinary/download return safe maintenance. Neither accepts bearer or creates second durable history; Review Lab unchanged. Startup warning in fallback contains no sensitive data.
- OpenAPI complete: only client policy/login/renew operation `security: []`; all examples fictional; exact paths/headers/errors/binary/cursors/enums including audit limit.
- Sensitive log test captures auth/save/jobs/policy/exports/Admin/failures and proves supplied markers absent.

## TDD and verification procedure

1. Add failing build/policy/Admin audit-health/legacy mode/sensitive logging cases first, including the exact nine public-policy keys and integer `field_notes_max_characters == 30000`, old-client read vs write, health redaction, exact four sanitized operational signal types/bounded fields with no RP-09 source, exact audit step-up, limits, deterministic CSV, invalid mode, and both legacy modes.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_build_info.py tests/unit/test_client_policy.py tests/integration/test_admin_audit_health.py tests/integration/test_legacy_pilot_controls.py tests/security/test_sensitive_logging.py -v
   ```

   Expected: FAIL because operational contracts/pilot gate are absent.
3. Implement safe build/policy projection without editing `release/version.json` or creating a second field-notes-limit source; then bounded Admin overview/audit/health and the exact sanitized operational signals within the existing allowlist; then legacy mode gate/warning; then complete OpenAPI/sensitive-marker coverage.
4. Run all backend gates:

   ```powershell
   python -m pytest -q
   python -m pytest tests/integration tests/contract tests/security -v
   python scripts/optimize_images.py --check
   git diff --check
   ```

   Expected: all credential-free tests PASS; no OpenAPI errors, sensitive marker leak, image drift, whitespace error. Integration requires dedicated test DB; stop rather than SQLite/production.
5. Do not run the plan's optional ADC/Discovery Engine parity commands in this Claude Code task. They require separately authorized credentialed access to the approved isolated test project/store and remain an external verification gate:

   ```powershell
   python tests/test_pipeline.py --demo all --output-dir tests/output/access-api-parity
   python tests/eval/run_eval.py --gate-only
   ```

   Record both commands as `NOT RUN — separately authorized isolated-test-cloud verification required` in the handoff. Do not authenticate to Google, inspect ADC, call Discovery Engine, or create/stage generated parity output. A human-controlled follow-up may run them only after the target and authorization are independently verified.
6. Verify full plan acceptance matrix: owner/preparer/unrelated/Admin auth; one immutable revision for every mutation/AI/restore/recovery/transfer/Admin edit; stale writes/jobs safe; idempotency; worker redelivery; Policy citations/no persistence; exact-revision metadata-only exports; bounded attributed Admin functions; explicit isolated legacy mode; all legacy regressions.
7. Enforce changed-file allowlist:

   ```powershell
   $allowed=@('backend/build_info.py','backend/webapp/api_v1/client_policy.py','backend/webapp/api_v1/admin_audit.py','backend/webapp/api_v1/admin_health.py','backend/webapp/api_v1/admin.py','backend/webapp/api_v1/__init__.py','backend/webapp/app.py','backend/webapp/routes/reports.py','backend/pipeline/config.py','openapi/access-v1.yaml','tests/unit/test_build_info.py','tests/unit/test_client_policy.py','tests/integration/test_admin_audit_health.py','tests/integration/test_legacy_pilot_controls.py','tests/contract/test_access_v1_openapi.py','tests/security/test_sensitive_logging.py')
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

## Security, non-goals, acceptance

Fictional data/markers only. No ADC, Google authentication, cloud calls, production data, or secrets. Never log/export health/audit fields containing raw request, report/field notes/policy text, names/employee/inmate IDs, PIN/token/device/network hashes/credentials/internal errors. Do not edit version registry, create an environment/version field-notes source, deploy, add Access/infra, retain generated parity artifacts, alter ID-02/RP-07 telemetry, claim RP-09 health output, or expand legacy writes. Acceptance: red evidence; exact nine-field policy with `30000`; exact sanitized RP-10 signal producers; exact version/health/audit/CSV/limits; safe legacy modes; full OpenAPI/log tests; all available backend gates/allowlist/whitespace green; optional parity explicitly recorded as the external `NOT RUN` gate above.

## Commit and handoff

```powershell
git commit -m "feat: complete access api operational contracts"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start SHA/baseline/prerequisites/branch/commit/files/red/all green gates/DB/optional ADC decision/version/audit/health/legacy/log-security/deviation/residual risks. Stop for missing review/prerequisite, dirty overlap, no dedicated DB for integration, ambiguous/production ADC, release projection conflict, allowlist expansion, secret/prod need, or any failed gate. Never push, merge, deploy, apply Terraform, sign, publish, change secrets, access production, delete data/resources, use destructive Git, or touch `.superpowers/`.
