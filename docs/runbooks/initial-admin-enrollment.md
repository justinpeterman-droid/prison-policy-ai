# Initial Admin enrollment

This procedure creates the only first Admin. It is an external, one-time enrollment ceremony under EXT-12. GitHub, Terraform, the bootstrap job, agents, and ordinary operators are not PIN custodians. The job is never retried automatically and is permanently unusable after any account exists.

## Roles and required approval

- The request custodian creates and uploads the encrypted/private request and records its immutable generation and SHA-256.
- The identity approver verifies the selected staff member is active, the request is approved, and zero accounts exist.
- The protected-workflow operator invokes only `access-test-bootstrap-admin` for test or `access-production-bootstrap-admin` through the exact `production-deploy` gate from `refs/heads/main`.
- The authorized PIN custodian alone may retrieve the exact new `initial-admin-pin` version through an agency-approved non-recorded channel, communicate it to the approved initial Admin, disable it, and later destroy it.
- A separate reviewer approves any reconciliation/cleanup evidence before a retry can be considered.

Stop if these roles, the protected environment, immutable request, one-time PIN delivery channel, short enrollment window, cleanup procedure, or enrollment-incident procedure are not approved.

## Create and seal the request

On an agency-approved encrypted workstation, create a UTF-8 JSON file of at most 4 KiB with exactly these fields and no extras:

```json
{
  "schema_version": 1,
  "operation_id": "00000000-0000-4000-8000-000000000001",
  "staff_member_id": "00000000-0000-4000-8000-000000000002",
  "approval_reference": "fictional-approval-reference"
}
```

The example is fictional. For an authorized operation, both identifiers must be version-4 UUIDs and the approval reference must be 1–200 visible ASCII characters. Never put the staff UUID, employee number, name, approval reference, PIN, or request body in workflow inputs, command lines, logs, tickets, chat, email, or clipboard history.

The object name is exactly `admin-bootstrap-requests/<operation-uuid>.json` in the environment's private configuration bucket, and the basename UUID equals `operation_id`. Upload it as a create-only object, apply the approved object hold/immutability control, and record only the opaque URI, generation, lowercase SHA-256, size, operation ID, approver role, and evidence references. Re-read the generation/hash metadata without downloading or printing the body. Stop if the object already exists, changes generation/hash, exceeds 4 KiB, or is outside the exact prefix.

The request custodian uses this create-only contract inside the approved encrypted workstation. Shell history/transcription is disabled, `$RequestFile` remains on encrypted temporary storage, and the workstation's approved secure-deletion procedure removes it after evidence review:

```powershell
$Environment = '<test-or-production>'
$ProjectId = '<approved-environment-project>'
$OperationId = '<approved-v4-operation-uuid>'
$RequestFile = '<approved-encrypted-local-path>'
$RequestUri = "gs://access-$Environment-configuration/admin-bootstrap-requests/$OperationId.json"
$RequestSize = (Get-Item -LiteralPath $RequestFile).Length
if ($RequestSize -gt 4096) { throw 'Request exceeds the 4 KiB maximum.' }
$RequestSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $RequestFile).Hash.ToLowerInvariant()
if ($RequestSha256 -notmatch '^[0-9a-f]{64}$') { throw 'Request hash is invalid.' }
gcloud storage cp $RequestFile $RequestUri --project=$ProjectId --if-generation-match=0
$Generation = gcloud storage objects describe $RequestUri --project=$ProjectId --format='value(generation)'
gcloud storage objects update $RequestUri --project=$ProjectId --temporary-hold --if-generation-match=$Generation
gcloud storage objects describe $RequestUri --project=$ProjectId --format='value(generation,size,temporaryHold)'
```

The final metadata must show the captured generation, exact size, and `True` hold. The custodian separately records `$RequestSha256`; the workflow must never print the request body or local path.

The protected workflow receives only:

```text
--request-uri gs://access-<environment>-configuration/admin-bootstrap-requests/<operation-uuid>.json
--expected-sha256 <lowercase-64-hex>
```

The runtime configuration is fixed by Terraform: `ADMIN_BOOTSTRAP_REQUEST_BUCKET=access-<environment>-configuration`, `ADMIN_BOOTSTRAP_REQUEST_PREFIX=admin-bootstrap-requests/`, and `INITIAL_ADMIN_PIN_SECRET` is the exact environment `initial-admin-pin` parent. None is a PIN value.

## Preflight and protected invocation

1. In test first, verify the exact request generation/hash, immutable image digest, source commit, job name, bootstrap runtime service account, and `max_retries = 0`. Confirm only the `admin-bootstrap` workflow identity has `roles/run.invoker` on the bootstrap job and that no public, application, deploy, migration, or scheduled invoker exists.

2. Through the approved database channel, bind the staff UUID privately and return only the boolean result of this precheck:

   ```sql
   SELECT NOT EXISTS (SELECT 1 FROM accounts)
          AND EXISTS (
            SELECT 1 FROM staff_members
            WHERE id = :approved_staff_member_id AND is_active IS TRUE
          ) AS bootstrap_precheck_ok;
   ```

   Stop unless the result is true. Do not retain the bind value or row data in execution evidence.

3. Complete the test ceremony with fictional data and verify the success, forced-change, immediate-disable, post-change destruction, and no-second-account controls. Production cannot proceed until the test evidence is reviewed.

4. From `refs/heads/main`, an authorized operator starts the reviewed `bootstrap-first-admin` workflow for exact environment `production-deploy`. The workflow cryptographically binds the approved opaque request URI and SHA-256 to the exact `access-production-bootstrap-admin` job. It accepts no staff, approval-reference, account, or PIN input and performs no log/secret/request-body read. Do not invoke the job directly.

5. The workflow executes once. The job uses the bootstrap runtime, mounts Cloud SQL at `/cloudsql`, reads only the approved request prefix and database URL, and may add one version only to `initial-admin-pin`. It cannot read any secret version. The application performs one Secret Manager add-version RPC with retries disabled before committing the Admin/account audit transaction.

## Closed result and PIN ceremony

The safe result has exactly four fields:

```json
{
  "operation_id": "00000000-0000-4000-8000-000000000001",
  "status": "bootstrapped",
  "expires_at": "<approved-short-window-timestamp-or-null>",
  "secret_version_reference": "initial-admin-pin/versions/<positive-integer-or-null>"
}
```

Permitted statuses are `bootstrapped`, `bootstrap_refused`, `pin_version_add_failed`, `pin_version_outcome_unknown_cleanup_required`, and `orphan_pin_version_cleanup_required`. No result or log may include request URI/body, staff/account identifier, approval reference/hash, PIN, secret bytes, project, bucket, or raw exception.

For `bootstrapped` only:

1. The authorized PIN custodian uses the approved non-recorded Secret Manager channel to retrieve exactly the returned version. GitHub, Terraform, the workflow operator, the job, and agents must not retrieve it.
2. The custodian communicates the PIN to the approved initial Admin through the approved non-recorded channel and confirms receipt without copying or transcribing it into operational evidence.
3. The custodian immediately disables that exact secret version. Retain only metadata/evidence that the exact safe version reference is disabled.
4. The initial Admin signs in within the approved short window and completes the forced PIN change. Verify only success/failure and the forced-change audit contract.
5. After successful forced change, the custodian destroys the exact disabled version and retains external destruction evidence only.

Disable and destruction use the safe numeric version parsed from the returned resource-relative reference; neither command reads payload data:

```powershell
$ProjectId = '<approved-environment-project>'
$SafeVersionReference = 'initial-admin-pin/versions/<positive-integer>'
$VersionNumber = ($SafeVersionReference -split '/')[-1]
if ($VersionNumber -notmatch '^[1-9][0-9]*$') { throw 'Unsafe secret version reference.' }
gcloud secrets versions disable $VersionNumber --secret='initial-admin-pin' --project=$ProjectId --quiet
# Run only after verified forced PIN change, or when the cleanup matrix requires destruction.
gcloud secrets versions destroy $VersionNumber --secret='initial-admin-pin' --project=$ProjectId --quiet
```

If the committed PIN becomes unavailable before forced change, stop and use the separately approved enrollment-incident process. Never re-enable/retrieve another version, rerun bootstrap, create another account through this job, or bypass the zero-account invariant.

## Failure and cleanup matrix

| Status or condition | Required action | Retry state |
| --- | --- | --- |
| `bootstrap_refused` | Confirm no Account/audit mutation, correct only the externally approved active-staff/zero-account/request issue, and obtain fresh approval. | Blocked until reviewed cause and evidence are complete. Permanently prohibited if any account exists. |
| `pin_version_add_failed` | Confirm the database transaction rolled back and Secret Manager definitively created no version. Retain safe status/operation evidence only. | Blocked until definitive failure evidence and new protected approval exist. |
| `pin_version_outcome_unknown_cleanup_required` | Perform metadata-only reconciliation on the dedicated `initial-admin-pin` secret over the exact operation window. Without reading payloads, disable and destroy every candidate new version; retain externally reviewed cleanup evidence. | Prohibited until every candidate is cleaned up and the independent reviewer approves evidence. |
| `orphan_pin_version_cleanup_required` | Disable and destroy the exact returned resource-relative version without reading its payload. Confirm zero Account/bootstrap-audit rows committed and retain external cleanup evidence. | Prohibited until exact-version cleanup and independent review are complete. |
| Safe result delivery lost after a successful execution | Stop. Use separately approved metadata-only reconciliation for this dedicated secret; never access another version's payload and never rerun to recover output. | Prohibited pending reconciliation, incident review, and cleanup. |
| Workflow/job completion unknown | Reconcile execution metadata only; do not read application logs, request objects, or secrets and do not invoke again. | Prohibited until the result/cleanup state is externally established. |

Outcome-unknown and orphan PINs cannot authenticate because Account and bootstrap audit rolled back. That fact does not waive cleanup. Never place a PIN in terminal capture, workflow output, GitHub, Terraform, tickets, chat, email, clipboard history, or recorded support tooling.

For the outcome-unknown or lost-result branches, the authorized custodian uses an independently approved UTC operation window and lists metadata only. The command must not include `versions access` or any payload-returning format:

```powershell
$ProjectId = '<approved-environment-project>'
$WindowStart = '<approved-rfc3339-utc-start>'
$WindowEnd = '<approved-rfc3339-utc-end>'
gcloud secrets versions list 'initial-admin-pin' --project=$ProjectId --filter="createTime>='$WindowStart' AND createTime<='$WindowEnd'" --format='table(name,createTime,state)'
```

An independent reviewer matches candidate metadata to the exact operation window. The custodian disables and destroys every candidate with the safe numeric-version procedure above, without reading any payload, and retains external cleanup evidence before any retry decision.

Enrollment is complete only after forced PIN change, immediate version disable, exact-version destruction, account/audit verification, and external evidence review. After the first Account exists, every later bootstrap attempt must be refused permanently.
