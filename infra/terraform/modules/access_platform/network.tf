resource "google_compute_network" "access" {
  name                    = var.network_name
  project                 = var.project_id
  auto_create_subnetworks = false
  depends_on              = [terraform_data.services_ready]
}

resource "google_compute_subnetwork" "private" {
  name                     = "${var.network_name}-private"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.access.id
  ip_cidr_range            = "10.20.0.0/24"
  private_ip_google_access = true
}

resource "google_compute_global_address" "private_services" {
  name          = "${var.network_name}-private-services"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.access.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.access.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
}
