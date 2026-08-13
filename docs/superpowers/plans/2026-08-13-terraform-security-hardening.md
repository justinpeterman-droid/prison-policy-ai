# Terraform Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate every actionable finding from the pinned Checkov 3.3.11 Terraform scan so OP-07 can enforce an honest infrastructure security gate.

**Architecture:** Keep runtime and delivery permissions least-privilege while moving mutable environment-specific encryption and bucket-log destinations to explicit, required root inputs. Harden the network, edge, workload identity, storage and Cloud SQL resources directly; do not baseline, skip, or suppress a finding. PostgreSQL 18 is valid because the program defines PostgreSQL 17 as a hard minimum.

**Tech Stack:** Terraform 1.15.8, Google provider, Checkov 3.3.11 pinned image, Python Terraform-contract tests, native mocked Terraform tests.

## Global Constraints

- Do not apply Terraform, access cloud credentials, mutate production, or use real identifiers.
- All production KMS and storage-log destinations are required external inputs with no defaults.
- Preserve private buckets, uniform bucket access, public-access prevention, versioning, state-prefix restrictions, and existing WIF role separation.
- Keep `POSTGRES_17` as the program floor by using `POSTGRES_18`; do not downgrade the platform to satisfy a scanner.
- Do not suppress, baseline, skip, or severity-filter any Checkov finding.
- Every production change must have a focused RED-to-GREEN contract test and pass pinned Checkov with zero failed checks.

---

### Task 1: Add explicit encryption and audit-log interfaces

**Files:**
- Modify: `infra/terraform/modules/access_platform/variables.tf`
- Modify: `infra/terraform/environments/test/variables.tf`
- Modify: `infra/terraform/environments/test/main.tf`
- Modify: `infra/terraform/environments/production/variables.tf`
- Modify: `infra/terraform/environments/production/main.tf`
- Modify: `infra/terraform/bootstrap/state/variables.tf`
- Modify: `infra/terraform/bootstrap/state/main.tf`
- Modify: `infra/terraform/tests/test_security_contract.py`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`

**Interfaces:**
- Consumes: opaque, externally provisioned `storage_log_bucket_name` and `artifact_registry_kms_key_name` strings.
- Produces: required no-default production inputs and fictional mocked test values; every managed application/state bucket forwards access logs to the approved destination.

- [ ] **Step 1: Write failing input and bucket-logging tests**

```python
def test_production_requires_external_log_and_kms_inputs():
    production = read("infra/terraform/environments/production/variables.tf")
    assert 'variable "storage_log_bucket_name"' in production
    assert 'default' not in variable_block(production, "storage_log_bucket_name")
    assert 'variable "artifact_registry_kms_key_name"' in production

def test_every_managed_bucket_forwards_access_logs():
    storage = read("infra/terraform/modules/access_platform/storage.tf")
    assert 'logging {' in storage
    assert 'log_bucket = var.storage_log_bucket_name' in storage
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest infra/terraform/tests/test_security_contract.py -q`

Expected: FAIL because neither required external interface nor bucket logging exists.

- [ ] **Step 3: Add the inputs and forward logs**

```hcl
variable "storage_log_bucket_name" {
  type      = string
  nullable  = false
  sensitive = false
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$", var.storage_log_bucket_name))
    error_message = "storage_log_bucket_name must be a provider-valid bucket name."
  }
}

resource "google_storage_bucket" "private" {
  # existing arguments
  logging {
    log_bucket        = var.storage_log_bucket_name
    log_object_prefix = "access/${var.environment}/"
  }
}
```

Use the same destination with prefix `terraform-state/${var.environment}/` for the bootstrap state bucket. Wire test-only fictional values through test root; make both production values required with no defaults.

- [ ] **Step 4: Verify GREEN and native plans**

Run: `python -m pytest infra/terraform/tests/test_security_contract.py -q`

Run: `terraform -chdir=infra/terraform/environments/test init -backend=false && terraform -chdir=infra/terraform/environments/test validate`

Expected: PASS with test values only; no cloud access.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform
git commit -m "infra: add encrypted and audited storage interfaces"
```

### Task 2: Harden IAM, WIF, network, edge, Artifact Registry, and Cloud SQL

**Files:**
- Modify: `infra/terraform/modules/access_platform/identities.tf`
- Modify: `infra/terraform/modules/access_platform/network.tf`
- Modify: `infra/terraform/modules/access_platform/edge.tf`
- Modify: `infra/terraform/modules/access_platform/serverless.tf`
- Modify: `infra/terraform/modules/access_platform/sql.tf`
- Modify: `infra/terraform/modules/access_platform/outputs.tf`
- Modify: `infra/terraform/tests/test_security_contract.py`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`

**Interfaces:**
- Consumes: Task 1’s `artifact_registry_kms_key_name`.
- Produces: scoped plan/viewer and service-account lifecycle custom roles, WIF subject assertion, VPC flow logs plus no-default firewall, Cloud Armor Log4j protection, KMS-backed Artifact Registry, and PostgreSQL 18 with audited security flags.

- [ ] **Step 1: Write failing security-contract tests per Checkov rule**

```python
def test_security_hardening_has_no_basic_project_roles_or_unscoped_sa_admin():
    identities = read("infra/terraform/modules/access_platform/identities.tf")
    assert 'roles/viewer' not in project_plan_binding(identities)
    assert 'roles/iam.serviceAccountAdmin' not in project_apply_binding(identities)
    assert 'assertion.sub ==' in identities

def test_network_edge_registry_and_sql_are_hardened():
    assert 'enable_flow_logs = true' in read("infra/terraform/modules/access_platform/network.tf")
    assert 'preconfigured_waf_config' in read("infra/terraform/modules/access_platform/edge.tf")
    assert 'kms_key_name = var.artifact_registry_kms_key_name' in read("infra/terraform/modules/access_platform/serverless.tf")
    sql = read("infra/terraform/modules/access_platform/sql.tf")
    assert 'database_version = "POSTGRES_18"' in sql
    for flag in ('log_connections', 'log_disconnections', 'log_checkpoints', 'log_lock_waits', 'log_hostname', 'log_min_messages', 'log_min_duration_statement', 'pgaudit.log'):
        assert flag in sql
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest infra/terraform/tests/test_security_contract.py -q`

Expected: FAIL for every missing hardening control.

- [ ] **Step 3: Implement minimum secure resource configuration**

```hcl
resource "google_compute_subnetwork" "private" {
  # existing arguments
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_artifact_registry_repository" "backend" {
  # existing arguments
  kms_key_name = var.artifact_registry_kms_key_name
}

resource "google_sql_database_instance" "postgres" {
  database_version = "POSTGRES_18"
  settings {
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    # Add separate database_flags blocks for the remaining tested flags.
  }
}
```

Replace broad `roles/viewer` and `roles/iam.serviceAccountAdmin` with custom roles containing only the read/lifecycle permissions needed by the existing Terraform plan. Add a WIF `assertion.sub ==` constraint that exactly matches each already-approved repository/ref/environment workflow identity, retaining existing claim checks. Add a default-deny ingress firewall and Cloud Armor Log4j preconfigured WAF protection without weakening current throttle/allow rules.

- [ ] **Step 4: Verify focused GREEN and zero pinned findings**

Run: `python -m pytest infra/terraform/tests/test_security_contract.py -q`

Run: `docker run --rm -v "${PWD}:/repo:ro" ghcr.io/bridgecrewio/checkov@sha256:e5e308e713725e73f517e4cb85b39d467f1e047204c174fb15eb444c27ffb745 -d /repo/infra/terraform --quiet`

Expected: PASS with zero failed checks; do not use `--skip-check`, baseline, or severity filtering.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform
git commit -m "infra: harden terraform security posture"
```

### Task 3: Verify all Terraform roots and unblock OP-07

**Files:**
- Modify: `infra/terraform/tests/test_security_contract.py`
- Modify: `infra/terraform/tests/access_platform.tftest.hcl`
- Modify: `docs/access-cloud-run-implementation-checklist.md`

**Interfaces:**
- Consumes: Tasks 1–2’s explicit inputs and hardened resources.
- Produces: evidence that the pinned Terraform scan has zero failures, so OP-07 can resume its final workflow correction.

- [ ] **Step 1: Add failing exhaustive contract assertions**

```python
def test_pinned_checkov_contract_has_no_unresolved_hardening_categories():
    contract = read("infra/terraform/tests/access_platform.tftest.hcl")
    for token in ('storage_log_bucket_name', 'artifact_registry_kms_key_name', 'enable_flow_logs', 'POSTGRES_18'):
        assert token in contract
```

- [ ] **Step 2: Run RED, then implement only resource-derived native assertions**

Run: `python -m pytest infra/terraform/tests/test_security_contract.py -q`

Expected: FAIL before Task 1/2 native contract additions.

- [ ] **Step 3: Run all local validation gates**

Run: `terraform fmt -check -recursive infra/terraform`

Run: `terraform -chdir=infra/terraform/environments/test init -backend=false && terraform -chdir=infra/terraform/environments/test validate`

Run: `terraform -chdir=infra/terraform/environments/production init -backend=false && terraform -chdir=infra/terraform/environments/production validate`

Run: `terraform -chdir=infra/terraform/environments/test test -test-directory=tests`

Run: `python -m pytest infra/terraform/tests -q`

Run: pinned Checkov command from Task 2.

Expected: all commands pass without cloud credentials or apply.

- [ ] **Step 4: Update the checklist only after the scan is green**

Replace OP-07’s Terraform finding blocker with an `IN PROGRESS` note that names the resumed supply-chain work; do not mark OP-07 complete until its own final review is clean.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform docs/access-cloud-run-implementation-checklist.md
git commit -m "test: verify terraform security hardening"
```

## Self-Review

- Spec coverage: Tasks 1–3 cover all Checkov findings: bucket logging, Cloud Armor, WIF subject, basic/broad IAM roles, VPC flow logs/firewall, Artifact Registry KMS, PostgreSQL version/logging/audit/SSL flags, and secret-scanner-safe native fixtures.
- Placeholder scan: no deferred implementation placeholders remain; each task has exact files, RED/GREEN commands, and required resource interfaces.
- Type/interface consistency: Task 1 defines the KMS/log values consumed by Task 2; Task 3 validates the outputs of both before OP-07 resumes.

