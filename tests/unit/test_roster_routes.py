"""Roster mutation route integrity."""

import json

import pytest

from backend.reports import roster_store
from backend.webapp import app as app_mod


@pytest.fixture
def roster_client(tmp_path, monkeypatch):
    path = tmp_path / "staff_roster.json"
    path.write_text(
        json.dumps(
            {
                "shifts": {},
                "staff": [
                    {
                        "rank": "Cpl",
                        "first": "Ray",
                        "last": "Alvarez",
                        "employee_number": "EMP-A",
                        "shift": "A",
                    },
                    {
                        "rank": "Cpl",
                        "first": "Tara",
                        "last": "Nguyen",
                        "employee_number": "EMP-B",
                        "shift": "B",
                    },
                ],
            }
        )
    )
    monkeypatch.setattr(roster_store, "SEED_PATH", path)
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    roster_store.invalidate()

    yield app_mod.create_app().test_client(), path

    roster_store.invalidate()


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


def test_update_finds_staff_member_from_a_case_insensitive_path_id(roster_client):
    client, path = roster_client

    response = client.put(
        "/api/roster/staff/emp-a",
        json={"first": "Rafael"},
    )

    assert response.status_code == 200
    assert json.loads(path.read_text())["staff"][0]["first"] == "Rafael"


def test_update_accepts_a_new_unused_employee_number(roster_client):
    client, path = roster_client

    response = client.put(
        "/api/roster/staff/EMP-A",
        json={"employee_number": " EMP-C "},
    )

    assert response.status_code == 200
    assert json.loads(path.read_text())["staff"][0]["employee_number"] == "EMP-C"


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
