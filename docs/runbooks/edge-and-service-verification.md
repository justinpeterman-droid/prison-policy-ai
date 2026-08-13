# Edge and service verification

This runbook is for an authorized human operator after an approved deployment. Agents do not run these commands against any cloud environment.

First-apply gate: an authorized human must pre-grant the terraform-apply
identity the reviewed OP-04 control-plane role. Terraform cannot create or
grant permissions it does not already hold. That role excludes artifact upload
or build, Storage object access, Cloud Tasks payload operations, secret reads,
migration invocation, and traffic/revision deployment. Cloud Run service-scoped
`run.services.update` cannot distinguish revision/traffic payloads from other
service updates; OP-08 protected workflow validation is the required control
that admits only immutable-digest deployment and reviewed rollback payloads.

Verify, read-only:

- DNS resolves the managed hostname to the approved load-balancer address.
- The managed certificate is active and the HTTPS proxy uses it.
- The API backend has the approved Cloud Armor policy attached.
- API ingress is internal-and-load-balancer only; worker ingress is internal only.
- Worker IAM grants `roles/run.invoker` only to the task-invoker service account.
- Cloud Tasks OIDC audience equals the reviewed worker URI.
- Every storage bucket enforces public-access prevention, uniform access, and versioning.
- The release bucket grants API read-only object access; no worker or workstation binding exists.
- The bootstrap binding reads only `admin-bootstrap-requests/` objects in the configuration bucket.
- API and worker revisions use the same immutable image digest.
- API has bounded HTTP startup/liveness checks on its private `/health` endpoint;
  worker has bounded TCP startup/liveness checks on port 8080 without exposing a
  health route or application data.

Do not use smoke requests, mutation commands, secret reads, traffic changes, DNS changes, or queue invocation as part of this verification.
