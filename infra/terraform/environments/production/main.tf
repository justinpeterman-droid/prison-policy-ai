locals {
  workflow_prefix = "${var.source_repository}/.github/workflows"
  wif_trust = {
    terraform-plan = {
      github_environment = "production-plan"
      workflow_refs      = ["${local.workflow_prefix}/terraform-plan.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    terraform-apply = {
      github_environment = "production-apply"
      workflow_refs      = ["${local.workflow_prefix}/terraform-apply.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    deploy = {
      github_environment = "production-deploy"
      workflow_refs      = ["${local.workflow_prefix}/deploy-production.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    rollback = {
      github_environment = "production-rollback"
      workflow_refs      = ["${local.workflow_prefix}/rollback-production.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    admin-bootstrap = {
      github_environment = "production-deploy"
      workflow_refs      = ["${local.workflow_prefix}/bootstrap-first-admin.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    access-release = {
      github_environment = "access-release"
      workflow_refs      = ["${local.workflow_prefix}/access-release.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
  }
}

module "access_platform" {
  source = "../../modules/access_platform"

  environment                    = var.environment
  project_id                     = var.project_id
  region                         = var.region
  network_name                   = var.network_name
  database_instance_name         = var.database_instance_name
  database_name                  = var.database_name
  sql_tier                       = var.sql_tier
  state_bucket_name              = var.state_bucket_name
  github_repository              = var.source_repository
  github_ref_pattern             = var.github_ref_pattern
  enable_access_release_identity = true
  wif_trust                      = local.wif_trust
  labels                         = var.labels
}
