locals {
  database_version = "POSTGRES_17"

  availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"

  deletion_protection = var.environment == "production"

  disk_autoresize = true
}

resource "google_sql_database_instance" "postgres" {
  name                = var.database_instance_name
  project             = var.project_id
  region              = var.region
  database_version    = local.database_version
  deletion_protection = local.deletion_protection

  settings {
    tier              = var.sql_tier
    availability_type = local.availability_type
    disk_autoresize   = local.disk_autoresize

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "07:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.access.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }
  }

  depends_on = [google_service_networking_connection.private_services]
}

resource "google_sql_database" "application" {
  project  = var.project_id
  instance = google_sql_database_instance.postgres.name
  name     = var.database_name
}
