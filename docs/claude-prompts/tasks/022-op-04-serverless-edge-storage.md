# Claude Code Prompt 022 — OP-04: Provision Cloud Run API and Worker, Cloud Tasks, Edge, DNS, and Private Storage

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **022**, task **OP-04: Provision Cloud Run API and Worker, Cloud Tasks, Edge, DNS, and Private Storage**.

## Objective, outcome, and rationale

Define—not deploy—the same-digest API/worker topology, OIDC-authenticated Cloud Tasks delivery, managed HTTPS load-balancer edge, Cloud Armor, DNS, and five private versioned buckets. The design must make the worker private, prevent direct external `run.app` API bypass, pin both services to one immutable digest, give the API read-only mediated access to release artifacts, restrict the first-Admin bootstrap identity to one private request prefix, and keep Access clients away from Google service credentials and bucket URLs.

## Repository, baseline, and branch

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-04-serverless-edge-storage`
- Commit: `infra: define private api worker and managed edge`

Run this preflight before recording the task start or creating the branch:

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The baseline must be an ancestor of current reviewed `main`. If `HEAD` advanced, inspect `git log --oneline $TaskBase..HEAD`, predecessor handoffs/plans, and confirm every commit is reviewed, OP-01 through OP-03 outputs exist, and no conflict exists. Create `claude/op-04-serverless-edge-storage` from current `HEAD`, not the old baseline. Stop on failed ancestry/review/prerequisites, existing branch, or overlapping/unsafe dirty work. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; the approved deployment-rollout design; roadmap global constraints/shared HTTP rules/program gates/agent protocol; the reviewed OP-03 module interfaces including `google_service_account.bootstrap`, `bootstrap_service_account_email`, and the dedicated `client-update-grant-key`; RP-07 worker task interface; and the detailed plan from the exact OP-04 heading through the OP-05 separator. Read-only upstream entry points are `backend.webapp.app:create_app()` and `backend.worker.app:create_worker_app()`.

## Exact allowed files

Create only:

- `infra/terraform/modules/access_platform/storage.tf`
- `infra/terraform/modules/access_platform/serverless.tf`
- `infra/terraform/modules/access_platform/tasks.tf`
- `infra/terraform/modules/access_platform/edge.tf`
- `infra/terraform/tests/test_serverless_contract.py`
- `docs/runbooks/edge-and-service-verification.md`

Modify only:

- `infra/terraform/modules/access_platform/variables.tf`
- `infra/terraform/modules/access_platform/outputs.tf`
- `infra/terraform/modules/access_platform/identities.tf`
- `infra/terraform/environments/test/main.tf`
- `infra/terraform/environments/production/main.tf`
- `infra/terraform/environments/test/variables.tf`
- `infra/terraform/environments/production/variables.tf`
- `infra/terraform/tests/access_platform.tftest.hcl`

No deletion is authorized. All other upstream files are consume-only.

## Locked interfaces

- Consume the OP-03 network, identities, DB connection name, and secret resource IDs plus one Artifact Registry `image_digest` ending in `@sha256:` and exactly 64 lowercase hex characters.
- After its concrete resources exist, bind the already-created OP-03 workflow accounts at resource scope only: deploy to this environment's Artifact Registry repository, API/worker/migration Cloud Run services/jobs and their runtime service accounts; rollback through its custom traffic role to only API/worker services; and production access-release to immutable release-bucket paths. Never replace these with project-wide roles. Vertex AI/Discovery Engine data-store and managed-signing-service permissions remain external resource-interface gates until their approved resource IDs and IAM interfaces are supplied. Cloud Run exposes no separate IAM permission for revision-only deployment or traffic-only updates: its service-scoped `run.services.update` is necessary for both. Therefore IAM limits deploy/rollback to the named services, while OP-08 protected workflow validation is the mandatory second control: deploy accepts only an approved immutable digest/projection and rollback accepts only reviewed prior revisions/traffic payloads; neither workflow may submit configuration, secret, service-account, ingress, or scaling changes.
- Extend the OP-03 Terraform-apply management identity only with the exact reviewed roles necessary to create/manage this task's declared Artifact Registry, Cloud Run, Cloud Tasks, Storage, DNS, certificate, load-balancer, and Cloud Armor resources. Keep application-secret payload access, build/push, migration invocation, revision deployment, signing, and unrelated project administration prohibited. The initial resource-management privilege required to create these IAM/custom-role bindings must be externally pre-granted and verified before the first human Terraform apply; the Terraform identity must not self-grant it. Bind deploy only to the named API/worker/migration services/jobs and their runtime service accounts; do not claim IAM can distinguish revision/traffic payloads from other service updates. The rollback custom role must include exactly `run.services.get`, `run.services.update`, `run.operations.get`, `run.revisions.get`, and `run.revisions.list`, scoped only to API and worker services.
- API and worker use the identical `var.image_digest`; never a tag or source deployment.
- API entry point is Gunicorn `backend.webapp.app:create_app()` with ingress exactly `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`. Grant `roles/run.invoker` to `allUsers` only on that API service, because Cloud Run still enforces invoker IAM after the external HTTPS load balancer. The internal-and-cloud-load-balancing ingress setting is the mandatory direct-`run.app` bypass control; never grant `allUsers` on worker or any other service/job.
- Worker entry point is Gunicorn `backend.worker.app:create_worker_app()` with ingress exactly `INGRESS_TRAFFIC_INTERNAL_ONLY`.
- Both API and worker containers define startup and liveness probes with bounded initial delay, timeout, period, and failure thresholds appropriate to their private health endpoints; probes never expose or log a secret, credential, report, or roster value.
- Only task-invoker receives worker `roles/run.invoker`; never `allUsers`.
- Create one environment-specific queue with reviewed retry/backoff/concurrency/rate settings. API enqueues; RP-07 supplies OIDC service-account email and audience equal to the reviewed worker URL.
- Create exactly five private, uniform, public-access-prevented, versioned buckets: release, configuration/templates, logical backups, roster, and Review Lab. Access clients receive no bucket credentials or direct URLs.
- Grant only the API identity `roles/storage.objectViewer` on the controlled immutable release bucket. It receives no object create/overwrite/delete permission; worker identities and Access workstations receive no release-bucket binding. Project the non-secret bucket name to API-only `ACCESS_RELEASE_BUCKET`.
- Grant `google_service_account.bootstrap.member` conditional `roles/storage.objectViewer` on configuration-bucket object resource names beginning with exactly `admin-bootstrap-requests/`. Expose non-secret `ADMIN_BOOTSTRAP_REQUEST_BUCKET` and `ADMIN_BOOTSTRAP_REQUEST_PREFIX=admin-bootstrap-requests/` for OP-06's `access-{environment}-bootstrap-admin` job, with no list-all/write/delete/outside-prefix access.
- Build the HTTPS edge from serverless NEG, backend with Cloud Armor, URL map, managed certificate, HTTPS proxy, global IP/forwarding, DNS; redirect HTTP to HTTPS and block direct external Cloud Run ingress.
- Consume all exact runtime names in the plan, including `ACCESS_API_ENABLED=true`, Google/model/search settings, Cloud Tasks/worker URL, source/version compatibility, public base URL, legacy mode, `ACCESS_RELEASE_BUCKET`, roster/review bucket names, bootstrap request bucket/prefix, legacy/feedback secret projections, and logging.
- Secret values are referenced only by the OP-03 Secret Manager resources. Project `DATABASE_URL`, `IDENTITY_HASH_PEPPER`, `CURSOR_SIGNING_KEY`, and `CLIENT_UPDATE_GRANT_KEY` from their exact containers into the API; worker receives no client-update key. The bootstrap bucket/prefix values are reserved for the OP-06 job, not injected into API/worker.
- Compatibility variables are `source_commit`, `release_version`, `api_version`, `latest_client_version`, `minimum_client_version`, `minimum_server_version`, and `release_notes`; production gives them no defaults. Require `api_version == "v1"`, validate four versions as SemVer-or-development, source commit as 40 hex outside fixtures, and one-line 1–500 character release notes without controls.
- The production root obtains image, source/version, hostname, model/search, capacity, and DNS values only through required external variables declared in its permitted `variables.tf`; no fictional/default production value may be embedded in `production/main.tf`. Test-only fictional values remain allowed only in test-root fixtures.
- Exact environment projection: `RELEASE_VERSION`, `API_VERSION`, `LATEST_CLIENT_VERSION`, `MINIMUM_CLIENT_VERSION`, `MINIMUM_SERVER_VERSION`, `RELEASE_NOTES`. Set managed HTTPS `PUBLIC_BASE_URL`; stamp both services with the same source, release, and digest labels.
- Outputs are exactly `api_service_name`, `worker_service_name`, `api_revision_uri`, `worker_uri`, `queue_name`, `managed_hostname`, `load_balancer_ip`, `release_bucket_name`, `configuration_bucket_name`, `logical_backup_bucket_name`, `roster_bucket_name`, and `review_bucket_name`.
- Native Terraform assertions may use a non-sensitive `terraform_test_contract` output containing only booleans, counts, role categories, and fixed labels. It must not expose image references, IAM members, resource names/IDs, hostnames, IPs, or any secret value. Every security assertion must derive from complete actual Terraform resource collections and exact safe per-key relationships, never source text or selected intended subsets.

## TDD and local validation

1. Write `infra/terraform/tests/test_serverless_contract.py` exactly from OP-04 Step 1 before Terraform implementation.
2. Run:

```powershell
python -m pytest infra/terraform/tests/test_serverless_contract.py -q
```

Expected red: missing `infra/terraform/modules/access_platform/serverless.tf`. Unrelated collection failures do not satisfy TDD.
3. Implement variables, storage and exact conditional IAM, services, Tasks, edge, outputs/root wiring, mocked assertions, and the read-only operator verification runbook. Tests must prove API-only release read/no write, no worker/workstation release access, exact bootstrap-prefix-only read, API-only grant-key projection, and absence of a bucket credential or public object path.
4. Run:

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
python -m pytest infra/terraform/tests/test_layout.py infra/terraform/tests/test_security_contract.py infra/terraform/tests/test_serverless_contract.py -q
git diff --check
```

Expected: all checks pass with mocked providers and no credential, resource creation, service request, or endpoint contact.

## External gates and dry-run boundary

Real digest, projects, hostnames/DNS zone, certificate state, model/search resources, queue capacities, bucket names, Cloud Run capacity, load/cost settings, secrets, and identity IDs remain approved external inputs. The runbook may document human read-only checks for DNS, certificate, Cloud Armor, ingress/IAM, Tasks audience, release-bucket API-only read, exact bootstrap request-prefix condition, bucket protection, and revision digest. Do not run them. Use `init -backend=false` and mocked Terraform tests only. No plan against real providers and no apply.

## Security/privacy and non-goals

Use fictional examples and data only; never use production data or real identifiers. No public bucket, public worker, direct external API ingress, mutable tag/model alias, source deployment, literal secret, real hostname/project/ID, or sensitive request logging. Test and production may share no resource identity or data. Do not modify Flask/worker/report code, implement RP-07, OP-05 observability, OP-06 jobs, or OP-08 workflows. Do not push, merge, deploy, invoke Cloud Tasks, call endpoints, apply/destroy/import Terraform, change traffic/DNS/secrets, sign/publish, access cloud/production, or run destructive Git/filesystem commands.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Required red test observed before implementation.
- [ ] API/worker share one immutable digest and have exact distinct ingress.
- [ ] Only task-invoker can invoke worker; API alone enqueues.
- [ ] Five exact buckets are private, uniform, versioned, and lifecycle-controlled.
- [ ] API alone has read-only release-object access; worker/workstations have none.
- [ ] Bootstrap runtime can read only exact `admin-bootstrap-requests/` configuration objects and no broader object set.
- [ ] HTTPS edge and Cloud Armor exist in mocked Terraform contract.
- [ ] All exact runtime/version projections, API-only grant key/release bucket, and Secret Manager references are present.
- [ ] Outputs and test/production naming/isolation match the plan.
- [ ] Runbook is read-only and agent-prohibited for cloud use.
- [ ] Focused/regression validation is green and only allowed files changed.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; inspect all task changes for tags, `allUsers`, source deployment, public storage, direct secret strings, and lifecycle ignores. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'infra/terraform/modules/access_platform/storage.tf'
    'infra/terraform/modules/access_platform/serverless.tf'
    'infra/terraform/modules/access_platform/tasks.tf'
    'infra/terraform/modules/access_platform/edge.tf'
    'infra/terraform/tests/test_serverless_contract.py'
    'docs/runbooks/edge-and-service-verification.md'
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
git commit -m "infra: define private api worker and managed edge"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including input/output and ingress/IAM/storage/version contracts; security/privacy results and confirmation that no endpoint/cloud/apply operation occurred; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates and inputs; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production. Independent specification review comes before code-quality review.

Stop without committing if upstream identities/entry points are missing, image equality or OIDC audience cannot be proven, a real identifier/secret is needed, Terraform would expose a service publicly, or any prohibited operation is required. Never weaken a test or boundary.
