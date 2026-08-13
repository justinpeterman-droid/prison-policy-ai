# Database migration and roster import

Obtain protected approval, a verified backup, the reviewed migration-register lock budget, and a single Alembic head before execution. Run the migration job, then the safe verification job and API compatibility check. Production `alembic downgrade`, deletion, automatic retries, and historical Word roster import are prohibited.

For roster work, first execute validation only with an approved private source URI, corrections URI, report URI, and exact SHA-256. Review private findings and correction authorization, then authorize one transactional apply. Compare only approved counts/checksums after import; never put roster contents in logs or tickets. Application-revision rollback, not schema downgrade, is the production rollback path.
