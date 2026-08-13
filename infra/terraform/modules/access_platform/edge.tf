resource "google_compute_region_network_endpoint_group" "api" {
  name                  = "access-${var.environment}-api-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run { service = google_cloud_run_v2_service.api.name }
}

resource "google_compute_security_policy" "edge" {
  name    = "access-${var.environment}-edge"
  project = var.project_id
  rule {
    action   = "throttle"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
  }
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
  }
}

resource "google_compute_backend_service" "api" {
  name                  = "access-${var.environment}-api-backend"
  project               = var.project_id
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.edge.id
  backend { group = google_compute_region_network_endpoint_group.api.id }
}

resource "google_compute_url_map" "api" {
  name            = "access-${var.environment}-api-url-map"
  project         = var.project_id
  default_service = google_compute_backend_service.api.id
}

resource "google_compute_url_map" "http_redirect" {
  name    = "access-${var.environment}-http-redirect"
  project = var.project_id
  default_url_redirect {
    https_redirect = true
    strip_query    = false
  }
}

resource "google_compute_managed_ssl_certificate" "api" {
  name    = "access-${var.environment}-api-cert"
  project = var.project_id
  managed { domains = [var.managed_hostname] }
}

resource "google_compute_target_https_proxy" "api" {
  name             = "access-${var.environment}-api-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.api.id
  ssl_certificates = [google_compute_managed_ssl_certificate.api.id]
}

resource "google_compute_global_address" "api" {
  name    = "access-${var.environment}-api-ip"
  project = var.project_id
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "access-${var.environment}-https"
  project               = var.project_id
  target                = google_compute_target_https_proxy.api.id
  ip_address            = google_compute_global_address.api.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "access-${var.environment}-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "access-${var.environment}-http"
  project               = var.project_id
  target                = google_compute_target_http_proxy.http_redirect.id
  ip_address            = google_compute_global_address.api.id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_dns_record_set" "api" {
  name         = "${var.managed_hostname}."
  managed_zone = var.dns_zone_name
  project      = var.project_id
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.api.address]
}
