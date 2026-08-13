"""The deferred disciplinary pass must be a transport change, not a behaviour change.

The disciplinary supplement consumes the finished first-person report, so it
can't join the concurrent batch and roughly doubles /generate to ~40s. Phones
drop the connection over that and the officer loses every report. Splitting it
into a second request fixes that — but only if the split is invisible in the
output, which is what these tests pin down.

Generation itself is stubbed; the validation path (repair_all, invented_facts,
validate_all) runs for real, because that is the part that must not drift.
"""

import pytest

from backend.webapp.app import create_app

NOTES = (
    "On 08/05/2026 at approximately 2:15 pm, while assigned to BMU 2 Barracks, "
    "I Sgt. John Smith observed Inmate Garcia 111111 and Inmate Whitaker 222222 "
    "striking each other with closed fists. Both refused verbal commands. "
    "Officer Jane Brown assisted with restraints."
)

BATCH = {
    "first_person": "I, Sgt. John Smith, observed the incident and responded.",
    "supervisor_summary": "Sgt. John Smith reported the incident.",
    "cover_letter": "Enclosed is the incident packet.",
}
DISCIPLINARY = "Inmate Garcia, ADC# 111111 is charged under 04-08."


@pytest.fixture
def client(monkeypatch):
    import backend.webapp.routes.reports as routes

    def fake_all(
        slots,
        category="",
        auto_content=None,
        reporter_actions="",
        include_disciplinary=True,
    ):
        out = dict(BATCH)
        if include_disciplinary and routes.has_charges(slots):
            out["disciplinary"] = DISCIPLINARY
        return out

    def fake_only(slots, first_person, auto_content=None):
        return {"disciplinary": DISCIPLINARY} if routes.has_charges(slots) else {}

    monkeypatch.setattr(routes, "generate_all_reports", fake_all)
    monkeypatch.setattr(routes, "generate_disciplinary_only", fake_only)
    monkeypatch.setattr("backend.webapp.app.ACCESS_CODE", "")

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _payload(**over):
    body = {"notes": NOTES, "category": "inmate_fight", "charges": ["04-08"]}
    body.update(over)
    return body


# ── deferral ─────────────────────────────────────────────────────────────────


def test_default_request_still_includes_the_supplement(client):
    """Existing clients that don't know about deferral must be unaffected."""
    d = client.post("/api/reports/generate", json=_payload()).get_json()
    assert "disciplinary" in d["reports"]
    assert d["disciplinary_deferred"] is False


def test_deferred_request_omits_the_supplement(client):
    d = client.post("/api/reports/generate", json=_payload(defer_disciplinary=True)).get_json()
    assert "disciplinary" not in d["reports"]
    assert set(d["reports"]) == set(BATCH)


def test_deferred_flag_tells_the_client_a_second_call_is_owed(client):
    d = client.post("/api/reports/generate", json=_payload(defer_disciplinary=True)).get_json()
    assert d["disciplinary_deferred"] is True


def test_no_charges_means_nothing_is_owed_even_when_deferring(client):
    """Otherwise the client waits on a second pass that will never produce one."""
    d = client.post("/api/reports/generate", json=_payload(charges=[], defer_disciplinary=True)).get_json()
    assert d["disciplinary_deferred"] is False


# ── the second pass ──────────────────────────────────────────────────────────


def test_second_pass_returns_the_complete_set(client):
    """It replaces the first payload wholesale, so the client never merges."""
    d = client.post("/api/reports/disciplinary", json=_payload(reports=BATCH)).get_json()
    assert set(d["reports"]) == set(BATCH) | {"disciplinary"}
    assert d["disciplinary_deferred"] is False


def test_second_pass_rejects_unknown_report_keys(client):
    """Client-supplied text joins the validated set, so only known keys ride."""
    d = client.post(
        "/api/reports/disciplinary",
        json=_payload(reports={**BATCH, "evil": "unvalidated"}),
    ).get_json()
    assert "evil" not in d["reports"]


def test_second_pass_with_no_charges_is_not_an_error(client):
    d = client.post("/api/reports/disciplinary", json=_payload(charges=[], reports=BATCH))
    assert d.status_code == 200
    assert "disciplinary" not in d.get_json()["reports"]


def test_both_endpoints_validate_their_inputs(client):
    for path in ("/api/reports/generate", "/api/reports/disciplinary"):
        assert client.post(path, json={"notes": "", "category": ""}).status_code == 400


# ── parity: the split must not change the output ─────────────────────────────


def test_split_produces_the_same_reports_as_one_request(client):
    one = client.post("/api/reports/generate", json=_payload()).get_json()
    client.post("/api/reports/generate", json=_payload(defer_disciplinary=True)).get_json()
    two = client.post("/api/reports/disciplinary", json=_payload(reports=BATCH)).get_json()
    assert one["reports"] == two["reports"]


def test_split_produces_the_same_005_and_flags(client):
    """The 005 and the fabrication flags are the filed artefacts — if the split
    changed either, it would be changing the record, not just the transport."""
    one = client.post("/api/reports/generate", json=_payload()).get_json()
    two = client.post("/api/reports/disciplinary", json=_payload(reports=BATCH)).get_json()
    assert one["form005"] == two["form005"]
    assert one["flags"] == two["flags"]
    assert one["markers"] == two["markers"]


def test_split_produces_the_same_style_score(client):
    """Style is scored over the whole set in both paths, so it must match."""
    one = client.post("/api/reports/generate", json=_payload()).get_json()
    two = client.post("/api/reports/disciplinary", json=_payload(reports=BATCH)).get_json()
    assert one["style"]["score"] == two["style"]["score"]
    assert one["style"]["blocking_count"] == two["style"]["blocking_count"]
