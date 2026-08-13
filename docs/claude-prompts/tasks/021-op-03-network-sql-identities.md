# Claude Code Prompt 021 — OP-03: Provision VPC, Cloud SQL PostgreSQL 17, Secret Containers, and Least-Privilege Identities

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **021**, task **OP-03: Provision VPC, Cloud SQL PostgreSQL 17, Secret Containers, and Least-Privilege Identities**.

## Objective, outcome, and rationale

Implement a plan-time-safe Terraform module for a private PostgreSQL 17 foundation, single-purpose runtime/workflow identities including first-Admin bootstrap, external GitHub WIF trust, and empty Secret Manager containers including isolated bootstrap-PIN and client-update-grant secrets. No secret values or service-account keys may enter Terraform or Git. The outcome must fail closed against public SQL, shared identities, broad roles, cross-environment trust, secret payload access, and repository-managed GitHub environment protection.

## Repository, baseline, and branch

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-03-private-sql-identities`
- Commit: `infra: define private sql and least privilege identities`

Run this preflight before recording the task start or creating the branch:

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The baseline must be an ancestor of current reviewed `main`. If `HEAD` advanced, inspect `git log --oneline $TaskBase..HEAD`, read predecessor handoffs/plans, and verify every intervening commit is reviewed, OP-01/OP-02 outputs exist, and no conflict exists. Start the branch with `git switch -c claude/op-03-private-sql-identities` from current `HEAD`. Stop if ancestry/review/prerequisites fail, the branch exists, or dirty work overlaps/makes switching unsafe. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; the approved deployment-rollout design; the roadmap's global constraints, locked repository structure, program gates, and agent protocol; OP-01's external/GitHub environment policy; OP-02 Terraform roots/interfaces; and the detailed plan from `### Task OP-03: Provision VPC, Cloud SQL PostgreSQL 17, Secret Containers, and Least-Privilege Identities` through the OP-04 separator. Consumed files are read-only unless listed below.

## Exact allowed files

Create only:

- `infra/terraform/modules/access_platform/project_services.tf`
- `infra/terraform/modules/access_platform/network.tf`
- `infra/terraform/modules/access_platform/sql.tf`
- `infra/terraform/modules/access_platform/identities.tf`
- `infra/terraform/modules/access_platform/secrets.tf`
- `infra/terraform/modules/access_platform/variables.tf`
- `infra/terraform/modules/access_platform/outputs.tf`
- `infra/terraform/environments/test/main.tf`
- `infra/terraform/environments/production/main.tf`
- `infra/terraform/tests/access_platform.tftest.hcl`
- `infra/terraform/tests/test_security_contract.py`
- `docs/runbooks/secret-population-and-rotation.md`

Do not modify or delete any other path. OP-02 files are consume-only except the two new `main.tf` files listed here.

## Locked interfaces

- Module inputs: `environment`, `project_id`, `region`, `network_name`, `database_instance_name`, `database_name`, `sql_tier`, `github_repository`, `github_ref_pattern`, `enable_access_release_identity`, and `wif_trust`.
- `wif_trust` is keyed exactly by `terraform-plan`, `terraform-apply`, `deploy`, `rollback`, `admin-bootstrap`, and `access-release`; each value contains `github_environment`, `workflow_refs`, and `ref_pattern` and agrees exactly with the external OP-01 policy.
- Runtime outputs: `api_service_account_email`, `worker_service_account_email`, `task_invoker_service_account_email`, `migration_service_account_email`, `bootstrap_service_account_email`.
- Workflow outputs: `terraform_plan_service_account_email`, `terraform_apply_service_account_email`, `deploy_service_account_email`, `rollback_service_account_email`, `admin_bootstrap_service_account_email`, nullable `access_release_service_account_email`; WIF outputs exactly `terraform_plan_wif_provider_name`, `terraform_apply_wif_provider_name`, `deploy_wif_provider_name`, `rollback_wif_provider_name`, `admin_bootstrap_wif_provider_name`, and nullable `access_release_wif_provider_name`.
- Other outputs: `network_id`, `private_subnet_id`, `database_instance_connection_name`, `database_private_ip`, `database_name`, and `secret_resource_ids`.
- Enable exactly the Google APIs enumerated in OP-03 Step 3 with `disable_on_destroy = false` and expose a dependency token.
- Custom VPC, `us-central1` subnet, Private Google Access, reserved private-service range, and Service Networking connection; no public DB/firewall path.
- Cloud SQL is exactly `POSTGRES_17`; private IP, `ssl_mode = "ENCRYPTED_ONLY"`, PITR, 14 retained backups, seven transaction-log days, automatic storage growth; production is regional HA and deletion-protected.
- Create the database but no password-bearing SQL user.
- Create ten accounts in test and eleven in production: runtime `api`, `worker`, `task-invoker`, `migration`, `bootstrap`; workflow `terraform-plan`, `terraform-apply`, `deploy`, `rollback`, `admin-bootstrap`; plus production-only `access-release`.
- Apply every exact least-privilege boundary in OP-03 Step 6. `terraform-plan` is read-only; `terraform-apply`, `deploy`, `rollback`, `admin-bootstrap`, and `access-release` remain distinct; no workflow identity reads application secret payloads.
- Bootstrap runtime has only Cloud SQL Client, accessor on `access-database-url`, and `roles/secretmanager.secretVersionAdder` on `initial-admin-pin`; it has no secret-version access. OP-04 later binds this exact identity to read private configuration-bucket objects under `admin-bootstrap-requests/` only. OP-06 later binds the workflow identity to invoke only `access-{environment}-bootstrap-admin`.
- `admin-bootstrap` WIF binds only `.github/workflows/bootstrap-first-admin.yml`, exact repository and `refs/heads/main`, environment `test` in test and `production-deploy` in production. It has no SQL, secret, bucket, build, deploy, Terraform, or other-job permission. No fork/unprotected workflow and no long-lived key.
- Secret containers are exactly `access-database-url`, `identity-hash-pepper`, `cursor-signing-key`, `client-update-grant-key`, `legacy-access-code`, `legacy-admin-code`, `github-feedback-token`, `flask-session-secret`, and `initial-admin-pin`. Never create `google_secret_manager_secret_version`.
- Per-secret IAM only. API is the sole accessor on `client-update-grant-key`; document its independent generation, population, version pinning, rotation, rollback, and audit verification along with the independent pepper/cursor-key procedures. `initial-admin-pin` is populated only later by bootstrap runtime and retrieved/disabled/destroyed only by the external custodian; neither bootstrap identity may read it.

## TDD and validation

1. Write `infra/terraform/tests/test_security_contract.py` from OP-03 Step 1 before implementation. Because the specified assertions call `re.findall`, include the required `import re`; do not remove or weaken any assertion.
2. Run:

```powershell
python -m pytest infra/terraform/tests/test_security_contract.py -q
```

Expected red: missing `infra/terraform/modules/access_platform/sql.tf`. An unrelated import/collection failure is not acceptable.
3. Implement services, network, SQL, all ten/eleven identities and six WIF contracts, nine empty secrets, isolated root wiring, mocked native tests, and the human-only runbook. Tests must prove bootstrap runtime/workflow separation, environment-specific bootstrap trust, API-only update-grant access, version-adder-without-accessor, and absence of secret versions.
4. Use only fictional native-test values `slut-access-production-fixture` and `example.invalid/agency/prison-policy-ai`.
5. Run:

```powershell
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
New-Item -ItemType Directory -Force infra/terraform/environments/test/tests | Out-Null
Copy-Item infra/terraform/tests/access_platform.tftest.hcl infra/terraform/environments/test/tests/access_platform.tftest.hcl -Force
terraform -chdir=infra/terraform/environments/test test -test-directory=tests
Remove-Item -LiteralPath infra/terraform/environments/test/tests -Recurse -Force
terraform -chdir=infra/terraform/environments/production init -backend=false
terraform -chdir=infra/terraform/environments/production validate
New-Item -ItemType Directory -Force infra/terraform/environments/production/tests | Out-Null
Copy-Item infra/terraform/tests/access_platform.tftest.hcl infra/terraform/environments/production/tests/access_platform.tftest.hcl -Force
terraform -chdir=infra/terraform/environments/production test -test-directory=tests
Remove-Item -LiteralPath infra/terraform/environments/production/tests -Recurse -Force
python -m pytest infra/terraform/tests/test_layout.py infra/terraform/tests/test_security_contract.py -q
git diff --check
```

Expected: local mocked-provider checks pass without Google credentials, and no plan is applied.

## External gates and local-only boundary

`EXT-05`, `EXT-12`, and `EXT-16`, project IDs, source repository, issuer inputs, SQL tier, state locations, request/PIN custodians, and secret custodians are external. Preserve the exact six environment names; bootstrap shares `test` and `production-deploy` and creates no seventh environment. Use variables and fictional mocked inputs only. Do not create/configure GitHub environments, reviewers, allowed refs, GitHub repository settings, secret versions, SQL users/passwords, WIF credentials, or service-account keys. Do not run `terraform plan` against a real provider, `terraform apply`, backend initialization, cloud CLI, console, or credentialed test.

## Security/privacy and non-goals

Never place a project ID, repository identity, database IP/password/URL, secret, WIF token, certificate, person, employee data, approval reference, report content, or operational evidence in Git/logs. No Owner/Editor role; no broad Secret Manager accessor; no public SQL; no shared test/production identity. Do not implement Cloud Run, Tasks, buckets, DNS, dashboards, jobs, deployment workflows, or populate anything. Do not refactor upstream roots. Do not push, merge, deploy, apply/destroy/import Terraform, sign, publish, change secrets, access production, or perform destructive Git/filesystem actions.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Required red failure was observed first.
- [ ] Exact module inputs/outputs and nine empty secret containers exist.
- [ ] PostgreSQL 17 private/encrypted/PITR/backup/HA/deletion controls match the plan.
- [ ] Test has ten and production eleven distinct service accounts.
- [ ] Six workflow roles/providers have exact trust and least-privilege boundaries, including test/production bootstrap environment claims.
- [ ] Bootstrap runtime can add but not read its PIN secret and cannot read outside the future request prefix; workflow bootstrap has no runtime privilege; API alone accesses the update-grant key.
- [ ] No secret version, key resource, GitHub provider/environment, Owner, or Editor exists.
- [ ] Test/production pass distinct fictional values and access-release is production-only.
- [ ] Native/Python Terraform tests pass with mocked providers and no credentials.
- [ ] Only exact allowed paths changed; one exact-message commit exists.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; inspect for `.tfstate`, `.tfvars`, plans, `.terraform`, credentials, identifiers, and secrets. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'infra/terraform/modules/access_platform/project_services.tf'
    'infra/terraform/modules/access_platform/network.tf'
    'infra/terraform/modules/access_platform/sql.tf'
    'infra/terraform/modules/access_platform/identities.tf'
    'infra/terraform/modules/access_platform/secrets.tf'
    'infra/terraform/modules/access_platform/variables.tf'
    'infra/terraform/modules/access_platform/outputs.tf'
    'infra/terraform/environments/test/main.tf'
    'infra/terraform/environments/production/main.tf'
    'infra/terraform/tests/access_platform.tftest.hcl'
    'infra/terraform/tests/test_security_contract.py'
    'docs/runbooks/secret-population-and-rotation.md'
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
git commit -m "infra: define private sql and least privilege identities"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including exact inputs/outputs, identity counts, and secret names; security/privacy review results and confirmation that no credential/cloud/apply action occurred; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production. Independent specification review precedes code-quality review.

Stop without committing if an upstream interface is absent, WIF policy cannot be expressed exactly, a role must be broadened, a secret value/real identifier is needed, tests cannot run locally, or any prohibited action is required. Never loosen assertions to obtain green.
