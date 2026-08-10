# Roster Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent lost local roster updates and partial JSON reads, and reject duplicate employee numbers during roster updates.

**Architecture:** Keep the existing GCS generation-based retry loop unchanged. For the local fallback, hold the existing roster lock across fetch, mutation, atomic same-directory replacement, and cache clearing. Enforce update-time employee-number uniqueness inside the mutation callback so GCS retries recheck fresh state.

**Tech Stack:** Python 3.14, Flask, pytest, `threading`, `tempfile`, `os.replace`, Google Cloud Storage generation preconditions.

## Global Constraints

- Local concurrency is guaranteed across threads in one application process, not across multiple operating-system processes.
- GCS remains the production cross-process and cross-instance concurrency mechanism.
- Do not change the roster schema, API shape, UI, authorization model, cache duration, Cloud Run configuration, dependencies, or secrets.
- Continue allowing employee-number edits; reject only values already assigned to another record.
- Compare employee numbers after stripping whitespace and case-folding, consistent with roster creation.
- Keep duplicate validation inside `mutate(data)` so every GCS retry re-evaluates it.
- Follow test-driven development: observe each new regression test fail before writing its production fix.

## File structure

- Modify `backend/reports/roster_store.py`: local transaction serialization, cache clearing under an already-held lock, and atomic local replacement.
- Modify `tests/unit/test_roster_store.py`: deterministic local concurrency, atomic replacement, and cleanup regression tests.
- Modify `backend/webapp/routes/roster.py`: duplicate employee-number validation for PUT mutations and HTTP 409 mapping.
- Create `tests/unit/test_roster_routes.py`: focused roster PUT response and persistence tests using the real local store.

---

### Task 1: Serialize local roster transactions

**Files:**
- Modify: `tests/unit/test_roster_store.py:35-80`
- Modify: `backend/reports/roster_store.py:45-160`

**Interfaces:**
- Consumes: `roster_store.update(mutate)`, where `mutate(data: dict)` edits in place and returns a caller-defined result or `None`.
- Produces: `_clear_cache_unlocked() -> None` and `_update_local(mutate)`, with local fetch, mutation, write, and cache clearing protected by `_lock`.
- Preserves: the GCS retry loop and public `read()`, `invalidate()`, and `update()` signatures.

- [ ] **Step 1: Write the failing concurrent-update test**

Add `threading` to the imports in `tests/unit/test_roster_store.py`, then add this test after `test_update_busts_the_cache`:

```python
def test_concurrent_local_updates_keep_both_changes(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    path.write_text(json.dumps({"shifts": {}, "staff": []}))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    original_write = roster_store._write
    write_barrier = threading.Barrier(2)

    def coordinated_write(data, generation):
        try:
            write_barrier.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        original_write(data, generation)

    monkeypatch.setattr(roster_store, "_write", coordinated_write)
    results = []

    def add(last, employee_number):
        def mutate(data):
            data["staff"].append({
                "last": last,
                "employee_number": employee_number,
            })
            return "added"

        results.append(roster_store.update(mutate))

    threads = [
        threading.Thread(target=add, args=("Nguyen", "100413")),
        threading.Thread(target=add, args=("Kaur", "100433")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)

    assert all(not thread.is_alive() for thread in threads)
    assert results.count("added") == 2
    names = sorted(person["last"] for person in json.loads(path.read_text())["staff"])
    assert names == ["Kaur", "Nguyen"]
```

- [ ] **Step 2: Run the test and verify the current race is exposed**

Run:

```powershell
python -m pytest tests/unit/test_roster_store.py::test_concurrent_local_updates_keep_both_changes -v
```

Expected: FAIL because both pre-fix mutations start from the empty snapshot, so the persisted file contains at most one complete edit. Both threads must terminate.

- [ ] **Step 3: Add cache clearing that is safe while the lock is held**

Replace `invalidate()` in `backend/reports/roster_store.py` with:

```python
def _clear_cache_unlocked() -> None:
    """Clear cached state. The caller must hold ``_lock``."""
    global _cache, _cache_expires, _cache_generation
    _cache = None
    _cache_expires = 0.0
    _cache_generation = None


def invalidate() -> None:
    """Drop the cached roster. Mainly for tests and for after an external edit."""
    with _lock:
        _clear_cache_unlocked()
```

- [ ] **Step 4: Add the locked local transaction and retain the GCS loop**

Add this helper immediately before `update()`:

```python
def _update_local(mutate):
    """Apply one local read-modify-write transaction under ``_lock``."""
    with _lock:
        data, generation = _fetch()
        result = mutate(data)
        if result is None:
            return None
        _write(data, generation)
        _clear_cache_unlocked()
        return result
```

Add this dispatch at the beginning of `update()` before the GCS retry loop:

```python
    if not using_gcs():
        return _update_local(mutate)
```

Do not move the GCS loop under `_lock`. Leave its conflict detection, retry count, logging, and calls to `invalidate()` unchanged.

- [ ] **Step 5: Run the focused local and GCS store tests**

Run:

```powershell
python -m pytest tests/unit/test_roster_store.py -v
```

Expected: PASS. The new two-thread test preserves both names, and every existing GCS generation-conflict test remains green.

- [ ] **Step 6: Commit the transaction fix**

```powershell
git add backend/reports/roster_store.py tests/unit/test_roster_store.py
git commit -m "fix: serialize local roster updates"
```

---

### Task 2: Replace the local roster atomically

**Files:**
- Modify: `tests/unit/test_roster_store.py:35-120`
- Modify: `backend/reports/roster_store.py:18-25,125-138`

**Interfaces:**
- Consumes: `_write(data: dict, generation: int | None) -> None` from the existing store path.
- Produces: `_write_local(payload: str) -> None`, which stages a complete file beside `SEED_PATH`, calls `os.replace()`, and removes an uncommitted temporary file on failure.
- Preserves: GCS `_blob().upload_from_string(..., if_generation_match=generation)` behavior.

- [ ] **Step 1: Write the failing replacement-boundary test**

Add `os` and `Path` to the test imports, then add:

```python
def test_local_write_atomically_replaces_complete_json(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    original = {"shifts": {}, "staff": [{"last": "Alvarez"}]}
    path.write_text(json.dumps(original))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    observed = {}
    real_replace = os.replace

    def inspect_replace(source, destination):
        observed["before"] = json.loads(path.read_text())
        observed["staged"] = json.loads(Path(source).read_text())
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", inspect_replace)

    def add(data):
        data["staff"].append({"last": "Nguyen"})
        return "added"

    assert roster_store.update(add) == "added"
    assert observed["before"] == original
    assert [person["last"] for person in observed["staged"]["staff"]] == [
        "Alvarez", "Nguyen",
    ]
    assert json.loads(path.read_text()) == observed["staged"]
```

- [ ] **Step 2: Write the failing replacement-cleanup test**

Add:

```python
def test_failed_local_replace_keeps_original_and_removes_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    original = {"shifts": {}, "staff": [{"last": "Alvarez"}]}
    path.write_text(json.dumps(original))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    def fail_replace(source, destination):
        raise OSError("replacement failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    def add(data):
        data["staff"].append({"last": "Nguyen"})
        return "added"

    with pytest.raises(OSError, match="replacement failed"):
        roster_store.update(add)

    assert json.loads(path.read_text()) == original
    assert list(tmp_path.glob(".staff_roster.json.*.tmp")) == []
```

- [ ] **Step 3: Run both new tests and verify they fail against direct writes**

Run:

```powershell
python -m pytest tests/unit/test_roster_store.py::test_local_write_atomically_replaces_complete_json tests/unit/test_roster_store.py::test_failed_local_replace_keeps_original_and_removes_temp_file -v
```

Expected: FAIL. The replacement-boundary test has no recorded `os.replace()` call, and the failure-path test does not receive the injected replacement error.

- [ ] **Step 4: Implement same-directory staging and atomic replacement**

Add these imports to `backend/reports/roster_store.py`:

```python
import os
import tempfile
```

Add this helper immediately before `_write()`:

```python
def _write_local(payload: str) -> None:
    """Atomically replace the local roster with a complete JSON payload."""
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{SEED_PATH.name}.",
        suffix=".tmp",
        dir=SEED_PATH.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as staged:
            staged.write(payload)
            staged.flush()
            os.fsync(staged.fileno())
        os.replace(temp_path, SEED_PATH)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
```

Change only the local branch of `_write()`:

```python
    if not using_gcs():
        _write_local(payload)
        return
```

- [ ] **Step 5: Run every roster-store test**

Run:

```powershell
python -m pytest tests/unit/test_roster_store.py -v
```

Expected: PASS, including local round-trip, no-op, cache, concurrency, atomic replacement, cleanup, and all GCS tests.

- [ ] **Step 6: Commit the atomic-write fix**

```powershell
git add backend/reports/roster_store.py tests/unit/test_roster_store.py
git commit -m "fix: atomically replace local roster data"
```

---

### Task 3: Reject duplicate employee numbers during PUT

**Files:**
- Create: `tests/unit/test_roster_routes.py`
- Modify: `backend/webapp/routes/roster.py:88-114`

**Interfaces:**
- Consumes: `roster_store.update(mutate)` and `PUT /api/roster/staff/<emp_id>` with a JSON object.
- Produces: mutation result `"duplicate"` and its HTTP 409 response; retains `"updated"`/200 and `"missing"`/404.
- Employee identity comparison: `(value or "").strip().casefold()`; exclude the located target object with `other is not person`.

- [ ] **Step 1: Create a real-store route-test fixture**

Create `tests/unit/test_roster_routes.py` with:

```python
"""Roster mutation route integrity."""
import json

import pytest

from backend.reports import roster_store
from backend.webapp import app as app_mod


@pytest.fixture
def roster_client(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    path.write_text(json.dumps({
        "shifts": {},
        "staff": [
            {
                "rank": "Cpl", "first": "Ray", "last": "Alvarez",
                "employee_number": "EMP-A", "shift": "A",
            },
            {
                "rank": "Cpl", "first": "Tara", "last": "Nguyen",
                "employee_number": "EMP-B", "shift": "B",
            },
        ],
    }))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    roster_store.invalidate()

    yield app_mod.create_app().test_client(), path

    roster_store.invalidate()
```

- [ ] **Step 2: Write the failing duplicate and unchanged-number tests**

Append:

```python
def test_update_rejects_another_staff_members_number_case_insensitively(roster_client):
    client, path = roster_client
    before = json.loads(path.read_text())

    response = client.put(
        "/api/roster/staff/EMP-A",
        json={"employee_number": " emp-b ", "first": "Changed"},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "Employee number emp-b already exists.",
    }
    assert json.loads(path.read_text()) == before


def test_update_accepts_the_target_staff_members_unchanged_number(roster_client):
    client, path = roster_client

    response = client.put(
        "/api/roster/staff/EMP-A",
        json={"employee_number": " EMP-A ", "first": "Rafael"},
    )

    assert response.status_code == 200
    staff = json.loads(path.read_text())["staff"]
    assert staff[0]["employee_number"] == "EMP-A"
    assert staff[0]["first"] == "Rafael"
```

- [ ] **Step 3: Add missing-record and ordinary-update regression tests**

Append:

```python
def test_update_missing_staff_member_stays_404(roster_client):
    client, path = roster_client
    before = json.loads(path.read_text())

    response = client.put(
        "/api/roster/staff/NOT-THERE",
        json={"employee_number": "EMP-B"},
    )

    assert response.status_code == 404
    assert json.loads(path.read_text()) == before


def test_update_existing_staff_shift_stays_successful(roster_client):
    client, path = roster_client

    response = client.put(
        "/api/roster/staff/EMP-A",
        json={"shift": "c"},
    )

    assert response.status_code == 200
    assert json.loads(path.read_text())["staff"][0]["shift"] == "C"
```

- [ ] **Step 4: Run the duplicate test and verify the current route fails it**

Run:

```powershell
python -m pytest tests/unit/test_roster_routes.py::test_update_rejects_another_staff_members_number_case_insensitively -v
```

Expected: FAIL because the current PUT route returns HTTP 200 and overwrites the first record with `emp-b`.

- [ ] **Step 5: Normalize the candidate and validate it inside the mutation**

In `update_staff()`, immediately after reading `body`, add:

```python
    new_employee_number = (
        body["employee_number"].strip()
        if "employee_number" in body else None
    )
```

Replace the mutation body with:

```python
    def mutate(data: dict):
        for person in data.get("staff", []):
            if person.get("employee_number", "").strip() == emp_id.strip():
                if new_employee_number is not None:
                    candidate = new_employee_number.casefold()
                    if any(
                        other is not person
                        and (other.get("employee_number") or "").strip().casefold()
                        == candidate
                        for other in data.get("staff", [])
                    ):
                        return "duplicate"
                for field in ("rank", "first", "last"):
                    if field in body:
                        person[field] = body[field].strip()
                if new_employee_number is not None:
                    person["employee_number"] = new_employee_number
                if new_shift is not None:
                    person["shift"] = new_shift
                return "updated"
        return "missing"
```

Capture the mutation result once and map both error cases:

```python
    result = roster_store.update(mutate)
    if result == "duplicate":
        return jsonify({
            "error": f"Employee number {new_employee_number} already exists.",
        }), 409
    if result == "missing":
        return jsonify({"error": f"Staff member {emp_id} not found."}), 404
```

- [ ] **Step 6: Run all route and roster-store tests**

Run:

```powershell
python -m pytest tests/unit/test_roster_routes.py tests/unit/test_roster_store.py tests/unit/test_admin_tier.py -v
```

Expected: PASS. Duplicate rejection leaves the file unchanged, unchanged identity succeeds, and existing authorization and store behavior remain green.

- [ ] **Step 7: Commit the PUT validation fix**

```powershell
git add backend/webapp/routes/roster.py tests/unit/test_roster_routes.py
git commit -m "fix: reject duplicate roster employee numbers"
```

---

### Task 4: Verify the complete branch

**Files:**
- Verify: `backend/reports/roster_store.py`
- Verify: `backend/webapp/routes/roster.py`
- Verify: `tests/unit/test_roster_store.py`
- Verify: `tests/unit/test_roster_routes.py`
- Verify: `docs/superpowers/specs/2026-08-09-roster-integrity-design.md`

**Interfaces:**
- Consumes: the completed local persistence and PUT validation tasks.
- Produces: fresh test, diff, and repository-state evidence suitable for pushing the branch and opening a draft PR that closes #68 and #70.

- [ ] **Step 1: Run the complete test suite**

```powershell
python -m pytest -q
```

Expected: PASS with zero failures. The pre-existing Google dependency deprecation warning may remain.

- [ ] **Step 2: Check patch formatting**

```powershell
git diff --check origin/main...HEAD
```

Expected: exit code 0 with no output.

- [ ] **Step 3: Review the complete branch diff**

```powershell
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- backend/reports/roster_store.py backend/webapp/routes/roster.py tests/unit/test_roster_store.py tests/unit/test_roster_routes.py
```

Confirm the diff contains only the approved local synchronization, atomic replacement, duplicate PUT validation, tests, design, and plan. Confirm no roster data, access code, admin code, GitHub token, or other secret appears.

- [ ] **Step 4: Confirm the branch is clean**

```powershell
git status --short
```

Expected: no output.

- [ ] **Step 5: Prepare the draft PR description**

Use this scope in the PR body after pushing:

```markdown
## Summary
- serialize local roster read-modify-write transactions across threads
- atomically replace local roster JSON and clean failed staging files
- reject duplicate employee-number changes with HTTP 409

## Verification
- `python -m pytest -q`
- deterministic concurrent local update regression
- atomic replacement and cleanup regressions
- duplicate, unchanged, missing, and ordinary PUT route tests

Closes #68
Closes #70
```
