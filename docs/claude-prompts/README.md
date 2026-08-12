# Claude Code Task Prompt Pack: Access + Cloud Run

This directory turns the approved Access + Cloud Run program into 42 independently reviewable Claude Code assignments. The binding planning baseline is commit `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`.

## How to use this pack

1. Start with task 001 and follow the sequence unless a prompt's prerequisites explicitly remain unavailable.
2. Give Claude Code exactly one file from `docs/claude-prompts/tasks/` in a fresh task context.
3. Begin from the current reviewed `main`. The baseline commit above must be an ancestor. If `main` has advanced, read every intervening reviewed change to the approved specifications, roadmap, implementation plans, and prior task outputs before creating the task branch.
4. Do not begin a dependent task until the preceding task has its required focused tests, regressions, specification-compliance review, and code-quality review.
5. Keep each task to one focused commit with the exact commit message in its prompt.
6. Treat every external gate as real. A local implementation or green dry run does not authorize cloud access, deployment, signing, artifact publication, production data, secret changes, or rollout.
7. After Claude returns its handoff, compare the changed paths to the prompt's allowlist before reviewing the code.

Never ask Claude Code to work directly on production, push, merge, deploy, apply Terraform, invoke cloud migration jobs, shift traffic, sign, publish, change secrets, or access real report/personnel data. Those actions remain separately authorized human/workflow operations even when a task creates the code or runbook for them.

## Binding documents

- `docs/superpowers/specs/2026-08-12-access-cloud-run-master-design.md`
- `docs/superpowers/specs/2026-08-12-cloud-identity-foundation-design.md`
- `docs/superpowers/specs/2026-08-12-report-storage-api-design.md`
- `docs/superpowers/specs/2026-08-12-access-user-client-design.md`
- `docs/superpowers/specs/2026-08-12-access-admin-client-design.md`
- `docs/superpowers/specs/2026-08-12-access-deployment-rollout-design.md`
- `docs/superpowers/plans/2026-08-12-access-cloud-run-program-roadmap.md`
- `docs/superpowers/plans/2026-08-12-cloud-identity-foundation-implementation.md`
- `docs/superpowers/plans/2026-08-12-report-storage-api-implementation.md`
- `docs/superpowers/plans/2026-08-12-access-user-client-implementation.md`
- `docs/superpowers/plans/2026-08-12-access-admin-client-implementation.md`
- `docs/superpowers/plans/2026-08-12-access-deployment-rollout-implementation.md`

The detailed task section is the executable source of truth. The roadmap's locked cross-client wire contracts, stable errors, and canonical version projection override an accidental stale example elsewhere; any genuine contradiction is a stop condition that must return to plan review.

For staging and committing, the assigned task prompt's exact `$allowed` array, union-based dirty-path check, `git add -A -- $allowed`, staged-path revalidation, and cached whitespace check are authoritative. Any broader `git add` example remaining in a detailed plan is non-executable legacy shorthand and is replaced by the prompt block; never execute both.

## Sequence and dependencies

| Seq. | Task | Prompt | Depends on |
|---:|---|---|---|
| 001 | OP-01 | `tasks/001-op-01-retire-unsafe-automation.md` | Approved plans |
| 002 | ID-01 | `tasks/002-id-01-database-foundation.md` | OP-01 safety invariant |
| 003 | ID-02 | `tasks/003-id-02-api-v1-contract.md` | ID-01 |
| 004 | ID-03 | `tasks/004-id-03-identity-schema-roster-import.md` | ID-01–ID-02 |
| 005 | ID-04 | `tasks/005-id-04-pin-account-lockout.md` | ID-03 |
| 006 | ID-05 | `tasks/006-id-05-opaque-sessions.md` | ID-02–ID-04 |
| 007 | ID-06 | `tasks/007-id-06-bearer-audit-idempotency.md` | ID-03–ID-05 |
| 008 | ID-07 | `tasks/008-id-07-admin-identity-apis.md` | ID-04–ID-06 |
| 009 | ID-08 | `tasks/009-id-08-browser-handoff-security.md` | ID-03–ID-07 |
| 010 | RP-01 | `tasks/010-rp-01-report-persistence.md` | ID-01–ID-08 |
| 011 | RP-02 | `tasks/011-rp-02-content-revisions.md` | RP-01 |
| 012 | RP-03 | `tasks/012-rp-03-engine-adapters-incidents.md` | RP-01–RP-02 |
| 013 | RP-04 | `tasks/013-rp-04-user-report-api.md` | RP-01–RP-03 |
| 014 | RP-05 | `tasks/014-rp-05-admin-report-api.md` | RP-01–RP-04, ID-07 |
| 015 | RP-06 | `tasks/015-rp-06-ai-jobs-outbox.md` | RP-01–RP-05, ID-06 |
| 016 | RP-07 | `tasks/016-rp-07-private-worker-dispatcher.md` | RP-06 |
| 017 | RP-08 | `tasks/017-rp-08-policy-expert-api.md` | ID-06, RP API foundation |
| 018 | RP-09 | `tasks/018-rp-09-word-exports.md` | RP-02, RP-04–RP-05 |
| 019 | RP-10 | `tasks/019-rp-10-operations-and-legacy-controls.md` | ID/RP tasks 001–018 |
| 020 | OP-02 | `tasks/020-op-02-terraform-bootstrap.md` | OP-01, backend contracts |
| 021 | OP-03 | `tasks/021-op-03-network-sql-identities.md` | OP-02 |
| 022 | OP-04 | `tasks/022-op-04-serverless-edge-storage.md` | OP-03, RP-07 |
| 023 | OP-05 | `tasks/023-op-05-monitoring-backup-budgets.md` | OP-03–OP-04 |
| 024 | OP-06 | `tasks/024-op-06-migration-roster-jobs.md` | OP-03–OP-04, identity migrations |
| 025 | OP-07 | `tasks/025-op-07-quality-supply-chain-gates.md` | Backend and OP-01 safety |
| 026 | OP-08 | `tasks/026-op-08-controlled-delivery-workflows.md` | OP-01–OP-07 |
| 027 | AC-01 | `tasks/027-ac-01-access-source-build-harness.md` | Stable OpenAPI, test workstation |
| 028 | AC-02 | `tasks/028-ac-02-access-api-core.md` | AC-01 |
| 029 | AC-03 | `tasks/029-ac-03-access-auth-dpapi.md` | AC-02, identity API |
| 030 | AC-04 | `tasks/030-ac-04-access-shell-client-policy.md` | AC-03 |
| 031 | AC-05 | `tasks/031-ac-05-report-workflow-foundation.md` | AC-04, report API |
| 032 | AC-06 | `tasks/032-ac-06-access-ai-jobs.md` | AC-05, RP-06–RP-07 |
| 033 | AC-07 | `tasks/033-ac-07-access-editor-recovery.md` | AC-05–AC-06, RP-04 |
| 034 | AC-08 | `tasks/034-ac-08-history-policy-account.md` | AC-03–AC-07, RP-08 |
| 035 | AC-09 | `tasks/035-ac-09-word-accessibility-windows.md` | AC-01–AC-08, RP-09 |
| 036 | AD-01 | `tasks/036-ad-01-admin-navigation-elevation.md` | AC-09, ID-07, RP-10 |
| 037 | AD-02 | `tasks/037-ad-02-admin-accounts-staff.md` | AD-01, ID-07 |
| 038 | AD-03 | `tasks/038-ad-03-admin-report-oversight.md` | AD-01–AD-02, RP-05/RP-09 |
| 039 | AD-04 | `tasks/039-ad-04-admin-audit-health.md` | AD-01, RP-10 |
| 040 | AD-05 | `tasks/040-ad-05-review-lab-windows-regression.md` | AD-01–AD-04, ID-08 |
| 041 | OP-09 | `tasks/041-op-09-signed-access-release-updater.md` | OP-01–OP-08, AC/AD acceptance |
| 042 | OP-10 | `tasks/042-op-10-pilot-dr-rollout-controls.md` | Every preceding task and external approvals |

## Review protocol

Review each task in two passes:

1. Specification compliance: exact files, interfaces, authorization, privacy, tests, and non-goals.
2. Code quality: clarity, maintainability, error handling, test strength, and unnecessary scope.

A dependent task starts only after both reviews pass. If a prompt and the reviewed current plans disagree, stop—do not let the worker choose a new contract during implementation.

## Required handoff fields

Every task response must include:

- task ID and branch;
- commit SHA and exact commit message;
- changed/deleted files;
- red-phase evidence;
- focused and regression commands with exit results;
- `git diff --check` result and changed-file allowlist result;
- interfaces produced or consumed;
- security/privacy checks;
- assumptions, risks, and remaining external gates;
- explicit confirmation that nothing was pushed, merged, deployed, applied, signed, published, or run against production.
