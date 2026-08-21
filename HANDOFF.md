# Production handoff

Repository code now defines a controlled, digest-only delivery path. Nothing in this handoff authorizes a deployment, production read, secret operation, roster import, migration, bootstrap, traffic change, or rollback. The external gates in `docs/operations/external-prerequisites.md` and `docs/operations/github-environment-policy.md` remain `CLOSED` until administrators record reviewed evidence in the approved system of record.

## Required external setup

1. A GitHub administrator verifies the exact six protected environments, reviewer counts, `refs/heads/main` restriction, workflow allowlists, self-review prohibition, and environment-scoped WIF variables required by EXT-16.
2. Cloud owners bootstrap remote state and apply the reviewed OP-03 through OP-06 Terraform stack through the protected plan/apply path. They populate secret versions through the separate secret-custodian runbook; repository workflows never create or read secret payloads.
3. Release managers replace the checked-in `0.0.0-development` registry values through a separate reviewed version-bump commit. Production validation intentionally fails while any development sentinel remains.
4. Database, security, operations, and records owners review the migration register, restore evidence, thresholds/windows, fictional test evidence, rollback evidence, pilot authorization, and written acceptance.
5. Initial-Admin custodians complete EXT-12 using the protected bootstrap workflow and the separate PIN custody/disable/destruction ceremony. The workflow operator and coding agents are never PIN custodians.

## Supported delivery order

1. Required OP-07 checks pass for the exact `refs/heads/main` commit.
2. `deploy-test.yml` builds once, resolves the Artifact Registry digest, verifies SBOM/provenance, applies a reviewed test plan, migrates/verifies, deploys the same digest, runs fictional qualification, and emits an attested descriptor.
3. A reviewer runs `terraform-plan.yml` for production with the descriptor's exact commit, digest, and version-registry hash. The numeric workflow/run/artifact IDs and plan hash are retained with the protected deployment receipt.
4. `deploy-production.yml` validates the unchanged descriptor and plan provenance before calling the separately approved apply workflow. The deploy gate then records known-good revisions, confirms backup/PITR evidence, migrates/verifies, creates no-traffic revisions, and advances 1/10/50/100 traffic only while smoke, error-rate, latency, observation-window, and traffic-state gates pass.
5. A failed stage restores the prior API and worker revisions without downgrading or deleting schema/data. Emergency operators use `rollback-production.yml` only with reviewed prior revisions, compatible schema evidence, the descriptor hash, and an incident reference.

Exact operator evidence and stop conditions are in `docs/runbooks/cloud-deploy-migration-rollback.md`.

## Explicitly retired paths

Do not restore automatic main-push deployment, long-lived service-account keys, mutable-tag/source promotion, or direct local deployment helpers. These files remain absent:

- `.github/workflows/cloud-run.yml`
- `backend/scripts/deploy.sh`
- `scripts/merge_and_deploy.py`

There is no supported long-lived key or local source-deploy path. All cloud mutation is human-approved workflow-only and uses environment-scoped WIF.

## Non-deployment follow-ups

- Live policy-chat evaluation still requires separately approved ADC and a non-production evaluation context.
- Feedback integration requires a dedicated least-privilege GitHub App or approved token custody design; do not place a token in a plain Cloud Run environment variable or this repository.
