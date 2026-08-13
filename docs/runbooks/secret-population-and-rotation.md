# Secret Population and Rotation

## Scope and safety boundary

This runbook is for the externally authorized secret custodian. Terraform creates
only empty Secret Manager containers; it never receives a secret value, creates
a version, or records a value in state. Run these procedures from an approved,
audited operator environment. Do not place secret values in Git, Terraform
variables, CI variables, shell history, tickets, or ordinary logs.

The custodian must confirm the target environment, container name, approved
change record, and current service identity bindings before every action. Record
only the environment, container, version number, operator record reference, and
verification result in the approved system of record.

## Generate and populate independent cryptographic secrets

Generate each of the following independently with the approved secrets tool:

- `identity-hash-pepper`
- `cursor-signing-key`
- `client-update-grant-key`

For each container, create a new secret version through the approved custodian
workflow, verify that only the documented runtime identity has version access,
and record the version number outside this repository. Pin a deployment to the
approved version by the platform's managed secret-reference mechanism; never
copy the value into a build or deployment configuration. Verify the resulting
service revision can start and that audit logs show only the authorized secret
access event, with no value in logs.

`client-update-grant-key` is independent from every application key. Its API
accessor is the API runtime only. Before releasing a client change, verify that
the key's new version is pinned, grant validation succeeds for a fictional test
request, no other runtime or workflow identity can read a version, and the
Secret Manager audit trail contains only approved access. Rotation must retain
the prior approved version until rollback validation is complete.

## Rotate, validate, and roll back

1. Obtain the required approval and schedule a maintenance window.
2. Generate a replacement value outside this repository and create one new
   version in the approved container.
3. Update the managed runtime reference to that numbered version and deploy
   through the approved human-controlled release procedure.
4. Validate health and the relevant functional flow using fictional data.
5. Review Secret Manager data-access audit events and runtime logs for the
   approved identity and absence of secret values.
6. If validation fails, pin the prior approved version, validate recovery, and
   record the rollback. Do not destroy either version until the records and
   retention authority approve disposal.
7. Disable and later destroy superseded versions only under the approved
   records-retention schedule.

The same procedure applies to `access-database-url`, `flask-session-secret`,
legacy-code containers, and `github-feedback-token`, subject to their separate
custodian approvals. The database URL is populated only after the human database
bootstrap creates the least-privilege application role; Terraform creates no SQL
user or password.

## Initial Admin PIN

`initial-admin-pin` starts empty. Only the bootstrap runtime may add a version;
it is deliberately not granted version access and therefore cannot retrieve the
PIN it writes. The external authorized PIN custodian alone retrieves the one-time
version, communicates it through the approved out-of-band procedure, and then
disables and destroys it according to the approved first-Admin enrollment record.
No workflow identity, including `admin-bootstrap`, may read this secret.

## Audit verification

After population, rotation, rollback, disablement, or destruction, the
custodian verifies per-secret IAM, version state, and data-access audit events in
the approved operations console. Record only safe metadata and the external
evidence reference. Never paste a secret value, database URL, identity, token,
or audit payload into this repository.
