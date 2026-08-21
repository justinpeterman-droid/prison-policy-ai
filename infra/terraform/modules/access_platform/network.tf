resource "google_compute_network" "access" {
  project                 = var.project_id
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.required]
}

resource "google_compute_subnetwork" "private" {
  project                  = var.project_id
  name                     = "${var.network_name}-${var.region}"
  region                   = var.region
  network                  = google_compute_network.access.id
  ip_cidr_range            = "10.42.0.0/24"
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# No workload accepts unsolicited VPC ingress. This explicit terminal rule
# also prevents the network from depending on provider-created default rules.
resource "google_compute_firewall" "default_deny_ingress" {
  name      = "${var.network_name}-default-deny-ingress"
  project   = var.project_id
  network   = google_compute_network.access.name
  direction = "INGRESS"
  priority  = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_global_address" "private_services" {
  project       = var.project_id
  name          = "${var.network_name}-private-services"
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
