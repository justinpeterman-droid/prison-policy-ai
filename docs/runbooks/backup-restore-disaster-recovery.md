# Backup, restore, and disaster recovery

Human operators only: verify automated backups and PITR, restore into an isolated nonproduction instance, restore a logical export, verify Alembic revision, and record safe counts/checksums. Verify account/session revocation and representative report/revision reads without copying records into this document. Calculate achieved RPO (target <=5 minutes) and RTO (target <=4 hours), record evidence in the restore template, obtain cleanup authorization, and escalate corrective actions. Perform this exercise quarterly. Do not run restore, export, SQL, or cleanup commands from automation.

## External gate: Cloud SQL operation polling

Cloud SQL IAM Conditions expose instance and backup-run resources, not operation resources. The workflow intentionally does **not** receive a project-wide `cloudsql.operations.get` grant. Before enabling scheduled operation polling in a production environment, the platform security owner must approve and record a supported, resource-scoped Cloud SQL operation-status access pattern. Until then, the scheduler/production gate remains closed; do not replace this gate with an unconditional project IAM grant.
