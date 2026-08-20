# Guided Operations Release Gates

This is a readiness checklist, not deployment authority. Gate state and completed
evidence belong in the agency-approved system of record; never commit identities,
production values, source workbooks, or completed operational paperwork.

## Required before a release candidate

- all automated suites pass twice, from clean checkouts;
- approved concept fidelity is complete;
- all print regressions pass;
- accessibility checks pass;
- test and production configuration are isolated;
- database migration backup and rollback readiness are documented;
- pilot acceptance is signed off;
- WEB_APP_MODE remains preview until explicit primary approval; and
- no source workbook or real identity exists in the image or repository.

The release owner records the evidence references, approves any progression to
`primary`, and coordinates production work. A passing CI run alone never changes
traffic, data, identities, or legacy ownership.

## Image review

The production image must contain the built Vite assets, approved templates, and
migrations. It must not contain `frontend/web/node_modules`, browser test output,
screenshots carrying operational information, uploaded `.xls` or `.xlsx` files,
or workbook previews. Review this alongside the Docker build before any pilot.

## Decision record

Until every item above has externally reviewed evidence, the release gate is
`CLOSED`. Test-only readiness may be recorded as `READY_FOR_TEST`; production
readiness may be recorded as `READY_FOR_PRODUCTION` only by the authorized
release owners.

Store completed records in the agency-approved system of record.
