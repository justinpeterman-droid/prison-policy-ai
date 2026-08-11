"""Feature-gated, admin-only HTTP surface for the Demo Review Lab."""
import json

import pytest

from backend.reports.review_store import ReviewStoreUnavailable
from backend.webapp import app as app_mod
from backend.webapp.routes import review_lab as review_routes


REGULAR = "regular-code"
ADMIN = "admin-code"


def valid_payload():
    return {
        "scenario_id": "inmate_fight_dayroom",
        "pipeline": {
            "classification": {"incident_type": "inmate_fight"},
            "extraction": {"slots": {}},
            "initial_gaps": {"gaps": []},
            "gap_answers": {},
            "generation_response": {"reports": {"first_person": "generated"}},
        },
        "reports": [{
            "report_type": "first_person",
            "reporter_id": "100411",
            "generated_text": "generated",
            "edited_text": "edited",
        }],
        "reviewed_fields": {"narrative": "edited"},
        "review": {"score": 4, "comments": "Better chronology."},
    }


class FakeStore:
    def __init__(self):
        self.saved = []

    def save(self, record):
        self.saved.append(record)
        return f"review-lab/submissions/2026/08/{record['submission_id']}.json"

    def list_records(self, limit=50):
        return list(reversed(self.saved))[:limit], 0

    def get(self, submission_id):
        return next((item for item in self.saved
                     if item["submission_id"] == submission_id), None)

    def export_jsonl(self, limit=1000):
        rows = self.list_records(limit)[0]
        return ("".join(json.dumps(row) + "\n" for row in rows).encode(), 0)


class UnavailableStore(FakeStore):
    def save(self, record):
        raise ReviewStoreUnavailable("bucket unavailable")


@pytest.fixture
def fake_store():
    return FakeStore()


def configured_app(monkeypatch, *, enabled, store):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", REGULAR)
    monkeypatch.setattr(app_mod, "ADMIN_CODE", ADMIN)
    monkeypatch.setattr(review_routes, "REVIEW_LAB_ENABLED", enabled)
    monkeypatch.setattr(review_routes, "_get_store", lambda: store)
    return app_mod.create_app()


def logged_in(app, code):
    client = app.test_client()
    client.set_cookie("access_code", code)
    return client


@pytest.mark.parametrize("path,method", [
    ("/review-lab", "get"),
    ("/api/review-lab/submissions", "get"),
    ("/api/review-lab/submissions", "post"),
    ("/api/review-lab/export", "get"),
])
def test_regular_users_get_concealed_404(monkeypatch, fake_store, path, method):
    app = configured_app(monkeypatch, enabled=True, store=fake_store)
    client = logged_in(app, REGULAR)

    response = getattr(client, method)(path, json={} if method == "post" else None)

    assert response.status_code == 404


@pytest.mark.parametrize("path", [
    "/review-lab", "/api/review-lab/submissions", "/api/review-lab/export",
])
def test_disabled_lab_returns_404_to_administrators(
        monkeypatch, fake_store, path):
    app = configured_app(monkeypatch, enabled=False, store=fake_store)

    assert logged_in(app, ADMIN).get(path).status_code == 404


def test_enabled_admin_can_open_the_lab(monkeypatch, fake_store):
    app = configured_app(monkeypatch, enabled=True, store=fake_store)

    response = logged_in(app, ADMIN).get("/review-lab")

    assert response.status_code == 200
    assert "Field notes" in response.get_data(as_text=True)


def test_admin_submission_is_validated_saved_and_returned(monkeypatch, fake_store):
    app = configured_app(monkeypatch, enabled=True, store=fake_store)

    response = logged_in(app, ADMIN).post(
        "/api/review-lab/submissions", json=valid_payload())

    assert response.status_code == 201
    body = response.get_json()
    assert body["submission_id"].startswith("review_")
    assert body["object_name"].endswith(body["submission_id"] + ".json")
    assert len(fake_store.saved) == 1


def test_invalid_submission_returns_400(monkeypatch, fake_store):
    app = configured_app(monkeypatch, enabled=True, store=fake_store)

    response = logged_in(app, ADMIN).post(
        "/api/review-lab/submissions", json={"scenario_id": "not-a-demo"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_storage_failure_returns_503(monkeypatch):
    app = configured_app(monkeypatch, enabled=True, store=UnavailableStore())

    response = logged_in(app, ADMIN).post(
        "/api/review-lab/submissions", json=valid_payload())

    assert response.status_code == 503
    assert "saved" in response.get_json()["error"].lower()


def test_admin_can_list_download_and_export_saved_reviews(monkeypatch, fake_store):
    app = configured_app(monkeypatch, enabled=True, store=fake_store)
    client = logged_in(app, ADMIN)
    created = client.post("/api/review-lab/submissions", json=valid_payload()).get_json()
    submission_id = created["submission_id"]

    listing = client.get("/api/review-lab/submissions").get_json()
    assert listing["submissions"][0]["submission_id"] == submission_id
    assert "pipeline" not in listing["submissions"][0]

    downloaded = client.get(f"/api/review-lab/submissions/{submission_id}")
    assert downloaded.status_code == 200
    assert downloaded.get_json()["submission_id"] == submission_id
    assert "attachment" in downloaded.headers["Content-Disposition"]

    exported = client.get("/api/review-lab/export")
    assert exported.status_code == 200
    assert exported.mimetype == "application/x-ndjson"
    assert exported.headers["X-Review-Records-Skipped"] == "0"
    assert json.loads(exported.get_data(as_text=True))["submission_id"] == submission_id
