"""Roster persistence.

The bug this module exists to fix is invisible locally: on Cloud Run the
container filesystem is discarded, so roster writes vanish, and two writers
racing over one JSON blob silently drop one of the changes. Neither shows up
without a bucket, so these tests drive the GCS path against a fake and assert
the compare-and-swap behaviour directly.
"""

import json
import os
import threading
from pathlib import Path

import pytest

from backend.reports import roster_store


@pytest.fixture(autouse=True)
def clean_cache():
    roster_store.invalidate()
    yield
    roster_store.invalidate()


@pytest.fixture
def no_cache(monkeypatch):
    """Disable the read cache so each read hits the backend."""
    monkeypatch.setattr(roster_store, "ROSTER_CACHE_TTL", 0)


# ── Local-file backend (the default: no bucket, no credentials) ──────────


def test_local_backend_is_the_default():
    assert roster_store.using_gcs() is False


def test_read_returns_the_packaged_roster():
    data = roster_store.read()
    assert data["staff"], "seed roster should not be empty"
    assert set(data["shifts"]) == {"A", "B", "C", "D", "U", "F"}


def test_local_update_round_trips(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    path.write_text(json.dumps({"shifts": {}, "staff": []}))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    def add(data):
        data["staff"].append({"last": "Halvorsen", "employee_number": "100411"})
        return "added"

    assert roster_store.update(add) == "added"
    assert json.loads(path.read_text())["staff"][0]["last"] == "Halvorsen"


def test_a_mutation_returning_none_writes_nothing(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    original = json.dumps({"shifts": {}, "staff": []})
    path.write_text(original)
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    assert roster_store.update(lambda data: None) is None
    assert path.read_text() == original, "no-op mutation must not rewrite the file"


def test_update_busts_the_cache(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    path.write_text(json.dumps({"shifts": {}, "staff": []}))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    roster_store.read()  # populate cache

    def add(data):
        data["staff"].append({"last": "Alvarez"})
        return True

    roster_store.update(add)
    assert [s["last"] for s in roster_store.read()["staff"]] == ["Alvarez"]


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
        "Alvarez",
        "Nguyen",
    ]
    assert json.loads(path.read_text()) == observed["staged"]


def test_failed_local_replace_keeps_original_and_removes_temp_file(
    tmp_path, monkeypatch
):
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
            data["staff"].append(
                {
                    "last": last,
                    "employee_number": employee_number,
                }
            )
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


# ── GCS backend, driven against a fake ───────────────────────────────────


class FakePreconditionFailed(Exception):
    pass


class FakeGCS:
    """Minimal stand-in for a GCS object with generation preconditions."""

    def __init__(self, data=None, generation=1):
        self.text = json.dumps(data) if data is not None else None
        self.generation = generation if data is not None else 0
        self.writes = 0
        # Runs before each write, so a test can simulate another instance
        # landing a write in between our read and our write.
        self.on_write = None

    def fetch(self):
        if self.text is None:
            raise FileNotFoundError
        return json.loads(self.text), self.generation

    def write(self, payload, generation):
        if self.on_write:
            # Cleared before the call so a hook can re-arm itself to fire again.
            hook, self.on_write = self.on_write, None
            hook(self)
        if generation != self.generation:
            raise FakePreconditionFailed(
                f"expected generation {generation}, object is at {self.generation}"
            )
        self.text = payload
        self.generation += 1
        self.writes += 1


@pytest.fixture
def gcs(monkeypatch, no_cache):
    fake = FakeGCS(
        {"shifts": {}, "staff": [{"last": "Alvarez", "employee_number": "100412"}]}
    )

    monkeypatch.setattr(roster_store, "ROSTER_BUCKET", "test-bucket")
    monkeypatch.setattr(roster_store, "using_gcs", lambda: True)
    monkeypatch.setattr(
        roster_store,
        "_is_conflict",
        lambda exc: isinstance(exc, FakePreconditionFailed),
    )

    def fake_fetch():
        try:
            return fake.fetch()
        except FileNotFoundError:
            return roster_store._read_seed(), roster_store._ABSENT

    def fake_write(data, generation):
        fake.write(json.dumps(data, indent=2) + "\n", generation)

    monkeypatch.setattr(roster_store, "_fetch", fake_fetch)
    monkeypatch.setattr(roster_store, "_write", fake_write)
    roster_store.invalidate()
    return fake


def test_gcs_read(gcs):
    assert roster_store.read()["staff"][0]["last"] == "Alvarez"


def test_gcs_update_writes_once_when_uncontended(gcs):
    def add(data):
        data["staff"].append({"last": "Nguyen", "employee_number": "100413"})
        return "added"

    assert roster_store.update(add) == "added"
    assert gcs.writes == 1
    assert [s["last"] for s in json.loads(gcs.text)["staff"]] == ["Alvarez", "Nguyen"]


def test_a_concurrent_writer_does_not_lose_either_change(gcs):
    """The actual production bug: two officers finishing reports at once.

    Before the compare-and-swap, the second write clobbered the first and one
    new staff member disappeared with no error anywhere.
    """

    def someone_else_writes_first(fake):
        current = json.loads(fake.text)
        current["staff"].append({"last": "Kaur", "employee_number": "100433"})
        fake.text = json.dumps(current)
        fake.generation += 1

    gcs.on_write = someone_else_writes_first

    def add(data):
        data["staff"].append({"last": "Nguyen", "employee_number": "100413"})
        return "added"

    assert roster_store.update(add) == "added"

    names = [s["last"] for s in json.loads(gcs.text)["staff"]]
    assert names == ["Alvarez", "Kaur", "Nguyen"], (
        "the retry must re-apply onto the other writer's version, keeping both"
    )


def test_the_mutation_re_runs_against_fresh_state_after_a_conflict(gcs):
    """A duplicate check inside the mutation must see the winning writer's
    change — otherwise the retry happily adds a second copy."""

    def someone_else_adds_the_same_person(fake):
        current = json.loads(fake.text)
        current["staff"].append({"last": "Nguyen", "employee_number": "100413"})
        fake.text = json.dumps(current)
        fake.generation += 1

    gcs.on_write = someone_else_adds_the_same_person

    def add_if_absent(data):
        if any(s["employee_number"] == "100413" for s in data["staff"]):
            return None
        data["staff"].append({"last": "Nguyen", "employee_number": "100413"})
        return "added"

    assert roster_store.update(add_if_absent) is None
    numbers = [s["employee_number"] for s in json.loads(gcs.text)["staff"]]
    assert numbers.count("100413") == 1, "retry must not add a duplicate"


def test_it_gives_up_rather_than_spinning_forever(gcs):
    def always_conflict(fake):
        fake.generation += 1
        fake.on_write = always_conflict

    gcs.on_write = always_conflict

    with pytest.raises(RuntimeError, match="concurrent writers"):
        roster_store.update(lambda data: data["staff"].append({"last": "X"}) or "added")


def test_a_missing_object_falls_back_to_the_seed(monkeypatch, no_cache):
    """First deploy against a fresh bucket: the app still has shift
    definitions, and nothing is written until a real edit arrives."""
    fake = FakeGCS(None)
    monkeypatch.setattr(roster_store, "using_gcs", lambda: True)
    monkeypatch.setattr(
        roster_store,
        "_is_conflict",
        lambda exc: isinstance(exc, FakePreconditionFailed),
    )

    def fake_fetch():
        try:
            return fake.fetch()
        except FileNotFoundError:
            return roster_store._read_seed(), roster_store._ABSENT

    monkeypatch.setattr(roster_store, "_fetch", fake_fetch)
    roster_store.invalidate()

    data = roster_store.read()
    assert data["staff"], "should fall back to the packaged seed"
    assert fake.text is None, "a read must not create the object"


def test_corrupt_json_raises_rather_than_reading_as_empty(monkeypatch, no_cache):
    """Returning {} for a corrupt object would let the next write replace the
    whole roster with nothing."""

    def boom():
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(roster_store, "using_gcs", lambda: True)
    monkeypatch.setattr(roster_store, "_fetch", boom)
    roster_store.invalidate()

    with pytest.raises(json.JSONDecodeError):
        roster_store.read()


# ── Gap-answer parsing (the auto-add path) ───────────────────────────────


@pytest.mark.parametrize(
    "answer,expected",
    [
        ("Sgt. Marek Thackeray 100888", ("Sgt", "Marek", "Thackeray", "100888")),
        ("Sgt Marek Thackeray 100888", ("Sgt", "Marek", "Thackeray", "100888")),
        ("Sergeant Marek Thackeray 100888", ("Sgt", "Marek", "Thackeray", "100888")),
        ("Cpl. Ines Ravenna 100999", ("Cpl", "Ines", "Ravenna", "100999")),
        ("Lt. Nora Franklin", ("Lt", "Nora", "Franklin", "")),
        ("Marek Thackeray 100888", ("Ofc", "Marek", "Thackeray", "100888")),
    ],
)
def test_a_rank_written_with_a_period_still_parses(
    tmp_path, monkeypatch, answer, expected
):
    """Regression: '\\b' after '\\.?' never matches, so "Sgt." matched as "Sgt"
    and left the period behind — which then became the officer's first name.
    Officers write the period, so this corrupted most auto-added records."""
    from backend.reports import roster as roster_mod

    path = tmp_path / "staff_roster.json"
    path.write_text(json.dumps({"shifts": {}, "staff": []}))
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    roster_store.invalidate()

    assert roster_mod.add_staff_from_gap_answer("", answer) is True
    person = json.loads(path.read_text())["staff"][0]
    assert (
        person["rank"],
        person["first"],
        person["last"],
        person["employee_number"],
    ) == expected
