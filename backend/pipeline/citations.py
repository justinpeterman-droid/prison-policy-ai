"""Pure citation post-processing for the policy chat — no AI, no GCP.

The generator is asked to cite numbered passages inline with [n] markers. This
module turns that raw answer + the numbered passages into:
  * a clean answer whose markers are renumbered 1..k in reading order, and
  * the exact passages that were actually cited (so the UI shows only the
    sources behind the answer, not every retrieved chunk).

Whether the answer cited anything at all is also the grounding signal: an answer
with no valid citations is flagged rather than presented as document-backed.
"""

import re

_MARKER = re.compile(r"\[(\d+)\]")

# ── Inferred grounding (fallback when the model omits [n] markers) ──
#
# Models routinely write a correct, passage-derived answer and simply forget the
# brackets. Treating that as ungrounded puts a scary "could not be tied to a
# policy passage" warning on a good answer, which is worse than useless here —
# it teaches officers to distrust correct answers.
#
# So when there are no markers, fall back to asking a cheaper question: does the
# wording of each sentence actually come from a retrieved passage? This is pure
# lexical overlap — no AI, no embeddings, no network.
#
# The thresholds deliberately err STRICT. A false "grounded" would present an
# invented answer as document-backed, which is the one failure this product
# cannot have; a false "ungrounded" only shows a warning that is merely annoying.

_WORD = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Words too common to be evidence that a sentence came from a given passage.
_STOPWORDS = frozenset(
    """
about above after again against all and any are because been before being below
between both but can cannot did does doing down during each few for from further
had has have having her here hers him his how into its itself may more most must
non nor not off once only other our out over own same shall she should some such
than that the their them then there these they this those through too under
until upon very was were what when where which while who whom why will with
would you your
""".split()
)

# A sentence needs at least this many content words before its overlap score
# means anything — "Yes." can't be evidence of anything either way.
MIN_SENTENCE_WORDS = 4
# Fraction of a sentence's content words that must appear in a passage.
SUPPORT_THRESHOLD = 0.6
# Fraction of substantive sentences that must be supported for the whole answer.
MIN_SUPPORTED_RATIO = 0.5


def _content_words(text: str) -> set[str]:
    """Lowercased content words, minus stopwords and very short tokens."""
    return {w for w in _WORD.findall((text or "").lower()) if len(w) > 2 and w not in _STOPWORDS}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def support_score(sentence: str, passage: str) -> float:
    """Fraction of the sentence's content words that also appear in `passage`.

    Containment rather than Jaccard: a short sentence drawn from a long passage
    should score high, and passage length shouldn't dilute the signal.
    """
    words = _content_words(sentence)
    if not words:
        return 0.0
    return len(words & _content_words(passage)) / len(words)


def infer_citations(
    answer: str,
    contexts: list[dict],
    threshold: float = SUPPORT_THRESHOLD,
    min_supported_ratio: float = MIN_SUPPORTED_RATIO,
) -> tuple[list[dict], bool]:
    """Grounding fallback for an answer that carries no [n] markers.

    Matches each substantive sentence to its best-supporting passage by lexical
    overlap. Returns (citations, grounded) — citations are the passages that
    actually supported a sentence, numbered in first-use order.

    The answer text is never modified: markers are not injected into model prose.
    """
    if not contexts:
        return [], False
    sentences = [s for s in _sentences(answer) if len(_content_words(s)) >= MIN_SENTENCE_WORDS]
    if not sentences:
        return [], False

    supported = 0
    used: list[int] = []
    for sentence in sentences:
        best_i, best_score = None, 0.0
        for i, ctx in enumerate(contexts):
            score = support_score(sentence, ctx.get("text", ""))
            if score > best_score:
                best_i, best_score = i, score
        if best_i is not None and best_score >= threshold:
            supported += 1
            if best_i not in used:
                used.append(best_i)

    if supported / len(sentences) < min_supported_ratio:
        return [], False

    citations = [
        {
            "n": n,
            "source": contexts[i].get("source", ""),
            "text": contexts[i].get("text", ""),
        }
        for n, i in enumerate(used, start=1)
    ]
    return citations, True


def cited_indices(answer: str, n_passages: int) -> list[int]:
    """Passage numbers cited in `answer`, in first-appearance order, deduped,
    and restricted to the valid 1..n_passages range."""
    out: list[int] = []
    for m in _MARKER.findall(answer or ""):
        i = int(m)
        if 1 <= i <= n_passages and i not in out:
            out.append(i)
    return out


def renumber(answer: str, cited: list[int]) -> tuple[str, dict]:
    """Rewrite the answer so cited markers become sequential 1..k (in the order
    given). Returns (new_answer, {original_index: new_index}). Markers outside
    `cited` are left unchanged."""
    mapping = {orig: new for new, orig in enumerate(cited, start=1)}

    def _repl(m):
        i = int(m.group(1))
        return f"[{mapping[i]}]" if i in mapping else m.group(0)

    return _MARKER.sub(_repl, answer or ""), mapping


def build_grounded(answer: str, contexts: list[dict], infer: bool = False) -> tuple[str, list[dict], bool]:
    """Post-process a cited answer.

    Args:
        answer: raw model output containing [n] markers.
        contexts: the passages fed to the model; passage [n] is contexts[n-1].
        infer: when the model emitted no valid markers, fall back to lexical
            overlap (`infer_citations`) before declaring the answer ungrounded.
            Off by default so marker handling stays exact for callers that want
            only explicit citations.

    Returns (clean_answer, citations, grounded):
        clean_answer: markers renumbered 1..k (unchanged if nothing cited).
        citations:    [{n, source, text}] for the cited passages, sorted by n.
        grounded:     True if at least one valid passage was cited, or — with
                      `infer` — if the answer's wording demonstrably came from
                      the retrieved passages.
    """
    cited = cited_indices(answer, len(contexts))
    if not cited:
        if infer:
            citations, grounded = infer_citations(answer, contexts)
            if grounded:
                return answer, citations, True
        return answer, [], False
    new_answer, mapping = renumber(answer, cited)
    citations = [
        {
            "n": mapping[o],
            "source": contexts[o - 1].get("source", ""),
            "text": contexts[o - 1].get("text", ""),
        }
        for o in cited
    ]
    citations.sort(key=lambda c: c["n"])
    return new_answer, citations, True
