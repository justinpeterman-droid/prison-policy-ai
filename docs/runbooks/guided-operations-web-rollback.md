# Guided Operations Web Rollback Runbook

Use this configuration-only UI rollback when sign-in failures increase, report
save or export regresses, a print template mismatches, an authorization defect is
found, or a critical officer workflow becomes inaccessible.

1. Have the authorized operator set WEB_APP_MODE=preview through the approved
   configuration process.
2. Verify the legacy routes and `/workspace` preview behave as expected for the
   affected role without using real credentials in test tooling.
3. Keep database migrations and data intact. No database downgrade is part of routine UI rollback.
4. Preserve logs and request IDs, then open a controlled incident review with
   the service, security, and records owners.
5. Repair and verify in test before another attempt to make the primary route
   active. Repeat the release-gate checks and obtain a new explicit approval.

This document does not authorize configuration changes. Store completed records
in the agency-approved system of record.
