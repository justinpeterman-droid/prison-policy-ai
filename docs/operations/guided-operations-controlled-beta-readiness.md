# Guided Operations Controlled Beta Readiness

**Status:** Merged repository candidate ready for external beta qualification; the controlled beta remains a no-go while the external stop gates below are open.
**Evidence date:** 2026-08-20
**Candidate:** reviewed `origin/main` commit `8021820bd49ed980871d8ff7a86a05515ac25203` (tree `3c45581dc27a5b87860c4b8946ee00d259fa022d`). Repository owner `justinpeterman-droid` squash-merged PR #108 at 2026-08-20 19:21 UTC. The merge tree is byte-for-byte identical to the PR's 21-check source head `960944ae3abfe6acd2adfb4b5f4fdeba8f645944`; runtime source candidate `0e1bd6b` supplies the exact four-job Foundation evidence described below.

## Proven in the repository

- Sections 3 through 5 of the website completion checklist are implemented with approved daily, empty weekly, and monthly paperwork behavior.
- The production React build is served through the Cloud Run image's same-origin static path. CI builds the image without pushing or deploying it.
- PostgreSQL 17 integration and migration upgrade/downgrade/upgrade checks pass in both supported Python release-gate jobs.
- Local backend evidence is 1,440 passing tests with 30 intentional skips, plus 41 explicit contract/security tests.
- Local frontend evidence is 181 passing component tests across 46 files, TypeScript, the production Vite build, and 128 passing Chromium workflows with one feature-detected skip.
- The exact `0e1bd6b` Foundation run passes browser API security/contracts, the reviewed frontend artifact, the Cloud Run image build, and two production-bundle browser smokes against Gunicorn and PostgreSQL 17. Those smokes use real cookie sessions and fictional records to verify dated incident creation, revisioned report persistence, packet rebuild, print invocation, DOCX download, count-sheet persistence/preview, administrator elevation and Paperwork Center access, logout, and the approved legacy `pilot_fallback` banner.
- Forty-eight committed Windows baselines cover Home states and viewports, every primary officer route on desktop and mobile, every administrator route on desktop, mobile administrator navigation, display scaling, and the missing count/monthly/incident print references.
- Print references use fictional data only. The incident form keeps an unknown value visibly `Not entered`, and print CSS removes application navigation and preview controls.
- The count-sheet API kind boundary is enforced on reads, saves, revisions, restores, actions, and idempotent replays; PostgreSQL integration coverage proves a non-elevated administrator cannot use count-sheet routes to access a daily record.
- Legacy browser and Microsoft Access fallback behavior remains available. This milestone does not retire, redirect, or mutate either legacy surface.
- Exact PR head `960944a` passed all 21 repository and third-party checks with no unresolved review threads before the repository owner merged it. The resulting `8021820` main tree is identical; its Unit Tests and CodeQL push runs are green.
- A post-merge local browser check served the reviewed main bundle through Flask against an isolated PostgreSQL 17 database and fictional accounts. Officer sign-in rendered the data-backed Home at 1536×1024, Quick Access navigated to Policy Expert, and the current origin produced no browser console warnings or errors. This spot-check supplements rather than replaces the complete automated suite.

## Sections 3–9 completion audit

| Checklist section | Repository-owned beta-critical result | Work that remains outside repository authority |
| --- | --- | --- |
| 3. Daily Paperwork Center | Complete: six revisioned daily workflows, print surfaces, fictional fixtures, API/contract/security coverage, and PostgreSQL verification. | Target-environment database, migration, account, browser/printer, and operator acceptance evidence. |
| 4. Weekly Paperwork Library | Complete for the approved beta scope: the library has an honest empty state and does not invent unapproved weekly forms. | Approved weekly source forms and retention/ownership decisions before adding content. |
| 5. Monthly Paperwork Library | Complete: approved monthly templates, variants, packet ordering/preview/print, non-persistence boundary, and regressions. | Supported browser/printer/PDF-driver comparison in the intended beta environment. |
| 6. Site-Wide Visual Polish | Complete for implemented, approved surfaces: production data remains authoritative; unapproved notification, service-health, checklist, activity, avatar, support, quote, and timestamp proposals remain excluded. Automated responsive, keyboard, contrast, focus, motion, and route coverage is recorded. | Manual screen-reader, native on-screen-keyboard, physical high-contrast/scaling, performance p75, generated-asset approval, and owner acceptance. |
| 7. Print and Visual Regression | Complete repository coverage: 48 fictional Windows baselines and required screen/print references pass. | Human comparison of browser print preview with downloaded/generated output across the approved browser and printer/PDF-driver matrix. |
| 8. Testing and Release Gate | Complete for the merged source tree: frontend, backend, contract, security, PostgreSQL 17, migration lifecycle, desktop/mobile/reduced-motion, image build, and production-session smoke evidence is green. | Every required exact-main external check and owner record must be green; the legacy Pages activation failure described below currently prevents go. |
| 9. Deployment and Pilot | Repository build, release gates, rollback, support, and training artifacts are complete. No deployment, secret, database, traffic, DNS, signing, or legacy-retirement state was mutated by this milestone. | All controlled-environment configuration, smoke, cohort, feedback, support ownership, and explicit beta approval actions below. |

## External stop gates

Do not begin the controlled beta until an authorized owner records evidence for every applicable row.

| Gate | Required evidence | Owner action |
| --- | --- | --- |
| Target database | PostgreSQL 17 identity, backup/restore readiness, connection policy, and capacity are verified in the intended beta environment. | Platform/database owner |
| Migration | The reviewed image digest and Alembic head are captured; controlled migration and verification jobs succeed against the beta database. | Protected deployment workflow plus approver |
| Browser sessions | Production-grade browser-session secrets and secure cookie/origin settings are configured without exposing values in tickets, logs, or this repository. | Security/platform owner |
| AI credentials | Vertex ADC and service identities are configured and Policy Expert plus incident AI flows pass with approved cloud services and fictional test records. | AI/platform owner |
| Legacy access | Any enabled legacy routes use secure non-empty settings and remain in the approved `pilot_fallback` mode. No normal-user cutover is part of this beta gate. | Application owner |
| Legacy static browser hosting | The GitHub Pages site/environment is enabled through an authorized repository setting and a reviewed `frontend/forms` deployment succeeds. Exact-main run `32408199092` currently fails at Pages configuration because the integration cannot create/enable the site; do not bypass this by publishing a different surface. | Repository/Pages owner |
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

The candidate is a **no-go** if any external stop gate is missing, if a required exact-candidate check fails, if rollback ownership is unavailable, or if test execution would require production data. The current exact-main GitHub Pages configuration failure therefore remains a no-go condition until an authorized owner enables the legacy site and records a successful reviewed run. Repository test success is necessary but does not authorize cloud mutation, database migration, secret configuration, pilot enrollment, traffic changes, or legacy retirement.
