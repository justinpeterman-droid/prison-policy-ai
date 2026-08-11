"""Immutable, prefix-scoped review persistence over the GCS boundary."""
import json

import pytest

from backend.reports.review_store import (
    ReviewConflictError,
    ReviewStore,
    ReviewStoreUnavailable,
)


def record(number: int = 1) -> dict:
    return {
        "schema_version": 1,
        "submission_id": f"review_2026081{number}T010203Z_abcdef{number}",
        "submitted_at": f"2026-08-1{number}T01:02:03Z",
        "scenario": {
            "scenario_id": "inmate_fight_dayroom",
            "label": "Inmate on inmate fight",
        },
        "reports": [{"changed": True}],
        "review": {"score": number},
    }


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name
        self.content = None
        self.content_type = None
        self.if_generation_match = None

    def upload_from_string(self, payload, *, content_type, if_generation_match):
        if if_generation_match == 0 and self.content is not None:
            raise RuntimeError("precondition failed")
        self.content = payload
        self.content_type = content_type
        self.if_generation_match = if_generation_match

    def download_as_text(self):
        if self.content is None:
            raise FileNotFoundError(self.name)
        return self.content


class FakeBucket:
    def __init__(self):
        self.blobs = {}

    def blob(self, name):
        return self.blobs.setdefault(name, FakeBlob(self, name))


class FakeClient:
    def __init__(self):
        self.bucket_obj = FakeBucket()

    def bucket(self, name):
        assert name == "private-bucket"
        return self.bucket_obj

    def list_blobs(self, bucket_name, *, prefix):
        assert bucket_name == "private-bucket"
        return [blob for name, blob in self.bucket_obj.blobs.items()
                if name.startswith(prefix)]


@pytest.fixture
def fake_client():
    return FakeClient()


def make_store(fake_client):
    return ReviewStore(
        "private-bucket",
        "review-lab/submissions",
        client_factory=lambda: fake_client,
    )


def seed(fake_client, item):
    month = item["submitted_at"][5:7]
    day_prefix = item["submitted_at"][:4]
    name = (f"review-lab/submissions/{day_prefix}/{month}/"
            f"{item['submission_id']}.json")
    fake_client.bucket_obj.blob(name).content = json.dumps(item)
    return name


def test_save_uses_create_only_json_under_the_dated_prefix(fake_client):
    store = make_store(fake_client)

    object_name = store.save(record(1))
    blob = fake_client.bucket_obj.blobs[object_name]

    assert object_name == (
        "review-lab/submissions/2026/08/"
        "review_20260811T010203Z_abcdef1.json")
    assert blob.if_generation_match == 0
    assert blob.content_type == "application/json"
    assert json.loads(blob.content)["submission_id"].endswith("abcdef1")


def test_save_never_overwrites_an_existing_review(fake_client):
    store = make_store(fake_client)
    store.save(record(1))

    with pytest.raises(ReviewConflictError):
        store.save(record(1))


def test_store_without_a_bucket_fails_clearly():
    store = ReviewStore("", "review-lab/submissions")

    with pytest.raises(ReviewStoreUnavailable, match="bucket"):
        store.save(record(1))


def test_get_derives_the_date_path_from_a_valid_id(fake_client):
    item = record(2)
    seed(fake_client, item)

    assert make_store(fake_client).get(item["submission_id"]) == item


@pytest.mark.parametrize("submission_id", ["../../roster.json", "review_bad", ""])
def test_get_rejects_untrusted_submission_ids(fake_client, submission_id):
    with pytest.raises(ValueError):
        make_store(fake_client).get(submission_id)


def test_list_is_newest_first_bounded_and_skips_malformed_json(fake_client):
    for number in (1, 2, 3):
        seed(fake_client, record(number))
    bad = fake_client.bucket_obj.blob(
        "review-lab/submissions/2026/08/review_20260814T010203Z_abcdef4.json")
    bad.content = "not json"

    records, skipped = make_store(fake_client).list_records(limit=2)

    assert [item["submission_id"] for item in records] == [
        "review_20260813T010203Z_abcdef3",
        "review_20260812T010203Z_abcdef2",
    ]
    assert skipped == 1


def test_export_returns_json_lines_and_skipped_count(fake_client):
    seed(fake_client, record(1))
    seed(fake_client, record(2))

    payload, skipped = make_store(fake_client).export_jsonl(limit=10)
    rows = [json.loads(line) for line in payload.decode("utf-8").splitlines()]

    assert [item["submission_id"] for item in rows] == [
        "review_20260812T010203Z_abcdef2",
        "review_20260811T010203Z_abcdef1",
    ]
    assert skipped == 0
