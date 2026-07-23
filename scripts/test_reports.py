#!/usr/bin/env python3
"""
Self-Teaching Report Test Harness
=================================
Feeds test notes through the full pipeline (classify -> extract -> generate),
validates every output against REPORT_WRITING_RULES.md.

Usage:
    python scripts/test_reports.py                    # run all test cases
    python scripts/test_reports.py --notes "..."      # test custom notes
    python scripts/test_reports.py --loop 3           # loop N times to check consistency
"""
import json
import sys
import requests
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "reports"))
from report_validator import validate_report, validate_all

BASE_URL = "https://prison-policy-ai-403037827694.us-central1.run.app"
ACCESS_CODE = "slut"
API_TIMEOUT = 120  # seconds — generate can be slow on Cloud Run

TEST_CASES = [
    {
        "name": "Standard Fight (witnessed)",
        "notes": "Smith ADC#123456 and Jones ADC#654321 fighting 8 Barracks ~10pm. Jones cut over eye. Sgt Peterman cuffed both. Cpl Powell and Sohns escorted Jones to Infirmary.",
    },
    {
        "name": "Notification (not witnessed)",
        "notes": "Inmate Williams ADC#111111 reported to me that Inmate Davis ADC#222222 stole his commissary from 4 House ~2pm. I reviewed camera footage which confirmed the theft. Confiscated items returned to Williams.",
    },
    {
        "name": "Single Inmate Contraband",
        "notes": "Inmate Brown ADC#888888 found with cell phone during shakedown 2 House ~8am. Sgt Peterman confiscated phone and placed Brown in RH.",
    },
]


def _api(path, data=None, method="POST"):
    s = requests.Session()
    s.get(f"{BASE_URL}/?code={ACCESS_CODE}", allow_redirects=True)
    if method == "POST":
        r = s.post(f"{BASE_URL}{path}", json=data, timeout=API_TIMEOUT)
    else:
        r = s.get(f"{BASE_URL}{path}", timeout=API_TIMEOUT)
    r.raise_for_status()
    return r.json()


def classify(notes: str) -> dict:
    return _api("/api/reports/classify", {"notes": notes})


def extract(notes: str, category: str) -> dict:
    return _api("/api/reports/extract", {"notes": notes, "category": category})


def generate(notes: str, category: str, slots: dict, answers: dict,
             reporter_index: int = 0) -> dict:
    return _api("/api/reports/generate", {
        "notes": notes,
        "category": category,
        "slots": slots,
        "answers": answers,
        "reporter_index": reporter_index,
    })


def run_test(name: str, notes: str, verbose: bool = True) -> dict:
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"NOTES: {notes}")
    print(f"{'='*60}")
    
    result = {"name": name, "notes": notes}
    
    # Step 1: Classify
    print("\n[1/3] Classifying...", end=" ", flush=True)
    try:
        c = classify(notes)
        incident_type = c.get("incident_type", "unknown")
        print(f"-> {incident_type}")
        result["incident_type"] = incident_type
    except Exception as e:
        print(f"FAIL: {e}")
        return result
    
    # Step 2: Extract
    print("[2/3] Extracting...", end=" ", flush=True)
    try:
        e = extract(notes, incident_type)
        slots = e.get("slots", {})
        gaps = e.get("gaps", [])
        officers = e.get("officers", [])
        blocking = e.get("blocking_remaining", 0)
        print(f"-> {len(officers)} officers, {len(gaps)} gaps ({blocking} blocking)")
        
        # Use first officer — fall back to default if names are null
        if officers:
            raw = officers[0]
            rl = raw.get("last")
            rf = raw.get("first")
            # If the extracted officer has no name (first-person unnamed gap),
            # use the default test officer so validation has real names.
            if rl and rf:
                officer = {
                    "rank": raw.get("rank") or "",
                    "first": rf,
                    "last": rl,
                    "employee_number": raw.get("employee_number", ""),
                }
            else:
                officer = {"rank": "Sgt.", "first": "Justin", "last": "Peterman",
                           "employee_number": "B5123"}
                print("  Reporter: [default] (unnamed in notes)")
        else:
            officer = {"rank": "Sgt.", "first": "Justin", "last": "Peterman",
                       "employee_number": "B5123"}
            print("  Reporter: [default]")
    except Exception as e:
        print(f"FAIL: {e}")
        return result
    
    # Step 3: Generate
    print("[3/3] Generating reports...", end=" ", flush=True)
    
    # Fill gaps with defaults
    answers = {}
    for g in gaps:
        slot = g.get("slot", "")
        if not slot:
            continue
        atype = g.get("answer_type", "text")
        if atype == "choice":
            answers[slot] = g.get("default", "") or (g.get("options", [""])[0] if g.get("options") else "")
        elif atype == "yes_no":
            answers[slot] = "Yes"
        elif slot == "officer_name":
            answers[slot] = "Sgt. Justin Peterman"
        else:
            answers[slot] = f"TEST-{slot}"
    
    reports = {}
    try:
        gen = generate(notes, incident_type, slots, answers, 0)
        reports = gen.get("reports", {})
        flags = gen.get("flags", [])
        print(f"-> {len(reports)} reports, {len(flags)} flags")
        result["reports"] = list(reports.keys())
        result["flags"] = len(flags)
    except Exception as e:
        print(f"FAIL: {e}")
        result["generate_error"] = str(e)[:200]
        return result
    
    # ─── VALIDATION ──────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("VALIDATION")
    print(f"{'─'*60}")
    
    if not reports:
        print("  No reports to validate")
        return result
    
    results = validate_all(reports, officer, notes)
    
    total = 0
    blocking = 0
    for rtype, vr in results.items():
        text = reports.get(rtype, "")
        score_pct = vr.score * 100
        passed = vr.checks_passed
        failed = vr.checks_failed
        print(f"\n  [{rtype}] {score_pct:.0f}% ({passed}/{passed + failed} checks passed)")
        
        # Show the generated text snippet
        short = text[:200].replace('\n', ' ')
        print(f"  Text: {short}...")
        
        for v in vr.violations:
            sev = v.severity
            marker = "BLOCK" if sev == "BLOCKING" else "ERROR" if sev == "ERROR" else "WARN "
            print(f"    [{marker}] {v.rule_id}: {v.message[:150]}")
            total += 1
            if sev == "BLOCKING":
                blocking += 1
    
    result["validation"] = {
        "total_violations": total,
        "blocking": blocking,
        "scores": {rt: vr.score for rt, vr in results.items()},
    }
    
    print(f"\n  -> {total} violations ({blocking} blocking)")
    print(f"  -> {'PASS' if blocking == 0 else 'FAIL'}")
    
    return result


def run_all(loop: int = 1):
    all_results = []
    for i in range(loop):
        if loop > 1:
            print(f"\n{'#'*60}")
            print(f"ITERATION {i + 1}/{loop}")
            print(f"{'#'*60}")
        for tc in TEST_CASES:
            r = run_test(tc["name"], tc["notes"])
            all_results.append(r)
    
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in all_results
                 if r.get("validation", {}).get("blocking", 999) == 0)
    print(f"  {len(all_results)} tests: {passed} PASS, {len(all_results) - passed} FAIL")
    for r in all_results:
        v = r.get("validation", {})
        b = v.get("blocking", "?")
        s = "PASS" if b == 0 else "FAIL" if isinstance(b, int) else "ERR"
        print(f"  [{s}] {r['name']}: {b} blocking")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--notes", type=str)
    p.add_argument("--loop", type=int, default=1)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()
    
    if args.notes:
        run_test("Custom", args.notes)
    else:
        run_all(args.loop)
