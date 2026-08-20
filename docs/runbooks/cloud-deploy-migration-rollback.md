# Controlled cloud deploy, migration, traffic, and rollback

This runbook is for authorized human operators using protected GitHub workflows. Commands shown inside workflow definitions are future workflow-only operations and are prohibited to coding agents. Local checks do not open a release gate.

## Stop conditions

Stop before plan download or cloud authentication when any of the following is absent, stale, or inconsistent:

- EXT-16 verification for the exact protected environment, workflow path, reviewer count, WIF identity, and `refs/heads/main`;
- all required OP-07 checks on the exact source commit;
- a schema-valid `release/version.json` with no production development sentinel;
- the tested descriptor, its SHA-256, SBOM hash, provenance ID, test run, migration head, source commit, and immutable Artifact Registry `@sha256:` digest;
- migration-register review, current backup/PITR and restore evidence, compatibility review, approved traffic thresholds/windows, security review, fictional test results, rollback evidence, or written approval;
- the prior known-good API and worker revisions and proof that their digests remain approved; or
- a single exact plan receipt and nonexpired artifact whose repository, workflow name/path/numeric ID, run ID, successful conclusion, protected environment, full ref, commit, digest, registry projection/hash, root, purpose, plan hash, numeric artifact ID, and artifact name all agree.

Never repair a mismatch by changing an input, downloading by name, replanning during apply, rebuilding for production, selecting a mutable tag, weakening an environment, or bypassing a reviewer.

## Plan receipt and apply handoff

`terraform-plan.yml` runs under `test` or `production-plan` as the plan identity. It emits `reviewed.tfplan`, redacted `reviewed.txt`, and closed `plan-metadata.json`, uploads one 30-day artifact named `tfplan-<environment>-<source_commit>-<run_id>`, and records the numeric artifact ID in the successful protected deployment receipt.

The handoff retains:

- `plan_workflow_run_id`, `plan_workflow_name`, `plan_workflow_id`;
- `plan_artifact_id`, `plan_artifact_name`, `plan_sha256`;
- repository, exact workflow path, protected environment, `refs/heads/main`, source commit;
- image digest, version-registry SHA-256 and six projected runtime values;
- Terraform root, plan purpose, approval reference, and receipt/status IDs.

Before download, `terraform-apply.yml` queries the Actions workflow/run/artifact and Deployments APIs with read-only repository permissions. It requires the exact successful origin run and receipt, then downloads by numeric artifact ID only. After extraction it rejects missing/extra/symlink members, recomputes the binary hash, validates every closed metadata field and current registry bytes, authenticates as the apply identity, and applies the saved binary plan. It never replans.

GitHub's artifact ID is assigned only after the immutable archive is finalized. The archive binds the exact artifact name/run/hash; the numeric ID is bound by the upload action output, Actions API object, and protected deployment receipt and is revalidated before numeric-ID download. Review those three records as one authority chain.

## Test qualification and descriptor

`deploy-test.yml` is manual and test-only. It verifies the exact required checks, builds the commit once, uses signed release metadata to verify the SBOM tool, validates SBOM/runtime ancestry, pushes once, and resolves the digest. The digest and canonical version projection are passed unchanged through test plan/apply, migration verification, worker/API revisions, managed-origin smoke, and fictional contract/load/failure tests.

The resulting `backend-release.json` is closed and records exactly source commit, digest, SBOM hash, provenance, migration head, API/release version, registry hash, test run/environment, timestamp, and creator workflow. Retain its SHA-256 and attestation with the test evidence. Production must download the same numeric artifact and reject any changed byte.

## Production sequence

1. Run the production plan separately under `production-plan`; obtain independent plan review.
2. Start `deploy-production.yml` from `refs/heads/main` with the exact tested descriptor run/artifact/hash, all six plan provenance outputs, and approval reference.
3. The workflow validates test-run provenance, descriptor, production registry policy, and plan authority before the separate `production-apply` approval and saved-plan apply.
4. Under the independent `production-deploy` approval, capture current 100% API/worker revisions and traffic, confirm externally reviewed backup/PITR state, run the migration job once, and run catalog-only verification.
5. Deploy the tested digest to worker and API; API starts with no traffic. Confirm created revision names and digest equality.
6. Advance API traffic to 1%, 10%, 50%, and 100%. At each stage verify exact traffic allocation, run managed-host health/client-policy samples, enforce approved maximum error rate and p95 latency, and wait the approved observation window.
7. At 100%, repeat traffic and smoke verification, retain safe aggregate evidence, and record the prior-revision rollback inputs.

Do not put request bodies, roster/report/person identifiers, secrets, tokens, approval content, environment dumps, raw exceptions, or application rows in plan text, descriptors, receipts, summaries, smoke output, or tickets.

## Rollback decision matrix

| Condition | Required action | Schema/data action |
| --- | --- | --- |
| Candidate health, error, latency, or traffic gate fails during promotion | Automated failure handler restores 100% API and worker traffic to captured prior revisions and exits nonzero. | Retain expanded schema/data. |
| API regression after promotion; prior revision remains schema-compatible | Use `rollback-production.yml` with descriptor hash, exact prior revisions, expected head, and incident reference after `production-rollback` approval. | No migration or deletion. |
| Worker regression while API remains safe | Restore the reviewed prior worker revision; evaluate API compatibility before any API change. | No migration or deletion. |
| Prior revision is not compatible with current schema or digest cannot be verified | Stop and escalate to incident/database/security owners. | Never downgrade automatically. |
| Terraform drift follows an authorized emergency traffic exception | Preserve incident evidence, then create a new reviewed reconciliation plan. | Never edit state or apply an unreviewed plan. |

Rollback workflows can read revision metadata and health endpoints and can change only revision/traffic selection. They cannot build, apply Terraform, invoke jobs, read/change secrets, downgrade Alembic, delete data, or use production data for testing.

## First-Admin separation

`bootstrap-first-admin.yml` accepts only target environment, opaque private request URI, and request SHA-256. Static jobs map test to `test`/`access-test-bootstrap-admin` and production to `production-deploy`/`access-production-bootstrap-admin`; each uses only the corresponding `admin-bootstrap` WIF identity and invokes once with `--wait`.

The workflow does not read the request, job logs, a secret version, or a PIN. Safe summary fields are limited to target, repository, workflow ref, main ref, commit, run ID, request hash, execution name, and status. PIN retrieval/communication, immediate disable, eventual destruction, and orphan cleanup are separate authorized-custodian duties in `initial-admin-enrollment.md`. An orphan/unknown outcome prohibits retry until external cleanup evidence receives independent review.

## Post-deploy evidence

Retain only safe references and aggregate outcomes in the approved system of record: descriptor/plan hashes and IDs, reviewed commit/digest/version/head, environment and workflow/run IDs, prior/candidate revision names, stage allocations, aggregate smoke thresholds/results, approval and incident references, and restore/rollback evidence classifications. Confirm monitoring is nominal and update release notes without copying operational data.
