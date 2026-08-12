# Sequence 018 — RP-09: Deterministic Single and Bounded Bulk Word Exports

Copy everything below into a fresh Claude Code session.

---

Implement only RP-09, “Deterministic single and bounded bulk Word exports.” Use TDD, one focused commit, hand off, and stop.

## Objective

Generate deterministic Word bytes from explicit immutable report revisions, persist/audit metadata only, stream/discard output, and add bounded Admin ZIP export with atomically resolved revisions and deterministic manifest. Identical export idempotency must reproduce identical bytes without floating to newer revisions.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-09-word-exports`
- Predecessor on current reviewed `main`: `feat: expose cited policy expert api`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: expose cited policy expert api"
git switch -c claude/rp-09-word-exports
```

Require clean tracked/index state; tolerate only untouched existing `.superpowers/`. Read intervening reviewed changes if main advanced; stop for missing/unreviewed/conflicting prerequisites. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; roadmap exact export paths/idempotency/bulk selection/step-up rules.
- Report plan exact RP-09 section including ZIP normalization, response headers, bulk bodies/limits/manifest/partial failure, tests.
- Report/Admin/master specs.
- Consume-only existing `fill_template`, template/version behavior, RP-05 `AdminReportFilters`, RP-06 Export/idempotency, report policies/revisions/audit.

## Exact allowed files

- Create: `backend/reports/deterministic_docx.py`
- Create: `backend/reports/export_service.py`
- Modify: `backend/webapp/api_v1/reports.py`
- Modify: `backend/webapp/api_v1/admin_reports.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_deterministic_docx.py`
- Create: `tests/integration/test_export_api.py`
- Create: `tests/integration/test_admin_bulk_export.py`

Consume-only: filler/templates/models/filter/idempotency/policy services, plans/specs/tests not above. No template content, migration, Access, legacy, README, or infra edits.

## Locked interfaces and wire rules

- Produce `normalize_docx_bytes`, `export_report_docx`, `export_reports_zip`; exact User/Admin single paths with required positive `revision` query and Admin `/bulk-export`, cap 100.
- Normalize ZIP members sorted by name; preserve content/compression/permissions/comments/extras; entry timestamp exactly 1980-01-01; normalize core created/modified to saved revision UTC. Deep-copy revision content before `fill_template` because filler mutates metadata.
- Single export authorizes exact immutable revision, generates deterministic bytes, creates one Export metadata row (hash/size/MIME/name/template), same-transaction idempotency+route-specific audit, streams then cleans temporary files. Never infer latest or accept revision in body.
- Response exact binary content plus `Content-Disposition`, `Digest`, `X-Export-ID`, `X-Report-Revision`, `X-Template-Version`.
- Bulk requires active Admin elevation, exact `bulk_export` step-up, idempotency, reason, `revision_selection:"current_at_request"`, and exactly one closed branch: 1–100 unique report UUIDs or RP-05 closed filters. No client limit/floating latest.
- In one repeatable-read transaction resolve/persist sorted `(report_id,revision_number)` before document generation. Zero is 404; >100 `bulk_export_limit_exceeded`; no partial archive before selection established.
- Deterministic ZIP has per-report docs plus sorted-key `manifest.json` with stable IDs/hashes/actor/filter names (not values), persisted idempotency timestamp, explicit failures, reason. Sort by report UUID. Documented post-selection failure may yield explicit partial archive; failed item never marked exported. Store no ZIP/DOCX after close.
- OpenAPI every object closed, binary types, exact headers/errors/security. Ordinary/Admin contexts remain distinct audits.

## TDD procedure

1. Add deterministic bytes/core-time, same-key single bytes/metadata, explicit revision validation, authorization, cleanup, Admin single, bulk branch/limit/selection/order/manifest/partial/idempotency tests first.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_deterministic_docx.py tests/integration/test_export_api.py tests/integration/test_admin_bulk_export.py -v
   ```

   Expected: FAIL because deterministic service/routes absent.
3. Implement normalization and owned temp cleanup, then single export atomics/headers, then repeatable-read bulk selection/manifest.
4. Add exact OpenAPI binary contracts and errors.
5. On dedicated test DB run:

   ```powershell
   python -m pytest tests/unit/test_deterministic_docx.py tests/integration/test_export_api.py tests/integration/test_admin_bulk_export.py tests/unit/test_filler_boxes.py -v
   ```

   Expected: PASS; DB stores metadata only, temporary files removed, filler regression green. Never use production/real docs.
6. Run allowlist/whitespace:

   ```powershell
   $allowed=@('backend/reports/deterministic_docx.py','backend/reports/export_service.py','backend/webapp/api_v1/reports.py','backend/webapp/api_v1/admin_reports.py','openapi/access-v1.yaml','tests/unit/test_deterministic_docx.py','tests/integration/test_export_api.py','tests/integration/test_admin_bulk_export.py')
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

Fictional in-memory DOCX/reports only. No real documents/data/Google. Never log/persist document bytes, manifest content beyond approved metadata, report/field-note/name/employee/inmate/PIN/token/raw body. Do not change template/filler rules, centrally retain binaries, build updater/Access/infra. Acceptance: red evidence; deterministic exact revision bytes; metadata-only persistence/cleanup; exact single/bulk security/limits/selection/manifest/idempotency; tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: export audited report revisions"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start/ancestry/prerequisite/branch/commit/files/red/green/determinism/hash/cleanup/bulk/security/deviation/risk. Stop for missing review/prerequisite, dirty overlap, no dedicated DB, nondeterminism/template drift, allowlist expansion, secret/prod need. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
