"""Unit tests for semantic reranking (no GCP — the network call is faked).

Two properties carry the whole module:

  * **It never loses a passage.** Reranking reorders; anything the response
    doesn't mention keeps its place at the end. If it could drop passages it
    would silently shrink the evidence the generator sees, which is worse than
    not reranking at all.
  * **It fails open.** Every error path — no credentials, transport failure,
    5xx, malformed response, permanent 403 — returns the retriever's ordering
    untouched. A ranking outage must never cost an officer their answer.
"""
import io
import json
import urllib.error

import pytest

from backend.pipeline import rerank
from backend.pipeline.rerank import build_records, reorder, rerank_passages


def _p(source: str, text: str) -> dict:
    return {"source": source, "text": text}


def _passages(n: int) -> list[dict]:
    return [_p(f"Policy {i}", f"passage text {i}") for i in range(n)]


def _raw(payload: dict):
    """A urlopen-style response carrying `payload` as JSON."""
    class _Resp:
        def read(self):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    return _Resp()


def _fake_response(ranked_ids):
    """A RankResponse carrying `ranked_ids` in order."""
    return _raw({"records": [{"id": str(i), "score": 0.9} for i in ranked_ids]})


@pytest.fixture(autouse=True)
def _clean_state():
    """The process-level disable is sticky by design — reset it between tests."""
    rerank.reset_rerank_state()
    yield
    rerank.reset_rerank_state()


class TestBuildRecords:
    def test_record_id_is_the_original_index(self):
        records = build_records(_passages(3))
        assert [r["id"] for r in records] == ["0", "1", "2"]

    def test_source_becomes_the_title(self):
        assert build_records([_p("AD 2024-15 Use of Force", "body")])[0]["title"] == \
            "AD 2024-15 Use of Force"

    def test_empty_passages_are_skipped_but_indices_stay_true(self):
        # Index 1 has no text; the record for index 2 must still say "2", or
        # reorder() maps the ranking onto the wrong passage.
        records = build_records([_p("A", "a"), _p("B", "   "), _p("C", "c")])
        assert [r["id"] for r in records] == ["0", "2"]

    def test_content_is_truncated_to_the_ranker_window(self):
        records = build_records([_p("A", "x" * 5000)], max_chars=100)
        assert len(records[0]["content"]) == 100

    def test_record_count_is_capped(self):
        assert len(build_records(_passages(10), max_records=4)) == 4

    def test_no_passages(self):
        assert build_records([]) == []


class TestReorder:
    def test_follows_the_ranked_order(self):
        passages = _passages(3)
        out = reorder(passages, ["2", "0", "1"])
        assert [p["source"] for p in out] == ["Policy 2", "Policy 0", "Policy 1"]

    def test_unmentioned_passages_keep_their_relative_order_at_the_end(self):
        passages = _passages(4)
        out = reorder(passages, ["3"])
        assert [p["source"] for p in out] == [
            "Policy 3", "Policy 0", "Policy 1", "Policy 2"]

    def test_never_drops_a_passage(self):
        passages = _passages(6)
        for ranked in ([], ["5"], ["1", "1"], ["9", "abc"], ["0", "1", "2"]):
            out = reorder(passages, ranked)
            assert len(out) == len(passages)
            assert {id(p) for p in out} == {id(p) for p in passages}

    def test_ignores_unknown_and_malformed_ids(self):
        passages = _passages(2)
        out = reorder(passages, ["99", "-1", "notanint", None, "1"])
        assert [p["source"] for p in out] == ["Policy 1", "Policy 0"]

    def test_duplicate_ids_are_used_once(self):
        passages = _passages(3)
        out = reorder(passages, ["2", "2", "2"])
        assert [p["source"] for p in out] == ["Policy 2", "Policy 0", "Policy 1"]


class TestRerankPassages:
    def test_reorders_on_a_successful_rank(self, monkeypatch):
        monkeypatch.setattr(rerank.urllib.request, "urlopen",
                            lambda _req, timeout=None: _fake_response([2, 0, 1]))
        out = rerank_passages("use of force", _passages(3),
                              token_provider=lambda: "tok")
        assert [p["source"] for p in out] == ["Policy 2", "Policy 0", "Policy 1"]

    def test_sends_the_question_and_every_record(self, monkeypatch):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data)
            return _fake_response([0, 1, 2])

        monkeypatch.setattr(rerank.urllib.request, "urlopen", fake_urlopen)
        rerank_passages("can I search a cell", _passages(3),
                        token_provider=lambda: "tok")
        assert captured["url"].endswith(":rank")
        assert captured["body"]["query"] == "can I search a cell"
        # topN covers the whole set: this pass reorders, and select_passages
        # still has its own cap and character budget to apply afterwards.
        assert captured["body"]["topN"] == 3
        assert len(captured["body"]["records"]) == 3

    def test_long_query_is_truncated(self, monkeypatch):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data)
            return _fake_response([0, 1])

        monkeypatch.setattr(rerank.urllib.request, "urlopen", fake_urlopen)
        rerank_passages("q" * 5000, _passages(2), token_provider=lambda: "tok")
        assert len(captured["body"]["query"]) == rerank.MAX_QUERY_CHARS


class TestFailsOpen:
    """Every one of these must return the input order, not raise."""

    def _assert_unchanged(self, out, passages):
        assert [p["source"] for p in out] == [p["source"] for p in passages]

    def test_credentials_failure(self, monkeypatch):
        def no_token():
            raise RuntimeError("Your default credentials were not found")

        passages = _passages(3)
        self._assert_unchanged(
            rerank_passages("q", passages, token_provider=no_token), passages)

    def test_transport_failure(self, monkeypatch):
        def boom(_req, timeout=None):
            raise urllib.error.URLError("connection reset")

        monkeypatch.setattr(rerank.urllib.request, "urlopen", boom)
        passages = _passages(3)
        self._assert_unchanged(
            rerank_passages("q", passages, token_provider=lambda: "tok"), passages)

    def test_server_error(self, monkeypatch):
        def boom(_req, timeout=None):
            raise urllib.error.HTTPError("u", 503, "Unavailable", {},
                                         io.BytesIO(b"down"))

        monkeypatch.setattr(rerank.urllib.request, "urlopen", boom)
        passages = _passages(3)
        self._assert_unchanged(
            rerank_passages("q", passages, token_provider=lambda: "tok"), passages)

    def test_malformed_response(self, monkeypatch):
        class _Resp:
            def read(self):
                return b"not json at all"

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

        monkeypatch.setattr(rerank.urllib.request, "urlopen",
                            lambda _req, timeout=None: _Resp())
        passages = _passages(3)
        self._assert_unchanged(
            rerank_passages("q", passages, token_provider=lambda: "tok"), passages)

    def test_empty_record_list_in_response(self, monkeypatch):
        monkeypatch.setattr(rerank.urllib.request, "urlopen",
                            lambda _req, timeout=None: _fake_response([]))
        passages = _passages(3)
        self._assert_unchanged(
            rerank_passages("q", passages, token_provider=lambda: "tok"), passages)

    def test_a_partial_response_still_returns_every_passage(self, monkeypatch):
        """The ranker answering about 2 of 5 records must not lose the other 3."""
        monkeypatch.setattr(rerank.urllib.request, "urlopen",
                            lambda _req, timeout=None: _fake_response([4, 3]))
        out = rerank_passages("q", _passages(5), token_provider=lambda: "tok")
        assert [p["source"] for p in out] == [
            "Policy 4", "Policy 3", "Policy 0", "Policy 1", "Policy 2"]


class TestShortCircuits:
    """Cases that must not spend a round-trip at all."""

    @pytest.fixture
    def no_network(self, monkeypatch):
        def fail(_req, timeout=None):
            raise AssertionError("rerank should not have called the Ranking API")

        monkeypatch.setattr(rerank.urllib.request, "urlopen", fail)

    def test_disabled_by_config(self, monkeypatch, no_network):
        monkeypatch.setattr(rerank, "RERANK_ENABLED", False)
        passages = _passages(5)
        assert rerank_passages("q", passages, token_provider=lambda: "tok") is passages

    def test_single_passage(self, no_network):
        passages = _passages(1)
        assert rerank_passages("q", passages, token_provider=lambda: "tok") is passages

    def test_no_passages(self, no_network):
        assert rerank_passages("q", [], token_provider=lambda: "tok") == []

    def test_blank_question(self, no_network):
        passages = _passages(3)
        assert rerank_passages("  ", passages, token_provider=lambda: "tok") is passages

    def test_only_one_passage_carries_text(self, no_network):
        passages = [_p("A", "real text"), _p("B", ""), _p("C", "  ")]
        assert rerank_passages("q", passages, token_provider=lambda: "tok") is passages


class TestPermanentFailureDisables:
    """A missing permission or a wrong ranking-config path repeats identically
    on every request. Paying that latency on every chat turn forever is the
    thing this avoids."""

    def _deny(self, status):
        def boom(_req, timeout=None):
            raise urllib.error.HTTPError("u", status, "Denied", {},
                                         io.BytesIO(b'{"error":"nope"}'))
        return boom

    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_permanent_status_disables_the_reranker(self, monkeypatch, status):
        monkeypatch.setattr(rerank.urllib.request, "urlopen", self._deny(status))
        rerank_passages("q", _passages(3), token_provider=lambda: "tok")
        assert rerank.rerank_status()["disabled_reason"]

    def test_no_further_calls_once_disabled(self, monkeypatch):
        calls = {"n": 0}

        def counted(_req, timeout=None):
            calls["n"] += 1
            raise urllib.error.HTTPError("u", 403, "Denied", {}, io.BytesIO(b""))

        monkeypatch.setattr(rerank.urllib.request, "urlopen", counted)
        for _ in range(5):
            rerank_passages("q", _passages(3), token_provider=lambda: "tok")
        assert calls["n"] == 1

    def test_a_transient_failure_does_not_disable(self, monkeypatch):
        calls = {"n": 0}

        def flaky(_req, timeout=None):
            calls["n"] += 1
            raise urllib.error.HTTPError("u", 503, "Unavailable", {}, io.BytesIO(b""))

        monkeypatch.setattr(rerank.urllib.request, "urlopen", flaky)
        for _ in range(3):
            rerank_passages("q", _passages(3), token_provider=lambda: "tok")
        assert calls["n"] == 3
        assert rerank.rerank_status()["disabled_reason"] is None


class TestWiredIntoAnswerQuestion:
    """The reordering has to survive all the way into the generator's prompt.

    Reranking that happens but doesn't change what the model sees would be an
    expensive no-op, and nothing else in the suite would notice: the pipeline's
    return shape is identical either way.
    """

    @pytest.fixture
    def chat(self, monkeypatch):
        query = pytest.importorskip(
            "backend.pipeline.query",
            reason="google-genai not importable in this environment")
        search_payload = {"results": [
            {"document": {"derivedStructData": {
                "title": f"Policy {i}",
                "snippets": [{"snippet": f"use of force text {i}"}]}}}
            for i in range(5)]}

        def fake_urlopen(req, timeout=None):
            if req.full_url.endswith(":rank"):
                # The ranker disagrees with retrieval: 4 and 3 belong on top.
                return _fake_response([4, 3, 0, 1, 2])
            return _raw(search_payload)

        monkeypatch.setattr(query, "_get_token", lambda: "tok")
        monkeypatch.setattr(rerank, "get_access_token", lambda: "tok")
        monkeypatch.setattr(query.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(query, "_classify_query", lambda *a, **k: True)

        captured = {}

        class _FakeAnswer:
            text = "Force must be reported [1]."

        class _Models:
            def generate_content(self, **kwargs):
                captured["prompt"] = kwargs["contents"]
                return _FakeAnswer()

        class _Client:
            models = _Models()

        monkeypatch.setattr(query, "_get_gen_client", lambda: _Client())
        return query, captured

    def _prompt_sources(self, prompt: str) -> list[str]:
        return [line.split("(Source: ")[1].rstrip(")")
                for line in prompt.splitlines() if line.startswith("[")]

    def test_the_generator_sees_the_reranked_order(self, chat):
        query, captured = chat
        query.answer_question("what is the use of force reporting rule")
        assert self._prompt_sources(captured["prompt"]) == [
            "Policy 4", "Policy 3", "Policy 0", "Policy 1", "Policy 2"]

    def test_citations_resolve_against_the_reranked_passages(self, chat):
        query, captured = chat
        out = query.answer_question("what is the use of force reporting rule")
        # "[1]" in the answer must mean the passage that is now first.
        assert [c["source"] for c in out["citations"]] == ["Policy 4"]

    def test_without_reranking_the_retriever_order_reaches_the_generator(
            self, chat, monkeypatch):
        """The control case: same pipeline, reranker off, retrieval order kept."""
        query, captured = chat
        monkeypatch.setattr(rerank, "RERANK_ENABLED", False)
        out = query.answer_question("what is the use of force reporting rule")
        assert self._prompt_sources(captured["prompt"]) == [
            f"Policy {i}" for i in range(5)]
        assert out["answer"].startswith("Force must be reported")


class TestStatus:
    def test_status_reports_the_resolved_config(self):
        status = rerank.rerank_status()
        assert status["ranking_config"].endswith("/rankingConfigs/default_ranking_config")
        assert "locations/" in status["ranking_config"]
        assert status["model"]
