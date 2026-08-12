output "state_bucket_name" {
  description = "Name of the remote-state bucket to supply as -backend-config=bucket=... when initializing an environment root."
  value       = google_storage_bucket.terraform_state.name
}
