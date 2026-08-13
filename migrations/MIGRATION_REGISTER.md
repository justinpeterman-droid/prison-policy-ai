# Migration register

All production execution is externally approved after backup, lock-budget, and compatibility review. Production downgrade is prohibited.

## 20260812_0001_identity_foundation

- Phase: expand; duration: under five minutes; lock risk: short DDL locks.
- Compatibility: old and new application revisions remain compatible.
- Rollback: isolated non-production review only; production uses application rollback.
- Verify: `SELECT version_num FROM alembic_version`; owner: database migration operator.

## 20260812_0002_identity_security_controls

- Phase: migrate; duration: under five minutes; lock risk: short DDL locks.
- Compatibility: old and new application revisions remain compatible.
- Rollback: isolated non-production review only; production uses application rollback.
- Verify: inspect `accounts` constraints and `alembic_version`; owner: database migration operator.

## 20260812_0003_report_storage

- Phase: expand; duration: under five minutes; lock risk: short DDL locks.
- Compatibility: old and new application revisions remain compatible.
- Rollback: isolated non-production review only; production uses application rollback.
- Verify: inspect report tables and `alembic_version`; owner: database migration operator.

## 20260812_0004_report_search_indexes

- Phase: migrate; duration: under five minutes; lock risk: index build locks.
- Compatibility: old and new application revisions remain compatible.
- Rollback: isolated non-production review only; production uses application rollback.
- Verify: inspect expected report indexes; owner: database migration operator.

## 20260812_0005_jobs_exports

- Phase: expand; duration: under five minutes; lock risk: short DDL locks.
- Compatibility: old and new application revisions remain compatible.
- Rollback: isolated non-production review only; production uses application rollback.
- Verify: inspect job/export tables and `alembic_version`; owner: database migration operator.

Contract migrations are never released with a minimum-client-version increase.
