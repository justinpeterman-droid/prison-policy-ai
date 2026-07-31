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


def build_grounded(answer: str, contexts: list[dict]) -> tuple[str, list[dict], bool]:
    """Post-process a cited answer.

    Args:
        answer: raw model output containing [n] markers.
        contexts: the passages fed to the model; passage [n] is contexts[n-1].

    Returns (clean_answer, citations, grounded):
        clean_answer: markers renumbered 1..k (unchanged if nothing cited).
        citations:    [{n, source, text}] for the cited passages, sorted by n.
        grounded:     True if at least one valid passage was cited.
    """
    cited = cited_indices(answer, len(contexts))
    if not cited:
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
