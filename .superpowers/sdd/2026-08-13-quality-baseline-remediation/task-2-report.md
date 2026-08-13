# Task 2 report: backend typing baseline remediation

Date: 2026-08-13

Branch: `fix/quality-mypy-review-round1`

Verification interpreter: `C:\Temp\op07-piptools-verify-20260813\venv\Scripts\python.exe`

## Outcome

The backend mypy baseline was reduced from 78 errors in 30 files to zero errors across all 98 checked source files. The remediation uses source annotations, concrete DTO shapes, boundary validation, nullable-value guards, and SQLAlchemy-compatible expressions. It does not add mypy exclusions, ignores, `noqa`, `type: ignore`, `Any`, or casts that erase typing defects.

## Baseline inventory

The noncommitted baseline command was:

```text
python -m mypy backend
```

Baseline result:

```text
Found 78 errors in 30 files (checked 98 source files)
```

The errors clustered into these root-cause families:

- nullable database/model values reaching APIs, services, and identity operations without boundary guards;
- dictionaries and JSON payloads whose runtime shapes were known but not represented with concrete typed structures;
- SQLAlchemy expressions constructed with Python values that did not match the typed SQL expression interface;
- variables reused across branches with incompatible inferred types;
- adapter interfaces for Google credentials and document extraction that were too broad or incompletely narrowed;
- PostgreSQL schema-inspection values represented as SQLAlchemy naming objects rather than normalized strings;
- literal and creation-time annotation mismatches in reporting schemas and admin filtering.

## Source remediation

The implementation made the following meaningful corrections:

- Established explicit missing-record, missing-staff, missing-static-folder, missing-token, and nullable-reporter guards at service boundaries while retaining the existing concealment and error contracts.
- Defined concrete typed payloads for token caching, migration constraint contracts, job-service JSON input, and admin report filters.
- Separated branch-local variables whose distinct runtime values had previously acquired incompatible inferred types.
- Replaced Python boolean/tuple operands with SQLAlchemy expressions where required by typed query construction.
- Normalized SQLAlchemy inspector names and PostgreSQL 17 JSONPath literals before contract comparison.
- Narrowed document pages, roster import values, date/time values, pagination inputs, and worker request arrays at their ingestion boundaries.
- Added a concrete Google authentication request adapter and guarded the optional credential token.
- Kept deployment-only legacy embedding imports lazy behind runtime-checked protocol boundaries, so the backend module remains importable in the lock-verified environment without weakening the type contract.

No dependency, mypy, Ruff, or pytest configuration was changed.

## Behavior proof

### Review remediation: missing shift classification

The first review identified that the typing-oriented roster narrowing had changed
the predecessor classification for an absent shift. A focused regression test was
written first and failed with both `invalid_shift` and `missing_required_field`.
`build_roster_plan` now handles `shift is None` explicitly, emits only
`invalid_shift` for that condition, and continues before constructing the typed
row. Missing first name, last name, or rank still emits
`missing_required_field`, including when one of those fields is missing alongside
the shift. The complete focused roster-import file passes with 9 tests.

### Review remediation: formatter baseline

The first review also reproduced 33 Task-2 Python files that Ruff would reformat
because the edits had left mixed line endings. Ruff 0.11.2 formatted the complete
required scope (`backend`, `tests`, and `scripts`), including the new regression
test. The exact formatter gate now reports all 237 Python files formatted, and the
exact lint gate reports no diagnostics.

### Missing staff during PIN reset

A focused unit regression was written first for an account whose staff relation is absent. Before the guard, the test failed with an `AttributeError` while reading `employee_number`. After the source guard, it passed with the same concealed `LookupError` contract used for a missing account.

### Flask application without a static folder

A focused unit regression was written for asset initialization with `static_folder=None`. Before the guard, the test failed with a `TypeError` from `Path(None)`. After the source guard, it passed with an explicit `RuntimeError` describing the invalid application configuration.

### Admin audit health integration fixture

The DB-backed health test initially returned:

```text
401 authentication_required
```

Before correcting the fixture, the identical isolated test was run on untouched predecessor commit `950d007` in disposable worktree `C:\Temp\op05-mypy-predecessor-950d007`, using the same disposable PostgreSQL 17 instance. It reproduced the identical 401 response at the job-creation request (`1 failed`). This establishes that the failure predated the typing remediation.

The smallest test-only correction was then applied in `tests/integration/test_admin_audit_health.py`:

- commit the SQLAlchemy fixture transaction before the distinct Flask request;
- use the fictional preparer identity that owns the fictional incident;
- assert explicitly that the request does not return 401 before checking for 202;
- retain the expected degraded aggregate state because the same scenario deliberately creates a failed job.

The focused test passed after the fixture correction, and the full DB-backed suite passed.

### PostgreSQL 17 schema reflection

The first DB-backed run exposed two migration verification failures caused by PostgreSQL 17 inspector canonicalization of JSONPath constraint literals. The migration comparison now normalizes the reflected literal before comparing it with the reviewed contract. The two focused migration tests passed, followed by the full DB-backed suite.

All test identities and records used in this work are fictional. No remote service, cloud environment, production system, secret, real report, or real PIN was accessed.

## Final verification

All commands below used the lock-verified interpreter named above. The database-backed command used a disposable local `postgres:17-alpine` container and a local test-only database.

1. `python -m mypy backend`

   ```text
   Success: no issues found in 98 source files
   ```

2. `python -m ruff check backend tests scripts`

   ```text
   All checks passed!
   ```

3. `python -m ruff format --check backend tests scripts`

   ```text
   237 files already formatted
   ```

4. `python -m pytest tests/unit/test_roster_import_job.py -q`

   ```text
   9 passed in 0.29s
   ```

5. `python -m pytest tests/unit tests/security -q`

   ```text
   1275 passed, 30 skipped, 1 warning in 7.24s
   ```

6. `python -m pytest tests/integration tests/contract tests/security -q`

   ```text
   297 passed, 1 skipped, 2 warnings in 130.78s
   ```

The warnings are dependency deprecations from `google.genai` and `openapi-spec-validator`; no project test failed. The skipped tests are existing conditional skips.

## Residual concerns

- `backend.pipeline.embed` intentionally retains a lazy dependency boundary for the legacy deployment-only Vertex AI and Google Cloud Storage packages, which are present in deployment requirements but absent from the lock-verification environment. Import smoke coverage and the full required suites pass.
- Mypy still reports informational notes that bodies of several pre-existing untyped functions are not checked by default. These are notes rather than errors and were outside the reported defect set.
