# GitHub Environment Policy

GitHub administrators configure these environments outside Terraform and repository workflows.

| Environment | Permitted workflows | WIF identities | Minimum reviewers | Allowed ref | Repository state |
|---|---|---|---:|---|---|
| test | deploy-test.yml, rollback-test.yml, terraform-plan.yml, terraform-apply.yml, bootstrap-first-admin.yml | terraform-plan, terraform-apply, deploy, rollback, admin-bootstrap | 1 | refs/heads/main | CLOSED |
| production-plan | terraform-plan.yml | terraform-plan | 2 | refs/heads/main | CLOSED |
| production-apply | terraform-apply.yml | terraform-apply | 2 | refs/heads/main | CLOSED |
| production-deploy | deploy-production.yml, bootstrap-first-admin.yml | deploy, admin-bootstrap | 2 | refs/heads/main | CLOSED |
| production-rollback | rollback-production.yml | rollback | 2 | refs/heads/main | CLOSED |
| access-release | access-release.yml | access-release | 2 | refs/heads/main | CLOSED |

Credentialed environments reject self-review, fork pull requests, and ordinary push entry. Repository workflows do not create or weaken environments, reviewers, ref policies, or credentials. Only external evidence references and reviewed/not-reviewed state may be recorded here; reviewer identities and cloud identifiers remain external.

Store completed records in the agency-approved system of record.
