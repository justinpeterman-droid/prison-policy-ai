// The state bucket name is supplied by the human operator at init time
// (-backend-config=bucket=...) and is never committed. Only the prefix,
// which keeps test state isolated from production state, lives in Git.
terraform {
  backend "gcs" {
    prefix = "access/test"
  }
}
