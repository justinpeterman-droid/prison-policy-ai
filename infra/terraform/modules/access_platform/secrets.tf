resource "google_secret_manager_secret" "access_database_url" {
  secret_id = "access-database-url"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "identity_hash_pepper" {
  secret_id = "identity-hash-pepper"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "cursor_signing_key" {
  secret_id = "cursor-signing-key"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "client_update_grant_key" {
  secret_id = "client-update-grant-key"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "legacy_access_code" {
  secret_id = "legacy-access-code"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "legacy_admin_code" {
  secret_id = "legacy-admin-code"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "github_feedback_token" {
  secret_id = "github-feedback-token"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "flask_session_secret" {
  secret_id = "flask-session-secret"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_secret_manager_secret" "initial_admin_pin" {
  secret_id = "initial-admin-pin"
  project   = var.project_id
  labels    = merge(var.labels, { environment = var.environment })
  replication {
    auto {}
  }
  depends_on = [terraform_data.services_ready]
}
