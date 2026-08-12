# Sequence 011 — RP-02: Versioned Content Schemas, Provenance, and Atomic Revisions

Copy everything below into a fresh Claude Code session.

---

Implement only RP-02, “Versioned content schemas, provenance, and atomic revisions.” Use TDD, one focused commit, hand off, and stop.

## Objective

Create strict versioned incident/report content schemas, centralized provenance fingerprints, the complete safe report audit-action catalog, and row-locked one-transaction save/restore/recovery services. The outcome prevents unknown/client-owned identity fields, stale overwrites, partial revisions, and sensitive audit details while preserving Review Lab provenance behavior.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-02-content-revisions`
- Required predecessor subject on reviewed `main`: `feat: add incident and report revision schema`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add incident and report revision schema"
git switch -c claude/rp-02-content-revisions
```

Clean tracked/index state required; only existing untracked `.superpowers/` is tolerated and untouchable. Read intervening reviewed changes if main advanced; stop for unreviewed/conflicting changes. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`, roadmap shared Python/HTTP/wire/error rules.
- Report plan exact RP-02 section with full schema fields, the ID-02 field-notes constant contract, audit allowlist, service algorithm, tests.
- Report/master specs; consume-only RP-01 models/fixtures, ID-06 Actor/audit/idempotency, and existing `backend/reports/review_schema.py` behavior/tests.

## Exact allowed files

- Create: `backend/webapp/api_v1/schemas/reporting.py`
- Create: `backend/reports/provenance.py`
- Create: `backend/reports/revisions.py`
- Modify: `backend/identity/audit.py`
- Modify: `backend/reports/review_schema.py`
- Create: `tests/unit/test_reporting_schemas.py`
- Create: `tests/unit/test_report_provenance.py`
- Create: `tests/unit/test_report_audit_schemas.py`
- Create: `tests/integration/test_revision_service.py`

Consume-only: `backend/webapp/api_v1/client_policy.py` for ID-02 `FIELD_NOTES_MAX_CHARACTERS`, models, persistence/database, existing review tests, plans/specs. No route/OpenAPI/migration/README/legacy engine edits.

## Locked interfaces and rules

- Produce strict `IncidentSnapshotV1`, `ReportContentV1`, `SaveIncidentRequest`, `SaveReportRequest`, `RevisionSummary`, bounded audit actions, `collect_provenance()`, `save_incident()`, `save_report()`, `restore_report()`, `create_recovery_revision()`.
- Use Pydantic strict models with `extra="forbid"`; exact schema version 1; `IncidentSnapshotV1.field_notes` and `SaveIncidentRequest.field_notes` both use `Field(max_length=FIELD_NOTES_MAX_CHARACTERS)` imported from the single ID-02 backend constant, whose release-one value is exactly `30_000`. Do not duplicate the literal into a second constant or source it from environment/version metadata. Keep narrative/editable/validation/warnings and all approved incident classification/facts/gaps/charges/search fields bounded. Reject nonfinite numbers, oversized JSON, unknown fields, client fingerprints, and actor/owner/preparer IDs.
- Provenance keys exact: fast/pro model, model location, three prompt/checklist hashes, template hash, Cloud Run revision, source commit. Move existing hash behavior into helper and make Review Lab consume it without changing outputs.
- Extend audit catalog with every exact action in the plan once. Details allow only stable IDs/revisions/result codes/changed-field names/filter names/counts/hashes/latency/request/job/export IDs. Reject field notes, report/policy text, names, employee/inmate identifiers, PINs/tokens and unknown keys.
- Save row-locks current report, checks base revision, validates content, computes names of changed fields without values, appends immutable snapshot, updates current, appends audit, and commits atomically. Conflict reports safe current metadata; no partial revision/audit.
- Restore creates current+1 copied snapshot and immutable source reference. Recovery appends separate recovery revision and never silently overwrites/promotes over newer current.
- Use exact roadmap shared signatures and Actor. Completed/Archived remain editable; no delete.

## TDD procedure

1. Add strict schema/provenance/audit/concurrency tests first using exact fictional examples from plan. Direct strict-model cases must prove both `IncidentSnapshotV1` and `SaveIncidentRequest` accept exactly 30,000 field-note characters and reject 30,001, repeat the boundary with a fictional non-BMP Unicode code point to lock decoded-code-point rather than byte/UTF-16-unit counting, and show their schema constraint comes from ID-02 `FIELD_NOTES_MAX_CHARACTERS`.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_reporting_schemas.py tests/unit/test_report_provenance.py tests/unit/test_report_audit_schemas.py tests/integration/test_revision_service.py -v
   ```

   Expected: FAIL on missing `ReportContentV1`, `collect_provenance`, and revision functions.
3. Implement strict schemas, then provenance extraction/reuse, then complete safe audit catalog.
4. Implement row-locked one-transaction save/restore/recovery. Use dedicated PostgreSQL integration; never SQLite/production.
5. Run focused plus Review Lab regression:

   ```powershell
   python -m pytest tests/unit/test_reporting_schemas.py tests/unit/test_report_provenance.py tests/unit/test_report_audit_schemas.py tests/integration/test_revision_service.py tests/unit/test_review_schema.py -v
   ```

   Expected: PASS; two same-base saves yield one revision and one conflict, no partial audit.
6. Run diff/allowlist:

   ```powershell
   $allowed=@('backend/webapp/api_v1/schemas/reporting.py','backend/reports/provenance.py','backend/reports/revisions.py','backend/identity/audit.py','backend/reports/review_schema.py','tests/unit/test_reporting_schemas.py','tests/unit/test_report_provenance.py','tests/unit/test_report_audit_schemas.py','tests/integration/test_revision_service.py')
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

Fictional content only; no Google calls; no sensitive content in audit/logs/errors. Do not add routes/OpenAPI/jobs/exports/Access/infra or alter prompts/engine behavior. Acceptance: red evidence, strict closed schemas, the shared 30,000/30,001 field-notes boundary on both incident models with no competing source, identical Review Lab provenance, full safe action schemas, concurrency/rollback/restore/recovery semantics, focused tests, allowlist and whitespace.

## Commit and handoff

```powershell
git commit -m "feat: add conflict-safe report revisions"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff all branch/start/ancestry/prerequisite/commit/files/red/green/concurrency/audit/provenance/security/deviation/risk evidence. Stop for missing review/prerequisite, dirty overlap, no dedicated DB before integration, allowlist expansion, secret/prod need, or contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.
