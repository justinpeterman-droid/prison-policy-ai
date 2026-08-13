# Initial Admin enrollment

The encrypted private request contains schema version 1, v4 operation ID, v4 staff ID, and a visible-ASCII approval reference. Store it only as `admin-bootstrap-requests/<operation-uuid>.json`, record its immutable generation and SHA-256, verify active staff and zero accounts, and invoke through the protected production-deploy approval path only.

The only accepted result has `operation_id`, `status`, `expires_at`, and `secret_version_reference`. The authorized PIN custodian retrieves the exact new version through an approved non-recorded channel, confirms receipt, disables it immediately, and destroys it after forced PIN change. Never copy a PIN to GitHub, Terraform, workflows, logs, terminals, tickets, chat, email, or clipboard history.

For orphan results disable/destroy the exact safe reference. For outcome-unknown results perform approved metadata-only reconciliation over the operation window, disable/destroy every candidate without reading payloads, retain external cleanup evidence, and do not retry. If delivery is lost, stop and use the enrollment-incident process; no account may be created by this job after any account exists.
