# Database migration and roster import

This runbook is executed only by the database migration operator through the reviewed, protected delivery workflow. It never authorizes a local agent or an application service to run a cloud job. Production `alembic downgrade`, deletion, automatic retry, and historical Word-document import are prohibited.

## Required evidence and stop conditions

Before scheduling the change, record these external approvals without roster rows, credentials, or database URLs:

- immutable image digest, source commit, release version, and the single reviewed Alembic head;
- a complete review of every entry in `migrations/MIGRATION_REGISTER.md`, including the approved duration and lock budget;
- a successful pre-change backup plus current point-in-time recovery and restore-drill evidence for the approved recovery window;
- old/new application compatibility, current and target API/client versions, and confirmation that no contract migration shares a release with a minimum-client-version increase;
- the exact private source, corrections, and report object URIs, immutable object generations, approved lowercase SHA-256, correction approver, expected staff count, and expected aggregate checksum; and
- protected-environment approval for the exact environment, project, region, job names, digest, and source commit.

Stop if the migration graph has zero or multiple heads; the database is unavailable; the current revision is unexpected; the backup/restore, lock, compatibility, or approval evidence is incomplete; an input object changed generation/hash; validation reports any finding; or a command would access a different project, environment, bucket, job, image, or database.

## Operator parameter contract

The protected workflow supplies these values. They are not committed and must not be printed with environment-dump or shell-tracing commands.

```powershell
$Environment = 'test' # production requires the production-deploy approval gate
$ProjectId = '<approved-environment-project>'
$Region = '<approved-region>'
$ExpectedHead = '<single-reviewed-alembic-head>'
$RosterSourceUri = '<approved-private-source-uri>'
$RosterCorrectionsUri = '<approved-private-corrections-uri>'
$RosterReportUri = '<approved-private-new-report-uri>'
$RosterExpectedSha256 = '<approved-lowercase-64-hex>'
$MigrationJob = "access-$Environment-migrate"
$RosterJob = "access-$Environment-roster-import"
```

The workflow must fail unless `$Environment` is exactly `test` or `production`, every roster URI is under `gs://access-$Environment-roster/`, the report object does not already exist, the hash is lowercase 64-hex, and the resolved Cloud Run job image digest and service account equal the reviewed Terraform outputs. Test completes successfully before production is approved.

## Migration execution

1. Confirm the code graph has one head and that it equals `$ExpectedHead`:

   ```powershell
   python -m alembic heads
   python -m alembic history
   ```

   `heads` must emit one revision. `history` must match every revision in the migration register. These local commands inspect code only.

2. Immediately before execution, confirm backup completion, available recovery window, database capacity, active sessions/long transactions, and that the approved lock budget remains safe. Record pass/fail and evidence references only.

3. Invoke the exact protected job once. Do not retry automatically after an unknown execution result.

   ```powershell
   gcloud run jobs execute $MigrationJob --project=$ProjectId --region=$Region --wait --format='value(metadata.name)'
   ```

   The immutable job command is exactly `python -m backend.jobs.migration upgrade`, uses the migration runtime identity, mounts Cloud SQL at `/cloudsql`, and has `max_retries = 0`. Expected application output contains only `status`, `revision`, and `duration`. It must report `status=ok` and `$ExpectedHead`.

4. Run safe verification through the same protected migration job by overriding only its Python arguments:

   ```powershell
   $VerifyArgs = '-m,backend.jobs.migration,verify'
   gcloud run jobs execute $MigrationJob --project=$ProjectId --region=$Region --args=$VerifyArgs --wait --format='value(metadata.name)'
   ```

   Require exactly one code head, database revision equal to it, and all expected tables/indexes/constraints. Execute each catalog-only query in the migration register through the approved database verification channel; every boolean must be true. Do not select application rows.

5. Run the reviewed API compatibility smoke check against the protected test origin, then production origin only after approval. Confirm the deployed API/server/client versions satisfy the approved compatibility matrix. Do not shift dependent traffic on any mismatch.

## Roster validation and apply

1. Confirm the source and corrections objects still have their approved immutable generations and compute SHA-256 over the exact downloaded bytes inside the protected workflow. The value must equal `$RosterExpectedSha256`; do not output object contents.

2. Create a fresh immutable validation report URI that has never existed. Supply
   it as the protected `roster_report_uri`, run the reviewed Terraform plan/apply
   so the job argument and exact-object create-only IAM condition both bind that
   URI, then execute the roster job with no `--apply` flag:

   ```powershell
   gcloud run jobs execute $RosterJob --project=$ProjectId --region=$Region --wait --format='value(metadata.name)'
   ```

   This is validation-only. The job must use the migration identity, mount `/cloudsql`, have `max_retries = 0`, and create detailed findings only at the exact new `$ValidationReportUri` using generation-match zero. Any existing object blocks the execution; it is never overwritten. Ordinary output is limited to counts, source hash, opaque finding codes, import-run UUID, and migration revision.

3. An authorized roster reviewer opens the private report through the approved non-recorded data channel. Stop on any finding, duplicate normalized employee number, missing ID, invalid shift, ambiguous mapping, unapproved correction, changed hash/generation, or unexpected count/checksum. Do not paste findings into tickets, chat, workflow output, or logs.

4. Every clean re-validation uses another never-before-created report URI and a
   reviewed Terraform update that rebinds both the job argument and exact-object
   creator IAM condition. After correction approval and a second clean validation
   pass, create a third fresh `$ApplyReportUri`, rebind the protected Terraform
   input to it, verify the plan changes only that argument/IAM condition, and run
   one transactional apply by overriding the full reviewed argument vector and
   appending `--apply`:

   ```powershell
   $ApplyArgs = "-m,backend.jobs.roster_import,--source-uri,$RosterSourceUri,--corrections-uri,$RosterCorrectionsUri,--report-uri,$ApplyReportUri,--expected-sha256,$RosterExpectedSha256,--apply"
   gcloud run jobs execute $RosterJob --project=$ProjectId --region=$Region --args=$ApplyArgs --wait --format='value(metadata.name)'
   ```

   The workflow must compare this vector to the currently bound protected inputs
   before invocation. The importer creates the apply report once before entering
   the database transaction; an existing URI fails closed. It preserves existing
   staff UUIDs, creates new staff only through the identity service, and applies
   all changes in one database transaction. An unknown result is a stop condition,
   not a retry instruction.

5. Through the approved database channel, compare only safe aggregates to the reviewed expectations:

   ```sql
   SELECT count(*) AS staff_count,
          encode(digest(coalesce(string_agg(employee_number, ',' ORDER BY employee_number), ''), 'sha256'), 'hex') AS employee_number_set_sha256
   FROM staff_members;
   ```

   Retain only the approved count, checksum, source hash, import-run UUID, revision, job execution reference, and pass/fail evidence. Never retain roster values in operational evidence.

## Failure and rollback

- Before traffic: stop on any failed/unknown migration, verification, compatibility, validation, or aggregate check. Preserve backup and execution evidence and escalate to the database migration owner.
- After a successful schema upgrade: production rollback is the previously reviewed compatible application revision and traffic plan. Production schema downgrade is prohibited.
- A validation-only roster failure changes no staff rows. Correct the source only through the approved correction process, create new immutable inputs/report URI/hash, and repeat validation.
- A committed roster import is not undone by deletion or ad hoc SQL. Use a separately reviewed corrective import that preserves staff UUIDs and auditability.
- Never automatically retry a Cloud Run job whose completion is unknown. First reconcile the exact execution metadata through the protected operations channel.

Completion requires migration head and catalog verification, API compatibility, clean validation, approved transactional apply, count/checksum agreement, and externally retained approval/backup/execution evidence. No dependent traffic proceeds before all required checks pass.
