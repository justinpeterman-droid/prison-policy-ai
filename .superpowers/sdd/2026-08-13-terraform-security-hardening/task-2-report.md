# Task 2 Report: Terraform Security Posture Hardening

## Scope

Implemented Task 2 on `fix/terraform-security-hardening` from Task 1 commit
`0a571e0`. No Terraform apply, cloud credentials, real project identifiers,
production mutation, or remote push was used.

Changed only the approved Task 2 Terraform module and contract files:

- `infra/terraform/modules/access_platform/identities.tf`
- `infra/terraform/modules/access_platform/network.tf`
- `infra/terraform/modules/access_platform/edge.tf`
- `infra/terraform/modules/access_platform/serverless.tf`
- `infra/terraform/modules/access_platform/sql.tf`
- `infra/terraform/modules/access_platform/outputs.tf`
- `infra/terraform/tests/test_security_contract.py`
- `infra/terraform/tests/access_platform.tftest.hcl`

## RED evidence

The first focused run, before production changes, produced six intended
failures and sixteen passes:

```text
python -m pytest infra/terraform/tests/test_security_contract.py -q
6 failed, 16 passed
```

The failures covered broad project roles, missing exact WIF subject, missing
VPC flow logs/default-deny firewall, missing Log4j Cloud Armor rule, missing
Artifact Registry CMEK, and the PostgreSQL version/SSL/audit flags.

The exact pinned scanner baseline after Task 1 was:

```text
Passed checks: 151, Failed checks: 18, Skipped checks: 0
```

Additional RED cycles caught and proved:

- the literal approved WIF subject and mismatched-repository precondition;
- Checkov 3.3.11's required `log_min_duration_statement = -1` value;
- removal of unmanaged or duplicate plan-role permissions; and
- regional NEG plus Service Networking read permissions derived from the
  managed resource graph.

## Implemented controls

- Replaced project-level `roles/viewer` with
  `accessTerraformPlanRead`, containing read-only permissions derived from the
  module's project-scoped managed resource types. IAM and secret metadata remain
  in the existing dedicated reviewer/viewer grants; state remains prefix-scoped.
- Replaced project-level `roles/iam.serviceAccountAdmin` with
  `accessServiceAccountLifecycle`, limited to create/delete/get/list/update and
  IAM-policy lifecycle. It includes no key, token, signing, delegation, or
  `actAs` permission.
- Constrained every GitHub provider to the literal approved subject prefix
  `repo:justinpeterman-droid/prison-policy-ai:environment:` plus its exact
  provider environment. Existing repository, ref, environment, and workflow
  claim checks remain. A lifecycle precondition rejects a configured repository
  that differs from the approved subject repository.
- Enabled subnet VPC flow logs with five-minute aggregation, 0.5 sampling, and
  full metadata; added a priority-65534 deny-all ingress firewall on the custom
  VPC.
- Added an enforced, non-preview Cloud Armor `cve-canary` deny rule at priority
  100, preserving the existing priority-1000 throttle and default allow rule.
- Bound Artifact Registry to Task 1's required external KMS key input.
- Upgraded Cloud SQL to `POSTGRES_18`, required trusted client certificates,
  and configured the exact connection, checkpoint, duration, hostname, lock,
  statement, message, and pgAudit flags asserted by the native contract and
  pinned scanner.
- Extended the non-sensitive Terraform test contract with resource-derived
  booleans, role permission sets, and exact relation checks only.

## Final verification

Terraform 1.15.8 formatting and validation:

```text
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
Success! The configuration is valid.
```

Full Python Terraform contracts:

```text
python -m pytest infra/terraform/tests -q
46 passed in 0.06s
```

The established environment-local copy workflow ran the real mocked native
test, not the misleading zero-test parent-directory invocation:

```text
terraform -chdir=infra/terraform/environments/test test -test-directory=tests
Success! 1 passed, 0 failed.
```

The exact Checkov 3.3.11 image digest was run with only `infra/terraform`
mounted read-only, networking disabled, a read-only container filesystem, all
capabilities dropped, and no privilege escalation. No skip check, baseline,
suppression, or severity filter was used:

```text
ghcr.io/bridgecrewio/checkov@sha256:e5e308e713725e73f517e4cb85b39d467f1e047204c174fb15eb444c27ffb745
Passed checks: 176, Failed checks: 0, Skipped checks: 0
```

Checkov emitted a non-fatal guideline-download warning because the container
was deliberately offline; the scan itself exited zero with the counts above.

## Result

All eighteen Task 2 baseline findings are eliminated directly in resource
configuration. No finding is hidden, suppressed, baselined, skipped, or
severity-filtered.
