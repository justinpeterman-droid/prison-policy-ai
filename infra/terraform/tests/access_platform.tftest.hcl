mock_provider "google" {}

run "private_platform_contract" {
  command = plan

  variables {
    project_id        = "slut-access-production-fixture"
    source_repository = "example.invalid/agency/prison-policy-ai"
    state_bucket_name = "slut-access-production-fixture"
    labels            = { fixture = "op03" }
  }

  assert {
    condition     = length(module.access_platform.secret_resource_ids) == 9
    error_message = "The platform must expose exactly nine secret containers."
  }

  assert {
    condition = length(setsubtract(toset(keys(module.access_platform.secret_resource_ids)), toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
      ]))) == 0 && length(setsubtract(toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
    ]), toset(keys(module.access_platform.secret_resource_ids)))) == 0
    error_message = "The platform must define exactly the nine approved secret containers."
  }

  assert {
    condition     = contains(["access_test", "access_production"], module.access_platform.database_name)
    error_message = "Each root must use one of the two isolated database names."
  }

}
