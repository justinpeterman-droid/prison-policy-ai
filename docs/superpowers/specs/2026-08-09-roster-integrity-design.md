# Roster Integrity Design

**Date:** 2026-08-09  
**Issues:** #68, #70  
**Branch:** `fix/roster-integrity-68-70`

## Context

The roster store has two persistence paths. Production uses Google Cloud Storage (GCS) generation preconditions to retry conflicting writes across instances. Local development and tests use `templates/staff_roster.json` directly.

The local path currently reads, mutates, and writes without holding a lock across the transaction. Two threads can therefore read the same roster and each replace it with a different edit, losing one update. The direct `Path.write_text()` call can also expose a truncated or partially written JSON document to a concurrent reader.

The roster create endpoint already rejects duplicate employee numbers inside its mutation callback. The update endpoint does not, so it can change one staff member to another member's employee number and make later lookup, update, and delete operations ambiguous.

## Goals

- Serialize the complete local read–mutate–write transaction across threads in one application process.
- Replace the local roster atomically so readers observe either the previous complete document or the next complete document.
- Reject employee-number changes that duplicate another staff member's number, using the same case-insensitive identity rule as roster creation.
- Keep an unchanged employee number valid.
- Preserve the existing GCS conflict-retry behavior, roster schema, API shape, UI, and authorization model.

## Non-goals

- Cross-process locking for the local fallback.
- Changes to GCS storage, Cloud Run configuration, or cache duration.
- Making employee numbers immutable.
- General roster validation or unrelated refactoring.

Production uses GCS, whose generation preconditions remain the cross-process and cross-instance concurrency mechanism. The local guarantee is intentionally limited to threads in one process.

## Approaches considered

### 1. Reuse the existing roster lock for the full local transaction — selected

The existing lock already protects cached reads. The local `update()` path will hold it while fetching the latest file, running the mutation, writing the result, and clearing the cache. This creates one synchronization boundary for local reads and writes with minimal new machinery.

### 2. Add a separate local transaction lock

A second lock could serialize updates while leaving the cache lock unchanged. It would require carefully defining lock ordering and would still rely on atomic replacement to protect readers that only take the cache lock. That extra synchronization layer is unnecessary for the current workload.

### 3. Add an operating-system file lock

A file lock could coordinate multiple processes, but it introduces platform-specific behavior or another dependency. It exceeds the agreed thread-only scope and duplicates the role GCS already serves in production.

## Storage design

### Local transaction boundary

`roster_store.update()` will select the local or GCS path before running the transaction.

For the local path, it will:

1. Acquire the existing roster lock.
2. Fetch the latest roster from disk.
3. Run `mutate(data)` while still holding the lock.
4. Return immediately without writing when the mutation returns `None`.
5. Persist the changed document atomically.
6. Clear the cached roster state while still holding the lock.
7. Release the lock and return the mutation result.

Because `read()` already holds the same lock while fetching and populating the cache, application readers cannot overlap a local update transaction. Cache clearing will use a private helper that assumes the lock is already held, avoiding recursive acquisition of the non-reentrant lock. The public `invalidate()` function will continue acquiring the lock before calling that helper.

The GCS update loop will retain its current behavior: fetch with a generation, mutate, conditionally write, retry precondition conflicts, and invalidate the cache after success. It will not be serialized by the local lock.

### Atomic local replacement

The local writer will serialize the complete JSON payload before touching the destination file. It will then:

1. Create a uniquely named temporary file in `SEED_PATH.parent`.
2. Write the complete UTF-8 payload, flush it, and synchronize it to disk.
3. Close the temporary file.
4. Replace `SEED_PATH` with `os.replace()`, which is atomic when source and destination are on the same filesystem.

Creating the temporary file beside the roster guarantees the replacement stays on one filesystem. If writing, flushing, or replacement fails, the original roster remains available and the temporary file is removed in a `finally` block. The error propagates to the existing caller rather than being converted into an empty or successful result.

## API design

The `PUT /api/roster/staff/<emp_id>` route will continue accepting updates to rank, first name, last name, employee number, and shift.

When `employee_number` is present, the route will strip it once and pass the normalized candidate into the mutation. After locating the target staff member, the mutation will compare the candidate with every other record using stripped, case-insensitive values. The target record is excluded by identity, so retaining the current number or changing only its letter case remains valid.

Mutation outcomes map to responses as follows:

- `"updated"` → HTTP 200 with `{"ok": true}`.
- `"duplicate"` → HTTP 409 with the existing duplicate-number error style.
- `"missing"` → HTTP 404 with the existing not-found error.

The duplicate check remains inside the mutation callback. This is required because the GCS path may rerun the callback against newer data after a generation conflict; each retry must re-evaluate uniqueness against that fresh state.

No UI change is required. The current roster page updates shifts only, while the API retains its existing support for broader administrative corrections.

## Testing design

Implementation will follow test-driven development.

### Local concurrency

A deterministic regression test will coordinate two update threads at the write boundary. Against the current implementation, both threads operate on the same snapshot and one edit is lost. With transaction serialization, the second thread fetches after the first commits and both edits survive. The test will also assert both threads terminate and both mutation results are returned.

### Atomic replacement

An atomic-write test will intercept the replacement operation and verify that:

- the destination still contains the previous valid JSON before replacement;
- the temporary source already contains the complete next JSON document; and
- the final destination contains the next complete document.

A failure-path test will make replacement raise, then verify the original JSON remains intact and no temporary roster file is left behind.

### Duplicate employee numbers

Route tests will exercise the real mutation callback against controlled roster data and verify:

- changing a record to another record's employee number returns 409;
- the duplicate comparison is case-insensitive;
- neither record changes after rejection;
- submitting the target record's unchanged employee number succeeds; and
- existing missing-record and valid-update behavior remains intact.

### Regression verification

The focused roster tests will run first, followed by the complete pytest suite. Existing GCS retry tests must remain green to demonstrate that local serialization did not alter production conflict handling.

## Acceptance mapping

- Issue #68 full local transaction serialization: the existing lock covers fetch through persistence and cache clearing.
- Issue #68 atomic writes: a complete same-directory temporary file is swapped with `os.replace()`.
- Issue #68 concurrent-update proof: coordinated threads must preserve both edits.
- Issue #68 partial-read proof: replacement-boundary tests establish that only complete old or new JSON is visible.
- Issue #70 duplicate rejection: the PUT mutation returns `"duplicate"`, mapped to HTTP 409.
- Issue #70 unchanged number: the target record is excluded from duplicate comparison.

## Deployment impact

No new environment variables, secrets, permissions, dependencies, migrations, or Cloud Run settings are required. Cloud Run continues using GCS for persistence. Production behavior changes only when an administrator uses the PUT API to change an employee number to one that already exists.
