# Guided Operations Controlled Beta Readiness

**Status:** Repository candidate ready for external beta qualification; rollout is not authorized by this document.
**Evidence date:** 2026-08-20
**Candidate:** PR #108, `feat/daily-paperwork-center`; source candidate `f6f23c1` is locally verified and remains subject to the exact final PR gate. Capture the final reviewed commit or merge SHA in the external approval record.

## Proven in the repository

- Sections 3 through 5 of the website completion checklist are implemented with approved daily, empty weekly, and monthly paperwork behavior.
- The production React build is served through the Cloud Run image's same-origin static path. CI builds the image without pushing or deploying it.
- PostgreSQL 17 integration and migration upgrade/downgrade/upgrade checks pass in both supported Python release-gate jobs.
- Local backend evidence is 1,440 passing tests with 30 intentional skips, plus 41 explicit contract/security tests.
- Local frontend evidence is 169 passing component tests, TypeScript, the production Vite build, and 121 passing Chromium workflows with one feature-detected skip.
- Forty-eight committed Windows baselines cover Home states and viewports, every primary officer route on desktop and mobile, every administrator route on desktop, mobile administrator navigation, display scaling, and the missing count/monthly/incident print references.
- Print references use fictional data only. The incident form keeps an unknown value visibly `Not entered`, and print CSS removes application navigation and preview controls.
- The count-sheet API kind boundary is enforced on reads, saves, revisions, restores, actions, and idempotent replays; PostgreSQL integration coverage proves a non-elevated administrator cannot use count-sheet routes to access a daily record.
- Legacy browser and Microsoft Access fallback behavior remains available. This milestone does not retire, redirect, or mutate either legacy surface.
- Predecessor `2249940` passed the complete PR check set, including PostgreSQL, browser, Windows visual, container, CodeQL, Codacy, and independent security-review jobs. Follow-on source candidate `f6f23c1` must pass the exact final PR gate before merge or beta qualification.

## External stop gates

Do not begin the controlled beta until an authorized owner records evidence for every applicable row.

| Gate | Required evidence | Owner action |
| --- | --- | --- |
| Target database | PostgreSQL 17 identity, backup/restore readiness, connection policy, and capacity are verified in the intended beta environment. | Platform/database owner |
| Migration | The reviewed image digest and Alembic head are captured; controlled migration and verification jobs succeed against the beta database. | Protected deployment workflow plus approver |
| Browser sessions | Production-grade browser-session secrets and secure cookie/origin settings are configured without exposing values in tickets, logs, or this repository. | Security/platform owner |
| AI credentials | Vertex ADC and service identities are configured and Policy Expert plus incident AI flows pass with approved cloud services and fictional test records. | AI/platform owner |
| Legacy access | Any enabled legacy routes use secure non-empty settings and remain in the approved `pilot_fallback` mode. No normal-user cutover is part of this beta gate. | Application owner |
| Accounts | Initial administrator bootstrap, staff provisioning, sign-in, forced PIN change, logout, and session revocation are verified through protected procedures. | Identity owner and pilot administrator |
| Supported browsers | Browser print preview is compared with generated/downloaded output for the supported browser and printer/PDF-driver matrix. | QA/records owner |
| Accessibility | Manual keyboard and screen-reader pass, physical Windows high-contrast review, native on-screen-keyboard review, and owner acceptance are recorded. | Accessibility/QA owner |
| Performance/assets | Production p75 LCP/CLS/INP evidence and final generated-asset usage approval are recorded. | Product/platform owner |
| Parallel operation | The React site is exercised beside the legacy browser experience, and the Access client remains available throughout the pilot. | Operations owner |
| Pilot cohort | A limited fictional or explicitly approved participant list, support contact, training acknowledgment, feedback channel, and stop criteria are recorded. | Product/operations owner |
| Release approval | Current commit checks are green, review threads are resolved, and the repository owner explicitly approves the controlled beta. | Repository owner |

## Required runbooks and guides

- Release criteria: [Guided Operations release gates](guided-operations-release-gates.md)
- Pilot sequence: [Guided Operations web pilot](../runbooks/guided-operations-web-pilot.md)
- Configuration-only UI rollback: [Guided Operations web rollback](../runbooks/guided-operations-web-rollback.md)
- Officer training: [Officer quick start](../user-guides/guided-operations-officer-quick-start.md)
- Administrator training: [Administrator quick start](../user-guides/guided-operations-admin-quick-start.md)

## Go/no-go rule

The candidate is a **no-go** if any external stop gate is missing, if a release-gate check fails on the exact candidate commit, if rollback ownership is unavailable, or if test execution would require production data. Repository test success is necessary but does not authorize cloud mutation, database migration, secret configuration, pilot enrollment, traffic changes, or legacy retirement.
