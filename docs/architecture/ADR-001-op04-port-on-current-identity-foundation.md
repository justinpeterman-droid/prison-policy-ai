# ADR-001: Port OP-04 onto the Current Identity Foundation

**Status:** Proposed
**Date:** 2026-08-20
**Deciders:** Repository owner, platform owner, and security reviewer

## Context

PR #110 merged OP-03 as a newer environment-scoped Terraform foundation. The
older OP-04 integration implements the required Cloud Run, storage, task queue,
and managed-edge resources, but it assumes an earlier service-account and WIF
module interface. Replaying that merge would conflict with or replace current
least-privilege controls.

## Decision

Preserve the current OP-03 module interface, workflow identities, WIF claim
model, Cloud SQL controls, secret bindings, and tests. Port OP-04 resource files
and extend the current variables, IAM grants, outputs, environment roots, and
Terraform tests around those boundaries. Do not carry forward the old OP-04
review marker; require fresh tests and review on the reconciled tree.

## Options Considered

### Replay the old OP-04 merge

| Dimension | Assessment |
| --- | --- |
| Complexity | Initially low, but conflict resolution is unsafe |
| Security | Risks replacing the newer WIF/IAM contract |
| Reviewability | Poor because unrelated OP-03 behavior changes |

**Pros:** Reuses the old merge directly.

**Cons:** Six core Terraform files conflict, and selecting the old side would
regress current identity boundaries.

### Port OP-04 onto current OP-03

| Dimension | Assessment |
| --- | --- |
| Complexity | Medium |
| Security | Preserves current least privilege |
| Reviewability | Strong; OP-04 additions remain explicit |

**Pros:** Keeps the merged foundation authoritative and makes the change
auditable by resource family.

**Cons:** Requires reconciliation tests and a new review pass.

## Trade-off Analysis

The port costs more implementation time but avoids treating stale review
evidence as authority over a newer security model. Production safety and
reviewability outweigh the convenience of replaying the old merge.

## Consequences

- OP-03 remains the source of truth for identities, WIF, secrets, and SQL.
- OP-04 owns Cloud Run API/worker services, Artifact Registry, task queue,
  private storage, load balancing, TLS, and Cloud Armor additions.
- IAM additions must bind to current workflow and runtime service accounts.
- OP-04 cannot be marked reviewed until the reconciled Terraform tests and an
  independent review pass.

## Action Items

1. [ ] Port OP-04 resources without replacing OP-03 controls.
2. [ ] Extend current environment variables and module inputs.
3. [ ] Add exact IAM and resource-boundary contract tests.
4. [ ] Run Terraform formatting, initialization without backend, validation,
   native tests, Python contract tests, and security review.
