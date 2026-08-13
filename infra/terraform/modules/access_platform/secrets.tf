locals {
  secret_container_ids = toset([
    "access-database-url",
    "identity-hash-pepper",
    "cursor-signing-key",
    "client-update-grant-key",
    "legacy-access-code",
    "legacy-admin-code",
    "github-feedback-token",
    "flask-session-secret",
    "initial-admin-pin",
  ])
}

# Empty containers only. Secret values are supplied later by their external
# custodians; this collection has no secret-version instances.
resource "google_secret_manager_secret" "containers" {
  for_each  = local.secret_container_ids
  secret_id = each.value
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })

  replication {
    auto {}
  }

  depends_on = [terraform_data.services_ready]
}

# Deliberately empty resource collection, retained only for the native
# plan-time contract to measure zero managed secret versions. It has no
# instances and therefore no secret data, value, or version is managed.
resource "google_secret_manager_secret_version" "managed" {
  for_each    = toset([])
  secret      = each.value
  secret_data = null
}
