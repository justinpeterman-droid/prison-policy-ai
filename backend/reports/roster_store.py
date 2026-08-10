"""Roster persistence — GCS when configured, the packaged file otherwise.

Why this exists
---------------
The roster is the one piece of runtime state the app writes. Before this
module both writers — `/api/roster` CRUD and `add_staff_from_gap_answer()` —
wrote straight to `templates/staff_roster.json` inside the container. On Cloud
Run that filesystem is scratch space: it is discarded on restart, on
scale-to-zero and on every redeploy, so an officer added during a shift was
gone by the next cold start. Multiple instances also never saw each other's
edits at all.

Both writers also did read-modify-write over the *whole* JSON document with no
concurrency control, so two officers finishing reports at the same moment
raced and one new staff member was silently dropped.

This module fixes both. Reads are cached briefly; writes go through
`update()`, which re-reads, re-applies the change and retries when another
writer got there first — GCS object generations give us the compare-and-swap
to detect that.

Set ROSTER_BUCKET to enable GCS. Left unset, everything below runs against the
local file exactly as before, so dev and the test suite need no bucket, no
credentials and no network.
"""
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

from backend.pipeline.config import (
    ROSTER_BUCKET, ROSTER_CACHE_TTL, ROSTER_OBJECT,
)

logger = logging.getLogger(__name__)

# Shipped seed. Used as the starting point when the GCS object doesn't exist
# yet, and as the whole story when no bucket is configured.
SEED_PATH = Path(__file__).parent.parent.parent / "templates" / "staff_roster.json"

EMPTY = {"shifts": {}, "staff": []}

# GCS sentinel: `if_generation_match=0` means "only if the object is absent",
# which is exactly the create-once case.
_ABSENT = 0

_lock = threading.Lock()
_cache: dict | None = None
_cache_expires: float = 0.0
_cache_generation: int | None = None

_MAX_ATTEMPTS = 5


def using_gcs() -> bool:
    """Whether the roster is backed by GCS rather than the local file."""
    return bool(ROSTER_BUCKET)


def _read_seed() -> dict:
    try:
        return json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Roster seed not found at %s", SEED_PATH)
        return dict(EMPTY)
    except json.JSONDecodeError:
        logger.exception("Roster seed is not valid JSON; starting empty")
        return dict(EMPTY)


def _blob():
    from google.cloud import storage  # imported lazily — optional dependency
    return storage.Client().bucket(ROSTER_BUCKET).blob(ROSTER_OBJECT)


def _fetch() -> tuple[dict, int | None]:
    """Read the roster and the generation it was read at.

    The generation is what makes a later write safe: passing it back as a
    precondition turns the write into a compare-and-swap. Returns `_ABSENT`
    for a bucket that has no roster object yet, and None when there is no
    bucket at all (the local file has nothing to compare against).
    """
    if not using_gcs():
        if SEED_PATH.exists():
            return _read_seed(), None
        return dict(EMPTY), None

    from google.api_core.exceptions import NotFound
    blob = _blob()
    try:
        text = blob.download_as_text()
    except NotFound:
        # First run against a fresh bucket: hand back the packaged seed so the
        # app has shift definitions to work with. Nothing is written until a
        # real edit comes through update().
        logger.info("No roster object in gs://%s yet — using the packaged seed",
                    ROSTER_BUCKET)
        return _read_seed(), _ABSENT
    try:
        return json.loads(text), blob.generation
    except json.JSONDecodeError:
        # Refuse to treat a corrupt object as an empty roster: returning {} here
        # would let the next write replace real staff with nothing.
        logger.exception("Roster object in gs://%s is not valid JSON", ROSTER_BUCKET)
        raise


def read(*, refresh: bool = False) -> dict:
    """The current roster. Cached for ROSTER_CACHE_TTL seconds.

    The returned dict is the cached object — callers must not mutate it. Use
    `update()` to change the roster.
    """
    global _cache, _cache_expires, _cache_generation
    with _lock:
        if not refresh and _cache is not None and time.monotonic() < _cache_expires:
            return _cache
        data, generation = _fetch()
        _cache, _cache_generation = data, generation
        _cache_expires = time.monotonic() + ROSTER_CACHE_TTL
        return _cache


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


def _write(data: dict, generation: int | None) -> None:
    payload = json.dumps(data, indent=2) + "\n"
    if not using_gcs():
        _write_local(payload)
        return
    _blob().upload_from_string(
        payload, content_type="application/json",
        if_generation_match=generation,
    )


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


def update(mutate):
    """Apply `mutate` to the roster and persist the result.

    `mutate(data)` edits `data` in place and returns whatever the caller wants
    back; returning None means "nothing changed", and no write is issued.

    On GCS the read-modify-write is guarded by the object generation. If
    another instance wrote in between, the write is rejected and we start over
    from the fresh copy — so `mutate` must be safe to run more than once, and
    should re-check its own preconditions (a duplicate check, say) each time
    rather than assuming the state it saw first.
    """
    if not using_gcs():
        return _update_local(mutate)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        data, generation = _fetch()
        result = mutate(data)
        if result is None:
            return None
        try:
            _write(data, generation)
        except Exception as exc:
            if not _is_conflict(exc):
                raise
            if attempt == _MAX_ATTEMPTS:
                # Surface this as its own failure rather than a bare 412: an
                # operator seeing "PreconditionFailed" has no way to tell a
                # contention problem from a misconfigured bucket.
                raise RuntimeError(
                    f"Roster write kept losing to concurrent writers after "
                    f"{_MAX_ATTEMPTS} attempts"
                ) from exc
            # Someone else wrote first. Re-read and re-apply rather than
            # clobbering their change.
            logger.info("Roster write conflict, retrying (attempt %d)", attempt)
            invalidate()
            continue
        invalidate()
        return result


def _is_conflict(exc: Exception) -> bool:
    """Whether a failed write was a lost compare-and-swap rather than a real error."""
    try:
        from google.api_core.exceptions import PreconditionFailed
    except ImportError:
        return False
    return isinstance(exc, PreconditionFailed)
