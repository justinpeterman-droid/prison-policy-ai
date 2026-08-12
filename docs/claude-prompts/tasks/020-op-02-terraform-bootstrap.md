# Claude Code Prompt 020 — OP-02: Establish Terraform Bootstrap, Remote State, and Isolated Environment Layout

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **020**, task **OP-02: Establish Terraform Bootstrap, Remote State, and Isolated Environment Layout**.

## Objective, outcome, and rationale

Create a pinned, locally valid Terraform foundation, protected state-bucket bootstrap definition, and distinct test/production roots without creating or changing any cloud resource. This establishes deterministic provider versions and prevents test and production from sharing state, projects, identities, or credentials.

## Repository, baseline, and branch

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Required branch: `claude/op-02-terraform-state-foundation`
- Exact commit: `infra: establish isolated terraform state roots`

Preflight from the root:

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

Require the baseline to be an ancestor of current reviewed `main`. If `HEAD` advanced, inspect `git log --oneline $TaskBase..HEAD`, read the predecessor handoffs/plans, and verify every intervening commit is reviewed, required OP-01 outputs exist, and nothing conflicts. Start from current `HEAD`. Stop if ancestry/review/prerequisites fail or a dirty path overlaps the allowlist or makes switching unsafe. Leave unrelated user changes untouched—never reset, clean, restore, stash, overwrite, or delete them. Run `git switch -c claude/op-02-terraform-state-foundation`; stop if the branch exists.

## Required reading

Read `AGENTS.md`; the approved deployment-rollout specification; the roadmap's `Global Constraints`, `Program Gates`, and `Agent Task Protocol`; and the detailed deployment plan from the exact heading `### Task OP-02: Establish Terraform Bootstrap, Remote State, and Isolated Environment Layout` through the separator before OP-03. Also read OP-01's `docs/operations/external-prerequisites.md` and `docs/operations/github-environment-policy.md` if present. Consumed documents are read-only.

## Exact allowed files

Create only:

- `infra/terraform/bootstrap/state/versions.tf`
- `infra/terraform/bootstrap/state/variables.tf`
- `infra/terraform/bootstrap/state/main.tf`
- `infra/terraform/bootstrap/state/outputs.tf`
- `infra/terraform/environments/test/versions.tf`
- `infra/terraform/environments/test/backend.tf`
- `infra/terraform/environments/test/variables.tf`
- `infra/terraform/environments/test/outputs.tf`
- `infra/terraform/environments/test/.terraform.lock.hcl`
- `infra/terraform/environments/production/versions.tf`
- `infra/terraform/environments/production/backend.tf`
- `infra/terraform/environments/production/variables.tf`
- `infra/terraform/environments/production/outputs.tf`
- `infra/terraform/environments/production/.terraform.lock.hcl`
- `infra/terraform/tests/test_layout.py`
- `docs/runbooks/terraform-state-bootstrap.md`

Do not modify or delete any other file. Provider/plugin download caches and Terraform local state must remain untracked and outside the commit.

## Locked interfaces

- Pin Terraform exactly to `1.15.8` and `hashicorp/google` exactly to `7.40.0` in all three roots.
- Bootstrap inputs are exactly `project_id`, `state_bucket_name`, `region`, and `authorized_member`; output is `state_bucket_name`.
- Environment inputs include exactly `project_id`, `environment`, `region`, `source_repository`, and `labels`.
- Test remote-state prefix is exactly `access/test`; production is exactly `access/production`. The GCS bucket name is supplied externally during human initialization and must not be committed.
- Test validates `environment == "test"`; production validates `environment == "production"` and `region == "us-central1"`.
- The state bucket uses uniform bucket-level access, public-access prevention, versioning, 30-day retention, noncurrent-version retention for 90 days, `prevent_destroy = true`, and grants only `var.authorized_member` `roles/storage.objectAdmin`.
- Create no project, credential, secret version, state object, or real cloud identifier.
- Both environment lock files select Google provider `7.40.0` and include Linux AMD64 and Windows AMD64 hashes.

## TDD test-first execution and expected results

1. Create `infra/terraform/tests/test_layout.py` exactly from OP-02 Step 1.
2. Run:

```powershell
python -m pytest infra/terraform/tests/test_layout.py -q
```

Expected red result: failure because `infra/terraform/bootstrap/state/versions.tf` is absent. Do not accept an unrelated collection/environment failure as the red state.

3. Implement the three identical exact provider blocks, bootstrap resources/variables/output, distinct environment backend/variable/output contracts, and runbook.
4. Generate provider locks from each environment root using only:

```powershell
terraform -chdir=infra/terraform/environments/test providers lock -platform=linux_amd64 -platform=windows_amd64
terraform -chdir=infra/terraform/environments/production providers lock -platform=linux_amd64 -platform=windows_amd64
```

This metadata download is permitted; Google authentication, backend initialization, and resource creation are not.
5. Run focused and regression checks:

```powershell
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/bootstrap/state init -backend=false
terraform -chdir=infra/terraform/bootstrap/state validate
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/production init -backend=false
terraform -chdir=infra/terraform/environments/production validate
python -m pytest infra/terraform/tests/test_layout.py -q
git diff --check
```

Expected: all checks pass locally without Google credentials. No `.tfstate`, `.tfvars`, project ID, bucket name, or member identity is tracked.

## External gates and dry-run boundary

OP-01 gates `EXT-01`, `EXT-02`, and `EXT-05` must be reviewed before a human apply; they may remain closed while this local definition is implemented. The runbook must clearly mark `terraform apply` and `terraform init -migrate-state` as human-operator-only. Document encrypted temporary local bootstrap state, control verification, migration verification, and secure disposal, but do not execute any of them. Use `init -backend=false` only. Do not contact a GCS backend or Google API.

## Security, privacy, and forbidden scope

Use fictional examples and data only; never use production data or real identifiers. Use no real project, member, repository, bucket, owner, or credential value. Do not create `.tfvars`, state, plan, credentials, service-account keys, secrets, or completed evidence. Do not implement OP-03 resources, WIF, service accounts, SQL, Cloud Run, DNS, or deployments. Do not refactor unrelated code. Do not push, merge, deploy, apply Terraform, migrate state, sign, publish, change secrets, access production/test cloud resources, or run destructive Git/filesystem commands.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Expected test-first failure was observed.
- [ ] Exact Terraform/provider pins appear in all three roots.
- [ ] State bootstrap has all required protection, retention, versioning, IAM, and `prevent_destroy` settings.
- [ ] Test/production prefixes and validation are distinct and exact.
- [ ] Both committed lock files support Linux/Windows AMD64.
- [ ] Runbook keeps mutating state/bootstrap commands human-only.
- [ ] All allowed-file local tests and validations pass credential-free.
- [ ] No state, plan, `.tfvars`, cache, or real identifier is tracked.
- [ ] Only allowed paths changed and one exact-message commit was created.

## Diff allowlist, commit, and handoff

Build the exact allowlist, check the union of unstaged, staged, and untracked paths, and ignore only user-owned `.superpowers/*`. Inspect `git status --short` for `.terraform/`, state, plan, crash, override, variable, or credential files and leave them untracked. Then stage only exact allowlisted paths and re-check the index before committing:

```powershell
$allowed = @(
    'infra/terraform/bootstrap/state/versions.tf'
    'infra/terraform/bootstrap/state/variables.tf'
    'infra/terraform/bootstrap/state/main.tf'
    'infra/terraform/bootstrap/state/outputs.tf'
    'infra/terraform/environments/test/versions.tf'
    'infra/terraform/environments/test/backend.tf'
    'infra/terraform/environments/test/variables.tf'
    'infra/terraform/environments/test/outputs.tf'
    'infra/terraform/environments/test/.terraform.lock.hcl'
    'infra/terraform/environments/production/versions.tf'
    'infra/terraform/environments/production/backend.tf'
    'infra/terraform/environments/production/variables.tf'
    'infra/terraform/environments/production/outputs.tf'
    'infra/terraform/environments/production/.terraform.lock.hcl'
    'infra/terraform/tests/test_layout.py'
    'docs/runbooks/terraform-state-bootstrap.md'
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
git commit -m "infra: establish isolated terraform state roots"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including provider-lock platforms and Terraform inputs/outputs; security/privacy review results and confirmation that no backend/cloud call or mutating Terraform command ran; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production. Independent specification review must precede code-quality review.

Stop without committing if a pin cannot be resolved from official distribution, isolation is ambiguous, a real identifier is required, an allowed path overlaps user work, any test cannot run as designed, or any prohibited action would be necessary. Never weaken tests or protections.
