# Backup, restore, and disaster recovery

Human operators only: verify automated backups and PITR, restore into an isolated nonproduction instance, restore a logical export, verify Alembic revision, and record safe counts/checksums. Verify account/session revocation and representative report/revision reads without copying records into this document. Calculate achieved RPO (target <=5 minutes) and RTO (target <=4 hours), record evidence in the restore template, obtain cleanup authorization, and escalate corrective actions. Perform this exercise quarterly. Do not run restore, export, SQL, or cleanup commands from automation.

## External gate: Cloud SQL operation polling

Cloud SQL IAM Conditions expose instance and backup-run resources, not operation resources. The workflow intentionally does **not** receive a project-wide `cloudsql.operations.get` grant. Terraform creates no logical-export workflow, scheduler, or invoker binding in any environment. There is intentionally no variable or text reference that can turn it on. Before proposing activation, the platform security owner must obtain externally recorded evidence of a supported, resource-scoped Cloud SQL operation-status authorization pattern, and a reviewed Terraform change must verify that exact provider behavior. Do not replace this gate with an unconditional project IAM grant.
