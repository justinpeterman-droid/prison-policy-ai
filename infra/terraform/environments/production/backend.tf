// The state bucket name is supplied by the human operator at init time
// (-backend-config=bucket=...) and is never committed. Only the prefix,
// which keeps production state isolated from test state, lives in Git.
terraform {
  backend "gcs" {
    prefix = "access/production"
  }
}
