# Guided Web GitHub Environment Variable Inventory

Configure these as environment-scoped GitHub Actions variables, never as
repository-wide variables. Values stay in GitHub or the approved system of
record; do not add a `.tfvars` file, project identifiers, hostnames, roster
object paths, approval records, or credential material to this repository.

## Test and production-plan environments

The `test` environment supplies the values used by the test deployment path.
The production environments use the corresponding production values. Every
listed value is required before the protected Terraform plan can run.

| Variable | Purpose |
| --- | --- |
| `GCP_PROJECT_ID` | Dedicated environment project. Test and production must differ. |
| `TERRAFORM_STATE_BUCKET` | Environment-only Terraform state bucket. |
| `CLOUD_SQL_TIER` | Reviewed PostgreSQL 17 capacity tier. |
| `STORAGE_LOG_BUCKET` | Existing bucket used for Cloud Storage access logs. |
| `ARTIFACT_REGISTRY_KMS_KEY` | Approved CMEK key for the Artifact Registry repository. |
| `MANAGED_HOSTNAME` | Approved managed HTTPS hostname. |
| `DNS_ZONE_NAME` | Cloud DNS zone containing the managed hostname. |
| `GCP_ARTIFACT_REPOSITORY` | Docker Artifact Registry repository ID. |
| `QUEUE_MAX_ATTEMPTS` | Approved Cloud Tasks retry limit. |
| `GCP_MODEL_LOCATION` | Vertex AI model location. |
| `AGENT_BUILDER_LOCATION` | Discovery Engine / Agent Builder location. |
| `AGENT_BUILDER_COLLECTION` | Approved collection identifier. |
| `AGENT_BUILDER_ENGINE_ID` | Approved search engine identifier. |
| `AGENT_BUILDER_SERVING_CONFIG` | Approved serving configuration. |
| `FAST_MODEL` | Approved fast-model identifier. |
| `PRO_MODEL` | Approved higher-capability-model identifier. |
| `REVIEW_OBJECT_PREFIX` | Bounded review-object prefix. |
| `LOG_LEVEL` | Approved application log level. |
| `API_MIN_INSTANCES`, `API_MAX_INSTANCES`, `API_MAX_CONCURRENCY` | Reviewed API capacity settings. |
| `WORKER_MIN_INSTANCES`, `WORKER_MAX_INSTANCES`, `WORKER_MAX_CONCURRENCY` | Reviewed worker capacity settings. |
| `NOTIFICATION_CHANNEL_IDS_JSON` | JSON array of approved Monitoring notification-channel IDs. |
| `BILLING_ACCOUNT_ID` | Approved billing account identifier. |
| `MONTHLY_BUDGET_AMOUNT` | Approved monthly budget amount. |
| `BUDGET_PUBSUB_TOPIC` | Approved budget-routing topic. |
| `OBSERVABILITY_OWNER_ROLE` | Non-personal role responsible for alert triage. |
| `SENSITIVE_LOG_SCANNER_METRIC_TYPE` | Verified scanner-failure metric type. |
| `ROSTER_SOURCE_URI`, `ROSTER_CORRECTIONS_URI`, `ROSTER_REPORT_URI` | Environment-bounded, approved roster inputs. |
| `ROSTER_EXPECTED_SHA256` | Approved checksum for the exact roster input. |
| `BOOTSTRAP_REQUEST_URI`, `BOOTSTRAP_REQUEST_SHA256` | Approved opaque first-admin bootstrap request and checksum. |

## Workflow identity variables

These variables belong only in the listed protected environment. They contain
resource identifiers, never a service-account key or other credential value.

| Environment | Required identity variables |
| --- | --- |
| `test` | `GCP_TERRAFORM_PLAN_WIF_PROVIDER`, `GCP_TERRAFORM_PLAN_SERVICE_ACCOUNT`, `GCP_TERRAFORM_APPLY_WIF_PROVIDER`, `GCP_TERRAFORM_APPLY_SERVICE_ACCOUNT`, `GCP_DEPLOY_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_ROLLBACK_WIF_PROVIDER`, `GCP_ROLLBACK_SERVICE_ACCOUNT`, `GCP_ADMIN_BOOTSTRAP_WIF_PROVIDER`, `GCP_ADMIN_BOOTSTRAP_SERVICE_ACCOUNT` |
| `production-plan` | `GCP_TERRAFORM_PLAN_WIF_PROVIDER`, `GCP_TERRAFORM_PLAN_SERVICE_ACCOUNT` plus the plan variables above |
| `production-apply` | `GCP_TERRAFORM_APPLY_WIF_PROVIDER`, `GCP_TERRAFORM_APPLY_SERVICE_ACCOUNT` plus the production variables above |
| `production-deploy` | `GCP_DEPLOY_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_ADMIN_BOOTSTRAP_WIF_PROVIDER`, `GCP_ADMIN_BOOTSTRAP_SERVICE_ACCOUNT` plus the production variables above |
| `production-rollback` | `GCP_ROLLBACK_WIF_PROVIDER`, `GCP_ROLLBACK_SERVICE_ACCOUNT` |

Do not configure a Google service-account JSON key, a Secret Manager payload,
or a real first-admin PIN as a GitHub variable or repository secret. Workload
Identity Federation and Secret Manager are the only supported paths.
