# W-01 Release Cleanup and Documentation — Completion Record

**Status:** Completed and accepted on `integration/access-cloud-run-rp02`.

**Merge:** PR #85, merge commit `8c3552130886dfd5368a1b363c713fa1f75ce440`.

**Purpose:** Preserve the test-first decisions and exact verification evidence for W-01. This file is no longer an executable implementation plan. The Guided Operations Web Foundation is the active next web-companion stage.

## Accepted outcomes

### #72 — bounded GitHub feedback submissions

The feedback endpoint now:

- passes a finite timeout to `urllib.request.urlopen`;
- reads `FEEDBACK_GITHUB_TIMEOUT_SECONDS` with a 10-second default;
- clamps finite values to 1–30 seconds and safely handles invalid/non-finite configuration;
- classifies direct and wrapped timeout failures as `feedback_github_timeout`;
- returns a generic retryable `503` without exposing internal transport details.

**Red evidence:** commit `0ed8ec76`, Unit Tests run `32168566445`; the new timeout tests failed while 1,342 existing tests passed.

### #71 — route-owned DOCX cleanup

The legacy report download route now:

- distinguishes route-owned temporary documents from caller-owned output paths;
- reads a route-owned document into `BytesIO`;
- deletes the pathname in `finally` before returning the response;
- preserves caller-owned paths;
- cleans up even when response construction fails.

This deliberately replaced the earlier `after_this_request` proposal. Reading, deleting, then returning `BytesIO` avoids deleting an open pathname on Windows and covers failures before Flask has registered a response callback. The temporary legacy documents are bounded, so buffering one document is accepted during migration.

**Red evidence:** commit `73feb69f`, Unit Tests run `32169324699`; four new ownership/cleanup tests failed while 1,347 existing tests passed.

### #69 — retired backend-local deployment path

The unsafe `backend/scripts/deploy.sh` path no longer exists and was not recreated. Repository documentation and tests now require source/container builds from the repository root. Production delivery remains OP-08 scope, using protected environments, Workload Identity Federation, reviewed ordering, verification, and rollback evidence.

Issue #69 was closed as **not planned**, because repairing and retaining an ad-hoc backend-local production script would conflict with the accepted delivery architecture.

### Current documentation

W-01 replaced stale project entry points with:

- a README describing the actual Access + React + `/api/v1` + PostgreSQL 17 platform;
- a current external-gates-only `HANDOFF.md`;
- `docs/architecture/unified-platform.md`;
- a persistent W-01 through W-05 web-companion workstream in the implementation ledger;
- documentation regression tests that prevent restoration of obsolete PR references and backend-local deployment guidance.

**Red evidence:** commit `9cb2776a`, Backend Quality run `32170908095`; four documentation-contract tests failed while 1,322 tests passed and 30 skipped.

## Exact final verification

Final feature-branch head: `ba337ebdde21ce46a7a86891c1fe97e8e723da66`.

### Unit Tests — run `32173978705`

- Python 3.12: 1,357 unit tests passed; 271 PostgreSQL integration tests passed, 1 skipped; optimized images current.
- Python 3.14: 1,357 unit tests passed; 271 PostgreSQL integration tests passed, 1 skipped; optimized images current.

### Backend Quality — run `32173978708`

- Ruff check and format check passed.
- mypy passed.
- Python 3.12 and 3.14 unit jobs passed.
- OpenAPI contract passed.
- PostgreSQL 17 integration passed: 271 passed, 1 skipped.
- Terraform formatting and pinned Checkov scan passed.
- Tracked sensitive-output/redaction check passed.

### Container Security — run `32173978585`

- container build passed;
- pinned runtime provenance passed;
- fixed High/Critical vulnerability scan passed;
- SPDX SBOM generation and binding passed;
- Pages publication-scope and redaction checks passed.

## Repository state after acceptance

- Issues #71 and #72 are closed as completed.
- Issue #69 is closed as not planned.
- No deployment, migration, cloud mutation, secret change, branch-protection change, or production operation was part of W-01.
- The next implementation stage is `docs/superpowers/plans/2026-08-18-guided-operations-web-foundation-implementation.md`, governed by `docs/superpowers/plans/2026-08-18-guided-operations-web-program-roadmap.md`.
- Preparation of an integration-to-`main` release PR is separate from deployment and does not claim that the Guided Operations web program is implemented.
