# Runbook — Secret Population and Rotation

**Audience:** authorized external secret custodians only.
**Scope:** populating, pinning, rotating, rolling back, and auditing the nine
Secret Manager containers created by Terraform.

Terraform creates empty containers and per-secret IAM only. It must never
create a secret version. Do not place secret values in Git, Terraform state or
variables, GitHub variables, workflow output, terminal history, tickets, chat,
email, logs, screenshots, or repository evidence.

## Custody boundary

- Generate and transfer values through the agency-approved, non-recorded
  channel outside repository and CI automation.
- Populate test and production independently. Never copy a production value
  or production data into test.
- Record only the secret name, numeric version, custodian, timestamp, change
  approval, and verification result in the external system of record.
- Applications consume an explicitly approved version. Do not silently switch
  `latest` during a rollout.

## Standard procedure

For each secret, the custodian must:

1. Verify the target project, environment, secret name, and approved change.
2. Generate a new independent value with the agency-approved cryptographic
   generator. Never derive one secret from another.
3. Add exactly one version without echoing or logging the payload.
4. Record the returned numeric version outside this repository.
5. Pin the consuming service to that version through the reviewed deployment
   configuration and verify the intended runtime identity is the only reader.
6. Exercise the test-only health and functional checks before promotion.
7. Disable the superseded version after the observation window. Destroy it
   only after rollback is no longer required and retention policy permits.

If submission has an ambiguous outcome, do not retry. Reconcile version
metadata for the exact operation window, disable and destroy any orphaned
candidate, obtain external review, and only then start a new operation.

## Independent signing and hashing material

Apply the standard procedure separately to:

- `identity-hash-pepper`: rotation changes device-hash interpretation. Use the
  separately reviewed session-transition plan and verify old sessions fail in
  the intended way before retiring the prior version.
- `cursor-signing-key`: keep the previous version available for the bounded
  rollback window. Verify newly issued cursors and the documented rejection of
  stale or tampered cursors.
- `client-update-grant-key`: the API identity is its sole runtime accessor.
  Verify five-minute update grants, signature rejection, replay rejection, and
  audit events. Generate, populate, pin, rotate, and audit it independently of
  every other signing key.

Never rotate these three together as a single unreviewed change.

## Other runtime secrets

- `access-database-url`: construct outside automation for the environment's
  private PostgreSQL instance. Keep database credentials out of shell history
  and verify private-only connectivity from the named runtime identities.
- `flask-session-secret`: rotate under the reviewed session-invalidation plan.
- `legacy-access-code` and `legacy-admin-code`: populate only when the preserved
  legacy fallback is explicitly enabled by its separate approval. Controlled
  beta does not enable legacy mode.
- `github-feedback-token`: use a narrowly scoped test credential only if the
  feedback integration is approved. Otherwise leave the container empty and
  the feature disabled.

## Initial administrator PIN

`initial-admin-pin` is not populated by Terraform, GitHub Actions, or a human
preload. Only the bootstrap runtime may add one version, and it cannot read any
version. The authorized external custodian must:

1. Retrieve only the exact returned numeric version through an approved
   non-recorded channel and deliver it only to the approved initial Admin.
2. Confirm receipt, then immediately disable that version.
3. Destroy it after the successful forced PIN change within the approved short
   enrollment window.
4. Retain only external metadata evidence—never the PIN or payload.

On an ambiguous add result, perform metadata-only reconciliation for the exact
operation window and disable/destroy every candidate without reading payloads.
On a known orphan, disable/destroy only the exact returned version. Do not
retry bootstrap until cleanup has independent external review.

## Rollback and audit verification

- Roll back by repinning the consuming service to the still-enabled previous
  version; never copy its payload into a new version.
- Confirm the service revision and secret version match the approved record,
  then rerun authentication, cursor, update-grant, and health checks relevant
  to the changed secret.
- Review Secret Manager data-access logs and IAM policy for unexpected reads,
  writers, project-level access, or workflow identities with payload access.
- Stop and escalate on any unexplained access, version, IAM member, or mismatch.

Repository evidence may state only pass/fail, timestamp, environment, and an
external evidence reference. It must not contain project identifiers, resource
names, principals, secret versions, or values.
