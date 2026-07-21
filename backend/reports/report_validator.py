"""
Report Writing Rules Validator — deterministic post-generation checker.
Scores reports against every rule in REPORT_WRITING_RULES.md.

Usage:
    from report_validator import validate_report, validate_all
    result = validate_report("first_person", report_text, officer, notes)
    print(result.score, result.violations)
"""
import re
from dataclasses import dataclass, field
from typing import Optional

# --- Medical / forbidden words ---
MEDICAL_WORDS = [
    "laceration", "fracture", "contusion", "abrasion", "hematoma",
    "diagnosed", "treated by", "prescribed", "stitches", "sutures",
    "concussion", "hemorrhage", "internal injury", "spinal",
]

FORBIDDEN_WORDS = [
    "clearly", "obviously", "unfortunately", "thankfully",
    "luckily", "miraculously",
]

FORBIDDEN_PLACEHOLDERS = [
    "[incident number]", "[name]", "[date]", "[time]", "[location]",
    "[NEEDED:", "[TO BE SUPPLEMENTED:",
]


@dataclass
class Violation:
    rule_id: str       # e.g. "RW-001"
    severity: str      # BLOCKING, ERROR, WARN
    message: str
    context: str = ""  # snippet of text that triggered it


@dataclass
class ValidationResult:
    report_type: str
    violations: list = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    
    @property
    def score(self) -> float:
        total = self.checks_passed + self.checks_failed
        return self.checks_passed / total if total > 0 else 1.0
    
    @property
    def blocking(self) -> list:
        return [v for v in self.violations if v.severity == "BLOCKING"]
    
    @property
    def has_blocking(self) -> bool:
        return len(self.blocking) > 0


def validate_report(report_type: str, text: str, officer: dict,
                    notes: str = "", auto_content: list[str] = None) -> ValidationResult:
    """Validate a single generated report against all rules."""
    r = ValidationResult(report_type=report_type)
    
    rank = officer.get("rank", "")
    first = officer.get("first", "")
    last = officer.get("last", "")
    emp_no = officer.get("employee_number", "")
    
    c = lambda rid, sev, msg, ctx="": _check(r, rid, sev, msg, text, ctx)
    
    # --- RW-001: Inmate first reference ---
    # Accept: "Inmate Last, First ADC#number" OR "Inmate Last ADC#number" (no first name available)
    has_full = re.search(r'Inmate [A-Z][a-z]+, [A-Z][a-z]+ ADC#\d+', text)
    has_last_adc = re.search(r'Inmate [A-Z][a-z]+ ADC#\d+', text)
    has_last_only = re.search(r'Inmate [A-Z][a-z]+', text)
    if has_full or has_last_adc:
        r.checks_passed += 1
    elif has_last_only:
        c("RW-001", "WARN", "Inmate referenced by last name only — ADC# missing from first reference")
    else:
        c("RW-001", "BLOCKING", "No recognizable inmate reference found")
    
    # --- RW-003: Officer self-reference exactly once ---
    # ONLY for first-person reports. Supervisor summaries/cover letters are third person.
    if report_type in ("first_person", "disciplinary"):
        full_ref = f"I, {rank} {first} {last}"
        count = text.count(full_ref)
        if count == 1:
            r.checks_passed += 1
        elif count == 0:
            c("RW-003", "BLOCKING", f"Missing self-reference '{full_ref}'")
        else:
            c("RW-003", "ERROR", f"Self-reference '{full_ref}' appears {count} times (must be exactly 1)")
        
        # Own name after first reference
        if last and first:
            after_first = _after_first_ref(text, full_ref)
            if after_first and (f"{rank} {last}" in after_first or f"{rank} {first} {last}" in after_first):
                c("RW-003", "ERROR", "Officer refers to self by name/rank after initial reference")
    else:
        r.checks_passed += 1  # Not applicable for third-person reports
    
    # --- RW-004: Time format ---
    times = re.findall(r'approximately \d{1,2}:\d{2}[ap]m', text)
    bad_times = re.findall(r'\d{2}:\d{2}\s?[AP]\.?M\.?|\d{4}\s?hours', text)
    if not bad_times:
        r.checks_passed += 1
    else:
        c("RW-004", "BLOCKING", f"Non-standard time format: {bad_times}")
    
    # --- RW-006: No "Unknown"/"None" as name ---
    if re.search(r'\b(None|Unknown)\b', text):
        c("RW-006", "BLOCKING", "Placeholder name 'None' or 'Unknown' found in text")
    else:
        r.checks_passed += 1
    
    # --- RW-010: Opening sentence ---
    sentences = _split_sentences(text)
    if sentences:
        first_sent = sentences[0]
        # Accept various date formats: "July 21, 2026", "07-21-2026", "7/21/2026"
        patterns = [
            r'On .+ at approximately .+ I, .+, was .+ when .+',
            r'On .+ at approximately .+ I, .+, was notified by .+ that .+',
            r'On .+ I, .+, was notified .+ that .+',  # cover letter: "On DATE I, RANK NAME, was notified..."
        ]
        if any(re.match(p, first_sent, re.I) for p in patterns):
            r.checks_passed += 1
        else:
            c("RW-010", "WARN", f"Opening may not match formula: '{first_sent[:100]}...'")
    
    # --- RW-013: Disciplinary closing ---
    if report_type == "disciplinary":
        if "Pending DCR." in text:
            r.checks_passed += 1
        else:
            c("RW-013", "BLOCKING", "Disciplinary report missing 'Pending DCR.' closing")
    
    # --- RW-020: Personal observation ---
    if "notified" in notes.lower() or "reported" in notes.lower():
        if "observed" in text.lower() or "witnessed" in text.lower() or "saw" in text.lower():
            c("RW-020", "BLOCKING", "Claims observation/witnessing but notes indicate notification")
        else:
            r.checks_passed += 1
    else:
        r.checks_passed += 1  # skip if can't determine
    
    # --- RW-030: No fabrication ---
    if notes:
        flags = invented_facts(text, notes, {})
        # Exclude pure date tokens (the date is a form field, always auto-generated)
        date_only = re.compile(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$|^\d{4}[-/]\d{1,2}[-/]\d{1,2}$')
        flags = [f for f in flags if not date_only.match(f)]
        # Also exclude tokens that look like incident numbers (auto-generated)
        flags = [f for f in flags if not re.match(r'^\d{2}-\d{2}-\d{3}$', f)]
        if not flags:
            r.checks_passed += 1
        else:
            c("RW-030", "BLOCKING", f"Fabricated facts: {flags}")
    
    # --- RW-031: No medical detail ---
    lower = text.lower()
    med_hits = [w for w in MEDICAL_WORDS if w.lower() in lower]
    if not med_hits:
        r.checks_passed += 1
    else:
        c("RW-031", "BLOCKING", f"Medical detail found: {med_hits}")
    
    # --- RW-032: Required sentences present ---
    if auto_content:
        missing = [s for s in auto_content if s.lower() not in text.lower()]
        if not missing:
            r.checks_passed += 1
        else:
            c("RW-032", "BLOCKING", f"Missing required sentences: {len(missing)}")
            for m in missing[:3]:
                c("RW-032", "BLOCKING", f"  Missing: '{m[:120]}...'")
    
    # --- RW-033: No bracketed placeholders ---
    hits = [p for p in FORBIDDEN_PLACEHOLDERS if p in text]
    if not hits:
        r.checks_passed += 1
    else:
        c("RW-033", "BLOCKING", f"Bracketed placeholders: {hits}")
    
    # --- RW-034: Objective tone ---
    forbidden_hits = [w for w in FORBIDDEN_WORDS if w.lower() in lower]
    if not forbidden_hits:
        r.checks_passed += 1
    else:
        c("RW-034", "ERROR", f"Subjective language: {forbidden_hits}")
    
    # --- RW-035: No first-person in supervisor ---
    if report_type == "supervisor_summary":
        # Remove quoted text
        no_quotes = re.sub(r'"[^"]*"', '', text)
        no_quotes = re.sub(r"'[^']*'", '', no_quotes)
        if re.search(r'\bI\b', no_quotes) or re.search(r'\bme\b', no_quotes):
            c("RW-035", "BLOCKING", "First-person pronouns in supervisor summary")
        else:
            r.checks_passed += 1
    
    return r


def invented_facts(text: str, notes: str, answers: dict) -> list[str]:
    """Check every ADC#, time, date in output appears in input."""
    source = (notes + " " + " ".join(str(v) for v in answers.values())).lower()
    source_clean = re.sub(r'\s', '', source)
    
    tokens = set(re.findall(
        r'ADC#\s?\d+|\d{1,2}[:/-]\d{2}(?:[/-]\d{2,4})?(?:\s?[ap]\.?m\.?)?',
        text, re.I))
    
    return [t for t in tokens
            if re.sub(r'\s', '', t.lower()) not in source_clean]


def validate_all(reports: dict, officer: dict, notes: str = "",
                 auto_content: list[str] = None) -> dict:
    """Validate all report types and return combined result."""
    results = {}
    for rtype, text in reports.items():
        results[rtype] = validate_report(rtype, text, officer, notes, auto_content)
    return results


def _check(r: ValidationResult, rule_id: str, severity: str,
           message: str, text: str, context: str = ""):
    r.violations.append(Violation(rule_id, severity, message, context))
    r.checks_failed += 1


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences naively."""
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def _after_first_ref(text: str, full_ref: str) -> str:
    """Return text after the first occurrence of full_ref."""
    idx = text.find(full_ref)
    if idx < 0:
        return text
    return text[idx + len(full_ref):]
