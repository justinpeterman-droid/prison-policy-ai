locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "certificatemanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "compute.googleapis.com",
    "dns.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "workflows.googleapis.com",
    "billingbudgets.googleapis.com",
    "certificatemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "sqladmin.googleapis.com",
    "sts.googleapis.com",
    "cloudtrace.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

output "services_ready" {
  description = "Dependency token for resources that require enabled project services."
  value       = join(",", sort([for service in google_project_service.required : service.service]))
}
