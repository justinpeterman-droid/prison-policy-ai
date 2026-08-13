"""Annotate templates/gold_reports/REVIEW.md with each report's ruling status.

The point is to make the human review pass fast. Every report is scored against
`STYLE_RULINGS.md` by `report_validator`, and one of three tags is written above
its text block:

  ✅ CONFORMS       — matches the rulings as written. Approve or reject on
                      content alone; nothing to fix.
  🔧 AUTO-FIXABLE   — diverges only in ways `repair()` corrects mechanically
                      (ADC# spacing, a rank period, a statement closer). Usable
                      as a few-shot example after normalizing. Still approve or
                      reject on content.
  ⚠️  NEEDS YOUR EDIT — something no code can fix without changing meaning,
                      such as a time format or medical detail in the narrative.
                      These need a human decision.

Why it matters: feeding the archive to the model raw would teach it to violate
the very rulings the validator now enforces. 36 of 94 reports conform as-is; 79
after repair. The remainder genuinely need editing.

Idempotent — re-running replaces existing tags rather than stacking them.

    PYTHONPATH=. python3 scripts/annotate_review.py [--check]
"""

import re
import sys
from pathlib import Path

from backend.reports.report_validator import repair, validate_report

REVIEW = Path(__file__).parent.parent / "templates" / "gold_reports" / "REVIEW.md"

# Must also swallow the blank line the tag is written with, or a re-run
# strips the tag and leaves the blank behind, accumulating whitespace.
TAG = re.compile(r"^> (?:✅|🔧|⚠️) [A-Z][^\n]*\n(?:> [^\n]*\n)*\n*", re.M)
BLOCK = re.compile(r"(```text\n)(.*?)(\n```)", re.S)

# Why each rule matters to a reviewer, in their words rather than rule ids.
EXPLAIN = {
    "RW-002": "ADC# written without a space",
    "RW-003": "rank abbreviation missing its period",
    "RW-005": "non-standard time format",
    "RW-006": "placeholder used as a name",
    "RW-014": "ends with a statement closer",
    "RW-031": "medical detail in the narrative",
    "RW-033": "bracketed placeholder",
    "RW-004": "self-reference count",
    "RW-000": "empty",
}


def _blocking(text: str) -> list[str]:
    """Style-only check: no notes, so the fabrication rule is skipped —
    these are real filed reports, not model output."""
    return sorted(
        {v.rule_id for v in validate_report("first_person", text, {}, notes="").violations if v.severity == "BLOCKING"}
    )


def classify(text: str) -> tuple[str, str, list[str]]:
    """Return (status, tag_line, remaining_issues) for one report."""
    before = _blocking(text)
    if not before:
        return (
            "conforms",
            "> ✅ CONFORMS — matches the style rulings. Judge it on content.",
            [],
        )

    after = _blocking(repair(text)[0])
    fixed = [r for r in before if r not in after]
    if not after:
        what = ", ".join(EXPLAIN.get(r, r) for r in fixed)
        return (
            "auto",
            f"> 🔧 AUTO-FIXABLE — {what}. Normalized automatically before use; judge it on content.",
            [],
        )

    what = ", ".join(EXPLAIN.get(r, r) for r in after)
    return (
        "edit",
        f"> ⚠️ NEEDS YOUR EDIT — {what}. No code can fix this without changing what the report says.",
        after,
    )


def main(check_only: bool = False) -> int:
    text = REVIEW.read_text()
    text = TAG.sub("", text)  # drop any previous run's tags

    counts = {"conforms": 0, "auto": 0, "edit": 0}
    needs_edit: list[str] = []

    def _annotate(m: re.Match) -> str:
        status, tag, remaining = classify(m.group(2))
        counts[status] += 1
        if remaining:
            needs_edit.append(", ".join(remaining))
        return f"{tag}\n\n{m.group(1)}{m.group(2)}{m.group(3)}"

    annotated = BLOCK.sub(_annotate, text)
    total = sum(counts.values())

    print(f"{total} reports scored against STYLE_RULINGS.md")
    print(f"  ✅ conforms as written : {counts['conforms']:3}")
    print(f"  🔧 auto-fixable        : {counts['auto']:3}")
    print(f"  ⚠️  needs your edit     : {counts['edit']:3}")
    if needs_edit:
        print("\n  reasons the ⚠️ ones need a human:")
        for reason in sorted(set(needs_edit)):
            n = needs_edit.count(reason)
            print(f"    {n:2}  {', '.join(EXPLAIN.get(r, r) for r in reason.split(', '))}")

    if check_only:
        print("\n--check: nothing written.")
        return 0
    REVIEW.write_text(annotated)
    print(f"\nAnnotated {REVIEW.relative_to(REVIEW.parent.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(check_only="--check" in sys.argv))
