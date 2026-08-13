"""Post-processing: enforce naming conventions in generated reports.

Prompt rules alone can't guarantee compliance — this deterministic step ensures
every person's first mention in a report uses full form (Last, First ADC# for
inmates; Rank First Last for staff) and subsequent mentions stay short.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────


def _inmate_full(person: dict) -> str:
    """Build the first-mention string for an inmate."""
    last = (person.get("last") or "").strip()
    first = (person.get("first") or "").strip()
    adc = (person.get("adc_number") or person.get("employee_number") or "").strip()
    if last and first and adc:
        return f"inmate {last}, {first} ADC# {adc}"
    if last and adc:
        return f"inmate {last} ADC# {adc}"
    if last and first:
        return f"inmate {last}, {first}"
    return f"inmate {last}" if last else ""


def _inmate_short(person: dict) -> str:
    """Short form for an inmate after first mention."""
    last = (person.get("last") or "").strip()
    return f"inmate {last}" if last else ""


def _staff_full(person: dict) -> str:
    """Build the first-mention string for a staff member."""
    rank = (person.get("rank") or "").strip()
    first = (person.get("first") or "").strip()
    last = (person.get("last") or "").strip()
    return f"{rank} {first} {last}".strip()


def _staff_short(person: dict) -> str:
    """Short form for a staff member after first mention."""
    rank = (person.get("rank") or "").strip()
    last = (person.get("last") or "").strip()
    return f"{rank} {last}".strip() if rank and last else (last or "")


def _rank_last(person: dict) -> str:
    """'Rank Last' form — what the LLM is most likely to output."""
    rank = (person.get("rank") or "").strip()
    last = (person.get("last") or "").strip()
    return f"{rank} {last}".strip()


# ── Finding and replacing ──────────────────────────────────────────────────
#
# Matching happens ONCE against the original text, and the output is rebuilt
# from the selected spans. The previous implementation recomputed matches, then
# spliced into a mutating buffer using those now-stale offsets, which shredded
# text ("applied restraints. Inmate Jones" -> "applied restraintCpl Jonesmate
# Jones"). It also let one person's bare-surname pattern match inside another
# person's name, so an officer and an inmate sharing a last name produced
# "Inmate Sgt Robert Smith, John ADC#123456".


def _rank_pattern(rank: str) -> str:
    """Match a rank whether or not the text abbreviates it with a period."""
    return re.escape(rank.strip().rstrip(".")) + r"\.?"


def _inmate_patterns(person: dict, allow_bare: bool) -> list[str]:
    """Ways an inmate may be written, longest/most-specific first."""
    last = re.escape((person.get("last") or "").strip())
    first = re.escape((person.get("first") or "").strip())
    adc = re.escape((person.get("adc_number") or person.get("employee_number") or "").strip())
    if not last:
        return []
    pats = []
    if first and adc:
        pats.append(rf"[Ii]nmate\s+{last},\s*{first}\s*ADC#\s*{adc}")
    if adc:
        pats.append(rf"[Ii]nmate\s+{last}\s*ADC#\s*{adc}")
    if first:
        pats.append(rf"[Ii]nmate\s+{last},\s*{first}")
        pats.append(rf"[Ii]nmate\s+{first}\s+{last}")
    pats.append(rf"[Ii]nmate\s+{last}")
    if allow_bare:
        pats.append(rf"(?<!\w){last}(?!\w)")
    return pats


def _staff_patterns(person: dict, allow_bare: bool) -> list[str]:
    """Ways a staff member may be written, longest/most-specific first."""
    last = re.escape((person.get("last") or "").strip())
    first = re.escape((person.get("first") or "").strip())
    rank = (person.get("rank") or "").strip()
    if not last:
        return []
    rank_pat = _rank_pattern(rank) if rank else ""
    pats = []
    if rank_pat and first:
        pats.append(rf"{rank_pat}\s+{first}\s+{last}")
    if first:
        pats.append(rf"{first}\s+{last}")
    if rank_pat:
        pats.append(rf"{rank_pat}\s+{last}")
    if allow_bare:
        pats.append(rf"(?<!\w){last}(?!\w)")
    return pats


def _ambiguous_last_names(persons: list[dict]) -> set[str]:
    """Last names shared by more than one person.

    A bare surname is then genuinely ambiguous — 'Smith' could be the inmate or
    the officer — so it is left untouched rather than guessed at. Only the
    qualified forms ('Inmate Smith', 'Sgt Smith') get rewritten.
    """
    counts: dict[str, int] = {}
    for p in persons:
        last = (p.get("last") or "").strip().lower()
        if last:
            counts[last] = counts.get(last, 0) + 1
    return {last for last, n in counts.items() if n > 1}


def _collect_spans(text: str, persons: list[dict]) -> list[tuple[int, int, int]]:
    """Every place any person is named, as (start, end, person_index).

    All matching is done against the untouched original text, so no offset can
    go stale.
    """
    ambiguous = _ambiguous_last_names(persons)
    spans: list[tuple[int, int, int]] = []
    for idx, person in enumerate(persons):
        last = (person.get("last") or "").strip()
        if not last:
            continue  # can't match anyone without a last name
        allow_bare = last.lower() not in ambiguous
        role = person.get("role", "")
        if role == "inmate":
            patterns = _inmate_patterns(person, allow_bare)
        elif role == "security_staff":
            patterns = _staff_patterns(person, allow_bare)
        else:
            continue
        for pattern in patterns:
            try:
                for m in re.finditer(pattern, text):
                    spans.append((m.start(), m.end(), idx))
            except re.error:  # pragma: no cover - defensive
                continue
    return spans


def _select_spans(spans: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Greedily keep non-overlapping spans, preferring the longest match.

    Longest-first is what stops a bare surname from being rewritten inside a
    longer name that contains it — 'Smith' inside 'Inmate Smith' loses to the
    full 'Inmate Smith' match.
    """
    chosen: list[tuple[int, int, int]] = []
    for span in sorted(spans, key=lambda s: (s[0], -(s[1] - s[0]))):
        if chosen and span[0] < chosen[-1][1]:
            continue  # overlaps a span we already committed to
        chosen.append(span)
    return chosen


def _full_form(person: dict) -> str:
    return _inmate_full(person) if person.get("role") == "inmate" else _staff_full(person)


def _short_form(person: dict) -> str:
    return _inmate_short(person) if person.get("role") == "inmate" else _staff_short(person)


def _match_sentence_case(replacement: str, text: str, start: int) -> str:
    """Capitalize a replacement that lands at the start of a sentence.

    'inmate' is lowercase mid-sentence (STYLE_RULINGS.md ruling 6), but still
    has to be capitalized when it opens one, so the form depends on where the
    match sits rather than being fixed.
    """
    if not replacement or replacement[0].isupper():
        return replacement
    preceding = text[:start].rstrip()
    if not preceding or preceding[-1] in ".!?:" or preceding.endswith("\n"):
        return replacement[0].upper() + replacement[1:]
    return replacement


def _rewrite(text: str, persons: list[dict]) -> str:
    """First mention of each person becomes the full form, later ones short."""
    selected = _select_spans(_collect_spans(text, persons))
    if not selected:
        return text

    out: list[str] = []
    cursor = 0
    seen: set[int] = set()
    for start, end, idx in selected:
        person = persons[idx]
        replacement = _full_form(person) if idx not in seen else _short_form(person)
        if not replacement:
            continue  # nothing sensible to write — leave the original text alone
        out.append(text[cursor:start])
        out.append(_match_sentence_case(replacement, text, start))
        seen.add(idx)
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


# ── Public API ──────────────────────────────────────────────────────────────


def enforce_naming(text: str, slots: dict) -> str:
    """Enforce first-mention conventions in a generated report.

    Args:
        text: The AI-generated report narrative.
        slots: Extraction slots dict (must include "persons" list).

    Returns:
        Text with first mentions corrected to full form.
    """
    if not text or not slots:
        return text

    persons = [p for p in (slots.get("persons") or []) if isinstance(p, dict) and (p.get("last") or "").strip()]
    if not persons:
        return text

    try:
        return _rewrite(text, persons)
    except Exception:
        logger.warning("Name enforcement failed", exc_info=True)
        return text  # never break the report over name fixes
