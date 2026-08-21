# Guided Web GCP Launch Runbook

Use this runbook for the new Guided Web application only. It does not retire,
redirect, or depend on the older web surface or Microsoft Access.

## Foundation

- [ ] Test and production use separate billing-enabled GCP projects.
- [ ] Each environment has its own protected Terraform state bucket, identity,
  and state prefix.
- [ ] The required Google APIs are enabled by the reviewed Terraform plan.
- [ ] GitHub environments match `docs/operations/github-environment-policy.md`:
  branch limited to `refs/heads/main`, self-review prevented, and at least the
  documented number of independent reviewers.
- [ ] All values in `github-environment-variable-inventory.md` are configured
  in the matching protected environment; no secrets were put in GitHub.

## Test deployment

- [ ] A reviewed release-version commit replaces the development sentinel.
- [ ] The test deployment workflow builds the exact main commit once and
  records the immutable Artifact Registry digest, SBOM, provenance, and
  migration head.
- [ ] The reviewed Terraform plan is applied from its exact artifact; no
  replan occurs during apply.
- [ ] Secret containers are populated by the approved custodian, outside Git.
- [ ] The migration job completes and verifies the expected Alembic revision.
- [ ] Fictional-data smoke covers health, authentication/session termination,
  paperwork/report output, print/download, and the Guided Web AI paths.
- [ ] Browser, keyboard, screen-reader, display-scaling, PDF/print, and mobile
  acceptance are recorded.
- [ ] Test rollback and a database restore exercise complete successfully.

## Production promotion

- [ ] Product, security, records, database, and operations approvals are
  recorded outside the repository.
- [ ] Backup and PITR readiness are set to `reviewed` only after a successful
  restore exercise.
- [ ] Production Terraform plan and apply approvals are independent.
- [ ] Production deploy starts the same test-qualified immutable digest with
  zero traffic.
- [ ] The release advances through 1%, 10%, 50%, and 100% traffic only when
  smoke, error-rate, latency, and observation-window gates pass.
- [ ] Any failed traffic, health, error-rate, or latency gate restores the
  captured prior API and worker revisions; never downgrade the database.

## Stop conditions

Stop if billing is disabled, a project is shared between environments, any
identity uses a long-lived key, a protected environment lacks independent
review, a release still carries development metadata, a secret has no approved
custodian, or the candidate digest/test descriptor/plan receipt does not agree.
