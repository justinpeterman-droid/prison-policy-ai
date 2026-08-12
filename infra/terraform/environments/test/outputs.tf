output "environment" {
  description = "Environment managed by this root."
  value       = var.environment
}

output "region" {
  description = "Primary region for this environment's regional resources."
  value       = var.region
}

output "state_prefix" {
  description = "Remote-state prefix that isolates this environment's state from every other environment."
  value       = "access/test"
}
