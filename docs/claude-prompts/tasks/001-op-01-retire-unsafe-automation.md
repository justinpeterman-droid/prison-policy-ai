# Claude Code Prompt 001 — OP-01: Retire Unsafe Automation and Close External Prerequisite Gates

Copy everything below this line into a fresh Claude Code session.

---

You are implementing sequence **001**, task **OP-01: Retire Unsafe Automation and Close External Prerequisite Gates** in the Prison Policy AI repository.

## Objective, outcome, and rationale

Remove the three known automatic/bypass deployment paths, restrict GitHub Pages to the static forms application, and add non-secret operational gate templates. The completed commit must make missing agency decisions visible without inventing or storing the decisions themselves. This is the safety foundation for every later identity, report, Access, infrastructure, and rollout task: ordinary pushes must not deploy Cloud Run, local helpers must not merge/push/deploy, and Pages must not expose backend or operational material.

## Repository, reviewed baseline, and branch

- Repository root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Reviewed baseline commit: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Required branch: `claude/op-01-retire-unsafe-deployers`
- Exact commit message: `chore: gate implementation and deployment prerequisites`

Begin in the repository root. Run:

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The reviewed baseline must be an ancestor of the current reviewed `main`. If `HEAD` is newer, inspect `git log --oneline $TaskBase..HEAD`, read the intervening prerequisite handoffs/plans, and confirm every intervening commit has completed review and does not conflict with this task. Start from current `HEAD`, not from the old baseline. Stop only if the baseline is not an ancestor, an intervening change is unreviewed/conflicting, a required predecessor output is absent, or a dirty path overlaps the allowed files or makes branch switching unsafe. Report unrelated user changes and leave them untouched; never discard, overwrite, stash, reset, clean, restore, or otherwise alter user work.

When ancestry/review/prerequisite checks pass and no dirty overlap makes switching unsafe, create the branch from current reviewed `HEAD`:

```powershell
git switch -c claude/op-01-retire-unsafe-deployers
```

If that branch already exists, stop rather than deleting or overwriting it.

## Required reading

Read these files before editing:

1. `AGENTS.md`
2. `docs/superpowers/specs/2026-08-12-access-deployment-rollout-design.md`
3. `docs/superpowers/plans/2026-08-12-access-cloud-run-program-roadmap.md`, especially `Global Constraints`, `Program Gates`, and `Agent Task Protocol`
4. `docs/superpowers/plans/2026-08-12-access-deployment-rollout-implementation.md`, from the exact heading `### Task OP-01: Retire Unsafe Automation and Close External Prerequisite Gates` through the separator immediately before OP-02
5. The current `.github/workflows/pages.yml` and each of the three deletion targets

Treat the approved specification and detailed task as authoritative. Do not broaden their scope.

## Exact allowed files

You may create only:

- `docs/operations/external-prerequisites.md`
- `docs/operations/workstation-inventory-template.md`
- `docs/operations/ownership-and-escalation.md`
- `docs/operations/environment-register-template.md`
- `docs/operations/github-environment-policy.md`
- `docs/operations/release-gates.md`
- `tests/unit/test_operations_prerequisites.py`
- `tests/unit/test_preimplementation_safety.py`

You may modify only:

- `.github/workflows/pages.yml`
- `tests/unit/test_deploy_config.py`

You are explicitly authorized to delete only these three tracked repository files:

- `.github/workflows/cloud-run.yml`
- `backend/scripts/deploy.sh`
- `scripts/merge_and_deploy.py`

No other deletion or destructive action is authorized. All files consumed from the specification, roadmap, and plan are read-only for this task.

## Locked interfaces and content contract

Implement the OP-01 interfaces exactly:

- Define gates `EXT-01` through `EXT-16`, with the exact required-evidence meanings and default `CLOSED` state in the plan.
- Define `EXT-08` as the preimplementation approval of the `.accde` trust mechanism and managed-signing service interface/policy without exported private key material. Do not require a signed .NET helper to exist before OP-09 builds it; actual signed helper/ACCDE, workstation-matrix, trusted-location/ACL, and endpoint-protection evidence are OP-09 release-readiness gates before signing or publication.
- Define workstation-class fields for Windows 11, Access/Microsoft 365 version/channel and bitness, Word, CPU architecture, display scale/resolution, Trust Center and macro policy, trusted location, proxy/firewall/TLS inspection, LocalAppData, endpoint protection, and supported/remediate/exclude decision.
- Define role-based ownership without personal names: business/system, technical/on-call, Access release/signing, database recovery, account/roster administration, security/incident, and records-retention authority.
- Define environment-isolation fields including Discovery Engine data store, WIF provider, Secret Manager namespace, projects/resources, database, queue, buckets, hostnames, identities, and audit separation.
- Define `CLOSED`, `READY_FOR_TEST`, and `READY_FOR_PRODUCTION` exactly as the plan states.
- Define the exact external GitHub environments: `test`, `production-plan`, `production-apply`, `production-deploy`, `production-rollback`, and `access-release`, with the exact workflows, WIF identities, reviewer counts, `refs/heads/main`, and `CLOSED` rows from the plan. Include `bootstrap-first-admin.yml` with WIF identity `admin-bootstrap` under `test` for test and under `production-deploy` for production; this does not create a seventh environment.
- Define EXT-12 evidence as the approved private request creation/hash, protected zero-account bootstrap, authorized PIN-custodian communication, and exact secret-version retrieval/disable/destruction procedure. Keep all operational identities, references, and completed evidence outside Git.
- Include exactly: `GitHub administrators configure these environments outside Terraform and repository workflows.`
- Include exactly: `Store completed records in the agency-approved system of record.`
- State that agents record only whether evidence was reviewed and never its contents. Repository documents contain no completed inventory, reviewer identity, owner name, project/resource identifier, certificate thumbprint, email address, secret, or real approval evidence.
- Reject self-review, fork pull requests, and ordinary pushes for credentialed environments.
- Pages must upload only `frontend/forms` at this stage while retaining its existing static validation and Pages deployment behavior.
- Do not add a replacement Cloud Run workflow; OP-08 owns that future protected path.

## TDD execution

1. Create the two tests exactly as specified in OP-01 Step 1, before changing workflow or documentation behavior.
2. Run the red test:

```powershell
python -m pytest tests/unit/test_operations_prerequisites.py tests/unit/test_preimplementation_safety.py -q
```

Expected red result: failure because the prerequisite documents do not exist, the three unsafe deployment files still exist, and Pages still publishes too broad a path. If it fails for an unrelated environment or collection problem, diagnose that first; do not claim the required red state.

3. Delete only the three explicitly authorized deployer files. Narrow `.github/workflows/pages.yml` to `frontend/forms` exactly. Replace the obsolete `test_cloud_run_deploy_stamps_the_source_commit` assertion in `tests/unit/test_deploy_config.py` with an assertion that the automatic Cloud Run workflow remains absent; do not remove or weaken the safety invariant. Create the six non-secret documents with all exact tables, phrases, gate states, and prohibitions from the plan.
4. Re-run the focused tests and require them to pass.
5. Run regressions:

```powershell
python -m pytest tests/unit/test_operations_prerequisites.py tests/unit/test_preimplementation_safety.py -q
python -m pytest -q
git diff --check
```

Expected green result: all tests pass; all three retired deployers are absent; Pages scope is static forms only; documentation contains no unfinished marker or operational identity/value.

## External gates and local-only boundary

This task creates templates and gate definitions; it does not close external gates. Leave every gate `CLOSED` unless evidence is separately supplied and reviewed outside Git. Do not create or configure GitHub environments, branch policies, reviewers, WIF, cloud resources, DNS, certificates, billing, notification channels, inventories, certificates, signing services, secrets, or owner records. Do not use cloud consoles or production/test credentials.

## Security and privacy

Use fictional examples only. Never add personal names, employee numbers, report or field-note text, inmate identifiers, PINs, tokens, project IDs, service-account identifiers, certificate details, email addresses, phone numbers, webhooks, secret values, or actual agency evidence. Preserve the Pages artifact boundary so backend, Access, infrastructure, release, tests, and operational material cannot be published.

## Forbidden scope and non-goals

- Do not implement identity, report, Access, Terraform, updater, or replacement deployment behavior.
- Do not refactor unrelated workflows, application code, tests, or documentation.
- Do not invent decisions to make a gate appear ready.
- Do not add GitHub providers or environment-creation automation.
- Do not change existing product behavior beyond the exact Pages path restriction and exact retirements.
- Do not push, merge, deploy, invoke workflows, apply Terraform, sign or publish artifacts, change secrets, access production/test cloud systems, or handle operational data.
- Do not run `git reset`, `git clean`, destructive checkout/restore commands, or any command that discards work.

Outside the three exact OP-01 deletions authorized above, do not perform any destructive action. Do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, or access production.

## Acceptance checklist

- [ ] Both failing tests were written first and their expected failure was observed.
- [ ] Only the exact allowed files changed.
- [ ] Only the three explicitly authorized files were deleted.
- [ ] `EXT-01` through `EXT-16` and all required evidence meanings are present.
- [ ] All six exact GitHub environment policy rows and required sentences are present.
- [ ] Workstation, ownership, environment, and release-state contracts are complete.
- [ ] No real operational record or identifying/sensitive value appears in Git.
- [ ] Pages publishes only `frontend/forms` and no replacement Cloud Run deployer exists.
- [ ] Focused tests, full pytest, and `git diff --check` pass.
- [ ] One commit uses the exact required message.

## Diff allowlist verification

Before committing, run:

```powershell
$allowed = @(
    'docs/operations/external-prerequisites.md'
    'docs/operations/workstation-inventory-template.md'
    'docs/operations/ownership-and-escalation.md'
    'docs/operations/environment-register-template.md'
    'docs/operations/github-environment-policy.md'
    'docs/operations/release-gates.md'
    'tests/unit/test_operations_prerequisites.py'
    'tests/unit/test_preimplementation_safety.py'
    '.github/workflows/pages.yml'
    'tests/unit/test_deploy_config.py'
    '.github/workflows/cloud-run.yml'
    'backend/scripts/deploy.sh'
    'scripts/merge_and_deploy.py'
)
$changed = @(
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
) | Sort-Object -Unique
$unexpected = $changed | Where-Object { $_ -notin $allowed -and $_ -notlike '.superpowers/*' }
if ($unexpected) { $unexpected; throw 'Changed-file allowlist violation.' }
git diff --name-status $TaskStart
git diff --check
```

Compare every path and status to the create/modify/delete lists above. Stop on any extra path. Inspect the complete diff for names, addresses, identifiers, secret-like values, completed evidence, and unfinished markers. Do not stage unrelated files.

Then commit only the allowed paths with the plan's exact staging pattern and message:

```powershell
git add -A -- $allowed
$staged = @(git diff --cached --name-only) | Sort-Object -Unique
$unexpectedStaged = $staged | Where-Object { $_ -notin $allowed }
if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
git diff --cached --name-status
git diff --cached --check
git commit -m "chore: gate implementation and deployment prerequisites"
```

After committing, run `git status --short`, `git show --stat --oneline HEAD`, and `git diff --name-status $TaskStart HEAD`. The committed task diff must still match the allowlist; unrelated pre-existing user changes must remain untouched.

## Handoff

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed; security/privacy and sensitive-data review results; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production.

Stop without committing if any required test cannot run, an unexpected file overlaps this task, exact content is ambiguous, a real identifier/evidence item is needed, or completion would require any prohibited action. Do not weaken a test or gate to force green.
