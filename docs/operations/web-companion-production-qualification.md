# Web Companion Production Qualification

**Status:** Repository candidate in preparation. This document records local,
fictional qualification evidence; it does not authorize cloud deployment,
production data access, roster import, secret changes, traffic changes, or
legacy retirement.

**Scope:** Guided Operations as a web companion to the existing Flask/Jinja and
Microsoft Access experiences. The companion release keeps both existing
surfaces available and leaves `LEGACY_REPORT_MODE=pilot_fallback` until an
authorized owner approves a later cutover.

## Candidate identity

Record these values from the protected delivery workflow after the readiness
change is reviewed and merged:

- source commit: `PENDING`
- reviewed container digest: `PENDING`
- Alembic head: `20260820_0011`
- release version and notes: `PENDING`
- protected workflow run: `PENDING`

Do not substitute a mutable branch name, local image tag, or latest successful
run for these immutable identifiers.

## Repository qualification evidence

The isolated readiness worktree was based on `origin/main` commit
`82f923680521d53112321e464962c6ea462a0f5b` on 2026-08-20. All records used
fictional data and loopback-only PostgreSQL 17.10.

| Check | Result |
| --- | --- |
| Backend unit suite | 1,440 passed; 30 intentional skips |
| Explicit contract suite | 33 passed |
| Explicit security suite | 8 passed |
| PostgreSQL 17 integration suite | 341 passed; 1 intentional skip |
| Alembic lifecycle | upgrade to head, downgrade to base, and upgrade to head passed |
| Frontend component suite | 181 passed across 46 files |
| Frontend type-check and production build | passed |
| Desktop/mobile/accessibility/visual Playwright gate | 128 passed; 1 feature-detected skip |
| Production image build | passed |
| Production-bundle smoke | 2 passed against the Linux image, PostgreSQL 17, real cookie sessions, and fictional records |

The frontend dependency graph is committed in `frontend/web/package-lock.json`.
Docker, CI, and documented clean installs use `npm ci`, and direct frontend
dependencies are pinned to the versions exercised by this evidence.

## Protected target-environment gates

Every row remains a stop gate until its owner records a safe evidence reference
in the agency-approved system of record. Never put secret values, real employee
identities, completed paperwork, or operational narratives in this repository.

| Gate | Required safe evidence | Owner |
| --- | --- | --- |
| Candidate | Exact source commit, image digest, Alembic head, and green protected workflow run agree | Release owner |
| Cloud boundary | Approved project, region, billing, quotas, VPC, ingress, DNS, and TLS are isolated from test | Platform owner |
| Database | Target is PostgreSQL 17; backup, PITR, capacity, private connectivity, and restore ownership are verified | Database owner |
| Migration | Pre-migration backup reference, reviewed image digest, controlled migration result, and post-migration revision are recorded | Database and release owners |
| Secrets | Browser-session, identity, cursor, legacy-access, and administrator secrets are populated and rotation ownership is assigned | Security owner |
| AI services | Approved Vertex identities and services pass Policy Expert and incident AI checks with fictional records | AI/platform owner |
| Accounts | First administrator bootstrap, approved staff provisioning, forced PIN change, logout, and session revocation pass | Identity owner |
| Legacy companion | Legacy routes use a secure non-empty setting and approved `pilot_fallback`; Access remains available | Application owner |
| Browser and print | Supported browsers, printers, and PDF drivers match reviewed screen, print-preview, and download output | QA/records owner |
| Accessibility | Manual keyboard, screen reader, Windows high contrast, display scaling, and on-screen keyboard checks pass | Accessibility owner |
| Operations | Monitoring, alerting, budgets, backup restore, rollback, support contact, and stop criteria are exercised | Operations owner |
| Approval | Pilot cohort, training acknowledgment, feedback route, current checks, and explicit beta approval are recorded | Product and repository owners |

## Qualification order

1. Merge only reviewed repository-readiness changes into protected `main`.
2. Build the image once in the protected workflow and promote by digest.
3. Provision or reconcile the isolated target environment without shifting traffic.
4. Populate secrets through the approved secret-management procedure.
5. Capture a backup, run the protected migration job, and verify Alembic head.
6. Bootstrap only the approved first administrator and pilot roster.
7. Run fictional production smoke checks for authentication, reports, paperwork,
   Policy Expert, incident AI, printing, downloads, audit, and session revocation.
8. Exercise rollback and database restore procedures.
9. Complete manual browser, print, accessibility, and performance acceptance.
10. Record explicit controlled-beta approval before enrolling the pilot cohort.

## No-go conditions

The web companion remains a no-go if an immutable candidate identifier is
missing, an exact-candidate check is red, PostgreSQL is not version 17, a secret
or roster action lacks an authorized owner, AI is not qualified, rollback or
restore ownership is unavailable, real operational data would be needed for a
test, or either companion surface would be retired as part of the change.
