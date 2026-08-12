# Claude Code Prompt 042 — OP-10: Execute Pilot Readiness, Parallel Operation, DR, Rollback, Runbooks, and General-Rollout Controls

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **042**, task **OP-10: Execute Pilot Readiness, Parallel Operation, DR, Rollback, Runbooks, and General-Rollout Controls**.

## Objective, outcome, and rationale

Make pilot entry/exit, parallel fallback, recovery exercises, compatibility, acceptance, general rollout, and legacy restriction explicit, machine-checkable, reversible, and owned. This implementation creates safe schemas, validators, fictional/manual scenarios, Terraform configuration, templates, guides, and runbooks. It does **not** start a pilot, use operational data, execute recovery/deployment, change production legacy mode, or record actual approvals.

## Repository, baseline, branch, and preflight

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Anchor baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-10-pilot-dr-rollout`
- Commit: `docs: define pilot recovery and general rollout gates`

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The anchor must be an ancestor of current reviewed `main`. Inspect `git log --oneline $TaskBase..HEAD`, all predecessor handoffs/reviews, and verify OP-01 through OP-09 and every ID/RP/AC/AD acceptance interface are present and reviewed. Verify safe `/api/v1/admin/health`, exact legacy-mode contract, current/prior manifests, and testable backup/rollback interfaces. Branch from current `HEAD` with `git switch -c claude/op-10-pilot-dr-rollout`. Stop on failed ancestry/review/prerequisites, conflict, existing branch, or overlapping/unsafe dirty work. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; all six approved specs; roadmap global constraints/wire contracts/version projection/program gates/task order/agent protocol/completion definition; every OP-01–OP-09 operational output; ID/RP/AC/AD acceptance requirements; current release-gates, health/legacy behavior, Terraform serverless/version inputs; and the detailed plan from the exact OP-10 heading through `## Completion Gate`.

## Exact allowed files

Create only:

- `release/acceptance.schema.json`
- `scripts/operations/verify_release_gates.py`
- `scripts/operations/create_safe_acceptance_record.py`
- `tests/unit/test_rollout_runbooks.py`
- `tests/unit/test_release_gate_verifier.py`
- `tests/manual/access-acceptance-scenarios.md`
- `docs/operations/pilot-register-template.md`
- `docs/operations/release-acceptance-template.md`
- `docs/operations/rollback-compatibility-matrix.md`
- `docs/operations/change-log.md`
- `docs/runbooks/pilot-parallel-operation.md`
- `docs/runbooks/ai-policy-outage.md`
- `docs/runbooks/security-incident-response.md`
- `docs/runbooks/account-onboarding-offboarding.md`
- `docs/runbooks/data-retention-export-printing.md`
- `docs/runbooks/general-rollout-and-legacy-restriction.md`
- `docs/user-guides/access-quick-start.md`
- `docs/user-guides/admin-quick-reference.md`

Modify only:

- `docs/operations/release-gates.md`
- `infra/terraform/modules/access_platform/variables.tf`
- `infra/terraform/modules/access_platform/serverless.tf`
- `infra/terraform/environments/test/main.tf`
- `infra/terraform/environments/production/main.tf`
- `infra/terraform/tests/access_platform.tftest.hcl`

No deletion is authorized. Release manifests/descriptors, external evidence, application routes, Access code, and earlier runbooks are consume-only.

## Locked interfaces and operational contract

- Acceptance states exactly `not_ready`, `pilot_approved`, `pilot_accepted`, `general_rollout_approved`.
- Acceptance schema contains identifiers/references only: descriptor/manifest hashes, gate IDs/statuses, evidence references, owner roles, timestamps, achieved RPO/RTO, accepted client/API/worker/schema versions, external approval references. Reject names, free-form incident narratives, report content, employee IDs, PINs, tokens, signatures, and contacts.
- `verify_release_gates.py` validates schema and every OP/ID/RP/AC/AD gate, freshness relative to candidate/latest change, and exact compatibility-matrix membership; output is only state and failing gate IDs. `create_safe_acceptance_record.py` creates fictional local template or validates safe references and never queries production.
- Pilot is exactly 5–10 employees and two administrators for two to four weeks. Fictional tests precede real operations; operational data waits for externally recorded approvals/training/security/records review.
- All 12 manual acceptance scenarios in OP-10 Step 4 must be complete with fictional steps/outcomes, keyboard-only, high contrast, supported display scales, approved officer terms.
- Parallel-operation runbook has entry/exit gates, training/external support, safe daily health, severity, request-ID-only feedback. Legacy web is marked fallback and does not create separate ordinary-report history; no automatic historical Word import.
- AI/policy outage preserves manual editing, cloud saves, saved-work access, resumable jobs, truthful status, controlled retry/cost, search checks.
- Incident runbook covers classification, containment, authorized revocation, evidence preservation, audit, legal/records notice, recovery/postmortem without report content in tickets/alerts.
- Account runbook includes approved identity, one-time temporary PIN channel, first change, roles, deactivation/revocation, last-active-Admin, stable history.
- Records runbook includes indefinite fail-safe retention until approved schedule, no permanent delete, controlled export/print/on-demand Word, DPAPI recovery, seven-day orphan cleanup, no credentials in Access.
- Compatibility matrix has one reviewed row per allowed exact client/API/worker/API-version/Alembic/legacy-mode combination; no wildcard. Each row says read/write, schema, migration head, legacy mode, verification. Decision order client/API/worker/coordinated. Targets: client rollback 30 minutes, service recovery four hours, DB RPO at most five minutes.
- Terraform input `legacy_report_mode` allows only `pilot_fallback` or `restricted`, maps to `LEGACY_REPORT_MODE`; test is `pilot_fallback`; production remains `pilot_fallback` until a separate reviewed production plan after written approval. RP-10 owns route enforcement.
- General rollout requires signed package through agency IT/narrow trusted location, activation groups, PIN training, monitored versions/support. After acceptance, ordinary shared-code writes are restricted while approved health/Review Lab remains. Re-enabling shared-code writes requires incident commander risk acceptance and protected approval.
- `READY_FOR_PRODUCTION` requires acceptance verifier success. Guides/change log/templates contain only safe summaries and external references.
- Recovery never runs production Alembic downgrade; never deletes/overwrites report, revision, audit, job, export metadata/data; never selects a release combination absent from matrix.

## TDD and local verification

1. Write `tests/unit/test_rollout_runbooks.py` exactly from OP-10 Step 1 and `test_release_gate_verifier.py` with a complete fictional record plus parametrized missing/failed gates before implementation.
2. Run:

```powershell
python -m pytest tests/unit/test_rollout_runbooks.py tests/unit/test_release_gate_verifier.py -q
```

Expected red: runbooks/verifier absent. Do not count unrelated collection or prerequisite failure.
3. Implement schema/scripts, 12 scenarios, templates/runbooks/guides/matrix/change log/release gate, Terraform mode and mocked assertions in plan order.
4. Run:

```powershell
python -m json.tool release/acceptance.schema.json | Out-Null
python -m pytest tests/unit/test_rollout_runbooks.py tests/unit/test_release_gate_verifier.py -q
python scripts/operations/verify_release_gates.py --fixture fictional-general-rollout
python -m pytest tests/unit tests/integration tests/contract tests/security -q
python scripts/ci/check_sensitive_output.py --paths release docs/operations docs/runbooks docs/user-guides tests/manual
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/test init -backend=false
terraform -chdir=infra/terraform/environments/test validate
terraform -chdir=infra/terraform/environments/test test -test-directory=../../tests
dotnet test access-updater/SLUT.AccessUpdater.sln --configuration Release
git diff --check
```

Expected: fictional general-rollout passes; every negative gate fixture fails closed; backend/Terraform/updater checks pass; no cloud, Access COM, signing, migration, deploy, traffic, restore, or operational-data action occurs.

## External gates and absolute non-execution boundary

Actual workstation/roster/training/security/records/support/cost/performance evidence, participant/admin identities, restore/rollback exercise evidence, owner approvals, signatures, change windows, pilot authorization/acceptance, and general-rollout approval remain outside Git. Templates record external references only. Do not start/exit a pilot, contact participants, use real data, execute training, restore, rollback, migration, deploy, package distribution, traffic shift, mode change, incident response, or general rollout. Do not run cloud/Access COM commands. Production `legacy_report_mode` stays `pilot_fallback` in code/config until separately approved workflow execution; this task does not apply it.

## Security/privacy and non-goals

No personal name, employee ID, real incident, PIN/token, support address, approval signature, operational narrative, report/field-note content, certificate, or production identifier may enter Git/output. Do not implement missing predecessor features, alter route enforcement, choose real compatibility rows without reviewed releases, or manufacture evidence. Do not push, merge, deploy, dispatch workflows, run Terraform plan/apply/destroy, migrate, restore, roll back, change traffic, sign, publish, change secrets, access production/cloud/data, or perform destructive Git/filesystem actions.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Expected red tests observed first.
- [ ] Strict safe acceptance schema and fail-closed verifier cover every program gate/freshness/matrix check.
- [ ] All 12 fictional acceptance scenarios and accessibility dimensions are complete.
- [ ] Pilot bounds/duration/entry/exit/parallel fallback are exact.
- [ ] Outage, incident, account, records, rollout, User, and Admin guidance is complete and non-sensitive.
- [ ] Compatibility rows are exact/no wildcard and recovery targets/destructive prohibitions explicit.
- [ ] Terraform legacy mode is closed to two values and remains fallback pending separate approval.
- [ ] `READY_FOR_PRODUCTION` requires verifier; no actual evidence/signature/data is in Git.
- [ ] Full local program suite passes without operational action.
- [ ] Only exact allowed files changed and exact one-commit message used.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; run the sensitive-output scanner and manually inspect task changes for people/employee IDs/incidents/PINs/tokens/contacts/signatures/real approvals, wildcards, destructive recovery, or premature `restricted`. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'release/acceptance.schema.json'
    'scripts/operations/verify_release_gates.py'
    'scripts/operations/create_safe_acceptance_record.py'
    'tests/unit/test_rollout_runbooks.py'
    'tests/unit/test_release_gate_verifier.py'
    'tests/manual/access-acceptance-scenarios.md'
    'docs/operations/pilot-register-template.md'
    'docs/operations/release-acceptance-template.md'
    'docs/operations/rollback-compatibility-matrix.md'
    'docs/operations/change-log.md'
    'docs/runbooks/pilot-parallel-operation.md'
    'docs/runbooks/ai-policy-outage.md'
    'docs/runbooks/security-incident-response.md'
    'docs/runbooks/account-onboarding-offboarding.md'
    'docs/runbooks/data-retention-export-printing.md'
    'docs/runbooks/general-rollout-and-legacy-restriction.md'
    'docs/user-guides/access-quick-start.md'
    'docs/user-guides/admin-quick-reference.md'
    'docs/operations/release-gates.md'
    'infra/terraform/modules/access_platform/variables.tf'
    'infra/terraform/modules/access_platform/serverless.tf'
    'infra/terraform/environments/test/main.tf'
    'infra/terraform/environments/production/main.tf'
    'infra/terraform/tests/access_platform.tftest.hcl'
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
git add -A -- $allowed
$staged = @(git diff --cached --name-only) | Sort-Object -Unique
$unexpectedStaged = $staged | Where-Object { $_ -notin $allowed }
if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
git diff --cached --name-status
git diff --cached --check
git commit -m "docs: define pilot recovery and general rollout gates"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results, including negative-gate coverage; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including acceptance states/schema safe fields, 12-scenario coverage, and compatibility/legacy controls; security/privacy and sensitive-scan results; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production, including no pilot, COM, recovery, or mode change. Independent specification review precedes code-quality review.

Stop without committing if any predecessor acceptance interface is absent, a Critical/High or data-loss issue is open, a compatibility row lacks evidence, a real value/approval would be needed, safe verification cannot avoid content, or any prohibited action is required. Never mark a gate ready or change production mode merely to complete code.
