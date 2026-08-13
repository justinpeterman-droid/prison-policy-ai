module "access_platform" {
  source = "../../modules/access_platform"

  environment                    = var.environment
  project_id                     = var.project_id
  region                         = var.region
  network_name                   = "access-test-network"
  database_instance_name         = "access-test-postgres"
  database_name                  = "access_test"
  sql_tier                       = "db-custom-1-3840"
  github_repository              = var.source_repository
  github_ref_pattern             = "refs/heads/main"
  enable_access_release_identity = false
  state_bucket_name              = var.state_bucket_name
  labels                         = merge(var.labels, { system = "access" })

  wif_trust = {
    terraform-plan = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-plan.yml@refs/heads/main"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = "refs/heads/main"
    }
    terraform-apply = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-apply.yml@refs/heads/main"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = "refs/heads/main"
    }
    deploy = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/deploy-test.yml@refs/heads/main"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = "refs/heads/main"
    }
    rollback = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/rollback-test.yml@refs/heads/main"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = "refs/heads/main"
    }
    admin-bootstrap = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/bootstrap-first-admin.yml@refs/heads/main"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = "refs/heads/main"
    }
    access-release = {
      github_environment = "access-release"
      workflow_refs      = ["${var.source_repository}/.github/workflows/access-release.yml@refs/heads/main"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = "refs/heads/main"
    }
  }
}
