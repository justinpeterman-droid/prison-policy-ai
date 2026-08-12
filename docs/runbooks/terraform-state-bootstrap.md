# Runbook — Terraform State Bootstrap and Migration

**Audience:** authorized human operators only.
**Scope:** creating the protected Terraform remote-state bucket and migrating each
environment root onto it.

> **Agent boundary.** Automated agents (Claude Code, Codex, CI jobs) may run only
> `terraform fmt`, `terraform init -backend=false`, `terraform validate`, and
> `terraform providers lock` against these roots. Every command in this runbook
> marked **HUMAN OPERATOR ONLY** — in particular `terraform apply` and
> `terraform init -migrate-state` — is prohibited to agents and must be executed
> interactively by a named operator. Agents must not authenticate to Google,
> contact a GCS backend, or create, modify, or destroy any cloud resource.

---

## 1. Prerequisites

Confirm before starting. Record only gate state in
`docs/operations/external-prerequisites.md` — never the evidence contents,
identities, or infrastructure values.

- `EXT-01` Separate cloud environments — reviewed.
- `EXT-02` Regional placement (production in `us-central1`) — reviewed.
- `EXT-05` WIF trust conditions — reviewed.
- Terraform CLI exactly `1.15.8` on the operator workstation (`terraform version`).
- Operator holds the project-level rights needed to create a storage bucket and
  set an IAM binding in the target project.
- A separate project (or equivalently isolated resource set) exists for **test**
  and for **production**. The two must never share a bucket, prefix, project,
  deployment identity, or provider credential.

Repeat this entire runbook **once per environment**. Do not reuse the test
bucket, the test credential, or the test operator session for production.

## 2. Values supplied at run time

These are supplied by the operator at the prompt or through an encrypted local
file. **None of them is ever committed to the repository**, and none appears in
this runbook, in a `.tfvars` file inside the working tree, or in ticket text.

| Input | Meaning |
|---|---|
| `project_id` | Project that owns the state bucket for this environment |
| `state_bucket_name` | Globally unique bucket name for this environment's state |
| `region` | Bucket location (production: `us-central1`) |
| `authorized_member` | The single IAM member granted `roles/storage.objectAdmin` |

## 3. Create an encrypted temporary directory for local bootstrap state

The bootstrap root has no backend, so its first apply writes `terraform.tfstate`
to local disk. That file contains the bucket name and the authorized member, so
it must never be written inside the Git working tree.

1. Create a working directory on encrypted storage approved by agency policy
   (for example a BitLocker-protected volume or an encrypted removable device),
   outside the repository.
2. Restrict its ACL to the operator account alone.
3. Copy `infra/terraform/bootstrap/state/*.tf` into it, or run Terraform with
   `-state=<encrypted-path>/terraform.tfstate` so no state file lands in the
   repository.
4. Record the chosen path in the operator's session notes only.

## 4. Apply the bootstrap root — **HUMAN OPERATOR ONLY**

```powershell
terraform -chdir=infra/terraform/bootstrap/state init -backend=false
terraform -chdir=infra/terraform/bootstrap/state validate

# HUMAN OPERATOR ONLY - creates cloud resources.
terraform -chdir=infra/terraform/bootstrap/state plan `
  -state="<encrypted-path>\terraform.tfstate" `
  -var="project_id=<supplied>" `
  -var="state_bucket_name=<supplied>" `
  -var="region=<supplied>" `
  -var="authorized_member=<supplied>"

# HUMAN OPERATOR ONLY - creates cloud resources.
terraform -chdir=infra/terraform/bootstrap/state apply `
  -state="<encrypted-path>\terraform.tfstate" `
  -var="project_id=<supplied>" `
  -var="state_bucket_name=<supplied>" `
  -var="region=<supplied>" `
  -var="authorized_member=<supplied>"
```

Read the plan before approving. It must show exactly one
`google_storage_bucket` and one `google_storage_bucket_iam_member`, and nothing
else. Stop if it proposes any other resource, or proposes replacing an existing
bucket.

## 5. Verify the bucket controls before migrating state

Confirm every control below on the created bucket. Do not proceed to migration
until all of them pass.

| Control | Expected |
|---|---|
| Uniform bucket-level access | Enabled |
| Public access prevention | `enforced` |
| Object versioning | Enabled |
| Retention policy | 30 days (2592000 seconds), unlocked |
| Noncurrent-version lifecycle | Delete 90 days after an object becomes noncurrent |
| IAM | Exactly one grant: `authorized_member` → `roles/storage.objectAdmin` |
| Terraform lifecycle | `prevent_destroy = true` in the bucket resource |

Verify with the operator's approved tooling, for example:

```powershell
# HUMAN OPERATOR ONLY - reads cloud resources.
gcloud storage buckets describe gs://<state_bucket_name> `
  --format="yaml(uniformBucketLevelAccess,publicAccessPrevention,versioning,retentionPolicy,lifecycle)"
gcloud storage buckets get-iam-policy gs://<state_bucket_name>
```

Stop and escalate if any control is missing, if an unexpected IAM member
appears, or if the bucket is publicly reachable.

## 6. Migrate an environment root onto the remote backend — **HUMAN OPERATOR ONLY**

Each environment root commits only its state **prefix**; the bucket name is
supplied at init time.

| Root | Committed prefix |
|---|---|
| `infra/terraform/environments/test` | `access/test` |
| `infra/terraform/environments/production` | `access/production` |

```powershell
# HUMAN OPERATOR ONLY - contacts the GCS backend and moves state.
terraform -chdir=infra/terraform/environments/test init -migrate-state `
  -backend-config="bucket=<test_state_bucket_name>"

# HUMAN OPERATOR ONLY - contacts the GCS backend and moves state.
terraform -chdir=infra/terraform/environments/production init -migrate-state `
  -backend-config="bucket=<production_state_bucket_name>"
```

Answer the migration prompt only after confirming the target bucket belongs to
the matching environment. Migrating production state into the test bucket, or
either environment into the other's prefix, breaks the isolation this task
exists to guarantee.

## 7. Verify the migration

1. Confirm the remote object exists under the expected prefix and nowhere else:

   ```powershell
   # HUMAN OPERATOR ONLY - reads cloud resources.
   gcloud storage ls gs://<state_bucket_name>/access/test/
   gcloud storage ls gs://<state_bucket_name>/access/production/
   ```

2. Confirm the object has at least one live generation and that versioning is
   recording generations.
3. Run a read-only `terraform -chdir=<root> plan` and confirm it reads state
   from the backend and reports no unexpected drift.
4. Confirm `git status --short` shows no `.terraform/`, `*.tfstate`,
   `*.tfstate.backup`, `*.tfvars`, `crash.log`, or credential file. These must
   remain untracked; commit only the files this task declares.

## 8. Securely dispose of the temporary local state

Once the remote object is verified:

1. Destroy the local bootstrap state file and its backup in the encrypted
   working directory using the agency-approved secure-deletion method for the
   storage class in use.
2. Remove the encrypted working directory itself, or return the encrypted
   device to approved custody.
3. Clear any shell history entry that captured a bucket name, project ID, or
   member identity.
4. Record completion in the agency system of record. Do not record bucket
   names, project IDs, or member identities in this repository.

## 9. Rollback and failure handling

- **Bootstrap apply fails partway.** Re-run the plan from the same encrypted
  state file. Do not delete the bucket; `prevent_destroy = true` intentionally
  blocks `terraform destroy`, and removing it requires a reviewed change.
- **Migration prompted for the wrong bucket.** Answer `no`, correct
  `-backend-config`, and re-run. Do not hand-edit state.
- **Wrong prefix was written.** Stop, escalate, and treat the misplaced object
  as an isolation incident under `docs/operations/ownership-and-escalation.md`.
  Do not delete state to "clean up".
- **A control in section 5 is missing.** Correct it in Terraform and re-apply;
  never patch the bucket by hand, or the next plan will revert it.

## 10. What must never happen

- No agent runs `apply`, `destroy`, `init -migrate-state`, or any authenticated
  Google command.
- No project ID, bucket name, member identity, credential, `.tfvars` file,
  state file, plan file, or provider cache is committed.
- Test and production never share a bucket, prefix, project, identity, or
  credential.
- Production data never appears in the test environment.
