module "access_platform" {
  source = "../../modules/access_platform"

  environment                    = var.environment
  project_id                     = var.project_id
  region                         = "us-central1"
  network_name                   = "access-production-network"
  database_instance_name         = "access-production-postgres"
  database_name                  = "access_production"
  sql_tier                       = "db-custom-2-7680"
  github_repository              = var.source_repository
  github_ref_pattern             = "refs/heads/main"
  enable_access_release_identity = true
  labels                         = merge(var.labels, { system = "access" })

  wif_trust = {
    terraform-plan = {
      github_environment = "production-plan"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-plan.yml@refs/heads/main"]
      ref_pattern        = "refs/heads/main"
    }
    terraform-apply = {
      github_environment = "production-apply"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-apply.yml@refs/heads/main"]
      ref_pattern        = "refs/heads/main"
    }
    deploy = {
      github_environment = "production-deploy"
      workflow_refs      = ["${var.source_repository}/.github/workflows/deploy-production.yml@refs/heads/main"]
      ref_pattern        = "refs/heads/main"
    }
    rollback = {
      github_environment = "production-rollback"
      workflow_refs      = ["${var.source_repository}/.github/workflows/rollback-production.yml@refs/heads/main"]
      ref_pattern        = "refs/heads/main"
    }
    admin-bootstrap = {
      github_environment = "production-deploy"
      workflow_refs      = ["${var.source_repository}/.github/workflows/bootstrap-first-admin.yml@refs/heads/main"]
      ref_pattern        = "refs/heads/main"
    }
    access-release = {
      github_environment = "access-release"
      workflow_refs      = ["${var.source_repository}/.github/workflows/access-release.yml@refs/heads/main"]
      ref_pattern        = "refs/heads/main"
    }
  }
}
