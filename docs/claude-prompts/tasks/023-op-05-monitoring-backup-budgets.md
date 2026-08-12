# Claude Code Prompt 023 — OP-05: Add Monitoring, Backup Exports, Restore Evidence, Alerts, and Budgets

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **023**, task **OP-05: Add Monitoring, Backup Exports, Restore Evidence, Alerts, and Budgets**.

## Objective, outcome, and rationale

Define privacy-safe observability, alerting, unique nightly logical exports, restore-evidence templates, and budget thresholds. Operators must be able to assess service availability, database protection, queue/AI health, compatibility failures, security signals, recovery targets, and cost without any report, roster, credential, or person-specific content entering logs, metrics, dashboards, alerts, or Git.

## Repository, baseline, and branch

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-05-observability-recovery`
- Commit: `infra: add monitored backup and budget controls`

Run this preflight before recording the task start or creating the branch:

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The baseline must be an ancestor of current reviewed `main`. When `HEAD` advanced, inspect `git log --oneline $TaskBase..HEAD`, predecessor plans/handoffs, and verify every commit is reviewed, OP-01 through OP-04 outputs exist, and no conflict exists. Create `claude/op-05-observability-recovery` from current `HEAD`. Stop on ancestry/review/prerequisite failure, an existing branch, or dirty overlap/unsafe switching. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; the approved deployment design; roadmap global constraints/program gates/agent protocol and locked observability producer contract; OP-03 database/identity and OP-04 service/queue/bucket outputs; ID-02 exact `request_event`; RP-07 `ai_provider_repeat_risk_total`; RP-10 exact `dependency_health`, `queue_health`, `backup_restore_health`, and `client_upgrade_required` signals; the platform-native Cloud Run/Cloud SQL/Cloud Tasks/Cloud Billing metric contracts; and the detailed plan from the exact OP-05 heading to the OP-06 separator. RP-09 is not a health producer. External records and consumed sources remain read-only.

## Exact allowed files

Create only:

- `infra/terraform/modules/access_platform/observability.tf`
- `infra/terraform/modules/access_platform/backups.tf`
- `infra/terraform/modules/access_platform/budgets.tf`
- `infra/terraform/modules/access_platform/sql_export_workflow.yaml.tftpl`
- `infra/monitoring/dashboards/api.json`
- `infra/monitoring/dashboards/database.json`
- `infra/monitoring/dashboards/jobs-and-ai.json`
- `infra/monitoring/dashboards/client-versions.json`
- `infra/terraform/tests/test_observability_contract.py`
- `docs/runbooks/backup-restore-disaster-recovery.md`
- `docs/operations/restore-exercise-template.md`

Modify only:

- `infra/terraform/modules/access_platform/variables.tf`
- `infra/terraform/modules/access_platform/outputs.tf`
- `infra/terraform/environments/test/main.tf`
- `infra/terraform/environments/production/main.tf`
- `infra/terraform/tests/access_platform.tftest.hcl`

No deletion is authorized. Other infrastructure and application files are consume-only.

## Locked interfaces

- Consume application telemetry only from ID-02 `request_event`, RP-07 `ai_provider_repeat_risk_total`, and RP-10 `dependency_health`, `queue_health`, `backup_restore_health`, and `client_upgrade_required`; consume infrastructure state only from platform-native Cloud Run, Cloud SQL, Cloud Tasks, and Cloud Billing metrics. Do not reference an RP-09 health field or scrape an Admin endpoint.
- ID-02 `request_event` has exactly request ID, stable action/result, latency milliseconds and stable bucket, HTTP status class, stable error code, parsed client version, and dependency name. Log-based metric labels may use only bounded stable environment/release/API/client/migration version, action/result/bucket/status/error, job type/stage/result, and dependency fields. Request ID and raw latency remain log-correlation/detail fields, never high-cardinality metric labels.
- Dashboards are exactly `api`, `database`, `jobs-and-ai`, and `client-versions`, with valid Google Monitoring JSON and display names beginning `Access `.
- Alerts cover API availability/latency/5xx; auth lockouts/denials; SQL saturation/storage/connections/backup; queue depth/age; AI job failure/latency buckets; policy search; exports; upgrade-required; sensitive-log scanner; and budget. Every alert has an owner role and repository runbook path. Do not invent per-model call-count/cost telemetry: provider-repeat risk comes only from RP-07 and cost/spend only from Cloud Billing.
- Use only externally supplied notification-channel IDs; never embed contact details/tokens.
- Dedicated logical-backup identity can request SQL export and create unique backup objects only. It cannot mutate SQL, read application secrets, overwrite/delete prior backups, or read `DATABASE_URL`.
- Workflow template builds a UTC timestamped `logical-exports/YYYYMMDDTHHMMSSZ.sql.gz`, uses offloaded Cloud SQL Admin export, waits for result, and returns only operation ID/object URI/status. Scheduler runs nightly.
- Budgets require external billing account, amount, owner, and Pub/Sub topic; thresholds are exactly 50%, 80%, 90%, 100%, 120%, plus forecasted 100%.
- Restore evidence fields are exactly `exercise_id`, `started_at`, `completed_at`, `source_backup_time`, `target_isolated_instance`, `achieved_rpo_minutes`, `achieved_rto_minutes`, `verification_summary`, `owner_role`, and `corrective_actions_reference`.
- Runbook covers automated backup/PITR checks, isolated nonproduction restore, logical restore, Alembic, safe counts/checksums, revocation checks, representative report/revision reads, RPO/RTO, cleanup authorization, quarterly cadence, and escalation. All restore/cleanup commands are human-only.
- Preserve targets RPO at most five minutes and RTO four hours unless externally revised in writing.

## TDD and local validation

1. Write `infra/terraform/tests/test_observability_contract.py` exactly from OP-05 Step 1, including the declared-producer assertions for `request_event`, `ai_provider_repeat_risk_total`, `dependency_health`, `queue_health`, `backup_restore_health`, and `client_upgrade_required`, the platform-native source checks for relevant infrastructure widgets, and rejection of any RP-09 health reference.
2. Run:

```powershell
python -m pytest infra/terraform/tests/test_observability_contract.py -q
```

Expected red: missing `infra/monitoring/dashboards/api.json`. Do not count unrelated import/collection errors.
3. Implement dashboards, Terraform dashboard/log-metric/alert resources, scheduled unique export, budgets, mocked assertions, runbook, and safe blank evidence template. Every widget/alert must map to one declared producer. Configure log-based metrics over existing exact safe events only; do not modify or manufacture application telemetry. Stop and hand a missing signal back to ID-02, RP-07, or RP-10.
4. Run:

```powershell
python -m json.tool infra/monitoring/dashboards/api.json | Out-Null
python -m json.tool infra/monitoring/dashboards/database.json | Out-Null
python -m json.tool infra/monitoring/dashboards/jobs-and-ai.json | Out-Null
python -m json.tool infra/monitoring/dashboards/client-versions.json | Out-Null
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
python -m pytest infra/terraform/tests/test_observability_contract.py -q
git diff --check
```

Also run existing Terraform security/serverless tests when locally available. Expected: JSON, mocked Terraform, privacy tests, and whitespace pass; no cloud backup, alert, notification, or budget is created.

## External gates and dry-run boundary

Notification channels, billing authorization/account, monthly budget, Pub/Sub topic, retention decision, restore target, owner roles, and production evidence are external. Require them as variables and leave relevant production gates closed. Never invent them or store completed evidence. Do not execute a restore, export, scheduler, backup, alert, budget, SQL, Cloud API, or cleanup command. `terraform init -backend=false`, validate, mocked tests, JSON parsing, and local pytest are the only infrastructure actions.

## Security/privacy and non-goals

Use fictional examples and data only; never use production data or real identifiers. Never include field notes, report text, employee/inmate identifiers, PIN/token/access material, names, query parameters, SQL values, machine/device identities, contact destinations, webhook details, request IDs as metric labels, or backup content in metrics/logs/alerts/dashboards/evidence. Do not alter ID-02/RP-07/RP-10 application telemetry, claim RP-09 telemetry, provision preceding infrastructure, implement migration jobs, run real health checks, scrape Admin endpoints, or set actual retention/budget values. Do not push, merge, deploy, apply/destroy/import Terraform, run backup/restore, change secrets, sign, publish, access production, or perform destructive Git/filesystem operations.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Expected red failure observed first.
- [ ] Four valid, privacy-safe dashboards and all alert families are defined.
- [ ] Every alert links an owner role and repository runbook.
- [ ] Logical export paths are unique/timestamped/offloaded and cannot overwrite.
- [ ] Backup identity has no data mutation, secret-read, overwrite, or delete power.
- [ ] Budget thresholds and external routing inputs are exact.
- [ ] Restore template has all exact fields and no production record value.
- [ ] RPO/RTO and human-only recovery procedure are explicit.
- [ ] Focused/regression tests pass with no cloud calls and only allowed paths changed.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`. Search/inspect task changes for forbidden sensitive keys, personal/contact data, real identifiers, SQL/query values, and completed evidence. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'infra/terraform/modules/access_platform/observability.tf'
    'infra/terraform/modules/access_platform/backups.tf'
    'infra/terraform/modules/access_platform/budgets.tf'
    'infra/terraform/modules/access_platform/sql_export_workflow.yaml.tftpl'
    'infra/monitoring/dashboards/api.json'
    'infra/monitoring/dashboards/database.json'
    'infra/monitoring/dashboards/jobs-and-ai.json'
    'infra/monitoring/dashboards/client-versions.json'
    'infra/terraform/tests/test_observability_contract.py'
    'docs/runbooks/backup-restore-disaster-recovery.md'
    'docs/operations/restore-exercise-template.md'
    'infra/terraform/modules/access_platform/variables.tf'
    'infra/terraform/modules/access_platform/outputs.tf'
    'infra/terraform/environments/test/main.tf'
    'infra/terraform/environments/production/main.tf'
    'infra/terraform/tests/access_platform.tftest.hcl'
)
$changed = @(
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
) | Sort-Object -Unique
$unexpected = $changed | Where-Object { $_ -notin $allowed -and $_ -notlike '.superpowers/*' }
if ($unexpected) { $unexpected; throw 'Changed-file allowlist violation.' }
git diff --name-status $TaskStart
git diff --check
git add -A -- $allowed
$staged = @(git diff --cached --name-only) | Sort-Object -Unique
$unexpectedStaged = $staged | Where-Object { $_ -notin $allowed }
if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
git diff --cached --name-status
git diff --cached --check
git commit -m "infra: add monitored backup and budget controls"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including the exact ID-02/RP-07/RP-10/platform-native producer-to-widget map and confirmation of no RP-09 health dependency, dashboards/alerts/export/budget/evidence contracts; security/privacy and sensitive-data inspection results plus no-cloud-action confirmation; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production. Independent specification review precedes code-quality review.

Stop without committing if safe labels are insufficient, retention conflicts with approved policy, notification/budget values would need invention, the backup identity needs broader access, a test cannot run locally, or any prohibited action is required. Never weaken privacy assertions.
