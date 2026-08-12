# Claude Code Prompt 026 — OP-08: Implement Controlled Plan, Apply, Migrate, Deploy, Traffic, and Rollback Workflows

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **026**, task **OP-08: Implement Controlled Plan, Apply, Migrate, Deploy, Traffic, and Rollback Workflows**.

## Objective, outcome, and rationale

Preserve OP-01's bypass-deployer retirement and implement protected workflow definitions for immutable build-once test delivery, separately reviewed Terraform plan/apply, production migration/verification, staged 1/10/50/100 traffic, known-good rollback, and manual first-Admin bootstrap invocation. This task designs and statically tests workflows; it must not invoke them or mutate any environment. Plan authority and bootstrap request authority must be cryptographically/contextually bound to exact protected workflow provenance without exposing a PIN.

## Repository, baseline, branch, and preflight

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Anchor baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-08-controlled-delivery`
- Commit: `ci: add approved digest promotion and rollback`

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The anchor must be an ancestor of current reviewed `main`. Inspect `git log --oneline $TaskBase..HEAD`, every predecessor handoff/review, and verify OP-01 through OP-07, all required ID/RP contracts, Alembic head, and required quality checks exist and are reviewed. Branch from current `HEAD` with `git switch -c claude/op-08-controlled-delivery`. Stop on failed ancestry/review/prerequisites, conflicts, existing branch, or overlapping/unsafe dirty work. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; approved deployment design; roadmap global constraints, canonical version projection, program gates, task order, agent protocol; `docs/operations/github-environment-policy.md`; OP-02 through OP-07 outputs including OP-03 `admin-bootstrap` WIF, OP-04 private request prefix, OP-06 bootstrap job/runbook, and EXT-12; release/API/OpenAPI/version settings; migration register; existing deployment documentation; and the detailed plan from the exact OP-08 heading to the OP-09 separator. The three OP-01 deletion targets must already be absent and remain absent.

## Exact allowed files

Create only:

- `.github/workflows/terraform-plan.yml`
- `.github/workflows/terraform-apply.yml`
- `.github/workflows/deploy-test.yml`
- `.github/workflows/deploy-production.yml`
- `.github/workflows/rollback-production.yml`
- `.github/workflows/bootstrap-first-admin.yml`
- `release/backend-release.schema.json`
- `release/version.schema.json`
- `release/version.json`
- `scripts/deploy/create_release_descriptor.py`
- `scripts/deploy/validate_release_descriptor.py`
- `scripts/deploy/smoke_test.py`
- `scripts/deploy/verify_traffic_state.py`
- `tests/unit/test_deployment_workflows.py`
- `docs/runbooks/cloud-deploy-migration-rollback.md`

Modify only:

- `tests/unit/test_deploy_config.py`
- `infra/terraform/modules/access_platform/serverless.tf`
- `README.md`
- `CLAUDE.md`
- `HANDOFF.md`

No deletion is authorized in this task. Specifically, do not recreate or touch the absent `.github/workflows/cloud-run.yml`, `backend/scripts/deploy.sh`, or `scripts/merge_and_deploy.py`; tests assert their absence. Other workflow, infrastructure, release, and migration files are consume-only.

## Locked release/version interfaces

- `release/version.json` is the sole checked-in compatibility source and contains exactly `$schema`, `schema_version`, `backend_version`, `api_version`, `client_version`, `minimum_client_version`, `minimum_server_version`, `release_notes`, `channel`—no extra properties.
- Local/test accepts the exact development sentinel shape from the plan; every production plan/deploy/release rejects development values. Production version changes occur only in a separate reviewed version-bump commit; this task does not choose a production version.
- Exact projection: backend → `RELEASE_VERSION`; API → `API_VERSION` and exactly `v1`; client → `LATEST_CLIENT_VERSION`; minimum client/server → matching variables; notes → `RELEASE_NOTES`. One validator emits the six-value immutable projection and `version_registry_sha256`; no CLI/input/Terraform/Python default competes.
- Backend descriptor required fields exactly: `schema_version`, `source_commit`, `image_digest`, `sbom_sha256`, `provenance_id`, `migration_head`, `api_version`, `release_version`, `version_registry_sha256`, `test_workflow_run`, `test_environment`, `created_at`, `creator_workflow`.
- Strict JSON Schemas reject extras; require 40-hex commit, Artifact Registry `@sha256:` digest, 64-hex hashes, UTC time, SemVer release, API `v1`, and nonempty test/provenance identifiers. Creation derives version only from validated registry; validation checks schema/hashes/digest/migration/registry/test evidence without production calls.

## Locked plan/apply and delivery interfaces

- `terraform-plan.yml` reusable inputs exactly `environment`, `terraform_root`, `image_digest`, `source_commit`, `version_registry_sha256`, `plan_purpose`; outputs exactly `plan_workflow_run_id`, `plan_workflow_name`, `plan_workflow_id`, `plan_artifact_id`, `plan_artifact_name`, `plan_sha256`.
- Plan has `workflow_call` plus manual wrapper, checks out source commit, validates registry, runs format/validate/test/policy/security, creates `reviewed.tfplan`, redacted `reviewed.txt`, and `plan-metadata.json`; upload name `tfplan-${environment}-${source_commit}-${github.run_id}`.
- Metadata/receipt binds repository, workflow name/numeric ID/run ID/job workflow ref, protected environment, full ref, source commit, digest, registry hash plus six values, root, purpose, plan hash, artifact numeric ID/name. Plan permissions are only the exact four read/OIDC/deployment permissions in the plan.
- `terraform-apply.yml` is `workflow_call` only. Before download it queries Actions/workflow/run/artifact and Deployments APIs read-only and validates current repo, expected origin workflow/path/ID, run success, protected environment, `refs/heads/main`, commit, receipt/hash, nonexpired exact numeric artifact ID and name tied to run. It downloads by numeric ID only, rejects extra/symlink members, recomputes binary hash, validates metadata/registry, then applies the exact saved plan after proper approval. It never replans or downloads by name alone.
- `deploy-test.yml` builds/pushes a test candidate once in the future protected workflow, resolves digest, validates SBOM/provenance/registry, calls plan and apply using all provenance values, then migration/verification, same-digest worker/API, fictional E2E/contract/load/failure tests, and attested descriptor. Workflow cannot access production/real data.
- `deploy-production.yml` is manual, consumes unchanged descriptor/hash and all six plan provenance values plus approval. It validates before download/apply, obtains separate production apply/deploy approvals, records prior revisions/traffic, verifies backup/PITR, runs migration/verification, worker, API `--no-traffic`, then exact candidate allocations 1, 10, 50, 100 with managed-host smoke/traffic/threshold gates.
- Failure restores 100% API traffic and worker to verified prior revisions, leaves expanded schema/data intact, exits nonzero.
- Terraform lifecycle ignore is narrowly limited to revision image/traffic fields; never IAM, ingress, secrets, service account, or configuration.
- `rollback-production.yml` requires environment `production-rollback` and exact inputs `release_descriptor_sha256`, `prior_api_revision`, `prior_worker_revision`, `expected_migration_head`, `incident_reference`; verifies revisions/digests/schema compatibility and changes only traffic/revision selection. No build, apply, job, secret, downgrade, or delete.
- Exact protected environments are external `test`, `production-plan`, `production-apply`, `production-deploy`, `production-rollback`. Workflows never create/weaken environments, reviewers, refs, secrets, or variables.
- No ordinary main push triggers credentialed deployment. No auto-merge/push, service-account key, mutable tag/source deployment, destructive Terraform/Alembic command, or production rebuild.
- `bootstrap-first-admin.yml` is manual only with exact inputs `target_environment`, `request_uri`, `expected_sha256`. It accepts target `test|production`, maps to static protected environments `test|production-deploy`, and invokes only exact `access-test-bootstrap-admin|access-production-bootstrap-admin` through OP-03 environment-scoped `admin-bootstrap` WIF. Each job authenticates only with environment variables `GCP_ADMIN_BOOTSTRAP_WIF_PROVIDER` and `GCP_ADMIN_BOOTSTRAP_SERVICE_ACCOUNT`, checked against the corresponding OP-03 outputs. Preserve the six existing environment names; do not add one.
- Bootstrap validates `refs/heads/main`, lowercase 64-hex request hash, `gs://` URI, and opaque `admin-bootstrap-requests/<v4-operation-uuid>.json` path. It passes only URI/hash as job arguments, invokes once with `--wait`, has no retry/continue-on-error, and never checks out/reads/echoes the request, logs, PIN, or secret version.
- Bootstrap job permissions are only `contents: read` and `id-token: write`. Safe summary provenance is exactly target environment, repository, workflow ref, main ref, source commit, workflow run ID, expected request hash, execution name, and status—never request URI/body, staff/account identity, approval reference/hash, PIN, secret/project/bucket value.
- PIN/version retrieval, communication, disable, and destruction remain an external authorized-custodian step under `docs/runbooks/initial-admin-enrollment.md`. On orphan cleanup status, workflow fails and protected retry is prohibited until external disable/destruction evidence is reviewed.

## TDD and local verification

1. Write `tests/unit/test_deployment_workflows.py` exactly from OP-08 Step 1 before workflows, including the bootstrap manual/protected/PIN-blind assertions. Extend `test_deploy_config.py` only as the plan requires.
2. Run:

```powershell
python -m pytest tests/unit/test_deployment_workflows.py tests/unit/test_deploy_config.py -q
```

Expected red: protected workflows are absent while OP-01 safety still proves old deployers absent. Do not accept unrelated failure.
3. Implement schema/registry/scripts, plan/apply, test/prod/rollback/bootstrap workflows, lifecycle ownership, documentation/runbook in plan order. Pin every third-party action to a reviewed full SHA. Bootstrap workflow definitions must not invoke a job in this session.
4. Run:

```powershell
python scripts/ci/check_workflow_pins.py
python -m json.tool release/backend-release.schema.json | Out-Null
python -m json.tool release/version.schema.json | Out-Null
python -m json.tool release/version.json | Out-Null
python -m pytest tests/unit/test_deployment_workflows.py tests/unit/test_deploy_config.py tests/unit/test_ci_release_gates.py -q
python -m pytest -q
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
git diff --check
```

Expected: all static/schema/local tests pass, bypass files remain absent, and no workflow is invoked.

## External gates and absolute dry-run boundary

`EXT-12`, `EXT-16`, GitHub environments/reviewers/ref policies/WIF variables, request objects/hashes, PIN custodian/cleanup evidence, required checks, Terraform plan review, migration review, security scan, test deployment evidence, backup state, traffic thresholds/windows, approvals, and production versions are external. Implement fail-closed checks and documentation only. Do not invoke `gh workflow`, Actions, artifact APIs against a live run, cloud auth, plan/apply, build push, migration/bootstrap job, deployment, smoke against an endpoint, traffic change, rollback, secret operation, or production read. The workflow YAML may describe those future protected operations; this Claude session must not execute them.

## Security/privacy and non-goals

Use only fictional/local fixtures. Descriptor, logs, receipts, summaries, smoke output, and docs contain no report/roster/person/PIN/token/secret/request-body/approval content. Do not expose environment configuration or accept long-lived keys. Do not alter application business logic, schema revisions, GitHub environment settings, or production versions. Do not push, merge, deploy, dispatch workflows, run Terraform plan against a real provider/apply/destroy, invoke migrations/bootstrap, shift traffic, sign, publish, change/read secrets, access cloud/production, or perform destructive Git/filesystem actions.

Explicitly—even though this task designs delivery workflows—do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Expected workflow test red state observed first.
- [ ] Registry has exact nine fields, strict schema, development sentinel, and sole-source projection.
- [ ] Descriptor schema/generator/validator bind all required provenance.
- [ ] Plan/apply bind exact run/workflow/repository/ref/environment/commit/digest/hash/artifact ID+name before download/apply.
- [ ] Test is build-once and fictional; production is manual, separate approvals, same digest, migrate/verify, staged traffic.
- [ ] Rollback changes no schema/data/secrets/Terraform and uses verified prior revisions.
- [ ] Bootstrap is manual/main-only, statically maps test/production protected environments and exact jobs/WIF, binds exact URI hash/provenance, and has no request/PIN/secret visibility or automatic retry.
- [ ] Custodian retrieval/communication/version disable/destruction and orphan cleanup remain explicit external human gates before completion/retry.
- [ ] Lifecycle ignore is narrow; bypass files remain absent; stale key/source guidance removed.
- [ ] All local checks pass and no workflow/cloud action ran.
- [ ] Only exact allowed files changed and exact commit message used once.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; run workflow-pin validation and complete diff review. Stop on any secret, production version, automatic trigger, mutable image/source deploy, by-name-only artifact, missing provenance check, or destructive command. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    '.github/workflows/terraform-plan.yml'
    '.github/workflows/terraform-apply.yml'
    '.github/workflows/deploy-test.yml'
    '.github/workflows/deploy-production.yml'
    '.github/workflows/rollback-production.yml'
    '.github/workflows/bootstrap-first-admin.yml'
    'release/backend-release.schema.json'
    'release/version.schema.json'
    'release/version.json'
    'scripts/deploy/create_release_descriptor.py'
    'scripts/deploy/validate_release_descriptor.py'
    'scripts/deploy/smoke_test.py'
    'scripts/deploy/verify_traffic_state.py'
    'tests/unit/test_deployment_workflows.py'
    'docs/runbooks/cloud-deploy-migration-rollback.md'
    'tests/unit/test_deploy_config.py'
    'infra/terraform/modules/access_platform/serverless.tf'
    'README.md'
    'CLAUDE.md'
    'HANDOFF.md'
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
git commit -m "ci: add approved digest promotion and rollback"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including registry/descriptor/provenance and every workflow trigger/environment/permission contract plus bootstrap request hash, exact job/WIF, safe summary, and external custodian boundary; security/privacy results and confirmation that no live workflow/cloud/secret/mutation occurred; assumptions, risks, deviations, NOT RUN items with reasons, remaining external gates, and unresolved production values; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, bootstrapped, traffic-shifted, signed, published, secrets-changed/read, or run against/accessed in production. Independent specification review precedes code-quality review.

Stop without committing if any prerequisite/check/evidence interface is absent, exact artifact/run provenance cannot be validated before apply, schema compatibility is uncertain, a production value would need invention, a workflow could bypass approval, or any prohibited action is required. Never weaken a gate to pass tests.
