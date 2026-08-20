locals {
  secret_labels = merge(var.labels, {
    environment = var.environment
    managed_by  = "terraform"
  })
}

resource "google_secret_manager_secret" "access_database_url" {
  project   = var.project_id
  secret_id = "access-database-url"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "identity_hash_pepper" {
  project   = var.project_id
  secret_id = "identity-hash-pepper"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "cursor_signing_key" {
  project   = var.project_id
  secret_id = "cursor-signing-key"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "client_update_grant_key" {
  project   = var.project_id
  secret_id = "client-update-grant-key"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "legacy_access_code" {
  project   = var.project_id
  secret_id = "legacy-access-code"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "legacy_admin_code" {
  project   = var.project_id
  secret_id = "legacy-admin-code"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "github_feedback_token" {
  project   = var.project_id
  secret_id = "github-feedback-token"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "flask_session_secret" {
  project   = var.project_id
  secret_id = "flask-session-secret"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "initial_admin_pin" {
  project   = var.project_id
  secret_id = "initial-admin-pin"
  labels    = local.secret_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}
