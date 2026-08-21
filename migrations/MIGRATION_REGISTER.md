# Migration register

This register covers every revision returned by `alembic history`. Production execution requires external backup, restore, lock-budget, compatibility, and protected-environment approval. The only production rollback is a reviewed compatible application revision; production `alembic downgrade` is prohibited. A contract migration must never ship in the same release that raises the minimum client version.

The database migration operator runs each verification query through the approved channel. Queries read PostgreSQL catalogs only and must return `true`; they do not inspect application row contents. The final deployment check separately requires `alembic_version.version_num` to equal the single reviewed code head.

## 20260812_0001_identity_foundation

- Phase: `expand`.
- Expected duration and lock budget: under five minutes; metadata and table-creation locks only on a preflight-confirmed database with no conflicting DDL. Stop if five minutes or the approved lock wait budget is exceeded.
- Lock risk: new tables, constraints, indexes, functions, and trigger; no existing application table rewrite.
- Old/new compatibility: old application revision does not use these new objects; new revision requires them. Both may run during the reviewed rollout after this revision succeeds.
- Rollback: isolated non-production downgrade test only. Production retains schema and rolls application traffic back to the reviewed compatible revision.
- Verification query:

  ```sql
  SELECT
    EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto')
    AND (SELECT count(*) = 10 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public' AND c.relkind = 'r'
        AND c.relname IN ('staff_members','accounts','sessions','renewal_token_history','admin_elevations','admin_step_up_tokens','browser_handoffs','browser_sessions','auth_rate_limits','audit_events'))
    AND (SELECT count(*) = 2 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'public' AND p.proname IN ('reject_audit_mutation','append_audit_event'))
    AND EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_events_append_only' AND NOT tgisinternal)
    AND (SELECT count(*) = 8 FROM pg_indexes WHERE schemaname = 'public'
      AND indexname IN ('ix_staff_members_employee_number','ix_accounts_role_status','ix_sessions_account_id','ix_sessions_renewal_family','ix_renewal_history_family','ix_admin_step_up_tokens_session_id','ix_auth_rate_limits_window','ix_audit_events_occurred_action'))
    AS revision_contract_ok;
  ```

- Production owner role: database migration operator; identity/security owner reviews the audit-function contract.

## 20260812_0002_identity_security_controls

- Phase: `expand`.
- Expected duration and lock budget: under two minutes; create-table/index locks only. Stop if two minutes or the approved lock wait budget is exceeded.
- Lock risk: creates one table, its constraints, and one index; no existing table rewrite.
- Old/new compatibility: old revision ignores idempotency records; new revision may begin using them only after the migration verifies. Both remain compatible during rollout.
- Rollback: isolated non-production downgrade test only. Production uses application rollback and retains the additive table.
- Verification query:

  ```sql
  SELECT to_regclass('public.idempotency_records') IS NOT NULL
    AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_idempotency_expiry')
    AND (SELECT count(*) = 5 FROM pg_constraint
      WHERE conname IN ('fk_idempotency_records_actor_account_id_accounts','uq_idempotency_actor_action_key','ck_idempotency_records_idempotency_status','ck_idempotency_records_idempotency_request_hash_length','ck_idempotency_records_idempotency_response_reference_size'))
    AS revision_contract_ok;
  ```

- Production owner role: database migration operator; identity/security owner reviews idempotency compatibility.

## 20260812_0003_report_storage

- Phase: `expand`.
- Expected duration and lock budget: under five minutes; metadata/table/index locks and enum creation only. Stop if five minutes or the approved lock wait budget is exceeded.
- Lock risk: new enum, five tables, constraints, indexes, one mutation-rejection function, and two triggers; no existing application table rewrite.
- Old/new compatibility: identity-only old revision ignores report objects; new report revision requires them. Both remain compatible after verification.
- Rollback: isolated non-production downgrade test only. Production retains schema and rolls application traffic back.
- Verification query:

  ```sql
  SELECT
    (SELECT count(*) = 5 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public' AND c.relkind = 'r'
        AND c.relname IN ('incidents','incident_revisions','reports','report_access','report_revisions'))
    AND EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
      WHERE n.nspname = 'public' AND t.typname = 'report_type')
    AND EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'public' AND p.proname = 'reject_report_revision_mutation')
    AND (SELECT count(*) = 2 FROM pg_trigger
      WHERE tgname IN ('trg_incident_revisions_immutable','trg_report_revisions_immutable') AND NOT tgisinternal)
    AND (SELECT count(*) = 11 FROM pg_indexes WHERE schemaname = 'public'
      AND indexname IN ('ix_incidents_status_date','ix_incidents_category_date','ix_incidents_updated_at','ix_incident_revisions_parent_created','ix_reports_incident','ix_reports_status_updated','ix_reports_owner_updated','ix_reports_preparer_updated','ix_report_access_staff_relationship','ix_report_revisions_parent_created','ix_report_revisions_editor_created'))
    AND (SELECT count(*) = 28 FROM pg_constraint
      WHERE conname IN ('ck_incident_revisions_number_nonnegative','ck_incident_revisions_reason','ck_incidents_current_revision_nonnegative','ck_incidents_status','ck_report_access_relationship','ck_report_revisions_number_nonnegative','ck_report_revisions_reason','ck_reports_current_revision_nonnegative','ck_reports_status','fk_incident_revisions_editor_account_id_accounts','fk_incident_revisions_editor_staff_member_id_staff_members','fk_incident_revisions_incident_id_incidents','fk_incidents_created_by_account_id_accounts','fk_incidents_created_by_staff_member_id_staff_members','fk_report_access_granted_by_account_id_accounts','fk_report_access_report_id_reports','fk_report_access_staff_member_id_staff_members','fk_report_revisions_editor_account_id_accounts','fk_report_revisions_editor_staff_member_id_staff_members','fk_report_revisions_report_id_reports','fk_report_revisions_source_incident_revision','fk_reports_created_by_account_id_accounts','fk_reports_incident_id_incidents','fk_reports_prepared_by_staff_member_id_staff_members','fk_reports_reporting_staff_member_id_staff_members','uq_incident_revisions_parent_number','uq_report_revisions_parent_number','uq_reports_incident_type_owner'))
    AS revision_contract_ok;
  ```

- Production owner role: database migration operator; report-data owner reviews immutable-history behavior.

## 20260812_0004_report_search_indexes

- Phase: `expand`.
- Expected duration and lock budget: under five minutes on the approved data-size estimate; each index must stay within its separately approved build/lock budget. Stop before retry if any build exceeds budget.
- Lock risk: seven index builds on `incidents`/`reports`, including one GIN index; index creation can consume I/O and briefly conflict with DDL. No row-content migration.
- Old/new compatibility: old and new application revisions work with or without the additional indexes; the new Admin search performance objective is enabled only after all indexes verify.
- Rollback: the migration has a non-destructive isolated-test downgrade that drops only these indexes. Production uses application rollback and retains verified indexes unless a separately reviewed database change removes them.
- Verification query:

  ```sql
  SELECT (SELECT count(*) = 7 FROM pg_indexes WHERE schemaname = 'public'
    AND indexname IN ('ix_incidents_extracted_facts_gin','ix_incidents_incident_date','ix_incidents_facility','ix_incidents_location','ix_incidents_shift','ix_reports_created_at','ix_reports_updated_at'))
    AND EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'public' AND indexname = 'ix_incidents_extracted_facts_gin'
        AND indexdef ILIKE '% USING gin %' AND indexdef ILIKE '%jsonb_path_ops%'
    ) AS revision_contract_ok;
  ```

- Production owner role: database migration operator; database performance owner reviews build duration and query plans.

## 20260812_0005_jobs_exports

- Phase: `expand`.
- Expected duration and lock budget: under five minutes; new-table/index locks plus one foreign-key addition to `report_revisions`. Stop if five minutes, foreign-key validation, or the approved lock wait budget is exceeded.
- Lock risk: creates three tables/indexes and validates one foreign key on an existing table; preflight must confirm `report_revisions.source_ai_job_id` is compatible and no conflicting DDL is active.
- Old/new compatibility: old report revision leaves the nullable source-job column unused; new worker/export revision requires these objects. Both remain compatible after verification.
- Rollback: isolated non-production downgrade test only. Production retains schema and rolls application traffic back; no job/export row deletion is authorized.
- Verification query:

  ```sql
  SELECT
    (SELECT count(*) = 3 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname IN ('ai_jobs','task_outbox','exports'))
    AND (SELECT count(*) = 8 FROM pg_indexes WHERE schemaname = 'public'
      AND indexname IN ('ix_ai_jobs_queue','ix_ai_jobs_claim','ix_ai_jobs_requested_actor','ix_ai_jobs_incident','ix_ai_jobs_report','ix_task_outbox_available','ix_exports_report_revision','ix_exports_actor_created'))
    AND EXISTS (SELECT 1 FROM pg_constraint
      WHERE conname = 'fk_report_revisions_source_ai_job_id_ai_jobs' AND contype = 'f' AND convalidated)
    AND (SELECT count(*) = 28 FROM pg_constraint
      WHERE conname IN ('ck_ai_jobs_attempts_nonnegative','ck_ai_jobs_base_revision_positive','ck_ai_jobs_error_code_format','ck_ai_jobs_job_type','ck_ai_jobs_lease_matches_running_state','ck_ai_jobs_lease_requires_start','ck_ai_jobs_request_hash_length','ck_ai_jobs_request_metadata_size','ck_ai_jobs_result_reference_incident_revision','ck_ai_jobs_result_reference_keys','ck_ai_jobs_result_reference_object','ck_ai_jobs_result_reference_reports','ck_ai_jobs_result_reference_size','ck_ai_jobs_stage','ck_ai_jobs_state','ck_exports_output_hash_length','ck_exports_size_nonnegative','ck_task_outbox_attempts_nonnegative','ck_task_outbox_last_error_code_format','ck_task_outbox_state','fk_ai_jobs_incident_id_incidents','fk_ai_jobs_report_id_reports','fk_ai_jobs_requested_by_account_id_accounts','fk_exports_exported_by_account_id_accounts','fk_exports_report_id_reports','fk_exports_report_revision_id_report_revisions','fk_task_outbox_ai_job_id_ai_jobs','uq_task_outbox_ai_job_id'))
    AS revision_contract_ok;
  ```

- Production owner role: database migration operator; jobs/export owner reviews queue and export compatibility.

## 20260818_0006_browser_sessions

- Phase: `expand`.
- Expected duration and lock budget: under two minutes; stop on any approved lock-wait breach.
- Lock risk: creates one session-binding table, constraints, and indexes; no row rewrite.
- Old/new compatibility: old code ignores the table; new browser sessions require it after verification.
- Rollback: application rollback only in production; retain the additive table.
- Verification query: `SELECT to_regclass('public.browser_session_bindings') IS NOT NULL AS revision_contract_ok;`
- Production owner role: identity/security owner and database migration operator.

## 20260818_0007_incident_packets

- Phase: `expand`.
- Expected duration and lock budget: under five minutes; stop if index or constraint work exceeds the approved budget.
- Lock risk: adds nullable incident identity fields and creates five packet/form audit tables with indexes and constraints.
- Old/new compatibility: old code ignores the additive objects; new guided-operations code requires them after verification.
- Rollback: application rollback only in production; no packet, form, or document-action data deletion.
- Verification query: `SELECT to_regclass('public.form_templates') IS NOT NULL AND to_regclass('public.incident_packet_items') IS NOT NULL AND to_regclass('public.form_instances') IS NOT NULL AND to_regclass('public.physical_paperwork_acknowledgments') IS NOT NULL AND to_regclass('public.document_action_events') IS NOT NULL AS revision_contract_ok;`
- Production owner role: reporting/forms owner and database migration operator.

## 20260819_0008_packet_officer_scope

- Phase: `expand`.
- Expected duration and lock budget: under two minutes; stop on constraint or index lock-budget breach.
- Lock risk: changes form-instance uniqueness and adds reporting-officer scope without rewriting report content.
- Old/new compatibility: old code remains readable; new code may create one form instance per reporting officer after verification.
- Rollback: application rollback only in production; retain scoped rows and constraints.
- Verification query: `SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='form_instances' AND column_name='reporting_staff_member_id') AS revision_contract_ok;`
- Production owner role: reporting/forms owner and database migration operator.

## 20260819_0009_operational_paperwork

- Phase: `expand`.
- Expected duration and lock budget: under three minutes; new-table and index locks only.
- Lock risk: creates revisioned paperwork tables, constraints, indexes, and an immutability trigger.
- Old/new compatibility: old code ignores these tables; new daily-paperwork persistence requires them after verification.
- Rollback: application rollback only in production; never delete paperwork records or revisions.
- Verification query: `SELECT to_regclass('public.paperwork_records') IS NOT NULL AND to_regclass('public.paperwork_revisions') IS NOT NULL AS revision_contract_ok;`
- Production owner role: operations-records owner and database migration operator.

## 20260819_0010_operational_paperwork

- Phase: `expand`.
- Expected duration and lock budget: under three minutes; new-table and index locks only.
- Lock risk: creates the legacy-compatible operational-paperwork pair and related constraints/indexes.
- Old/new compatibility: existing paperwork tables remain intact; consumers must use only their reviewed storage contract.
- Rollback: application rollback only in production; never delete operational-paperwork history.
- Verification query: `SELECT to_regclass('public.operational_paperwork') IS NOT NULL AND to_regclass('public.operational_paperwork_revisions') IS NOT NULL AS revision_contract_ok;`
- Production owner role: operations-records owner and database migration operator.

## 20260820_0011_daily_paperwork_uniqueness

- Phase: `expand`.
- Expected duration and lock budget: under two minutes after duplicate preflight; stop on index lock-budget breach.
- Lock risk: adds a uniqueness index across daily paperwork identity; preflight must prove no duplicate key exists.
- Old/new compatibility: reads remain compatible; new writes rely on database duplicate prevention after verification.
- Rollback: application rollback only in production; retain the protective uniqueness constraint.
- Verification query: `SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='paperwork_records' AND indexdef ILIKE '%UNIQUE%') AS revision_contract_ok;`
- Production owner role: operations-records owner and database migration operator.

## Release-level verification

After all catalog contracts return true, require the exact final head without exposing row content:

```sql
SELECT version_num = :single_reviewed_code_head AS exact_head_ok
FROM alembic_version;
```

The query must return exactly one row and `true`. Any missing/extra revision, false catalog contract, timeout, unexpected lock, or compatibility mismatch blocks roster apply and dependent traffic.
