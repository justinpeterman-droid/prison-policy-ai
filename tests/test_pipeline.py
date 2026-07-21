#!/usr/bin/env python3
"""Test harness for the notes → reports pipeline.

Run a fixture through the full pipeline (classify → extract → generate),
save all intermediate outputs to disk, and compare against prior runs.

Usage:
    python tests/test_pipeline.py fixtures/inmate_fight_01.txt
    python tests/test_pipeline.py fixtures/inmate_fight_01.txt --step classify
    python tests/test_pipeline.py fixtures/inmate_fight_01.txt --step extract
    python tests/test_pipeline.py fixtures/inmate_fight_01.txt --compare
    python tests/test_pipeline.py --all
    python tests/test_pipeline.py --all --compare
"""
import argparse
import difflib
import json
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path so backend.* imports work
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

FIXTURES_DIR = _PROJECT_ROOT / "tests" / "fixtures"
OUTPUT_DIR = _PROJECT_ROOT / "tests" / "output"

# ── Helpers ──────────────────────────────────────────────────────

def _save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _diff_dicts(a: dict, b: dict, label_a: str = "previous", label_b: str = "current") -> list[str]:
    """Return a human-readable list of differences between two dicts."""
    lines = []
    all_keys = sorted(set(a.keys()) | set(b.keys()))
    for key in all_keys:
        va = a.get(key, "<MISSING>")
        vb = b.get(key, "<MISSING>")
        if va != vb:
            if isinstance(va, str) and isinstance(vb, str) and len(va) > 120:
                # For long text (like report narratives), show a unified diff
                diff = list(difflib.unified_diff(
                    str(va).splitlines(), str(vb).splitlines(),
                    fromfile=f"{label_a}.{key}", tofile=f"{label_b}.{key}",
                    lineterm=""))
                lines.append(f"\n  ── {key} changed ({len(vb)} chars) ──")
                lines.extend(f"  {l}" for l in diff[:40])
                if len(diff) > 40:
                    lines.append(f"  ... ({len(diff) - 40} more diff lines)")
            else:
                lines.append(f"  {key}: {repr(va)[:200]} -> {repr(vb)[:200]}")
    return lines

# ── Pipeline runner ─────────────────────────────────────────────

def run_pipeline(fixture_path: Path, step: str = "generate",
                 compare: bool = False) -> int:
    """Run the pipeline against a fixture file. Returns exit code."""
    name = fixture_path.stem
    out_dir = OUTPUT_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)

    notes = fixture_path.read_text(encoding="utf-8").strip()
    if not notes:
        print(f"  WARN {name}: empty fixture — skipping")
        return 1

    # Save input copy
    (out_dir / "input.txt").write_text(notes, encoding="utf-8")

    timing = {}
    errors = []
    t0 = time.time()

    # ── Step 1: Classify ─────────────────────────────────────────
    classification = None
    if step in ("classify", "extract", "generate"):
        try:
            t1 = time.time()
            from backend.reports.classifier import classify_incident
            classification = classify_incident(notes)
            timing["classify"] = round(time.time() - t1, 2)
            _save_json(classification, out_dir / "01_classify.json")
            cat = classification.get("incident_type", "?")
            label = classification.get("label", cat)
            print(f"  OK classify -> {cat} ({label})  [{timing['classify']}s]")
        except Exception as e:
            errors.append(("classify", str(e)))
            print(f"  FAIL classify: {e}")
            classification = {"incident_type": "other_rule_violation",
                              "label": "Other Rule Violation",
                              "persons_involved": [], "charges_applicable": [],
                              "charge_descriptions": {}}

    if step == "classify":
        return 0 if not errors else 1

    # ── Step 2: Extract ──────────────────────────────────────────
    slots = {}
    if step in ("extract", "generate"):
        category = classification.get("incident_type", "other_rule_violation")
        try:
            t1 = time.time()
            from backend.reports.extraction import extract_slots
            slots = extract_slots(notes, category)
            timing["extract"] = round(time.time() - t1, 2)

            # Roster resolution
            from backend.reports.roster import resolve_staff_from_persons
            persons = slots.get("persons", [])
            roster_gaps = []
            if persons:
                resolved, roster_gaps = resolve_staff_from_persons(persons)
                slots["persons"] = resolved

            # Gap analysis
            from backend.reports.validate import find_gaps
            gap_result = find_gaps(category, slots)
            if roster_gaps:
                gap_result["gaps"] = gap_result.get("gaps", []) + roster_gaps
                gap_result["blocking_remaining"] = sum(
                    1 for g in gap_result["gaps"] if g.get("blocking"))

            _save_json(slots, out_dir / "02_extract.json")
            _save_json(gap_result, out_dir / "03_gaps.json")

            n_facts = len(slots.get("narrative_facts", []))
            n_persons = len(slots.get("persons", []))
            n_gaps = len(gap_result.get("gaps", []))
            blocking = gap_result.get("blocking_remaining", 0)

            print(f"  OK extract -> {n_persons} persons, {n_facts} facts, "
                  f"{n_gaps} gaps ({blocking} blocking)  [{timing['extract']}s]")
        except Exception as e:
            errors.append(("extract", str(e)))
            print(f"  FAIL extract: {e}")
            slots = {}

    if step == "extract":
        return 0 if not errors else 1

    # ── Step 3: Generate ─────────────────────────────────────────
    try:
        from backend.reports.schema import bind_reporter, security_staff
        from backend.reports.validate import find_gaps

        category = classification.get("incident_type", "other_rule_violation")

        # Re-resolve gaps with answered slots (no answers in test mode)
        gap_result = find_gaps(category, slots)
        auto_content = gap_result.get("auto_content", [])

        # Bind first reporting officer
        officers = security_staff(slots)
        if officers:
            bound_slots = bind_reporter(slots, officers[0])
        elif reporters := [p for p in slots.get("persons", [])
                          if p.get("role") == "security_staff"]:
            bound_slots = bind_reporter(slots, reporters[0])
        else:
            bound_slots = dict(slots)

        t1 = time.time()
        from backend.reports.generator import generate_all_reports
        reports = generate_all_reports(bound_slots, category,
                                       auto_content=auto_content)
        timing["generate"] = round(time.time() - t1, 2)

        # Validation: invented facts check
        from backend.reports.validate import invented_facts
        all_text = " ".join(v for v in reports.values() if isinstance(v, str))
        flags = invented_facts(all_text, notes, {})

        _save_json(reports, out_dir / "04_reports.json")

        n_flags = len(flags)
        report_names = list(reports.keys())
        synopsis = {k: (v[:120] + "..." if isinstance(v, str) and len(v) > 120 else v)
                    for k, v in reports.items()}
        _save_json({"timing": timing, "errors": errors, "flags": flags,
                    "synopsis": synopsis},
                   out_dir / "05_summary.json")

        print(f"  OK generate -> {report_names}  [{timing['generate']}s]")
        if flags:
            print(f"  WARN {n_flags} invented-fact flag(s):")
            for f in flags:
                print(f"    - {f}")

    except Exception as e:
        errors.append(("generate", str(e)))
        print(f"  FAIL generate: {e}")
        reports = {}

    timing["total"] = round(time.time() - t0, 2)

    # ── Human-readable summary ───────────────────────────────────
    summary_lines = [
        f"Test: {name}",
        f"Fixture: {fixture_path}",
        f"Ran: {step}",
        f"Total time: {timing['total']}s",
        f"",
    ]
    if classification:
        summary_lines.append(f"Incident type: {classification.get('incident_type')} "
                            f"({classification.get('label', '?')})")
        summary_lines.append(f"Charges: {classification.get('charges_applicable', [])}")
        persons = classification.get("persons_involved", [])
        for p in persons:
            summary_lines.append(f"  - {p.get('role')}: {p.get('name', '?')}")
    summary_lines.append("")
    if slots:
        summary_lines.append(f"Persons: {len(slots.get('persons', []))}")
        summary_lines.append(f"Narrative facts: {len(slots.get('narrative_facts', []))}")
        summary_lines.append(f"Quotes: {len(slots.get('quotes', []))}")
    summary_lines.append("")
    for report_type, text in reports.items():
        if isinstance(text, str):
            preview = text[:200].replace('\n', ' ')
            summary_lines.append(f"── {report_type} ({len(text)} chars) ──")
            summary_lines.append(f"   {preview}...")
            summary_lines.append("")
    (out_dir / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    # ── Compare (if requested) ───────────────────────────────────
    if compare:
        print()
        print("── Snapshot comparison ──")
        snapshot_dir = out_dir.parent / f"{name}_snapshot"
        if not snapshot_dir.exists():
            print(f"  No snapshot at {snapshot_dir} — saving current as baseline")
            # Copy current output to snapshot
            import shutil
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)
            shutil.copytree(out_dir, snapshot_dir)
        else:
            diffs_found = 0
            for fname in ["01_classify.json", "02_extract.json",
                          "03_gaps.json", "04_reports.json"]:
                cur = out_dir / fname
                prev = snapshot_dir / fname
                if not cur.exists():
                    print(f"  {fname}: missing in current run")
                    continue
                if not prev.exists():
                    print(f"  {fname}: no previous snapshot")
                    continue
                try:
                    cur_data = _load_json(cur)
                    prev_data = _load_json(prev)
                    diffs = _diff_dicts(prev_data, cur_data, "snapshot", "current")
                    if diffs:
                        diffs_found += 1
                        print(f"  DIFF {fname}: {len(diffs)} differences")
                        for d in diffs[:25]:
                            print(d)
                        if len(diffs) > 25:
                            print(f"  ... ({len(diffs) - 25} more)")
                    else:
                        print(f"  OK {fname}: identical")
                except Exception as e:
                    print(f"  WARN {fname}: comparison error - {e}")

                if diffs_found == 0:
                    print("  OK ALL: no differences from snapshot")
                else:
                    print(f"  DIFF {diffs_found} file(s) differ")

    print()
    if errors:
        for step_name, msg in errors:
            print(f"  ERROR [{step_name}]: {msg}")
        return 1
    return 0

# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run field notes through the report pipeline")
    parser.add_argument("fixture", nargs="?", default=None,
                        help="Fixture file path (relative to tests/fixtures/)")
    parser.add_argument("--step", choices=["classify", "extract", "generate"],
                        default="generate",
                        help="How far to run the pipeline (default: generate)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare against previous snapshot after running")
    parser.add_argument("--all", action="store_true",
                        help="Run all fixtures in tests/fixtures/")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    if args.all:
        fixtures = sorted(FIXTURES_DIR.glob("*.txt"))
        if not fixtures:
            print(f"No .txt fixtures found in {FIXTURES_DIR}")
            return 1
        exit_code = 0
        for fp in fixtures:
            print(f"\n{'='*60}")
            print(f"  {fp.stem}")
            print(f"{'='*60}")
            rc = run_pipeline(fp, step=args.step, compare=args.compare)
            if rc != 0:
                exit_code = 1
        return exit_code

    if not args.fixture:
        parser.error("Either --all or a fixture path is required")

    fp = Path(args.fixture)
    if not fp.is_absolute():
        fp = FIXTURES_DIR / args.fixture
    if not fp.exists():
        # Try as a name stem
        fp2 = FIXTURES_DIR / f"{args.fixture}.txt"
        if fp2.exists():
            fp = fp2
        else:
            print(f"Fixture not found: {args.fixture} (tried {fp}, {fp2})")
            print(f"Available fixtures:")
            for f in sorted(FIXTURES_DIR.glob("*.txt")):
                print(f"  {f.stem}")
            return 1

    return run_pipeline(fp, step=args.step, compare=args.compare)

if __name__ == "__main__":
    sys.exit(main())
