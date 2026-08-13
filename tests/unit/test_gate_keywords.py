"""Unit tests for the policy-chat gate's keyword fast-path (no AI, no GCP).

The gate decides whether a question reaches the policy corpus at all. Two ways
to get it wrong, and both were live:

  * over-accept — the original list matched bare substrings, so "gate" fired
    inside "gateway" and "report" accepted "write me a report about my dog".
  * over-reject — a short follow-up inside an active conversation ("and if he
    refuses?") carries no work vocabulary, so it fell to the LLM gate with no
    context and could be told "you're at work" mid-conversation.

Only the deterministic keyword path is tested here; the LLM fallback needs GCP.
Importing query.py pulls google.genai, so these skip cleanly without it.
"""

import pytest

try:
    from backend.pipeline import query
except ImportError as exc:  # pragma: no cover - environment-dependent
    query = None
    _import_error = str(exc)

pytestmark = pytest.mark.skipif(
    query is None,
    reason=f"google-genai not importable: {globals().get('_import_error', '')}",
)


# The real function, not a re-implementation of it. An earlier version of this
# file replayed the gate's rules inline — which passes happily while the gate
# itself drifts away from the copy.
def _keyword_verdict(question: str) -> str | None:
    verdict = query.classify_by_keyword(question)
    return None if verdict is None else ("work" if verdict else "off_topic")


class TestOverAcceptance:
    """None of these may be accepted by the keyword path. Falling through to
    the LLM gate is the correct outcome — it has judgement, the keyword list
    does not."""

    @pytest.mark.parametrize(
        "question",
        [
            "write me a report about my dog",
            "how do I count cards at blackjack",
            "my cell phone is broken who do I call",
            "what form of exercise is best for back pain",
            "search for a good pizza place near me",
            "is a gateway drug a real thing",
            "what's the medical term for a headache",
            "who is on staff at the new restaurant",
        ],
    )
    def test_generic_word_alone_does_not_accept(self, question):
        assert _keyword_verdict(question) is None

    def test_gate_does_not_match_inside_gateway(self):
        # The bug in miniature: a bare-substring "gate" accepted this.
        assert _keyword_verdict("is a gateway drug a real thing") is None


class TestRealQuestionsStillRoute:
    """Tightening the gate must not start rejecting the job."""

    @pytest.mark.parametrize(
        "question",
        [
            "When am I authorized to use force on an inmate?",
            "how do I fill out a 005 form",
            "what is the policy on a shakedown",
            "how do I report a medical emergency",
            "inmate having a seizure what do I do",
            "what's the procedure for a security check on night shift",
            "PREA reporting timeline",
            "how does an inmate file a grievance",
            "can a visitor bring an inmate a phone",
            "what are the rules for restrictive housing",
        ],
    )
    def test_officer_question_is_accepted(self, question):
        assert _keyword_verdict(question) == "work"

    def test_two_generic_words_together_are_a_real_signal(self):
        # Neither "report" nor "medical" alone means anything; together they do.
        assert _keyword_verdict("how do I report a medical emergency") == "work"


class TestFollowUps:
    """A short follow-up to an on-topic exchange is on-topic — the gate already
    passed the turn it refers to."""

    FOLLOWUPS = [
        "and if he refuses?",
        "how long do I have?",
        "what if he's already cuffed?",
        "does that apply at night?",
    ]
    HISTORY = [
        {
            "question": "When am I authorized to use force?",
            "answer": "Force may be used ...",
        }
    ]

    @pytest.mark.parametrize("question", FOLLOWUPS)
    def test_followup_has_no_work_vocabulary_of_its_own(self, question):
        assert _keyword_verdict(question) is None

    @pytest.mark.parametrize("question", FOLLOWUPS)
    def test_followup_is_accepted_when_a_conversation_is_open(self, question):
        # Deliberately the private entry point: this asserts the COMPOSITION —
        # that the gate consults is_short_followup before anything else.
        # Testing the parts separately would not prove they are wired together.
        # pylint: disable=protected-access
        assert query._classify_query(question, self.HISTORY) is True

    def test_a_long_question_is_still_judged_on_its_merits(self):
        """The follow-up shortcut is bounded by length — otherwise an officer
        could open a conversation and then ask anything at all."""
        long_offtopic = " ".join(["tell me about the history of pizza in italy"] * 3)
        assert len(long_offtopic.split()) > query.FOLLOWUP_MAX_WORDS
        assert _keyword_verdict(long_offtopic) is None

    def test_no_history_means_no_shortcut(self):
        assert _keyword_verdict("and if he refuses?") is None


class TestOffTopicKeywords:
    @pytest.mark.parametrize(
        "question",
        [
            "write a poem about my dog",
            "tell me a joke",
            "give me a recipe for chili",
            "who won the game last night",
            "write code to sort a list",
        ],
    )
    def test_obvious_off_topic_is_rejected_outright(self, question):
        assert query.classify_by_keyword(question) is False

    def test_an_empty_question_is_undecided(self):
        assert query.classify_by_keyword("") is None
        assert query.classify_by_keyword(None) is None


class TestShortFollowup:
    HISTORY = [{"question": "When am I authorized to use force?", "answer": "..."}]

    def test_no_history_is_never_a_followup(self):
        assert query.is_short_followup("and if he refuses?", None) is False
        assert query.is_short_followup("and if he refuses?", []) is False

    def test_short_question_with_history_is_a_followup(self):
        assert query.is_short_followup("and if he refuses?", self.HISTORY) is True

    def test_a_long_question_is_not(self):
        long_q = " ".join(["tell me about the history of pizza in italy"] * 3)
        assert query.is_short_followup(long_q, self.HISTORY) is False

    def test_an_empty_question_is_not_a_followup(self):
        assert query.is_short_followup("", self.HISTORY) is False


class TestConfig:
    def test_the_gate_call_is_bounded(self):
        """A hung gate call would hang every chat turn — every other Gemini
        call in this codebase sets a timeout."""
        assert 0 < query.GATE_TIMEOUT_MS <= query.ANSWER_TIMEOUT_MS

    def test_keyword_lists_are_lowercase_and_deduped(self):
        for terms in (query.STRONG_WORK_TERMS, query.WEAK_WORK_TERMS):
            assert terms == [t.lower() for t in terms]
            assert len(terms) == len(set(terms))

    def test_strong_and_weak_lists_do_not_overlap(self):
        # A term in both would make the weak-pair rule unreachable for it.
        assert not set(query.STRONG_WORK_TERMS) & set(query.WEAK_WORK_TERMS)
