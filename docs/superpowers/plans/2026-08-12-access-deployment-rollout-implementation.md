# Access Deployment, Testing, and Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved Microsoft Access client and centralized Cloud Run system without replacing the existing report, policy-search, validation, or Word-template engines.

**Architecture:** The existing Flask application gains a versioned `/api/v1` boundary, PostgreSQL persistence, individual authentication, immutable report revisions, and private background workers. A rebuildable Microsoft Access client consumes only that API; Terraform, GitHub Actions, signed release tooling, and operational runbooks provide isolated test and production delivery.

**Tech Stack:** Python 3.14 container and Python 3.12/3.14 CI, Flask 3, SQLAlchemy 2.0.51, Alembic 1.18.5, Psycopg 3.3.4, Pydantic 2.13.4, Argon2-cffi 25.1.0, PostgreSQL 17, Google Cloud Run/Cloud SQL/Cloud Tasks/Secret Manager/Cloud Armor, Terraform 1.15.8 with Google provider 7.40.0, Microsoft Access/VBA7, WinHTTP, Windows DPAPI, PowerShell, and a .NET 8 self-contained updater.

## Global Constraints

- Windows clients are agency-managed Windows 11 workstations with Microsoft Access already installed.
- The existing Flask report pipeline, Policy Expert citation behavior, validation rules, anti-fabrication controls, and `templates/005_template_v3.docx` remain the behavioral baseline.
- Access never connects directly to PostgreSQL, Vertex AI, Discovery Engine, Cloud Storage, Secret Manager, or Cloud Tasks.
- `/api/v1` uses individual bearer authentication; legacy shared-code browser cookies never authenticate `/api/v1`.
- All database and API timestamps are UTC; all public identities are server-generated UUIDs.
- Employee numbers are normalized case-insensitively but remain display identifiers, not secrets.
- PINs contain only ASCII letters and digits, preserve leading zeroes, are 4–8 characters, and compare case-insensitively after uppercase normalization.
- PIN hashes use Argon2id with 64 MiB memory, three iterations, parallelism 1, a 16-byte salt, and a 32-byte hash; one verification must benchmark below 500 ms on the selected Cloud Run minimum instance.
- Access tokens last 15 minutes. Nonpersistent renewal tokens remain in memory and expire within 12 hours. Persistent renewal tokens are DPAPI-protected and expire after 30 days of inactivity.
- Admin Center elevation expires after 15 minutes of inactivity. Sensitive Admin step-up grants expire after five minutes and are purpose-scoped.
- Every successful content change creates an immutable, attributable revision. Completed and Archived are organizational statuses and never permanently lock editing.
- Owner and preparer access the same canonical report; no copied report is created for collaboration.
- All modifying and AI-submission requests use idempotency keys. Revisioned writes require a base revision and return `409 revision_conflict` rather than overwriting.
- Report AI work uses durable Cloud Tasks jobs. Policy Expert remains synchronous with a 90-second timeout in release 1.
- Word documents are generated from an explicit saved revision, streamed, hashed, audited, and not retained centrally.
- Production regional resources are in `us-central1`. Production PostgreSQL is Cloud SQL PostgreSQL 17 with regional high availability, private IP, deletion protection, automated backups, and point-in-time recovery.
- Test and production use separate projects or equivalently isolated resources, identities, databases, queues, buckets, secrets, hostnames, audit data, and Discovery Engine data stores. Production data is prohibited in test.
- Terraform CLI is pinned to `1.15.8`; `hashicorp/google` is pinned to `7.40.0`; `.terraform.lock.hcl` is committed with Linux and Windows AMD64 hashes.
- VBA declarations use `PtrSafe` and `LongPtr` with `#If VBA7` and `#If Win64` where pointer width matters.
- VBA-JSON is vendored from tag `v2.3.1`, commit `1e49ba826b979d1851029dc965ecb6a3ead2a32c`. `JsonConverter.bas` SHA-256 is `1C240AA3C7EF536C25BF44061B02B0FADEB39BFB449F67C419822650E23F6169`; `LICENSE` SHA-256 is `F902104A3E36DAEA3A33F7ADFCD25C5AC69791E9164B83A81B8D0B235728C9BD`.
- Every automated test uses fictional identities and incidents. PINs, tokens, field notes, reports, names, employee numbers, and inmate identifiers never enter logs, diagnostics, alerts, or public issues.
- Codex and Claude Code may edit and test local/test-scope code only. They must not deploy, push, merge, delete resources/data, access production data, handle signing keys, or change secrets without separate explicit authorization.
- One task produces one focused commit and passes an independent specification-compliance and code-quality review before a dependent task begins.

## Plan-Specific Constraints

- Read `AGENTS.md`, all six approved specifications, and `docs/superpowers/plans/2026-08-12-access-cloud-run-program-roadmap.md` before starting any task.
- Use only fictional values in tests and examples. Real workstation inventories, employee rosters, account approvals, hostnames, project IDs, billing IDs, notification destinations, certificate identities, and production acceptance records stay in the agency-approved system of record.
- Root `access-updater/` is authoritative. Do not create the superseded `access-client/updater/` path.
- Terraform lives only under `infra/terraform/`; dashboards live under `infra/monitoring/dashboards/`.
- Terraform creates Secret Manager containers and IAM bindings, never secret versions or secret values.
- GitHub protected environments and their reviewer/branch policies are external agency prerequisites. Terraform and repository workflows reference their exact names but never create or weaken them.
- A deployable backend artifact is one immutable Artifact Registry digest. Test and production promotion must use that same digest; no workflow rebuilds production from source.
- Database rollback means application revision rollback over an expanded compatible schema. No production workflow runs `alembic downgrade`, drops data, or deletes report, revision, audit, or job rows.
- A signing workflow may submit hashes to an agency-managed signing service only after protected-environment approval. No repository worker reads, exports, uploads, or stores a private signing key.
- This plan creates no Claude prompts. Prompt creation is a separate authorized deliverable.

## Cross-Plan File Ownership

| Path | Creator and owner | Other-plan rule |
|---|---|---|
| `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako` | Identity foundation task ID-01 | OP-06 consumes and packages these files; it does not recreate or change Alembic transaction/model-loading behavior. |
| `migrations/versions/*.py` | The ID or RP task that introduces the corresponding model/schema change | OP-06 consumes all reviewed migration files and tests the combined graph; it creates no schema revision. A later schema task owns its new revision and must update the migration register in the same commit. |
| `migrations/MIGRATION_REGISTER.md` | OP-06 | OP-06 creates the register and records every existing revision. Later migration-owning tasks append their exact duration, lock, compatibility, rollback, and verification contract. |
| `backend/jobs/migration.py`, `backend/jobs/roster_import.py`, `scripts/verify_migration.py` | OP-06 | Delivery workflows call these stable entry points and do not duplicate migration/import logic. |
| `scripts/import_roster_to_postgres.py` | Identity foundation creates the database-aware import CLI; OP-06 takes ownership of its deployment wrapper contract | OP-06 may modify it only after the identity import service is reviewed; later callers consume its validation-first CLI. |
| `release/version.schema.json`, `release/version.json` | OP-08 | OP-08 creates the central compatibility registry with a non-production development sentinel. OP-09 reads it but does not modify it. A separately authorized, reviewed release-version commit replaces the sentinel; production workflows reject development values. |
| `release/backend-release.schema.json`, `scripts/deploy/*` | OP-08 | OP-09 and OP-10 consume backend descriptor hashes/versions and never rewrite backend provenance. |
| `release/access-release.schema.json`, `scripts/release/*`, `access-updater/**` | OP-09 | AC tasks own the Access database/source/build output; OP-09 consumes those outputs and owns packaging, verification, updater, signing-service integration, and publication contracts. |
| `access-client/SLUT-Client.accdb`, `access-client/src/**`, `access-client/build/**`, `access-client/tests/**` | AC-01 through AC-09 | OP-09 does not edit Access source or build automation; it stops if their signed-build interfaces are absent. |
| `backend/webapp/api_v1/client_policy.py`, `openapi/access-v1.yaml` | ID-02 creates the bootstrap endpoint/contract; RP-10 adds build/production validation; OP-09 owns the authenticated release-manifest projection it adds | Any compatibility field change updates Python, OpenAPI, Access contract tests, and manifest schema in one reviewed task. |

`release/version.json` has this exact source-controlled development shape:

```json
{
  "$schema": "./version.schema.json",
  "schema_version": 1,
  "backend_version": "0.0.0-development",
  "api_version": "v1",
  "client_version": "0.0.0-development",
  "minimum_client_version": "0.0.0-development",
  "minimum_server_version": "0.0.0-development",
  "release_notes": "Development compatibility metadata; no production release is authorized.",
  "channel": "development"
}
```

OP-08 creates this file and its schema. OP-09 is read-only with respect to it. Release managers change it through a distinct reviewed version-bump commit; agents do not choose a production version, publish that commit, or invoke the release. Every backend descriptor, Terraform variable, runtime environment value, client-policy response, and Access manifest compatibility field is derived from the schema-validated `release/version.json` at the reviewed source commit. No workflow, environment default, manifest generator, or application module may maintain an independent production version or release-notes source.

## Task Protocol and Stop Conditions

For every OP task:

1. Run `git status --short` and record the reviewed base commit with `git rev-parse HEAD`.
2. Stop if an unexpected change overlaps any declared file, if a required upstream interface is absent, or if the task would require a credential, secret value, production/test cloud access, signing action, deployment, push, merge, destructive command, or real operational data.
3. Write the named failing test or validation assertion first and run only the focused local command needed to observe the specified failure.
4. Implement only the declared files and interfaces.
5. Run focused checks, the listed regressions, `git diff --check`, and the sensitive-data scan specified by the task.
6. Inspect `git diff --name-only` and stop if any path falls outside the task's file list.
7. Commit once with the exact commit message. Do not push, merge, apply Terraform, deploy Cloud Run, shift traffic, invoke a migration job, publish an artifact, sign anything, change secrets, or access cloud consoles.
8. Hand off the commit SHA, changed files, commands/results, assumptions, risks, blockers, and produced interfaces for independent specification and code-quality review.

---

### Task OP-01: Retire Unsafe Automation and Close External Prerequisite Gates

**Objective:** Before any identity/report implementation can merge, remove automatic/bypass deployment paths, restrict public Pages output, and create a non-secret gate register that makes missing agency decisions visible.

**Files:**

- Create: `docs/operations/external-prerequisites.md`
- Create: `docs/operations/workstation-inventory-template.md`
- Create: `docs/operations/ownership-and-escalation.md`
- Create: `docs/operations/environment-register-template.md`
- Create: `docs/operations/github-environment-policy.md`
- Create: `docs/operations/release-gates.md`
- Create: `tests/unit/test_operations_prerequisites.py`
- Create: `tests/unit/test_preimplementation_safety.py`
- Modify: `.github/workflows/pages.yml`
- Delete: `.github/workflows/cloud-run.yml`
- Delete: `backend/scripts/deploy.sh`
- Delete: `scripts/merge_and_deploy.py`

**Interfaces:**

- Consumes: approved deployment specification; agency-supplied decisions delivered outside Git.
- Produces: gate IDs `EXT-01` through `EXT-16`; workstation-class record fields; named-owner roles; environment isolation fields; explicit `CLOSED`, `READY_FOR_TEST`, and `READY_FOR_PRODUCTION` gate states consumed by OP-02, OP-03, OP-05, OP-08, OP-09, and OP-10.
- Produces the external GitHub-environment policy for exact names `test`, `production-plan`, `production-apply`, `production-deploy`, `production-rollback`, and `access-release`; repository code validates names and workflow references but does not create environments, reviewers, branch policies, or approvals.
- Produces the preimplementation invariant that no ordinary push deploys Cloud Run, no local helper merges/pushes/deploys, and GitHub Pages publishes only `frontend/forms` rather than the repository root.
- Produces no cloud identifiers, credentials, names, or inventory records in Git.

**Stop conditions:**

- Stop and leave the relevant gate `CLOSED` if agency IT has not selected separate test/production projects or equivalent isolation, DNS zones, billing ownership, approved regions, notification channels, or WIF trust conditions.
- Stop Access packaging if exact Windows 11, Access/Microsoft 365, Word, bitness, display-scale, Trust Center, proxy/TLS inspection, endpoint-protection, and LocalAppData constraints are not recorded for every supported workstation class.
- Stop signing design if agency IT has not demonstrated which certificate and signing mechanism Access Trust Center accepts for `.accde` and which managed service signs the .NET helper. Do not assume `signtool` can sign an Access database.
- Stop production planning until business, technical/on-call, Access release/signing, database recovery, account/roster administration, security/incident, and records-retention owners are named in the agency system of record.
- Stop any credentialed workflow until EXT-16 is externally verified: every named GitHub environment exists, uses the required reviewer count and `refs/heads/main` deployment policy, and exposes only its assigned WIF provider/service-account identifiers.
- Stop every ID/RP/AC/AD implementation merge if the three retired deployers reappear or Pages can expose backend, Access source, release, test, or infrastructure paths.

- [ ] **Step 1: Write the failing documentation-contract test**

Create `tests/unit/test_operations_prerequisites.py` with exact path and heading assertions:

```python
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OPERATIONS = ROOT / "docs" / "operations"

REQUIRED = {
    "external-prerequisites.md": {
        "EXT-01 Separate cloud environments",
        "EXT-08 Managed signing proof",
        "EXT-15 Written production acceptance",
        "EXT-16 GitHub protected environments",
    },
    "workstation-inventory-template.md": {
        "Access version and update channel",
        "Access bitness",
        "Endpoint protection result",
        "Supported or excluded decision",
    },
    "ownership-and-escalation.md": {
        "Business/system owner",
        "Technical service owner",
        "Records-retention authority",
    },
    "environment-register-template.md": {
        "Discovery Engine data store",
        "WIF provider",
        "Secret Manager namespace",
    },
    "github-environment-policy.md": {
        "test | deploy-test.yml, terraform-plan.yml, terraform-apply.yml | terraform-plan, terraform-apply, deploy, rollback | 1 | refs/heads/main | CLOSED",
        "production-plan | terraform-plan.yml | terraform-plan | 2 | refs/heads/main | CLOSED",
        "production-apply | terraform-apply.yml | terraform-apply | 2 | refs/heads/main | CLOSED",
        "production-deploy | deploy-production.yml | deploy | 2 | refs/heads/main | CLOSED",
        "production-rollback | rollback-production.yml | rollback | 2 | refs/heads/main | CLOSED",
        "access-release | access-release.yml | access-release | 2 | refs/heads/main | CLOSED",
    },
    "release-gates.md": {
        "READY_FOR_TEST",
        "READY_FOR_PRODUCTION",
        "CLOSED",
    },
}


def test_prerequisite_documents_are_complete():
    for filename, required_phrases in REQUIRED.items():
        text = (OPERATIONS / filename).read_text(encoding="utf-8")
        assert all(phrase in text for phrase in required_phrases)
        assert "T" + "BD" not in text
        assert "T" + "ODO" not in text


def test_templates_forbid_real_operational_records_in_git():
    for filename in REQUIRED:
        text = (OPERATIONS / filename).read_text(encoding="utf-8")
        assert "Store completed records in the agency-approved system of record." in text
```

Create `tests/unit/test_preimplementation_safety.py` with exact assertions:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_unsafe_automatic_and_local_deployers_are_absent():
    for relative in (
        ".github/workflows/cloud-run.yml",
        "backend/scripts/deploy.sh",
        "scripts/merge_and_deploy.py",
    ):
        assert not (ROOT / relative).exists()


def test_pages_publishes_only_static_forms():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "frontend/forms" in workflow
    assert "path: ." not in workflow
    for forbidden in ("backend", "access-client", "infra", "release", "tests"):
        assert f"path: {forbidden}" not in workflow


def test_github_environment_policy_is_external_and_exact():
    policy = (ROOT / "docs" / "operations" / "github-environment-policy.md").read_text(encoding="utf-8")
    assert "GitHub administrators configure these environments outside Terraform and repository workflows." in policy
    assert "Store completed records in the agency-approved system of record." in policy
    for environment in (
        "test",
        "production-plan",
        "production-apply",
        "production-deploy",
        "production-rollback",
        "access-release",
    ):
        assert f"| {environment} |" in policy
```

- [ ] **Step 2: Run the focused test and confirm the missing-document failure**

Run:

```powershell
python -m pytest tests/unit/test_operations_prerequisites.py tests/unit/test_preimplementation_safety.py -q
```

Expected: FAIL because prerequisite documents are absent, the automatic/bypass deployers still exist, and Pages still publishes the repository root.

- [ ] **Step 3: Retire automatic/bypass deployment and narrow Pages**

Delete `.github/workflows/cloud-run.yml`, `backend/scripts/deploy.sh`, and `scripts/merge_and_deploy.py`. Change `.github/workflows/pages.yml` so its upload artifact root is exactly `frontend/forms`; preserve its static validation and Pages deployment behavior. Do not replace Cloud Run deployment yet—OP-08 adds the reviewed protected path. Until then, repository automation cannot deploy Cloud Run.

- [ ] **Step 4: Define the external prerequisite register**

Create `docs/operations/external-prerequisites.md` with one row for each exact gate:

```markdown
| Gate | Required evidence | Repository state when evidence is absent |
|---|---|---|
| EXT-01 Separate cloud environments | Approved test and production project/resource isolation | CLOSED |
| EXT-02 Regional placement | Production regional services approved for us-central1 | CLOSED |
| EXT-03 DNS and certificates | Managed test and production hostnames and DNS authority | CLOSED |
| EXT-04 Billing and budgets | Billing owner, budget amounts, and escalation destinations | CLOSED |
| EXT-05 WIF trust | Repository, branch/ref, provider, and environment trust conditions | CLOSED |
| EXT-06 Runtime secrets | Named human custodian and approved Secret Manager population procedure | CLOSED |
| EXT-07 Access trusted location | Narrow managed local installation directory and ACL policy | CLOSED |
| EXT-08 Managed signing proof | Test .accde and .NET helper accepted by Access, Windows, and endpoint protection | CLOSED |
| EXT-09 Workstation matrix | Every supported or excluded workstation class recorded | CLOSED |
| EXT-10 Network allowlist | Proxy, firewall, TLS inspection, DNS, and Google endpoint decisions | CLOSED |
| EXT-11 Initial roster correction | Approved duplicate, missing-ID, invalid-shift, and ambiguous-name mapping | CLOSED |
| EXT-12 Initial Admin enrollment | Approved first-Admin bootstrap and one-time PIN communication procedure | CLOSED |
| EXT-13 Security and records review | Data classification, retention, export, printing, and incident requirements | CLOSED |
| EXT-14 Pilot authorization | Named 5-10 employees, two administrators, training, support, and real-data approval | CLOSED |
| EXT-15 Written production acceptance | Business, IT/security, and records-management sign-off | CLOSED |
| EXT-16 GitHub protected environments | Exact six environments, reviewer counts, refs/heads/main policies, workflow allowlist, and environment-scoped WIF variables verified by a GitHub administrator | CLOSED |
```

End the document with `Store completed records in the agency-approved system of record.` and an explicit statement that agents may record only whether evidence was reviewed, never the evidence contents.

- [ ] **Step 5: Define the workstation-class template and support decision**

Create `docs/operations/workstation-inventory-template.md` with fields for Windows edition/build/patch policy, Access/Microsoft 365 exact version and channel, Access bitness, Word version/bitness, display scale/resolution, Trust Center/macro policy, trusted-location capability, proxy/firewall/TLS interception, LocalAppData permission, endpoint-protection result for `.accde` and updater, CPU architecture, and supported/remediate/exclude decision. State that both Access bitnesses require separate artifacts and tests when both appear in inventory.

- [ ] **Step 6: Define ownership, environment, GitHub protection, and release gate contracts**

Create the remaining four documents. Use role names rather than personal names in Git. `github-environment-policy.md` must contain this exact non-secret register; completed reviewer identities, cloud resource identifiers, and approval evidence remain external:

```markdown
| Environment | Permitted workflows | WIF identities | Minimum reviewers | Allowed ref | Repository state |
|---|---|---|---:|---|---|
| test | deploy-test.yml, terraform-plan.yml, terraform-apply.yml | terraform-plan, terraform-apply, deploy, rollback | 1 | refs/heads/main | CLOSED |
| production-plan | terraform-plan.yml | terraform-plan | 2 | refs/heads/main | CLOSED |
| production-apply | terraform-apply.yml | terraform-apply | 2 | refs/heads/main | CLOSED |
| production-deploy | deploy-production.yml | deploy | 2 | refs/heads/main | CLOSED |
| production-rollback | rollback-production.yml | rollback | 2 | refs/heads/main | CLOSED |
| access-release | access-release.yml | access-release | 2 | refs/heads/main | CLOSED |
```

State exactly: `GitHub administrators configure these environments outside Terraform and repository workflows.` and `Store completed records in the agency-approved system of record.` The policy rejects administrators as self-reviewers, permits no fork pull request or ordinary push to enter a credentialed environment, and records only external evidence references rather than reviewer names or cloud identifiers.

`release-gates.md` must define:

```text
CLOSED: one or more required evidence items is absent; dependent work cannot enter production scope.
READY_FOR_TEST: test-only prerequisites are reviewed and all test data is fictional.
READY_FOR_PRODUCTION: every production prerequisite, restore exercise, rollback exercise, security review, and written acceptance is recorded externally.
```

- [ ] **Step 7: Run focused and regression checks**

Run:

```powershell
python -m pytest tests/unit/test_operations_prerequisites.py tests/unit/test_preimplementation_safety.py -q
python -m pytest -q
git diff --check
```

Expected: all tests pass; no deploy-on-push or local merge/push/deploy path remains; Pages scope is static forms only; no completed inventory, owner name, cloud identifier, certificate thumbprint, email address, or secret appears in the diff.

- [ ] **Step 8: Commit the safety and gate foundation**

```powershell
git add docs/operations tests/unit/test_operations_prerequisites.py tests/unit/test_preimplementation_safety.py .github/workflows/pages.yml
git add -u .github/workflows/cloud-run.yml backend/scripts/deploy.sh scripts/merge_and_deploy.py
git commit -m "chore: gate implementation and deployment prerequisites"
```

---

### Task OP-02: Establish Terraform Bootstrap, Remote State, and Isolated Environment Layout

**Objective:** Create a pinned, locally valid Terraform foundation with protected remote-state bootstrap code and separate test/production roots, without creating cloud resources.

**Files:**

- Create: `infra/terraform/bootstrap/state/versions.tf`
- Create: `infra/terraform/bootstrap/state/variables.tf`
- Create: `infra/terraform/bootstrap/state/main.tf`
- Create: `infra/terraform/bootstrap/state/outputs.tf`
- Create: `infra/terraform/environments/test/versions.tf`
- Create: `infra/terraform/environments/test/backend.tf`
- Create: `infra/terraform/environments/test/variables.tf`
- Create: `infra/terraform/environments/test/outputs.tf`
- Create: `infra/terraform/environments/test/.terraform.lock.hcl`
- Create: `infra/terraform/environments/production/versions.tf`
- Create: `infra/terraform/environments/production/backend.tf`
- Create: `infra/terraform/environments/production/variables.tf`
- Create: `infra/terraform/environments/production/outputs.tf`
- Create: `infra/terraform/environments/production/.terraform.lock.hcl`
- Create: `infra/terraform/tests/test_layout.py`
- Create: `docs/runbooks/terraform-state-bootstrap.md`

**Interfaces:**

- Consumes: OP-01 `EXT-01`, `EXT-02`, and `EXT-05` evidence before any human apply.
- Produces: Terraform `1.15.8`/Google provider `7.40.0` roots; bootstrap inputs `project_id`, `state_bucket_name`, `region`, and `authorized_member`; environment inputs `project_id`, `environment`, `region`, `source_repository`, and `labels`; remote-state prefixes `access/test` and `access/production`.
- Produces: state-bucket output `state_bucket_name`; no state object, project, or bucket is created by an agent.

**Stop conditions:**

- Stop if Terraform `1.15.8` or Google provider `7.40.0` cannot be resolved from official distribution sources.
- Stop if test and production would share a state prefix, runtime project, deployment identity, or provider credential.
- Stop if a proposed bootstrap command would expose a project ID, member identity, or local state file in Git.

- [ ] **Step 1: Write the failing Terraform-layout test**

Create `infra/terraform/tests/test_layout.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TF = ROOT / "infra" / "terraform"


def test_versions_are_exactly_pinned():
    for root in [TF / "bootstrap" / "state", TF / "environments" / "test", TF / "environments" / "production"]:
        versions = (root / "versions.tf").read_text(encoding="utf-8")
        assert 'required_version = "= 1.15.8"' in versions
        assert 'version = "= 7.40.0"' in versions


def test_environment_backends_are_distinct():
    test_backend = (TF / "environments" / "test" / "backend.tf").read_text(encoding="utf-8")
    production_backend = (TF / "environments" / "production" / "backend.tf").read_text(encoding="utf-8")
    assert 'prefix = "access/test"' in test_backend
    assert 'prefix = "access/production"' in production_backend
    assert test_backend != production_backend


def test_lock_files_include_both_runner_platforms():
    for environment in ["test", "production"]:
        lock = (TF / "environments" / environment / ".terraform.lock.hcl").read_text(encoding="utf-8")
        assert 'version     = "7.40.0"' in lock
        assert lock.count('h1:') >= 2
```

- [ ] **Step 2: Run the layout test and observe failure**

Run:

```powershell
python -m pytest infra/terraform/tests/test_layout.py -q
```

Expected: FAIL because `infra/terraform/bootstrap/state/versions.tf` does not exist.

- [ ] **Step 3: Implement the shared version/provider contract**

Use this exact provider block in all three `versions.tf` files:

```hcl
terraform {
  required_version = "= 1.15.8"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.40.0"
    }
  }
}
```

- [ ] **Step 4: Implement protected state bootstrap resources**

In `infra/terraform/bootstrap/state/main.tf`, define one `google_storage_bucket` using `var.state_bucket_name`, `var.project_id`, and `var.region`; enable uniform bucket-level access, public-access prevention, versioning, a 30-day retention policy, and a lifecycle rule that retains noncurrent versions for 90 days. Bind only `var.authorized_member` as `roles/storage.objectAdmin`. Add `lifecycle { prevent_destroy = true }` to the bucket. Do not create credentials or secret versions.

- [ ] **Step 5: Implement backend and environment variable contracts**

Use backend blocks with committed prefixes and externally supplied bucket names:

```hcl
terraform {
  backend "gcs" {
    prefix = "access/test"
  }
}
```

The production file differs only by `prefix = "access/production"`. Add validation that `environment` is exactly `test` in the test root and exactly `production` in the production root; require `region` to equal `us-central1` for production.

- [ ] **Step 6: Generate committed provider locks for both supported runner platforms**

From each environment directory, run:

```powershell
terraform providers lock -platform=linux_amd64 -platform=windows_amd64
```

Expected: `.terraform.lock.hcl` selects `registry.terraform.io/hashicorp/google` version `7.40.0` and contains hashes for both platforms. This command downloads provider metadata but does not authenticate to Google or create resources.

- [ ] **Step 7: Document operator-only bootstrap and state migration**

Create `docs/runbooks/terraform-state-bootstrap.md`. Clearly label `terraform apply` and `terraform init -migrate-state` as human-operator commands that remain prohibited to agents. Require the operator to use an encrypted temporary directory for local bootstrap state, verify bucket versioning/retention/public-access prevention, migrate state, verify the remote object, and securely dispose of the temporary local state according to agency policy.

- [ ] **Step 8: Validate locally without a backend or cloud credential**

Run in each Terraform root:

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

Expected: formatting, initialization, validation, tests, and whitespace checks pass without Google credentials. No `.tfstate`, `.tfvars`, project identifier, or member identity is tracked.

- [ ] **Step 9: Commit the Terraform foundation**

```powershell
git add infra/terraform docs/runbooks/terraform-state-bootstrap.md
git commit -m "infra: establish isolated terraform state roots"
```

---

### Task OP-03: Provision VPC, Cloud SQL PostgreSQL 17, Secret Containers, and Least-Privilege Identities

**Objective:** Implement the plan-time-safe infrastructure contract for private PostgreSQL 17, environment-scoped service identities, WIF trust, and Secret Manager containers without storing secret values in Terraform.

**Files:**

- Create: `infra/terraform/modules/access_platform/project_services.tf`
- Create: `infra/terraform/modules/access_platform/network.tf`
- Create: `infra/terraform/modules/access_platform/sql.tf`
- Create: `infra/terraform/modules/access_platform/identities.tf`
- Create: `infra/terraform/modules/access_platform/secrets.tf`
- Create: `infra/terraform/modules/access_platform/variables.tf`
- Create: `infra/terraform/modules/access_platform/outputs.tf`
- Create: `infra/terraform/environments/test/main.tf`
- Create: `infra/terraform/environments/production/main.tf`
- Create: `infra/terraform/tests/access_platform.tftest.hcl`
- Create: `infra/terraform/tests/test_security_contract.py`
- Create: `docs/runbooks/secret-population-and-rotation.md`

**Interfaces:**

- Consumes: OP-02 provider/environment roots; OP-01 EXT-05 and EXT-16 evidence; externally approved `project_id`, `source_repository`, WIF issuer inputs, Cloud SQL tier, and secret custodians.
- Produces: module inputs `environment`, `project_id`, `region`, `network_name`, `database_instance_name`, `database_name`, `sql_tier`, `github_repository`, `github_ref_pattern`, `enable_access_release_identity`, and `wif_trust`. `wif_trust` is a map keyed exactly by `terraform-plan`, `terraform-apply`, `deploy`, `rollback`, and `access-release`; each value contains `github_environment`, `workflow_refs`, and `ref_pattern` and must agree with `docs/operations/github-environment-policy.md`.
- Produces runtime identity outputs `api_service_account_email`, `worker_service_account_email`, `task_invoker_service_account_email`, and `migration_service_account_email`; workflow identity outputs `terraform_plan_service_account_email`, `terraform_apply_service_account_email`, `deploy_service_account_email`, `rollback_service_account_email`, and nullable `access_release_service_account_email`; and WIF outputs `terraform_plan_wif_provider_name`, `terraform_apply_wif_provider_name`, `deploy_wif_provider_name`, `rollback_wif_provider_name`, and nullable `access_release_wif_provider_name`, in addition to `network_id`, `private_subnet_id`, `database_instance_connection_name`, `database_private_ip`, `database_name`, and `secret_resource_ids`.
- Produces Secret Manager containers named `access-database-url`, `identity-hash-pepper`, `cursor-signing-key`, `legacy-access-code`, `legacy-admin-code`, `github-feedback-token`, and `flask-session-secret`; no `google_secret_manager_secret_version` resource is permitted.
- Produces no GitHub environment, GitHub reviewer/branch policy, database password, connection string, WIF credential, service-account key, or secret value.

**Stop conditions:**

- Stop if production cannot use private IP, PostgreSQL 17, regional HA, deletion protection, PITR, automatic storage increase, and encrypted application connections.
- Stop if a role requires project Owner, Editor, broad Secret Manager access, or service-account key creation.
- Stop if the proposed WIF condition permits another repository, an unapproved ref, pull requests from forks, or an identity shared by test and production.
- Stop if `terraform-plan` can mutate cloud resources or read secret payloads/state writes; if `rollback` can build/push images, apply Terraform, invoke migrations, or read secrets; or if `access-release` can access Cloud Run, Cloud SQL, application secrets, or signing private material.
- Stop if Terraform contains a GitHub provider or `github_repository_environment`; GitHub environment protection is externally owned under EXT-16.
- Stop if secret population would put a value in Terraform configuration, Terraform state, a GitHub variable, command history, logs, or this repository.

- [ ] **Step 1: Write failing security-contract tests**

Create `infra/terraform/tests/test_security_contract.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"


def read(name: str) -> str:
    return (MODULE / name).read_text(encoding="utf-8")


def test_sql_is_postgres_17_private_and_protected():
    sql = read("sql.tf")
    assert 'database_version = "POSTGRES_17"' in sql
    assert "ipv4_enabled    = false" in sql
    assert 'availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"' in sql
    assert 'deletion_protection = var.environment == "production"' in sql
    assert "point_in_time_recovery_enabled = true" in sql
    assert "disk_autoresize = true" in sql


def test_terraform_never_manages_secret_values_or_keys():
    terraform = "\n".join(path.read_text(encoding="utf-8") for path in MODULE.glob("*.tf"))
    assert "google_secret_manager_secret_version" not in terraform
    assert "google_service_account_key" not in terraform
    assert "github_repository_environment" not in terraform
    assert "roles/owner" not in terraform.lower()
    assert "roles/editor" not in terraform.lower()


def test_runtime_identities_are_single_purpose():
    identities = read("identities.tf")
    for account_id in [
        "api",
        "worker",
        "task-invoker",
        "migration",
        "terraform-plan",
        "terraform-apply",
        "deploy",
        "rollback",
        "access-release",
    ]:
        assert f'account_id   = "access-${{var.environment}}-{account_id}"' in identities


def test_workflow_identities_have_distinct_wif_and_secret_boundaries():
    identities = read("identities.tf")
    outputs = read("outputs.tf")
    for identity in ("terraform_plan", "terraform_apply", "deploy", "rollback", "access_release"):
        assert f'output "{identity}_service_account_email"' in outputs
        assert f'output "{identity}_wif_provider_name"' in outputs
    secret_bindings = "\n".join(re.findall(
        r'resource "google_secret_manager_secret_iam_member" "[^"]+" \{.*?\n\}',
        identities,
        flags=re.DOTALL,
    ))
    for identity in ("terraform_plan", "terraform_apply", "deploy", "rollback", "access_release"):
        assert f"google_service_account.{identity}.member" not in secret_bindings
    assert 'role = "roles/viewer"' in identities
    assert 'role = google_project_iam_custom_role.rollback_traffic.name' in identities
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run:

```powershell
python -m pytest infra/terraform/tests/test_security_contract.py -q
```

Expected: FAIL because `infra/terraform/modules/access_platform/sql.tf` does not exist.

- [ ] **Step 3: Enable only required Google APIs**

In `project_services.tf`, manage these services with `disable_on_destroy = false`: Compute, Service Networking, Cloud SQL Admin, Secret Manager, IAM, IAM Credentials, Security Token Service, Cloud Run, Cloud Tasks, Artifact Registry, Cloud Build, Cloud Logging, Cloud Monitoring, Cloud Trace, Cloud Scheduler, Cloud DNS, Certificate Manager, and Service Usage. Export a `services_ready` dependency token used by later resources.

- [ ] **Step 4: Build the private network and service connection**

In `network.tf`, create a custom-mode VPC, one `us-central1` subnet with Private Google Access, a reserved private-service range, and a `servicenetworking.googleapis.com` private service connection. Do not create a workstation VPN, public database path, or broad firewall allow rule.

- [ ] **Step 5: Implement PostgreSQL 17 safety controls**

Use this invariant shape in `sql.tf`:

```hcl
resource "google_sql_database_instance" "postgres" {
  name                = var.database_instance_name
  project             = var.project_id
  region              = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = var.environment == "production"

  settings {
    tier              = var.sql_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "07:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.access.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }
  }

  depends_on = [google_service_networking_connection.private_services]
}
```

Create the application database but not a password-bearing SQL user. The human database bootstrap procedure creates the least-privilege application role and populates `access-database-url` outside Terraform. Production requires an approved maintenance window and deletion-protection verification before any apply.

- [ ] **Step 6: Create single-purpose service accounts and WIF conditions**

Create eight service accounts in test and nine in production. Both environments create `api`, `worker`, `task-invoker`, `migration`, `terraform-plan`, `terraform-apply`, `deploy`, and `rollback`; only production sets `enable_access_release_identity=true` and creates `access-release`. The four runtime identities retain the existing narrow boundaries: API connects to Cloud SQL, enqueues tasks, and reads only its named secrets/buckets; worker connects to Cloud SQL and approved AI/search services; task-invoker invokes only the worker; migration connects to Cloud SQL and reads only the roster-import object.

Implement these workflow boundaries exactly:

- `terraform-plan`: `roles/viewer` and `roles/iam.securityReviewer` on its environment project, `roles/secretmanager.viewer` for secret metadata without `secretmanager.versions.access`, and `roles/storage.objectViewer` on that environment's Terraform state bucket. It has no write permission.
- `terraform-apply`: only the reviewed resource-admin roles required by `infra/terraform/modules/access_platform/**`, `roles/storage.objectAdmin` on that environment's state prefix, and service-account impersonation only for Terraform-managed bindings. It cannot access secret payloads, build/push artifacts, invoke migration jobs, deploy revisions, or sign releases.
- `deploy`: `roles/artifactregistry.writer` on the environment repository, Cloud Run revision/job deployment permissions, and `roles/iam.serviceAccountUser` only on API, worker, and migration identities. It can invoke the reviewed migration/verification jobs but cannot read application secrets or Terraform state.
- `rollback`: a custom `accessRollbackTraffic` role containing only `run.services.get`, `run.services.update`, `run.operations.get`, `run.revisions.get`, and `run.revisions.list`, scoped to the API and worker services. It has no Artifact Registry, build, job-invocation, secret, database, or Terraform-state permission.
- `access-release`: production only, with object-create/read permission on immutable versioned paths in the release bucket and the agency-managed signing service's submit-and-read-result role. It cannot overwrite/delete prior releases, read signing keys, access application secrets/state/database, or administer Cloud Run.

Create a distinct service-account IAM binding and WIF provider for each workflow identity. Every provider condition includes the exact GitHub repository, `refs/heads/main`, the matching `job_workflow_ref`, and the exact environment claim from the OP-01 policy. `terraform-plan.yml` is allowed in `test` and `production-plan`; `terraform-apply.yml` in `test` and `production-apply`; test deploy and rollback-verification jobs in `deploy-test.yml` use their distinct identities under `test`; `deploy-production.yml` uses `deploy` in `production-deploy`; `rollback-production.yml` uses `rollback` in `production-rollback`; and `access-release.yml` uses `access-release` in `access-release`. No provider accepts a fork pull request, an unprotected environment, or another workflow. Do not issue or download a service-account key.

- [ ] **Step 7: Create secret containers and per-secret IAM**

Implement only `google_secret_manager_secret` resources with automatic replication and environment labels. Bind `roles/secretmanager.secretAccessor` at the individual secret resource, not the project. The API receives database, identity pepper, cursor signing, session, legacy, and feedback secrets only when required. The worker receives the database secret only. The migration identity receives the database secret only. Document independent generation/population/rotation of `identity-hash-pepper` and `cursor-signing-key`, revision pinning, rollback, and audit verification in `docs/runbooks/secret-population-and-rotation.md`.

- [ ] **Step 8: Wire isolated environment roots**

Add `module "access_platform"` to both environment `main.tf` files. Test and production pass different project IDs, network names, database instance names, database names, repository/ref/workflow/environment conditions, and labels. Test passes `enable_access_release_identity=false`; production passes `true`. Production fixes `region = "us-central1"`. No `.tfvars` containing real identifiers is committed.

- [ ] **Step 9: Add native Terraform safety assertions**

Create `infra/terraform/tests/access_platform.tftest.hcl` with a mocked Google provider and separate test/production plan runs. Assert `POSTGRES_17`, regional production availability, deletion protection, eight distinct test service-account emails, nine distinct production service-account emails, four non-null test workflow-provider outputs, five non-null production workflow-provider outputs, and exactly seven secret resource IDs including `identity-hash-pepper` and `cursor-signing-key`. Assert plan/rollback/release identities have the exact permissions above and no application-secret accessor binding. Use fictional input values `slut-access-production-fixture` and `example.invalid/agency/prison-policy-ai`.

- [ ] **Step 10: Run local Terraform and Python validation**

Run:

```powershell
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
terraform -chdir=infra/terraform/environments/production init -backend=false
terraform -chdir=infra/terraform/environments/production validate
terraform -chdir=infra/terraform/environments/production test -test-directory=../../tests
python -m pytest infra/terraform/tests/test_layout.py infra/terraform/tests/test_security_contract.py -q
git diff --check
```

Expected: all local checks pass with mocked providers and no Google credential; no plan is applied.

- [ ] **Step 11: Commit the private data foundation**

```powershell
git add infra/terraform docs/runbooks/secret-population-and-rotation.md
git commit -m "infra: define private sql and least privilege identities"
```

---

### Task OP-04: Provision Cloud Run API and Worker, Cloud Tasks, Edge, DNS, and Private Storage

**Objective:** Define the same-digest API/worker topology, authenticated task delivery, managed HTTPS edge, Cloud Armor, DNS, and private versioned buckets.

**Files:**

- Create: `infra/terraform/modules/access_platform/storage.tf`
- Create: `infra/terraform/modules/access_platform/serverless.tf`
- Create: `infra/terraform/modules/access_platform/tasks.tf`
- Create: `infra/terraform/modules/access_platform/edge.tf`
- Modify: `infra/terraform/modules/access_platform/variables.tf`
- Modify: `infra/terraform/modules/access_platform/outputs.tf`
- Modify: `infra/terraform/environments/test/main.tf`
- Modify: `infra/terraform/environments/production/main.tf`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`
- Create: `infra/terraform/tests/test_serverless_contract.py`
- Create: `docs/runbooks/edge-and-service-verification.md`

**Interfaces:**

- Consumes: OP-03 network, identities, database connection name, and secret resource IDs; backend entry points `backend.webapp.app:create_app()` and `backend.worker.app:create_worker_app()`; worker task endpoint produced by RP-07; immutable `image_digest` in Artifact Registry.
- Consumes exact runtime configuration names: `ACCESS_API_ENABLED`, `GCP_PROJECT_ID`, `GCP_LOCATION`, `GCP_MODEL_LOCATION`, `AGENT_BUILDER_LOCATION`, `AGENT_BUILDER_COLLECTION`, `AGENT_BUILDER_ENGINE_ID`, `AGENT_BUILDER_SERVING_CONFIG`, `FAST_MODEL`, `PRO_MODEL`, `DATABASE_URL`, `IDENTITY_HASH_PEPPER`, `CURSOR_SIGNING_KEY`, `CLOUD_TASKS_PROJECT`, `CLOUD_TASKS_LOCATION`, `CLOUD_TASKS_QUEUE`, `AI_WORKER_URL`, `CLOUD_TASKS_OIDC_SERVICE_ACCOUNT`, `SOURCE_COMMIT`, `RELEASE_VERSION`, `API_VERSION`, `LATEST_CLIENT_VERSION`, `MINIMUM_CLIENT_VERSION`, `MINIMUM_SERVER_VERSION`, `RELEASE_NOTES`, `PUBLIC_BASE_URL`, `LEGACY_REPORT_MODE`, `ROSTER_BUCKET`, `REVIEW_BUCKET`, `REVIEW_OBJECT_PREFIX`, `ACCESS_CODE`, `ADMIN_CODE`, `GITHUB_TOKEN`, and `LOG_LEVEL`.
- Produces: `api_service_name`, `worker_service_name`, `api_revision_uri`, `worker_uri`, `queue_name`, `managed_hostname`, `load_balancer_ip`, `release_bucket_name`, `configuration_bucket_name`, `logical_backup_bucket_name`, `roster_bucket_name`, and `review_bucket_name`.
- Produces API ingress `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`; worker ingress `INGRESS_TRAFFIC_INTERNAL_ONLY`; only the task-invoker identity receives worker invocation permission.

**Stop conditions:**

- Stop if API and worker image inputs are tags rather than the same `@sha256:` digest.
- Stop if the worker can be invoked by `allUsers`, the API can bypass the load balancer through direct external ingress, or a bucket permits public access.
- Stop if test and production share a queue, bucket, hostname, service account, database, Discovery Engine resource, or audit data.
- Stop if Cloud Tasks OIDC audience and the worker's expected audience are not the same reviewed worker URL.
- Stop if a source deployment, mutable model alias, or secret literal appears in Terraform.

- [ ] **Step 1: Write failing serverless-contract tests**

Create `infra/terraform/tests/test_serverless_contract.py`:

```python
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"


def read(name: str) -> str:
    return (MODULE / name).read_text(encoding="utf-8")


def test_cloud_run_ingress_and_digest_are_locked():
    serverless = read("serverless.tf")
    assert 'ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"' in serverless
    assert 'ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"' in serverless
    assert "image = var.image_digest" in serverless
    assert 'condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image_digest))' in read("variables.tf")


def test_worker_has_no_public_invoker():
    terraform = "\n".join(path.read_text(encoding="utf-8") for path in MODULE.glob("*.tf"))
    bindings = re.findall(
        r'resource "google_cloud_run_v2_service_iam_member" "[^"]+" \{.*?\n\}',
        terraform,
        flags=re.DOTALL,
    )
    worker_bindings = [block for block in bindings if "google_cloud_run_v2_service.worker.name" in block]
    assert worker_bindings
    assert all("allUsers" not in block for block in worker_bindings)
    assert "task_invoker_service_account_email" in terraform


def test_storage_is_private_versioned_and_uniform():
    storage = read("storage.tf")
    assert storage.count('public_access_prevention    = "enforced"') == 5
    assert storage.count("uniform_bucket_level_access = true") == 5
    assert storage.count("versioning") >= 5


def test_compatibility_environment_projection_is_complete():
    serverless = read("serverless.tf")
    for name, variable in {
        "RELEASE_VERSION": "release_version",
        "API_VERSION": "api_version",
        "LATEST_CLIENT_VERSION": "latest_client_version",
        "MINIMUM_CLIENT_VERSION": "minimum_client_version",
        "MINIMUM_SERVER_VERSION": "minimum_server_version",
        "RELEASE_NOTES": "release_notes",
    }.items():
        assert f'name = "{name}"' in serverless
        assert f"value = var.{variable}" in serverless
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run:

```powershell
python -m pytest infra/terraform/tests/test_serverless_contract.py -q
```

Expected: FAIL because `infra/terraform/modules/access_platform/serverless.tf` does not exist.

- [ ] **Step 3: Define immutable artifact and compatibility variables**

Add this exact validation shape to `variables.tf`:

```hcl
variable "image_digest" {
  type        = string
  description = "Artifact Registry image reference pinned by sha256 digest."

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "image_digest must be an Artifact Registry reference ending in an immutable sha256 digest."
  }
}
```

Add non-secret variables `source_commit`, `release_version`, `api_version`, `latest_client_version`, `minimum_client_version`, `minimum_server_version`, and `release_notes`, plus model/search identifiers, queue, DNS zone/hostname, Cloud Run capacity, and bucket names. Validate the four SemVer values as SemVer-or-development, require `api_version == "v1"`, require a nonempty 40-character source commit outside local fixtures, and constrain `release_notes` to one line of 1–500 characters with control characters rejected. Production environment roots give these seven release inputs no defaults: OP-08 must project them from one schema-validated `release/version.json`. Production minimum instances and concurrency remain explicit reviewed inputs because Argon2 and load tests determine the accepted values.

- [ ] **Step 4: Create private versioned buckets**

In `storage.tf`, create exactly five buckets: controlled release artifacts, configuration/templates, scheduled logical backups, legacy roster persistence, and immutable Review Lab submissions. All use uniform bucket-level access, public-access prevention, versioning, environment labels, and lifecycle rules. Release artifacts retain the current and immediately previous known-good client package. Backup objects use retention and lifecycle controls that cannot undercut the approved restore window. Roster and Review Lab access is limited to the API identity and migration/backup identities that require it. Access workstations never receive bucket credentials or direct bucket URLs.

- [ ] **Step 5: Define API and worker services from one digest**

In `serverless.tf`, define two `google_cloud_run_v2_service` resources using `var.image_digest`:

```hcl
resource "google_cloud_run_v2_service" "api" {
  name     = "access-${var.environment}-api"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.api.email
    containers {
      image   = var.image_digest
      command = ["gunicorn"]
      args    = ["--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "300", "backend.webapp.app:create_app()"]
    }
  }
}

resource "google_cloud_run_v2_service" "worker" {
  name     = "access-${var.environment}-worker"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.worker.email
    containers {
      image   = var.image_digest
      command = ["gunicorn"]
      args    = ["--bind", ":8080", "--workers", "1", "--threads", "4", "--timeout", "900", "backend.worker.app:create_worker_app()"]
    }
  }
}
```

Add Cloud SQL connectivity, secret references, startup/liveness probes, request timeouts, explicit scaling, CPU/memory, execution environment, and all reviewed non-secret environment values. Set `ACCESS_API_ENABLED=true`; project `DATABASE_URL`, `IDENTITY_HASH_PEPPER`, and `CURSOR_SIGNING_KEY` from their exact Secret Manager containers; map `release_version`, `api_version`, `latest_client_version`, `minimum_client_version`, `minimum_server_version`, and `release_notes` to `RELEASE_VERSION`, `API_VERSION`, `LATEST_CLIENT_VERSION`, `MINIMUM_CLIENT_VERSION`, `MINIMUM_SERVER_VERSION`, and `RELEASE_NOTES`; set `PUBLIC_BASE_URL` to the managed HTTPS origin; and set the reviewed `LEGACY_REPORT_MODE`. Secret references use Secret Manager resource IDs, never values. Stamp both services with identical `SOURCE_COMMIT`, `RELEASE_VERSION`, and digest labels.

- [ ] **Step 6: Create authenticated Cloud Tasks delivery**

In `tasks.tf`, create one environment-specific queue with explicit retry count, exponential backoff, dispatch concurrency, and rate limits derived from the approved load/cost model. Bind queue enqueue permission only to the API account. Bind `roles/run.invoker` on the worker only to `serviceAccount:${google_service_account.task_invoker.email}`. RP-07's dispatcher sends an OIDC token whose service-account email and audience match Terraform outputs.

- [ ] **Step 7: Create the managed HTTPS edge**

In `edge.tf`, create a serverless NEG for the API, backend service with attached Cloud Armor policy, URL map, managed certificate, HTTPS proxy, global address, forwarding rule, and Cloud DNS record. The Cloud Armor policy applies bounded rate limiting and standard protocol enforcement without placing request bodies or identifiers in logs. HTTP redirects to HTTPS. Direct `run.app` external ingress remains blocked by the Cloud Run ingress setting.

- [ ] **Step 8: Extend native Terraform tests**

Add assertions that API/worker images equal the same fixture digest, API and worker ingress values differ exactly as required, only the task-invoker can invoke the worker, Cloud Armor is attached, all five buckets prevent public access, and test/production names include their environment.

- [ ] **Step 9: Document non-mutating edge/service verification**

Create `docs/runbooks/edge-and-service-verification.md` with human-operator read-only checks for DNS resolution, managed certificate state, Cloud Armor attachment, API ingress, worker IAM policy, Cloud Tasks audience, bucket public-access prevention, and service revision digest. Separate those commands from smoke requests and state that agents do not execute them against cloud environments.

- [ ] **Step 10: Run local validation**

Run:

```powershell
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
terraform -chdir=infra/terraform/environments/production init -backend=false
terraform -chdir=infra/terraform/environments/production validate
terraform -chdir=infra/terraform/environments/production test -test-directory=../../tests
python -m pytest infra/terraform/tests/test_layout.py infra/terraform/tests/test_security_contract.py infra/terraform/tests/test_serverless_contract.py -q
git diff --check
```

Expected: all checks pass locally using mocked providers; no cloud resource is created and no endpoint is contacted.

- [ ] **Step 11: Commit the serverless platform contract**

```powershell
git add infra/terraform docs/runbooks/edge-and-service-verification.md
git commit -m "infra: define private api worker and managed edge"
```

---

### Task OP-05: Add Monitoring, Backup Exports, Restore Evidence, Alerts, and Budgets

**Objective:** Make availability, database protection, job health, client compatibility, security signals, and spend observable without placing sensitive content in logs or alerts.

**Files:**

- Create: `infra/terraform/modules/access_platform/observability.tf`
- Create: `infra/terraform/modules/access_platform/backups.tf`
- Create: `infra/terraform/modules/access_platform/budgets.tf`
- Create: `infra/terraform/modules/access_platform/sql_export_workflow.yaml.tftpl`
- Modify: `infra/terraform/modules/access_platform/variables.tf`
- Modify: `infra/terraform/modules/access_platform/outputs.tf`
- Modify: `infra/terraform/environments/test/main.tf`
- Modify: `infra/terraform/environments/production/main.tf`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`
- Create: `infra/monitoring/dashboards/api.json`
- Create: `infra/monitoring/dashboards/database.json`
- Create: `infra/monitoring/dashboards/jobs-and-ai.json`
- Create: `infra/monitoring/dashboards/client-versions.json`
- Create: `infra/terraform/tests/test_observability_contract.py`
- Create: `docs/runbooks/backup-restore-disaster-recovery.md`
- Create: `docs/operations/restore-exercise-template.md`

**Interfaces:**

- Consumes: OP-03 database and identities; OP-04 services, queue, buckets, and managed hostname; RP-09 safe health/metrics fields; approved external notification-channel IDs, billing account ID, monthly budget amount, and budget Pub/Sub topic.
- Consumes safe metric labels only: environment, release version, API version, Cloud Run revision, HTTP status class, stable error code, job type/stage/result, client version, migration revision, dependency name, and request ID.
- Produces: dashboards `api`, `database`, `jobs-and-ai`, and `client-versions`; alerts for API availability/latency/5xx, auth lockouts and denials, Cloud SQL saturation/storage/connection/backup state, queue depth/age, AI job failure/latency, policy search, export failure, client-upgrade-required, sensitive-log scanner failure, and budget thresholds.
- Produces: nightly logical export workflow output under the private logical-backup bucket; restore exercise evidence fields `exercise_id`, `started_at`, `completed_at`, `source_backup_time`, `target_isolated_instance`, `achieved_rpo_minutes`, `achieved_rto_minutes`, `verification_summary`, `owner_role`, and `corrective_actions_reference`.

**Stop conditions:**

- Stop if an alert, dashboard, log metric, trace attribute, or backup workflow includes report text, field notes, employee/inmate identifiers, PINs, tokens, names, secret values, or SQL query parameters.
- Stop if production has no verified notification channel, budget owner, billing account authorization, automated backups, PITR, or isolated restore target.
- Stop if a logical export identity can modify Cloud SQL data, read application secrets, or overwrite/delete existing backups.
- Stop if retention values conflict with agency records requirements or reduce the approved five-minute RPO/four-hour RTO acceptance targets without written revision.

- [ ] **Step 1: Write the failing observability privacy test**

Create `infra/terraform/tests/test_observability_contract.py`:

```python
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DASHBOARDS = ROOT / "infra" / "monitoring" / "dashboards"
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"
FORBIDDEN = {
    "field_notes",
    "report_text",
    "employee_number",
    "inmate_identifier",
    "pin",
    "renewal_token",
    "access_token",
}


def test_dashboards_are_valid_and_contain_no_sensitive_fields():
    for filename in ["api.json", "database.json", "jobs-and-ai.json", "client-versions.json"]:
        payload = json.loads((DASHBOARDS / filename).read_text(encoding="utf-8"))
        encoded = json.dumps(payload).lower()
        assert not any(field in encoded for field in FORBIDDEN)
        assert payload["displayName"].startswith("Access ")


def test_every_alert_links_to_a_runbook():
    observability = (MODULE / "observability.tf").read_text(encoding="utf-8")
    assert observability.count("documentation {") >= 10
    assert observability.count("docs/runbooks/") >= 10


def test_backup_workflow_cannot_overwrite_a_fixed_object():
    workflow = (MODULE / "sql_export_workflow.yaml.tftpl").read_text(encoding="utf-8")
    assert "time.format(sys.now()" in workflow
    assert "logical-exports/" in workflow
    assert "offload" in workflow
```

- [ ] **Step 2: Run the focused test and observe failure**

Run:

```powershell
python -m pytest infra/terraform/tests/test_observability_contract.py -q
```

Expected: FAIL because `infra/monitoring/dashboards/api.json` does not exist.

- [ ] **Step 3: Create safe dashboards**

Create four valid Google Monitoring dashboard JSON documents. Every widget uses resource metrics or explicitly approved stable labels. API widgets show request count, latency percentiles, status classes, and availability. Database widgets show CPU, memory, storage, connections, instance availability, backup/PITR state, and migration revision. Jobs/AI widgets show queue depth/oldest age, stage duration, safe result codes, model-call count/cost estimate, idempotency conflicts, search health, and export failures. Client widgets show version counts and upgrade-required events only; they do not show employee or device identity.

- [ ] **Step 4: Manage dashboards, log-based metrics, and alerts**

In `observability.tf`, load the four JSON documents with `file()` and create the required alert policies. Alert documentation must name an owner role and repository runbook path. Use externally supplied notification-channel IDs; Terraform does not embed email addresses, phone numbers, webhooks, or pager tokens. Disable alert autoclose behavior that could conceal an ongoing database or backup fault.

- [ ] **Step 5: Implement scheduled unique logical exports**

Create a dedicated logical-backup service account with only Cloud SQL export and backup-bucket object-creation permissions. `sql_export_workflow.yaml.tftpl` must construct a UTC timestamped object such as `logical-exports/20260812T070000Z.sql.gz`, call the Cloud SQL Admin export API with `offload: true`, wait for the operation result, and return only operation ID, object URI, and completion status. A Cloud Scheduler job starts the workflow nightly. Neither workflow nor scheduler may read `DATABASE_URL`.

- [ ] **Step 6: Add budget thresholds and anomaly routing**

In `budgets.tf`, create environment-specific budgets at 50%, 80%, 90%, 100%, and 120% of the approved monthly amount, with forecasted-spend notifications at 100%. Route notifications through the externally approved Pub/Sub topic. Add labels for environment and owner role. Do not invent a budget amount or billing account; require them as validated inputs and keep production Gate `CLOSED` until supplied externally.

- [ ] **Step 7: Write the restore runbook and evidence template**

`docs/runbooks/backup-restore-disaster-recovery.md` must cover automated-backup verification, PITR into an isolated nonproduction instance, logical-export restore, Alembic version verification, safe row-count/checksum queries, account/session revocation checks, representative report/revision reads, achieved RPO/RTO calculation, cleanup authorization, quarterly cadence, and escalation. Mark all gcloud/console/SQL restore commands as human-operator actions. Never place a production record value in the evidence template.

- [ ] **Step 8: Extend Terraform assertions**

Assert with mocked providers that production creates enabled PITR, a nightly logical export scheduler, a private versioned backup bucket, all required dashboards/alerts, and budget thresholds. Assert test and production backup destinations differ.

- [ ] **Step 9: Run local checks**

Run:

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

Expected: dashboard JSON, Terraform validation/tests, privacy assertions, and whitespace checks pass locally. No cloud backup, notification, or budget is created.

- [ ] **Step 10: Commit observability and recovery controls**

```powershell
git add infra/terraform infra/monitoring docs/runbooks/backup-restore-disaster-recovery.md docs/operations/restore-exercise-template.md
git commit -m "infra: add monitored backup and budget controls"
```

---

### Task OP-06: Package Alembic Migration and Roster Import as Dedicated Cloud Run Jobs

**Objective:** Add locally testable, noninteractive migration and roster-import entry points and Terraform job definitions that run before dependent traffic without logging sensitive roster data.

**Files:**

- Create: `backend/jobs/migration.py`
- Create: `backend/jobs/roster_import.py`
- Modify: `scripts/import_roster_to_postgres.py`
- Create: `scripts/verify_migration.py`
- Create: `migrations/MIGRATION_REGISTER.md`
- Modify: `Dockerfile`
- Create: `infra/terraform/modules/access_platform/jobs.tf`
- Modify: `infra/terraform/modules/access_platform/variables.tf`
- Modify: `infra/terraform/modules/access_platform/outputs.tf`
- Modify: `infra/terraform/environments/test/main.tf`
- Modify: `infra/terraform/environments/production/main.tf`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`
- Create: `tests/unit/test_roster_import_job.py`
- Create: `tests/integration/test_deployment_migrations.py`
- Create: `docs/runbooks/database-migration-and-roster-import.md`

**Interfaces:**

- Consumes: identity/report workstream `alembic.ini`, `migrations/env.py`, committed migration heads, `backend.persistence.database.session_scope()`, `backend.identity.config.normalize_employee_number()`, identity staff models/services, OP-03 migration identity/database secret, and OP-04 immutable image digest.
- Produces: `python -m backend.jobs.migration upgrade` and `python -m backend.jobs.migration verify`; `RosterImportPlan`, `RosterFinding`, `RosterImportResult`, `build_roster_plan()`, and `apply_roster_plan()`; Cloud Run jobs `access-{environment}-migrate` and `access-{environment}-roster-import` using the same image digest as API/worker.
- Produces roster-import CLI inputs `--source-uri`, `--corrections-uri`, `--report-uri`, `--expected-sha256`, and opt-in `--apply`; omission of `--apply` is always validation-only.
- Produces safe job output containing counts, source hash, import run UUID, migration revision, and request/operation ID only.

**Stop conditions:**

- Stop if upstream migrations are not one reviewed linear head, fail on empty or populated PostgreSQL 17, or require destructive production downgrade for rollback.
- Stop if a migration lacks expected duration, locking risk, compatibility phase, rollback behavior, and verification query in `migrations/MIGRATION_REGISTER.md`.
- Stop if the roster contains duplicate normalized employee numbers, missing employee IDs, invalid shifts outside `A/B/C/D/U/F`, ambiguous identities, an unapproved correction, or a source hash different from the approved value.
- Stop if initial Admin bootstrap has no approved one-time PIN delivery method. Never print a temporary PIN to Cloud Run logs.
- Stop if a job command can run against production without protected-environment approval or can emit names/employee numbers in ordinary logs.

- [ ] **Step 1: Write failing roster-plan tests**

Create `tests/unit/test_roster_import_job.py` with fictional input:

```python
from backend.jobs.roster_import import build_roster_plan


def test_roster_plan_rejects_duplicates_and_invalid_shifts_without_guessing():
    rows = [
        {"employee_number": "FX-100", "first_name": "Avery", "last_name": "North", "rank": "Officer", "shift": "A"},
        {"employee_number": "fx-100", "first_name": "Avery", "last_name": "North", "rank": "Officer", "shift": "Z"},
    ]
    plan = build_roster_plan(rows, corrections={})
    assert plan.ready is False
    assert {finding.code for finding in plan.findings} == {"duplicate_employee_number", "invalid_shift"}
    assert plan.inserts == ()
    assert plan.updates == ()


def test_roster_plan_requires_source_hash_match_before_apply():
    rows = [
        {"employee_number": "FX-200", "first_name": "Jordan", "last_name": "West", "rank": "Sergeant", "shift": "D"}
    ]
    plan = build_roster_plan(rows, corrections={}, expected_sha256="0" * 64)
    assert plan.ready is False
    assert [finding.code for finding in plan.findings] == ["source_hash_mismatch"]
```

- [ ] **Step 2: Write failing migration lifecycle tests**

Create `tests/integration/test_deployment_migrations.py` to start from the PostgreSQL 17 integration fixture, run `alembic upgrade head`, assert exactly one head and expected core tables, insert fictional staff/account/report rows through upstream services, rerun upgrade idempotently, and perform only the explicitly supported non-destructive downgrade in an isolated transaction/database. Assert production runner code exposes no downgrade subcommand.

- [ ] **Step 3: Run focused tests and observe failure**

Run:

```powershell
python -m pytest tests/unit/test_roster_import_job.py -q
python -m pytest tests/integration/test_deployment_migrations.py -q
```

Expected: unit test collection fails because `backend.jobs.roster_import` does not exist; integration test fails because deployment migration entry points are absent.

- [ ] **Step 4: Implement the migration runner**

Create `backend/jobs/migration.py` with this public interface:

```python
def upgrade() -> str:
    """Upgrade to the single Alembic head and return its revision identifier."""


def verify() -> dict[str, str]:
    """Return safe database, migration, and compatibility status without row data."""


def main(argv: list[str] | None = None) -> int:
    """Accept only `upgrade` or `verify`; return a process exit code."""
```

Use Alembic's Python API, reject multiple heads, emit structured JSON containing only status/revision/duration, and return nonzero on failure. Do not expose `downgrade` in the production entry point.

- [ ] **Step 5: Implement deterministic roster validation and import**

Create immutable dataclasses `RosterFinding`, `RosterImportPlan`, and `RosterImportResult`. Normalize employee numbers through the identity module; validate required IDs, shifts, names, duplicate IDs, ambiguous name mappings, and correction authorization. Existing staff keep their UUID when an employee number or name is corrected. New rows receive server-generated UUIDs through the identity service. `apply_roster_plan()` runs one database transaction and refuses any plan with findings or a source-hash mismatch.

The command writes detailed findings only to the explicitly supplied private `--report-uri`; logs contain counts and opaque finding codes, never roster values. `scripts/import_roster_to_postgres.py` becomes a thin wrapper over `backend.jobs.roster_import.main()`.

- [ ] **Step 6: Register migration operational metadata**

Create `migrations/MIGRATION_REGISTER.md` with one section for every revision reported by `alembic history`. Each section records revision ID, phase (`expand`, `migrate`, or `contract`), expected duration, locking risk, old/new application compatibility, rollback behavior, verification query, and production owner role. A contract migration cannot be scheduled in the same release that raises the minimum client version.

- [ ] **Step 7: Package migration assets in the backend image**

Modify `Dockerfile` to copy `alembic.ini` and `migrations/` into `/app` in addition to existing backend/templates content. Run the image as a non-root user and preserve API/worker command override support. Do not copy test fixtures, Access sources, Terraform, release output, `.git`, or operational records.

- [ ] **Step 8: Define dedicated Cloud Run jobs**

In `jobs.tf`, create migration and roster-import `google_cloud_run_v2_job` resources using `var.image_digest` and the migration service account. Migration command is `python -m backend.jobs.migration upgrade`; roster import defaults to validation-only and receives private GCS URIs plus the approved source hash through non-secret operator inputs. Bind database and source/report bucket access narrowly. Neither job is scheduled, public, nor invoked by the application runtime.

- [ ] **Step 9: Implement safe post-migration verification**

Create `scripts/verify_migration.py` to call `backend.jobs.migration.verify()`, compare the current revision to the single code head, verify expected tables/indexes/constraints through SQLAlchemy inspection, and print only safe names/counts. It exits nonzero on revision mismatch, multiple heads, missing constraints, or database unavailability.

- [ ] **Step 10: Write the human migration/import runbook**

Document preflight backup checks, reviewed migration metadata, expected duration/lock budget, validation-only roster pass, correction approval, source SHA-256 confirmation, migration job execution, verification job execution, API compatibility check, roster count/checksum comparison, and application-revision rollback. Explicitly prohibit production `alembic downgrade`, deletion, and automatic historical Word import.

- [ ] **Step 11: Run focused and regression checks**

Run:

```powershell
python -m pytest tests/unit/test_roster_import_job.py -q
python -m pytest tests/integration/test_deployment_migrations.py -q
python -m pytest tests/unit tests/integration -q
docker build --tag prison-policy-ai:op06-local .
docker run --rm --entrypoint python prison-policy-ai:op06-local -m backend.jobs.migration --help
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
git diff --check
```

Expected: unit/integration tests pass against PostgreSQL 17; the local image contains Alembic assets and prints safe help; Terraform job assertions pass; no job is executed against Google Cloud.

- [ ] **Step 12: Commit migration and import jobs**

```powershell
git add backend/jobs scripts/import_roster_to_postgres.py scripts/verify_migration.py migrations/MIGRATION_REGISTER.md Dockerfile infra/terraform tests/unit/test_roster_import_job.py tests/integration/test_deployment_migrations.py docs/runbooks/database-migration-and-roster-import.md
git commit -m "feat: add controlled migration and roster import jobs"
```

---

### Task OP-07: Enforce Backend, Container, SBOM, Vulnerability, and Pages Quality Gates

**Objective:** Replace best-effort checks with required, reproducible backend and container gates, and narrow GitHub Pages before any Access source is committed.

**Files:**

- Create: `requirements-dev.in`
- Create: `requirements-dev.lock`
- Create: `pyproject.toml`
- Modify: `.github/workflows/tests.yml`
- Create: `.github/workflows/backend-quality.yml`
- Create: `.github/workflows/container-security.yml`
- Modify: `.github/workflows/codacy.yml`
- Modify: `.github/workflows/pages.yml`
- Modify: `Dockerfile`
- Modify: `.dockerignore`
- Create: `scripts/ci/check_sensitive_output.py`
- Create: `scripts/ci/check_workflow_pins.py`
- Create: `scripts/ci/validate_sbom.py`
- Create: `scripts/ci/build_pages_dist.py`
- Create: `tests/unit/test_ci_release_gates.py`
- Create: `tests/unit/test_pages_publish_scope.py`
- Create: `tests/unit/test_container_contract.py`
- Create: `docs/operations/software-supply-chain.md`
- Create: `docs/operations/vulnerability-exceptions.md`

**Interfaces:**

- Consumes: complete credential-free test suite, PostgreSQL 17 integration tests, OpenAPI contract tests, security tests, OP-06 Docker image, and existing image-optimization check.
- Produces required status checks `backend-quality-3.12`, `backend-quality-3.14`, `postgres-integration-17`, `openapi-contract`, `security-redaction`, `container-build`, `sbom`, `container-vulnerability`, `terraform-static`, and `pages-scope`.
- Produces a hash-locked `requirements-dev.lock`, SPDX JSON SBOM artifact, container vulnerability report artifact, and build provenance for later trusted deployment workflows.
- Produces a Pages artifact containing only `index.html` and `frontend/forms/`; no backend, template, staff roster, Access source, release, infrastructure, test, or documentation path is uploaded.

**Stop conditions:**

- Stop if any required check is allowed to continue on error, if an action is not pinned to a full reviewed commit SHA, or if a vulnerability exception has no owner role, rationale, compensating control, issue reference, and expiry date.
- Stop if a fixable Critical or High vulnerability remains in the runtime image, if the SBOM cannot be tied to the exact image digest, or if the base image is not pinned by digest.
- Stop if the Pages artifact contains `templates/staff_roster.json`, `backend/`, `access-client/`, `access-updater/`, `infra/`, `release/`, `.git/`, `.github/`, tests, or operational documents.
- Stop if CI needs a production credential, service-account key, signing key, real report fixture, or secret value.

- [ ] **Step 1: Write failing workflow and artifact-scope tests**

Create `tests/unit/test_pages_publish_scope.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pages_workflow_never_uploads_repository_root():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "path: pages-dist" in workflow
    assert "path: .\n" not in workflow
    assert "frontend/forms" in workflow
    assert "templates" not in workflow


def test_pages_distribution_allowlist_is_exact():
    script = (ROOT / "scripts" / "ci" / "build_pages_dist.py").read_text(encoding="utf-8")
    assert 'ALLOWED = ("index.html", "frontend/forms")' in script
```

Create `tests/unit/test_ci_release_gates.py` to parse every workflow, reject `continue-on-error: true` in required jobs, require full 40-character SHA pins for third-party actions, require Python 3.12/3.14 and PostgreSQL 17, and require every named status check. Create `tests/unit/test_container_contract.py` to require a 64-hex base-image digest, non-root `USER`, a health check, and exclusion of Access/Terraform/release source from the image.

- [ ] **Step 2: Run focused tests and observe failure**

Run:

```powershell
python -m pytest tests/unit/test_pages_publish_scope.py tests/unit/test_ci_release_gates.py tests/unit/test_container_contract.py -q
```

Expected: FAIL because Pages uploads `path: .`, required workflows/scripts are absent, and `Dockerfile` uses an unpinned mutable base image.

- [ ] **Step 3: Add reproducible developer and CI dependencies**

Create `requirements-dev.in` referencing the application requirements plus pytest, coverage, Ruff, mypy, pip-audit, pip-tools, OpenAPI validation, and PostgreSQL test support. Generate `requirements-dev.lock` with hashes:

```powershell
python -m piptools compile --generate-hashes --resolver=backtracking --output-file=requirements-dev.lock requirements-dev.in
python -m pip install --require-hashes --requirement requirements-dev.lock
```

Expected: every transitive dependency is pinned with hashes. Record the regeneration command and review policy in `docs/operations/software-supply-chain.md`.

- [ ] **Step 4: Configure deterministic formatting, lint, typing, and pytest**

Create `pyproject.toml` with Ruff formatting/lint rules, mypy Python 3.12 compatibility plus explicit package overrides, and existing pytest paths/markers. Preserve `pytest.ini` behavior until a separately reviewed cleanup removes duplication. CI runs Ruff check/format, mypy, credential-free unit tests, PostgreSQL integration tests, OpenAPI contract tests, security/redaction tests, and existing policy/report/Word regressions.

- [ ] **Step 5: Pin and harden the runtime image**

Resolve the official `python:3.14-slim` manifest and replace the `FROM` line with `python:3.14-slim@sha256:` followed by the reviewed 64-hex digest. Use a build stage, install only deployed dependencies, create a non-root application user, copy only runtime/Alembic assets with owned permissions, and retain overridable API/worker/job commands. The test assertion is the authoritative format check; do not paste an unverified digest into the plan.

- [ ] **Step 6: Implement sensitive-output, workflow-pin, and SBOM validators**

`scripts/ci/check_sensitive_output.py` scans tracked text, test output, SARIF/SBOM reports, and logs for forbidden secret/PII keys and known fictional-fixture allowlists. `check_workflow_pins.py` rejects third-party actions not pinned to a 40-character SHA. `validate_sbom.py` requires SPDX document metadata, the exact image digest, package licenses, and absence of environment values or file contents.

- [ ] **Step 7: Create required backend and container workflows**

`backend-quality.yml` runs Python 3.12 and 3.14 credential-free checks plus PostgreSQL 17 integration, OpenAPI, and security jobs. `container-security.yml` builds locally without pushing, generates an SPDX JSON SBOM, scans OS/Python dependencies and Docker/IaC configuration, fails on fixable Critical/High findings, uploads safe reports, and attests build provenance. Pin every action to a reviewed full commit SHA. No workflow receives Google or signing credentials.

Remove Codacy's release-gate ambiguity: keep it as supplemental analysis, clearly name it non-authoritative, and ensure required native security jobs fail closed. Do not claim Codacy success when its scanner crashes.

- [ ] **Step 8: Narrow GitHub Pages before Access source lands**

Create `scripts/ci/build_pages_dist.py` with the exact allowlist asserted by the test. It creates a fresh `pages-dist/`, copies only root `index.html` and `frontend/forms/`, rejects symlinks and unexpected files outside that allowlist, and exits nonzero if a source map or secret-like file is present. Change `pages.yml` to upload only `pages-dist`.

- [ ] **Step 9: Define vulnerability-exception governance**

Create `docs/operations/vulnerability-exceptions.md` with `No active exceptions.` and a schema requiring finding ID, affected digest/package, severity, exploitability, owner role, issue reference, compensating control, approval date, and fixed expiry date. The workflow accepts no blanket ignore file; a future exception requires its own reviewed commit.

- [ ] **Step 10: Run all local quality gates**

Run:

```powershell
python scripts/ci/check_workflow_pins.py
python scripts/ci/build_pages_dist.py
python scripts/ci/check_sensitive_output.py --paths pages-dist
python -m ruff check backend tests scripts
python -m ruff format --check backend tests scripts
python -m mypy backend
python -m pytest tests/unit -q
python -m pytest tests/integration tests/contract tests/security -q
python scripts/optimize_images.py --check
docker build --tag prison-policy-ai:op07-local .
python scripts/ci/validate_sbom.py --image prison-policy-ai:op07-local --output tests/output/sbom-op07.spdx.json
python -m pytest tests/unit/test_pages_publish_scope.py tests/unit/test_ci_release_gates.py tests/unit/test_container_contract.py -q
git diff --check
```

Expected: every quality gate passes; the Pages distribution contains only allowed files; the image runs as non-root; SBOM validation succeeds; no image is pushed.

- [ ] **Step 11: Commit required quality and supply-chain gates**

```powershell
git add requirements-dev.in requirements-dev.lock pyproject.toml .github/workflows Dockerfile .dockerignore scripts/ci tests/unit/test_ci_release_gates.py tests/unit/test_pages_publish_scope.py tests/unit/test_container_contract.py docs/operations/software-supply-chain.md docs/operations/vulnerability-exceptions.md
git commit -m "ci: enforce backend container and pages release gates"
```

---

### Task OP-08: Implement Controlled Plan, Apply, Migrate, Deploy, Traffic, and Rollback Workflows

**Objective:** Preserve OP-01's removal of automatic/bypass deployment and add protected, environment-isolated workflows that promote one tested digest and preserve a known-good rollback path.

**Files:**

- Create: `.github/workflows/terraform-plan.yml`
- Create: `.github/workflows/terraform-apply.yml`
- Create: `.github/workflows/deploy-test.yml`
- Create: `.github/workflows/deploy-production.yml`
- Create: `.github/workflows/rollback-production.yml`
- Create: `release/backend-release.schema.json`
- Create: `release/version.schema.json`
- Create: `release/version.json`
- Create: `scripts/deploy/create_release_descriptor.py`
- Create: `scripts/deploy/validate_release_descriptor.py`
- Create: `scripts/deploy/smoke_test.py`
- Create: `scripts/deploy/verify_traffic_state.py`
- Create: `tests/unit/test_deployment_workflows.py`
- Modify: `tests/unit/test_deploy_config.py`
- Modify: `infra/terraform/modules/access_platform/serverless.tf`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `HANDOFF.md`
- Create: `docs/runbooks/cloud-deploy-migration-rollback.md`

**Interfaces:**

- Consumes: OP-01 gate states and external `docs/operations/github-environment-policy.md`; OP-02 remote state; OP-03 `terraform-plan`, `terraform-apply`, `deploy`, and `rollback` WIF providers/service accounts; OP-04 services/edge; OP-06 jobs; OP-07 required checks/SBOM/provenance; and the exact upstream Alembic head.
- Produces immutable `release/backend-release.json` artifacts validated by `release/backend-release.schema.json` with fields `schema_version`, `source_commit`, `image_digest`, `sbom_sha256`, `provenance_id`, `migration_head`, `api_version`, `release_version`, `version_registry_sha256`, `test_workflow_run`, `test_environment`, `created_at`, and `creator_workflow`.
- Produces central source-controlled compatibility metadata in `release/version.json`; development values are accepted by local/test validation and rejected by every production workflow.
- References externally configured GitHub environments `test`, `production-plan`, `production-apply`, `production-deploy`, and `production-rollback`. Workflows do not create, modify, or weaken those environments, reviewers, allowed refs, secrets, or variables.
- Produces reusable `terraform-plan.yml` inputs `environment`, `terraform_root`, `image_digest`, `source_commit`, `version_registry_sha256`, and `plan_purpose`, with outputs `plan_workflow_run_id`, `plan_workflow_name`, `plan_workflow_id`, `plan_artifact_id`, `plan_artifact_name`, and `plan_sha256`. Reusable `terraform-apply.yml` consumes those exact inputs/outputs plus `approval_reference`; artifact name alone is never sufficient authority.
- Produces deployment order: plan, explicit apply, migration, verification, worker revision, API no-traffic revision, 1% canary, smoke/monitor, 10%, 50%, 100%, post-deploy verification.
- Produces rollback inputs `release_descriptor_sha256`, `prior_api_revision`, `prior_worker_revision`, `expected_migration_head`, and `incident_reference`; rollback never changes schema or deletes data.

**Stop conditions:**

- Stop if required OP-07 checks, Terraform plan review, migration review, security scan, test deployment, fictional end-to-end tests, backup status, or protected-environment approval is absent or stale.
- Stop if production rebuilds source, accepts an image tag, uses a different digest than test, accepts a changed release descriptor, or cannot identify prior known-good API/worker revisions.
- Stop if EXT-16 is not externally verified, if a workflow names an environment/workflow/ref not present in the policy, or if repository code attempts to configure a GitHub environment.
- Stop if plan provenance lacks the originating GitHub repository, exact workflow name and numeric ID, run ID, successful conclusion, protected environment, full Git ref, source commit, expected plan hash, or exact artifact ID and name; stop if any check occurs only after Terraform apply begins.
- Stop if the database head is incompatible with either the candidate or prior application revision.
- Stop if smoke/health checks expose sensitive content, if canary error/latency thresholds fail, or if a traffic command would target an unverified revision.
- Stop if a workflow could auto-merge, push, deploy on ordinary `main` push, use a service-account key, apply an unreviewed plan, invoke a production job without approval, or run destructive Terraform/Alembic commands.

- [ ] **Step 1: Write failing deployment-workflow tests**

Create `tests/unit/test_deployment_workflows.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_production_is_manual_protected_and_digest_only():
    text = workflow("deploy-production.yml")
    assert "workflow_dispatch:" in text
    assert "environment: production-deploy" in text
    assert "@sha256:" in text
    assert "--source" not in text
    assert "--no-traffic" in text
    assert "SOURCE_COMMIT" in text
    assert "RELEASE_VERSION" in text
    assert "MINIMUM_SERVER_VERSION" in text
    assert "RELEASE_NOTES" in text


def test_production_uses_staged_traffic_and_rolls_back_on_failed_smoke():
    text = workflow("deploy-production.yml")
    for allocation in ["1", "10", "50", "100"]:
        assert f"candidate={allocation}" in text
    assert "rollback-production.yml" in text or "prior_api_revision" in text


def test_old_bypass_deployers_are_removed():
    assert not (WORKFLOWS / "cloud-run.yml").exists()
    assert not (ROOT / "backend" / "scripts" / "deploy.sh").exists()
    assert not (ROOT / "scripts" / "merge_and_deploy.py").exists()


def test_plan_apply_handoff_is_bound_to_origin_run_and_exact_artifact():
    plan = workflow("terraform-plan.yml")
    apply = workflow("terraform-apply.yml")
    production = workflow("deploy-production.yml")
    for field in (
        "plan_workflow_run_id",
        "plan_workflow_name",
        "plan_workflow_id",
        "plan_artifact_id",
        "plan_artifact_name",
        "plan_sha256",
    ):
        assert field in plan
        assert field in apply
        assert field in production
    for check in (
        "github.repository",
        "workflow_id",
        "conclusion",
        "protected_environment",
        "git_ref",
        "source_commit",
        "plan_sha256",
    ):
        assert check in apply
    assert "artifact-id" in plan
    assert "artifact-ids:" in apply
    assert "plan_artifact_name" in apply
    assert "download by name" not in apply.lower()


def test_version_registry_is_the_only_projection_source():
    combined = "\n".join(workflow(name) for name in (
        "terraform-plan.yml",
        "deploy-test.yml",
        "deploy-production.yml",
    ))
    assert "release/version.json" in combined
    assert "version_registry_sha256" in combined
    for name in (
        "RELEASE_VERSION",
        "LATEST_CLIENT_VERSION",
        "MINIMUM_CLIENT_VERSION",
        "MINIMUM_SERVER_VERSION",
        "API_VERSION",
        "RELEASE_NOTES",
    ):
        assert name in combined
    assert "inputs.release_version" not in combined


def test_no_workflow_uses_long_lived_keys_or_destructive_commands():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.yml"))
    for forbidden in ["GCP_SA_KEY", "service_account_key", "terraform destroy", "alembic downgrade", "git push", "git merge"]:
        assert forbidden not in combined
```

- [ ] **Step 2: Run focused tests and observe failure**

Run:

```powershell
python -m pytest tests/unit/test_deployment_workflows.py tests/unit/test_deploy_config.py -q
```

Expected: FAIL because the new protected workflows do not exist; OP-01's safety test continues to prove the old automatic/bypass deployment files remain absent.

- [ ] **Step 3: Define and validate the immutable backend release descriptor**

Create a JSON Schema that requires every produced field, rejects additional properties, requires a 40-hex source commit, an Artifact Registry `@sha256:` digest, 64-hex SBOM and version-registry hashes, UTC release time, semantic release version, API version `v1`, and nonempty test run/provenance identifiers. `create_release_descriptor.py` derives `release_version` only from the schema-validated registry and records its SHA-256; `validate_release_descriptor.py` verifies schema, hashes, digest equality, migration head, registry equality, and test-environment evidence without calling production.

Create `release/version.schema.json` and `release/version.json` with the exact development shape in the ownership section. The schema rejects additional properties and requires all nine fields: schema URI/version, backend/API/client/minimum client/minimum server versions, release notes, and channel. Version fields accept only SemVer-or-development, `api_version` is `v1`, `release_notes` is one line of 1–500 non-control characters, and channel is from the reviewed allowlist. Test workflows may consume `channel=development`; production plan/deploy/release workflows fail unless a separate reviewed version-bump commit supplies non-development backend/client compatibility values, production-safe release notes, and an approved channel.

The deployment projection is exact: `backend_version` becomes `RELEASE_VERSION`, `api_version` becomes `API_VERSION` and must equal the backend descriptor/OpenAPI value `v1`, `client_version` becomes `LATEST_CLIENT_VERSION`, `minimum_client_version` becomes `MINIMUM_CLIENT_VERSION`, `minimum_server_version` becomes `MINIMUM_SERVER_VERSION`, and `release_notes` becomes `RELEASE_NOTES`. A single validator reads `release/version.json` at `source_commit`, rejects any schema/development-policy violation, computes `version_registry_sha256`, and emits all six runtime values as one immutable job output object. Terraform, the backend descriptor, `/api/v1/client-policy`, and OP-09 manifest generation consume that object/hash and accept no parallel CLI, GitHub input, Terraform default, or application default for production compatibility values.

- [ ] **Step 4: Separate Terraform plan from apply**

`terraform-plan.yml` supports `workflow_call` with the exact inputs/outputs above and a manual `workflow_dispatch` wrapper using the same schema. It checks out `source_commit`, validates/hash-projects `release/version.json`, rejects a supplied `version_registry_sha256` mismatch, runs formatting, validation, tests, and policy/security scan, then creates `reviewed.tfplan`. Pull requests receive static/mocked checks only. Credentialed jobs declare exactly `environment: test` or `environment: production-plan` and authenticate only as OP-03's `terraform-plan` identity.

Grant the plan job only `contents: read`, `actions: read`, `id-token: write`, and `deployments: write`; grant apply only `contents: read`, `actions: read`, `deployments: read`, and `id-token: write`. Upload exactly one artifact with `retention-days` covering the approved promotion window and name `tfplan-${environment}-${source_commit}-${github.run_id}`. It contains only `reviewed.tfplan`, redacted `reviewed.txt`, and `plan-metadata.json`. Metadata binds `github_repository`, `plan_workflow_name`, numeric `plan_workflow_id`, `plan_workflow_run_id`, reusable `plan_job_workflow_ref`, `protected_environment`, `git_ref`, `source_commit`, `image_digest`, `version_registry_sha256`, all projected registry values, `terraform_root`, `plan_purpose`, and `plan_sha256`. Capture the upload action's numeric artifact ID as `plan_artifact_id`; expose that ID, the exact name, workflow identity, run ID, and hash as outputs. After upload, create a successful GitHub deployment receipt for the protected plan environment whose non-secret payload explicitly binds `plan_workflow_run_id`, `plan_workflow_name`, `plan_workflow_id`, `plan_artifact_id`, `plan_artifact_name`, `plan_sha256`, repository, environment, ref, source commit, digest, registry hash, and plan purpose. The receipt is provenance, not environment creation.

`terraform-apply.yml` supports `workflow_call` only. Before artifact download it validates numeric/string input formats, queries the GitHub Actions workflow/run/artifact APIs and Deployments API using read-only repository permissions, and requires: the current `github.repository`; the expected originating workflow path/name and numeric ID (`terraform-plan.yml` for a direct production-plan run or `deploy-test.yml` calling the pinned `terraform-plan.yml` for test); exact `plan_workflow_run_id`; `conclusion=success`; the policy-approved protected environment; exact `refs/heads/main`; `head_sha=source_commit`; a successful deployment receipt binding `plan_sha256`; and a nonexpired artifact whose numeric ID and name both match and whose `workflow_run.id` is the supplied run ID. Any mismatch stops before download. It then downloads by numeric artifact ID, rejects extra archive members/symlinks, recomputes the binary SHA-256, validates every metadata field and registry hash, requires `test` or `production-apply` approval, and applies `reviewed.tfplan` directly. It never downloads by name alone, regenerates a plan, or changes environment policy.

- [ ] **Step 5: Implement build-once test deployment**

`deploy-test.yml` runs only after OP-07 required checks. Job `build_candidate` authenticates with test deploy WIF, builds/pushes the commit once, resolves `image_digest`, verifies SBOM/provenance, validates `release/version.json`, and exposes only digest, source commit, registry hash, and the immutable projection object as job outputs. Job `plan_test` calls `terraform-plan.yml` with those exact authoritative values. Job `apply_test` calls `terraform-apply.yml` with all six plan provenance outputs, original plan inputs, and approval reference under `test`. Only after apply succeeds do later jobs invoke test migration/verification, deploy worker/API with the same digest/projection, run fictional end-to-end/contract/load/failure tests, and emit the GitHub-attested release descriptor. The workflow never accesses production or real data.

- [ ] **Step 6: Implement explicitly approved production sequencing**

`deploy-production.yml` is manual and consumes the unchanged test release descriptor plus exact `release_descriptor_sha256`, `plan_workflow_run_id`, `plan_workflow_name`, `plan_workflow_id`, `plan_artifact_id`, `plan_artifact_name`, `plan_sha256`, and `approval_reference` inputs. The production plan must already have been created by `terraform-plan.yml` under externally protected `production-plan` using the descriptor's exact digest, source commit, and version-registry hash. Deployment validates the descriptor/registry hashes and passes every plan input/provenance field unchanged to `terraform-apply.yml` under externally protected `production-apply`. Only after apply succeeds does it obtain separate `production-deploy` approval, authenticate as the deploy identity, record prior revisions/traffic, confirm backup/PITR readiness, invoke migration then verification, deploy the worker revision, and deploy the API candidate with `--no-traffic`. Any mismatch among descriptor, registry, GitHub run/deployment receipt, artifact, plan metadata, workflow inputs, or checked-out source commit stops before download or apply.

Shift API traffic to the exact candidate at 1%, 10%, 50%, and 100%. At every stage, run `scripts/deploy/smoke_test.py` through the managed hostname and `verify_traffic_state.py`; enforce approved observation windows and metric thresholds. A failed stage restores 100% API traffic to `prior_api_revision`, restores the prior worker revision, leaves expanded schema/data intact, and exits nonzero.

- [ ] **Step 7: Make Terraform and deployment ownership compatible**

Modify `serverless.tf` so Terraform owns service configuration, IAM, ingress, scaling, secrets, and base resources while GitHub deployment workflows own revision image and traffic. Add narrowly documented lifecycle ignores only for the image digest and traffic fields; tests must fail if any IAM, ingress, secret, or service-account field is ignored.

- [ ] **Step 8: Implement explicit rollback workflow**

`rollback-production.yml` requires `production-rollback` approval and the exact rollback inputs. It verifies both revisions exist, both use approved digests, current schema is compatible, and the incident reference is present. It shifts API and worker traffic without rebuilding, changing secrets, applying Terraform, downgrading Alembic, or deleting data. It runs read-only health and representative saved-record checks after rollback.

- [ ] **Step 9: Preserve bypass retirement and correct documentation**

Assert the OP-01-retired automatic source deployment workflow, broken backend deploy helper, and direct merge/push/deploy helper remain absent. Update deployment tests and docs so the only supported path is protected workflows using WIF and immutable digests. Remove stale `GCP_SA_KEY`, mutable-source deploy, outdated model-default, and manual secret-in-env guidance from `HANDOFF.md`; preserve historical context only when clearly marked obsolete.

- [ ] **Step 10: Write the cloud deploy/migration/rollback runbook**

Document the exact plan receipt fields, read-only GitHub API provenance checks, numeric artifact-ID download, binary hash verification, external environment-policy evidence, reviewer roles, migration metadata, prior-revision capture, staged traffic, smoke thresholds, rollback decision matrix for client/API/worker, compatibility verification, incident recording, and Terraform reconciliation after an emergency exception. Mark every mutating command as human/workflow-only and prohibited to agents.

- [ ] **Step 11: Run workflow, schema, and regression validation**

Run:

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

Expected: workflow/static tests pass, old deployers are absent, schemas are valid, full tests pass, and no workflow is invoked.

- [ ] **Step 12: Commit controlled delivery workflows**

```powershell
git add .github/workflows release/backend-release.schema.json release/version.schema.json release/version.json scripts/deploy tests/unit/test_deployment_workflows.py tests/unit/test_deploy_config.py infra/terraform/modules/access_platform/serverless.tf README.md CLAUDE.md HANDOFF.md docs/runbooks/cloud-deploy-migration-rollback.md
git commit -m "ci: add approved digest promotion and rollback"
```

---

### Task OP-09: Build the .NET 8 Updater, Release Manifest, Access Signing, and Publication Pipeline

**Objective:** Produce verifiable, bitness-aware Access releases and a self-contained updater that preserves a known-good client and rolls back automatically without exposing signing keys or tokens.

**Files:**

- Create: `access-updater/SLUT.AccessUpdater.sln`
- Create: `access-updater/src/SLUT.AccessUpdater/SLUT.AccessUpdater.csproj`
- Create: `access-updater/src/SLUT.AccessUpdater/packages.lock.json`
- Create: `access-updater/src/SLUT.AccessUpdater/Program.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Configuration/UpdateRequest.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Manifest/ReleaseManifest.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Manifest/ManifestVerifier.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Security/HashVerifier.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Security/AuthenticodeVerifier.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Install/AccessProcessCoordinator.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Install/AtomicInstaller.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Install/RollbackManager.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Validation/ClientValidator.cs`
- Create: `access-updater/src/SLUT.AccessUpdater/Telemetry/SafeUpdateLog.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/SLUT.AccessUpdater.Tests.csproj`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/packages.lock.json`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/ManifestVerifierTests.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/HashVerifierTests.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/AuthenticodeVerifierTests.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/AtomicInstallerTests.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/RollbackManagerTests.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/ClientValidatorTests.cs`
- Create: `access-updater/tests/SLUT.AccessUpdater.Tests/SafeUpdateLogTests.cs`
- Create: `release/access-release.schema.json`
- Create: `release/fixtures/access-release.fixture.json`
- Create: `scripts/release/New-AccessReleaseManifest.ps1`
- Create: `scripts/release/Test-AccessReleaseManifest.ps1`
- Create: `scripts/release/Invoke-ManagedSigning.ps1`
- Create: `scripts/release/Test-AccessSignatures.ps1`
- Create: `scripts/release/Publish-AccessRelease.ps1`
- Create: `.github/workflows/access-validate.yml`
- Create: `.github/workflows/access-release.yml`
- Modify: `.gitignore`
- Modify: `backend/webapp/api_v1/client_policy.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/contract/test_client_release_policy.py`
- Create: `tests/unit/test_access_release_workflow.py`
- Create: `docs/runbooks/access-deploy-update-rollback.md`

**Interfaces:**

- Consumes: OP-01 supported Access version/bitness/Windows architecture matrix, managed-signing proof, and externally verified EXT-16 `access-release` environment policy; OP-03 production `access_release_service_account_email` and `access_release_wif_provider_name`; AC-01/AC-09 `access-client/SLUT-Client.accdb`, exported sources, build scripts, `ValidateRelease` startup hook, and compiled `.accde`; OP-04 private release bucket/managed hostname; OP-08 read-only `release/version.json`, its `version_registry_sha256`, backend descriptor, and exact compatibility projection; `/api/v1/client-policy`.
- Produces: .NET target `net8.0-windows`, self-contained baseline RID `win-x64`, optional `win-arm64` only when OP-01 inventory requires it; Access artifacts `SLUT-Client-access32.accde` and/or `SLUT-Client-access64.accde` only for inventoried supported classes.
- Produces: `release/access-release.schema.json` fields `schema_version`, `release_version`, `api_version`, `minimum_server_version`, `minimum_client_version`, `source_commit`, `version_registry_sha256`, `released_at`, `channel`, `release_notes_url`, `rollback_notes_url`, `manifest_signature`, `updater`, and `packages`; every updater/package entry contains file name, byte size, SHA-256, signer subject, signer thumbprint, Windows architecture, Access bitness, and protected package path.
- Produces: detached CMS signature `access-release.json.p7s`; Authenticode validation for the updater and the agency-approved Access signing verification for `.accde` established by OP-01 evidence.
- Produces updater exit codes `0` success, `10` optional update deferred, `20` download failure, `21` manifest failure, `22` hash/size failure, `23` signer failure, `24` Access close failure, `25` install failure with successful rollback, `26` install and rollback failure, and `27` post-install validation failure with successful rollback.
- Produces no editable `.accdb`, source export, fixture, signing key, certificate private material, or build intermediate in a user package.

**Stop conditions:**

- Stop if OP-01 has not proven the actual `.accde` signing/trust mechanism on every supported Access class. Do not substitute an assumed Authenticode command for demonstrated Access Trust Center behavior.
- Stop if the managed signing service requires exporting a private key, if CI can read key material, or if an agent would need to invoke signing/publishing.
- Stop if the external `access-release` environment is absent or permits fewer than two reviewers, a ref other than `refs/heads/main`, another workflow, or a WIF identity other than OP-03's production `access-release` identity.
- Stop if Access and updater bitness/architecture combinations are not derived from inventory, if antivirus/endpoint protection blocks them, or if the narrow trusted location/ACL is not approved.
- Stop if package delivery is public, if Access credentials/tokens must be passed on a command line or written unencrypted, or if the manifest/package endpoint is not protected by the approved server contract.
- Stop if minimum-client enforcement would prevent authentication, saved-work recovery/view, or export of existing revisions from a below-minimum client.

- [ ] **Step 1: Write the failing release-policy contract test**

Create `tests/contract/test_client_release_policy.py`:

```python
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_fixture_manifest_validates_and_openapi_matches():
    schema = yaml.safe_load((ROOT / "release" / "access-release.schema.json").read_text(encoding="utf-8"))
    fixture = yaml.safe_load((ROOT / "release" / "fixtures" / "access-release.fixture.json").read_text(encoding="utf-8"))
    jsonschema.validate(fixture, schema)
    openapi = yaml.safe_load((ROOT / "openapi" / "access-v1.yaml").read_text(encoding="utf-8"))
    policy = openapi["paths"]["/api/v1/client-policy"]["get"]
    assert policy["operationId"] == "getClientPolicy"
    assert policy["responses"]["200"]["description"] == "Current Access release and compatibility policy"


def test_manifest_fixture_uses_only_fictional_release_material():
    text = (ROOT / "release" / "fixtures" / "access-release.fixture.json").read_text(encoding="utf-8")
    assert "0.0.0-test" in text
    assert "example.invalid" in text
    assert "0" * 64 in text
```

Create `tests/unit/test_access_release_workflow.py` with these exact boundary assertions:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_access_release_uses_only_external_protected_environment_and_dedicated_wif():
    workflow = (ROOT / ".github" / "workflows" / "access-release.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "environment: access-release" in workflow
    assert "vars.GCP_ACCESS_RELEASE_WIF_PROVIDER" in workflow
    assert "vars.GCP_ACCESS_RELEASE_SERVICE_ACCOUNT" in workflow
    assert "release/version.json" in workflow
    assert "version_registry_sha256" in workflow
    for forbidden in ("push:", "GCP_SA_KEY", "service_account_key", ".pfx", "github_repository_environment"):
        assert forbidden not in workflow
```

- [ ] **Step 2: Write failing updater unit tests**

In the C# test project, create tests that reject a changed manifest byte, wrong package size/hash, untrusted signer, signer-thumbprint mismatch, expired package URL, path traversal, non-HTTPS URL, and extra manifest properties. Atomic-install tests use a temporary directory to preserve `current`, move it to `previous`, install `candidate`, validate, and restore `previous` after injected failure. Safe-log tests assert that bearer tokens, signed URL query strings, local user names, and file contents are redacted.

- [ ] **Step 3: Run focused tests and observe failure**

Run:

```powershell
python -m pytest tests/contract/test_client_release_policy.py -q
dotnet test access-updater/SLUT.AccessUpdater.sln --configuration Release
```

Expected: Python fails because the schema/fixture is absent; .NET fails because the solution is absent.

- [ ] **Step 4: Define the strict release-manifest schema and fixture**

Set `additionalProperties` to `false` at every object level. Require SemVer release/minimum versions, `api_version = v1`, a 40-hex source commit, 64-hex `version_registry_sha256`, UTC timestamp, HTTPS documentation URLs, detached signature metadata, at least one package, positive sizes, and 64-hex artifact hashes/thumbprints. Use a fully fictional `0.0.0-test` fixture with `https://example.invalid/` URLs and zero-valued test hashes clearly marked fixture-only.

- [ ] **Step 5: Implement typed manifest and verification boundaries**

Use immutable records:

```csharp
namespace SLUT.AccessUpdater.Manifest;

public sealed record ReleaseManifest(
    int SchemaVersion,
    string ReleaseVersion,
    string ApiVersion,
    string MinimumServerVersion,
    string MinimumClientVersion,
    string SourceCommit,
    string VersionRegistrySha256,
    DateTimeOffset ReleasedAt,
    string Channel,
    Uri ReleaseNotesUrl,
    Uri RollbackNotesUrl,
    SignatureDescriptor ManifestSignature,
    ArtifactDescriptor Updater,
    IReadOnlyList<ArtifactDescriptor> Packages);

public sealed record SignatureDescriptor(string Algorithm, string FileName, string SignerSubject, string SignerThumbprint);

public sealed record ArtifactDescriptor(
    string FileName,
    long SizeBytes,
    string Sha256,
    string SignerSubject,
    string SignerThumbprint,
    string WindowsArchitecture,
    string AccessBitness,
    string PackagePath);
```

`ManifestVerifier` performs strict JSON deserialization, detached CMS verification, signer-chain trust, expected signer matching, schema/version bounds, HTTPS/path validation, and constant-time hash comparison. It accepts a test trust provider through dependency injection; production uses the Windows trust store.

- [ ] **Step 6: Implement secure update request and download behavior**

`UpdateRequest` arrives through the AC-09 approved in-memory IPC contract, never command-line secret text or plaintext disk. It contains the protected package endpoint, short-lived access material, selected Access bitness, install path, current version, expected manifest hash, and request ID. Download to a unique LocalAppData temporary directory over HTTPS, enforce redirect/domain policy, byte limits, timeout, and content length, then clear access material from managed references before install logging.

- [ ] **Step 7: Implement signature, atomic install, validation, and rollback**

Verify detached manifest signature, exact size/SHA-256, Windows chain trust, and expected signer before touching the installation. `AccessProcessCoordinator` asks Access to save/close and enforces a bounded wait without killing it silently. `AtomicInstaller` requires candidate/current/previous on the same volume, moves current to previous, atomically moves candidate to current, and never deletes previous until the next release is accepted. `ClientValidator` launches the signed client in `ValidateRelease` mode and checks client version, signer, source commit, API reachability, and startup form. Any validation failure invokes `RollbackManager`, revalidates previous, and returns the defined exit code.

- [ ] **Step 8: Implement safe local update telemetry**

`SafeUpdateLog` records UTC time, release/current version, stage, exit code, request ID, file hash prefix, and elapsed time. It never records package URL query/fragment, bearer material, report data, employee identity, user profile path, machine name, or signature private data. Log files are bounded and stored under the current user's LocalAppData outside the trusted application directory.

- [ ] **Step 9: Implement manifest generation, verification, managed signing, and publication scripts**

`New-AccessReleaseManifest.ps1` takes explicit artifact paths/source commit plus read-only `release/version.json` and its expected SHA-256. It schema-validates the registry, maps its release/API/minimum compatibility fields without overrides, and computes actual artifact compatibility, size, and hash values. `release_notes_url` points to the signed release-notes artifact whose safe summary is the registry's exact `release_notes`; it does not introduce a second compatibility or notes source. The script fails if the registry hash, Access build metadata, backend descriptor, or requested manifest disagrees. `Test-AccessReleaseManifest.ps1` validates schema, registry hash, CMS signature, artifact hash/size, expected signers, and package allowlist. `Invoke-ManagedSigning.ps1` submits an artifact digest/reference to the approved managed service using ephemeral WIF or interactive agency authentication; it contains no certificate/key import command and refuses local PFX paths. `Publish-AccessRelease.ps1` verifies every signature/hash again, uploads only signed user artifacts/manifest/notes to the private release channel, preserves the previous release, and requires an externally provided approval reference.

Agents may implement and unit-test these scripts with fictional self-signed fixtures, but must not invoke managed signing or publication.

- [ ] **Step 10: Implement protected Access validation and release workflows**

`access-validate.yml` runs on Windows runners with Access installed, checks exported-source consistency, compiles VBA/missing references, scans forbidden URLs/secrets/unsafe declarations, builds supported `.accde` files, runs fake-API VBA and COM smoke tests, builds/tests/publishes the updater locally for required RIDs, and uploads unsigned test artifacts only.

`access-release.yml` is manual and references—but never creates or configures—the externally protected `access-release` environment. It fails unless EXT-16 is verified and the environment supplies `GCP_ACCESS_RELEASE_WIF_PROVIDER` and `GCP_ACCESS_RELEASE_SERVICE_ACCOUNT` identifiers matching OP-03 outputs. After two-reviewer approval it authenticates only as the dedicated production access-release identity, consumes approved backend/client evidence plus the exact version-registry hash, rebuilds from the reviewed commit, repeats all tests, requests managed signatures without accessing key material, builds/signs the CMS manifest, validates all artifacts, and publishes only immutable versioned objects. It never runs for a normal push, uses deploy/apply/rollback identities, changes environment protection, or reads application secrets.

- [ ] **Step 11: Project release policy through `/api/v1/client-policy`**

Modify the endpoint/OpenAPI so authenticated clients receive latest/minimum client version, API/server compatibility, release notes, selected package metadata, expected hash/signer, and read-only requirement. A client below minimum can authenticate, read/recover saved work, and export existing revisions, but mutation endpoints return `client_upgrade_required`. Protected package delivery stays behind the managed hostname and private bucket service boundary.

- [ ] **Step 12: Write the Access deployment/update/rollback runbook**

Document supported matrix, narrow trusted location and ACL, build/export consistency, managed signing ownership, endpoint-protection validation, manifest/package verification, staged release channel, optional/required update UX, automatic rollback, manual recovery, prior-release retention, signer rotation, certificate expiry/revocation, and the 30-minute client rollback target. State that Office itself is not updated by this helper.

- [ ] **Step 13: Run local release checks without organizational signing**

Run:

```powershell
dotnet restore access-updater/SLUT.AccessUpdater.sln --locked-mode
dotnet build access-updater/SLUT.AccessUpdater.sln --configuration Release --no-restore
dotnet test access-updater/SLUT.AccessUpdater.sln --configuration Release --no-build
dotnet publish access-updater/src/SLUT.AccessUpdater/SLUT.AccessUpdater.csproj --configuration Release --runtime win-x64 --self-contained true --no-build
python -m json.tool release/access-release.schema.json | Out-Null
python -m json.tool release/fixtures/access-release.fixture.json | Out-Null
python -m pytest tests/contract/test_client_release_policy.py tests/unit/test_access_release_workflow.py -q
powershell -File scripts/release/New-AccessReleaseManifest.ps1 -FixtureMode
powershell -File scripts/release/Test-AccessReleaseManifest.ps1 -FixtureMode
python scripts/ci/check_workflow_pins.py
git diff --check
```

Expected: .NET unit/build/publish tests pass for `win-x64`; fixture-only manifest/signature checks pass; contract/workflow tests pass; no `.accde` is distributed, no organization signing call occurs, and no artifact is published.

- [ ] **Step 14: Commit updater and release pipeline**

```powershell
git add access-updater release/access-release.schema.json release/fixtures scripts/release .github/workflows/access-validate.yml .github/workflows/access-release.yml .gitignore backend/webapp/api_v1/client_policy.py openapi/access-v1.yaml tests/contract/test_client_release_policy.py tests/unit/test_access_release_workflow.py docs/runbooks/access-deploy-update-rollback.md
git commit -m "feat: add signed access update and release pipeline"
```

---

### Task OP-10: Execute Pilot Readiness, Parallel Operation, DR, Rollback, Runbooks, and General-Rollout Controls

**Objective:** Make production entry, pilot operation, recovery exercises, acceptance, general rollout, and legacy-web restriction explicit, measurable, reversible, and owned.

**Files:**

- Create: `release/acceptance.schema.json`
- Create: `scripts/operations/verify_release_gates.py`
- Create: `scripts/operations/create_safe_acceptance_record.py`
- Create: `tests/unit/test_rollout_runbooks.py`
- Create: `tests/unit/test_release_gate_verifier.py`
- Create: `tests/manual/access-acceptance-scenarios.md`
- Create: `docs/operations/pilot-register-template.md`
- Create: `docs/operations/release-acceptance-template.md`
- Create: `docs/operations/rollback-compatibility-matrix.md`
- Create: `docs/operations/change-log.md`
- Modify: `docs/operations/release-gates.md`
- Create: `docs/runbooks/pilot-parallel-operation.md`
- Create: `docs/runbooks/ai-policy-outage.md`
- Create: `docs/runbooks/security-incident-response.md`
- Create: `docs/runbooks/account-onboarding-offboarding.md`
- Create: `docs/runbooks/data-retention-export-printing.md`
- Create: `docs/runbooks/general-rollout-and-legacy-restriction.md`
- Create: `docs/user-guides/access-quick-start.md`
- Create: `docs/user-guides/admin-quick-reference.md`
- Modify: `infra/terraform/modules/access_platform/variables.tf`
- Modify: `infra/terraform/modules/access_platform/serverless.tf`
- Modify: `infra/terraform/environments/test/main.tf`
- Modify: `infra/terraform/environments/production/main.tf`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`

**Interfaces:**

- Consumes: all OP-01 through OP-09 outputs; every ID/RP/AC/AD acceptance result; `/api/v1/admin/health`; RP-10 environment contract `LEGACY_REPORT_MODE` with exact values `pilot_fallback` and `restricted`; current/prior backend and Access manifests; backup/restore evidence; external written approvals.
- Produces: machine-readable safe gate evaluation; acceptance states `not_ready`, `pilot_approved`, `pilot_accepted`, and `general_rollout_approved`; a rollback compatibility matrix keyed by client release, API release, worker release, API version, Alembic head, and legacy mode.
- Produces pilot bounds of 5-10 employees and two administrators for two to four weeks; test scenarios use fictional data, and operational data begins only after agency approval/training.
- Produces production Terraform input `legacy_report_mode`; initial/pilot value `pilot_fallback`; post-acceptance value `restricted`; no workflow returns to shared-code writes without a documented incident decision and protected approval.
- Produces no personal names, employee IDs, real incident details, PINs, tokens, support addresses, or acceptance signatures in Git.

**Stop conditions:**

- Stop pilot entry if any Critical/High security or data-loss issue is open; any required automated/manual gate fails; backup/PITR restore, client rollback, API/worker rollback, workstation matrix, roster import, documentation, training, or support ownership is incomplete.
- Stop use of real operational data until agency approval, participant training, security review, and records-management approval are recorded externally.
- Stop pilot exit/general rollout if core acceptance scenarios lack named external evidence, support/cost/performance exceed limits, or business, IT/security, and records stakeholders have not accepted in writing.
- Stop legacy restriction if the managed Access/backend release is not accepted and recoverable. Stop legacy re-enablement unless an incident commander explicitly accepts the shared-code authorization risk.
- Stop any recovery action that deletes failed-release data, downgrades production schema, overwrites audit/revision history, or restores a client/API/worker combination absent from the compatibility matrix.

- [ ] **Step 1: Write failing rollout-document and gate-verifier tests**

Create `tests/unit/test_rollout_runbooks.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNBOOKS = ROOT / "docs" / "runbooks"

REQUIRED = {
    "pilot-parallel-operation.md": ["Pilot entry gates", "Two to four weeks", "Pilot exit gates"],
    "ai-policy-outage.md": ["Manual editing remains available", "Previously saved work remains available"],
    "security-incident-response.md": ["Containment", "Evidence preservation", "Notification authority"],
    "account-onboarding-offboarding.md": ["Temporary PIN", "Session revocation", "Last active Admin"],
    "data-retention-export-printing.md": ["Indefinite fail-safe retention", "No permanent delete", "Local-file rules"],
    "general-rollout-and-legacy-restriction.md": ["pilot_fallback", "restricted", "Written acceptance"],
}


def test_required_runbook_sections_exist_without_unfinished_markers():
    for filename, phrases in REQUIRED.items():
        text = (RUNBOOKS / filename).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text
        assert "T" + "BD" not in text
        assert "T" + "ODO" not in text


def test_runbooks_prohibit_destructive_recovery():
    combined = "\n".join((RUNBOOKS / name).read_text(encoding="utf-8") for name in REQUIRED)
    assert "Production rollback never runs Alembic downgrade." in combined
    assert "Rollback never deletes report, revision, audit, job, or export metadata." in combined
```

Create `tests/unit/test_release_gate_verifier.py` with a complete fictional accepted record and parametrized deletion/failure of each required gate. Assert the complete record returns `general_rollout_approved`; every missing/failed gate returns `not_ready` with only gate IDs, never record content.

- [ ] **Step 2: Run focused tests and observe failure**

Run:

```powershell
python -m pytest tests/unit/test_rollout_runbooks.py tests/unit/test_release_gate_verifier.py -q
```

Expected: FAIL because rollout runbooks and gate verifier do not exist.

- [ ] **Step 3: Define safe acceptance evidence and gate evaluation**

Create `release/acceptance.schema.json` with identifiers/references only: release descriptor hashes, manifest hash, gate IDs/statuses, evidence references, owner roles, timestamps, achieved RPO/RTO, accepted client/API/worker/schema versions, and external approval references. Reject names, free-form incident narratives, report content, employee IDs, PINs, or tokens.

`verify_release_gates.py` validates schema and every OP/ID/RP/AC/AD gate, ensures evidence predates neither candidate artifact nor latest relevant change, verifies compatibility matrix membership, and emits only status plus failing gate IDs. `create_safe_acceptance_record.py` creates a local fictional template or validates operator-supplied safe references; it never queries production.

- [ ] **Step 4: Write all twelve manual acceptance scenarios**

Create `tests/manual/access-acceptance-scenarios.md` with exact fictional steps and expected outcomes for:

1. Admin/User creation, temporary PIN, and first-use change.
2. Persistent sessions across Access restart and expired Admin elevation.
3. Own report and one prepared for another officer.
4. Owner/preparer visibility and revision attribution from different workstations.
5. Network interruption before/during save and forced-termination recovery.
6. Simultaneous edit conflict and recovery revision without overwrite.
7. Access close during each AI stage and resume without duplicate durable work.
8. Word generation from a named revision and official-template inspection.
9. Admin search/view/edit/restore/transfer/export with audit attribution.
10. PIN reset, deactivation, role change, lockout, and session revocation.
11. Optional/required client update and automatic previous-release rollback.
12. Cloud SQL, queue, AI, search, storage, and network degradation with truthful safe UI.

Include keyboard-only use, high contrast, every supported display scale, and approved officer terminology.

- [ ] **Step 5: Define pilot and parallel-operation control**

`pilot-parallel-operation.md` must enforce the approved size/duration, training, support contacts held externally, controlled production authorization, daily safe health review, issue severity, request-ID-only feedback, and exit criteria. The legacy web remains a marked fallback and must not create a separate ordinary-report history. Existing historical Word files are not imported automatically.

- [ ] **Step 6: Define incident and dependency-outage behavior**

`ai-policy-outage.md` documents manual editing/cloud save availability, resumable jobs, no false success, safe notices, retry/cost controls, and search-specific checks. `security-incident-response.md` documents classification, containment, credential/session revocation by authorized humans, evidence preservation, audit review, legal/records notification, recovery, and post-incident actions without copying report content into tickets or alerts.

- [ ] **Step 7: Define account, records, and local-file operations**

`account-onboarding-offboarding.md` covers approved roster identity, one-time temporary PIN channel, first-use change, role approval, deactivation, revocation, last-active-Admin protection, and stable history. `data-retention-export-printing.md` covers indefinite fail-safe retention until an approved schedule, no permanent-delete surface, controlled exports/printing, on-demand Word behavior, LocalAppData DPAPI recovery, seven-day orphan cleanup, and prohibition on cloud/workstation credentials in Access.

- [ ] **Step 8: Define compatibility and rollback decisions**

Create `rollback-compatibility-matrix.md` with one reviewed row per allowed release combination and no wildcard versions. Decision order is client-only, API-only, worker-only, or coordinated rollback. Every row states read/write allowance, schema compatibility, required migration head, legacy mode, and verification command. Client rollback target is 30 minutes; service recovery target is four hours; database RPO target is five minutes or less.

- [ ] **Step 9: Add explicit legacy mode to Terraform**

Add a validated variable:

```hcl
variable "legacy_report_mode" {
  type        = string
  description = "Legacy browser ordinary-report behavior during pilot and after acceptance."

  validation {
    condition     = contains(["pilot_fallback", "restricted"], var.legacy_report_mode)
    error_message = "legacy_report_mode must be pilot_fallback or restricted."
  }
}
```

Pass it to API as `LEGACY_REPORT_MODE`. Test defaults to `pilot_fallback`; production remains `pilot_fallback` through accepted pilot. A separate reviewed production plan changes it to `restricted` only after written general-rollout approval. RP-10 owns route enforcement; this task owns deployment state and operating procedure.

- [ ] **Step 10: Write general rollout and emergency reversion procedure**

`general-rollout-and-legacy-restriction.md` requires written acceptance, signed package distribution by agency IT to the narrow trusted location, scheduled account activation groups, temporary-PIN training, monitored client-version distribution, and support escalation. After acceptance, restrict shared-code ordinary report endpoints while preserving health and specifically approved Review Lab behavior. Emergency reversion may restore prior accepted client/API/worker revisions; shared-code writes remain restricted unless an incident decision explicitly accepts the risk.

- [ ] **Step 11: Complete guides, ownership/change records, and release gates**

Create concise User/Admin guides covering sign-in, save/recovery states, report ownership/preparer behavior, revisions/conflicts, AI draft status, Word export, update notices, account administration, audit, health, and support reference. Templates store only external evidence references. `change-log.md` records version, safe summary, compatibility, migration, approval reference, and rollback reference. Update `release-gates.md` so `READY_FOR_PRODUCTION` requires the acceptance schema verifier to pass.

- [ ] **Step 12: Run the full local program gate suite**

Run:

```powershell
python -m json.tool release/acceptance.schema.json | Out-Null
python -m pytest tests/unit/test_rollout_runbooks.py tests/unit/test_release_gate_verifier.py -q
python scripts/operations/verify_release_gates.py --fixture fictional-general-rollout
python -m pytest tests/unit tests/integration tests/contract tests/security -q
python scripts/ci/check_sensitive_output.py --paths release docs/operations docs/runbooks docs/user-guides tests/manual
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
dotnet test access-updater/SLUT.AccessUpdater.sln --configuration Release
git diff --check
```

Expected: safe fictional general-rollout fixture passes; every negative gate fixture fails closed; backend/Terraform/updater checks pass; no cloud, Access COM, signing, migration, deployment, traffic, or operational-data action is performed.

- [ ] **Step 13: Commit rollout governance and operating controls**

```powershell
git add release/acceptance.schema.json scripts/operations tests/unit/test_rollout_runbooks.py tests/unit/test_release_gate_verifier.py tests/manual docs/operations docs/runbooks docs/user-guides infra/terraform
git commit -m "docs: define pilot recovery and general rollout gates"
```

---

## Completion Gate

This plan is complete only after OP-01 through OP-10 each have one independently reviewed commit, all upstream ID/RP/AC/AD interfaces pass their own plans, all five roadmap program gates pass, the agency records named external owners and approvals, the isolated restore exercise demonstrates the approved targets, the client/API/worker rollback exercise succeeds, the pilot receives written acceptance, and `LEGACY_REPORT_MODE=restricted` is approved through a reviewed production plan. Implementation completion does not itself authorize any apply, deploy, migration invocation, signing operation, artifact publication, pilot start, traffic shift, secret change, production-data access, or general rollout.
