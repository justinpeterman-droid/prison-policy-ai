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
        return f"Inmate {last}, {first} ADC#{adc}"
    if last and adc:
        return f"Inmate {last} ADC#{adc}"
    if last and first:
        return f"Inmate {last}, {first}"
    return f"Inmate {last}" if last else ""


def _inmate_short(person: dict) -> str:
    """Short form for an inmate after first mention."""
    last = (person.get("last") or "").strip()
    return f"Inmate {last}" if last else ""


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

def _re_replace_first(text: str, pattern: str, replacement: str) -> str:
    """Replace the first match of *pattern* with *replacement* in *text*."""
    m = re.search(pattern, text)
    if not m:
        return text
    return text[:m.start()] + replacement + text[m.end():]


def _find_inmate_short_matches(person: dict) -> list[str]:
    """Build regex patterns to find any short-form mention of an inmate."""
    last = re.escape((person.get("last") or "").strip())
    first = re.escape((person.get("first") or "").strip())
    adc = (person.get("adc_number") or person.get("employee_number") or "").strip()
    adc_esc = re.escape(adc) if adc else None

    patterns = []
    if last:
        # "Inmate Last"  (most common short form from LLM)
        patterns.append(rf'\bInmate\s+{last}\b')
        if first:
            # "Inmate First Last" (LLM occasionally outputs this order)
            patterns.append(rf'\bInmate\s+{first}\s+{last}\b')
            # "Last, First"  (if model outputs the correct order but without ADC#)
            patterns.append(rf'\b{last},\s+{first}\b')
    if adc_esc:
        # "ADC#number" — any inmate mention anchored to their number
        patterns.append(rf'\b{adc_esc}\b')
    return patterns


def _find_staff_short_matches(person: dict) -> list[str]:
    """Build regex patterns to find any short-form mention of a staff member."""
    last = re.escape((person.get("last") or "").strip())
    first = re.escape((person.get("first") or "").strip())
    rank = (person.get("rank") or "").strip()
    rank_esc = re.escape(rank) if rank else None

    patterns = []
    if rank_esc and last:
        # "Rank Last" — what the LLM outputs most
        patterns.append(rf'\b{rank_esc}\s+{last}\b')
    if last:
        # bare last name
        patterns.append(rf'(?<!\w){last}(?!\w)')
    if first and last:
        # "First Last" (LLM might drop rank)
        patterns.append(rf'\b{first}\s+{last}\b')
    return patterns


def _build_replacements(slots: dict) -> list[tuple[str, str, str]]:
    """Build a list of (search_pattern, full_form, short_form) for every person.

    Each entry maps the regex that matches a person's short/partial mention
    to the replacements: first match → full form, subsequent matches → short.
    """
    replacements = []
    persons = slots.get("persons", [])
    if not persons:
        return replacements

    for person in persons:
        role = person.get("role", "")
        last = (person.get("last") or "").strip()
        if not last:
            continue  # can't match without a last name

        if role == "inmate":
            full = _inmate_full(person)
            short = _inmate_short(person)
            if not full:
                continue
            # Build a regex that finds any short-form mention
            parts = [re.escape(last)]
            first = (person.get("first") or "").strip()
            adc = (person.get("adc_number") or "").strip()
            if first:
                parts.append(re.escape(first))
            if adc:
                parts.append(re.escape(adc))

            # Match "Inmate Last" or "Inmate First Last" or bare "Last"
            alt_pats = []
            if last:
                alt_pats.append(rf'Inmate\s+{re.escape(last)}\b')
            if first and last:
                alt_pats.append(rf'Inmate\s+{re.escape(first)}\s+{re.escape(last)}\b')
            pattern = '|'.join(alt_pats) if alt_pats else rf'\b{re.escape(last)}\b'
            replacements.append((pattern, full, short))

        elif role == "security_staff":
            full = _staff_full(person)
            short = _staff_short(person)
            rank = (person.get("rank") or "").strip()
            if not full or not rank:
                continue
            # Match "Rank Last" or bare "Last" for staff
            alt_pats = []
            if rank and last:
                alt_pats.append(rf'\b{re.escape(rank)}\s+{re.escape(last)}\b')
            if last:
                # Only match bare last name for staff when it appears without rank
                alt_pats.append(rf'(?<!\w){re.escape(last)}(?!\w)')
            pattern = '|'.join(alt_pats) if alt_pats else rf'\b{re.escape(last)}\b'
            replacements.append((pattern, full, short))

    return replacements


def _fix_inmates_staff(text: str, replacements: list[tuple[str, str, str]],
                       reporter_last: str = "") -> str:
    """Apply deterministic naming corrections.

    For each person:
      1st match → full form (Inmate Last, First ADC### / Rank First Last)
      subsequent → short form (Inmate Last / Rank Last)

    Processing order: by person priority (we process each person's matches
    sequentially, left-to-right within that person). This prevents overlapping
    replacements across different persons from colliding.
    """
    import re

    # We'll process one person at a time. For each person:
    #   - Find all matches
    #   - Skip if already full form
    #   - Replace first remaining match with full, rest with short
    offset = 0
    result = list(text)

    for pattern, full, short in replacements:
        # Find all current matches for this pattern in the (possibly modified) text
        current_text = ''.join(result)
        matches = list(re.finditer(pattern, current_text))

        applied_full = False
        for m in matches:
            match_text = m.group()

            # Skip if already in full form
            if match_text == full:
                applied_full = True
                continue

            # Skip if this match overlaps with any full form in current text
            # (prevents corrupting "I, Sgt Miguel Delgado," → "I, Sgt Miguel Sgt Miguel Delgado,")
            if full in current_text and match_text in full:
                applied_full = True
                continue

            replacement = full if not applied_full else short
            if replacement == match_text:
                continue

            start = m.start()
            end = m.end()
            result[start:end] = list(replacement)
            applied_full = True

    return ''.join(result)


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

    replacements = _build_replacements(slots)
    if not replacements:
        return text

    reporter_last = slots.get("officer_last", "").strip()
    try:
        return _fix_inmates_staff(text, replacements, reporter_last)
    except Exception:
        logger.warning("Name enforcement failed", exc_info=True)
        return text  # never break the report over name fixes
