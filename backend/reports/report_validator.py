"""Deterministic post-generation checker. No AI in this file.

Scores each generated report against the rulings in
`templates/gold_reports/STYLE_RULINGS.md`. Runs after generation, after
`enforce_naming()` and `_clean_report()` have already done their deterministic
passes — so anything this still finds is something those could not fix.

Two kinds of finding:

  * BLOCKING — the report is wrong in a way an officer must not file. Surfaced
    in the UI; `repair()` fixes the subset that has a safe mechanical fix.
  * WARN     — worth a look, not worth stopping for.

What this deliberately does NOT do: rewrite facts. A validator that "fixes" a
report by inventing the missing piece is the exact failure this system exists to
prevent. Every repair here is a formatting transform on text that is already
there.

    from backend.reports.report_validator import validate_all, repair_all
    results = validate_all(reports, officer, notes, auto_content)
"""
import re
from dataclasses import dataclass, field

from backend.reports.validate import invented_facts

# Clinical language belongs in the infirmary report, never the 005.
MEDICAL_WORDS = [
    "laceration", "fracture", "contusion", "abrasion", "hematoma",
    "diagnosed", "treated by", "prescribed", "stitches", "sutures",
    "concussion", "hemorrhage", "internal injury", "spinal",
]

# Editorializing. A report states what happened.
FORBIDDEN_WORDS = [
    "clearly", "obviously", "unfortunately", "thankfully",
    "luckily", "miraculously",
]

# Placeholders the model must never emit. NOTE: '[TO BE SUPPLEMENTED:' is NOT
# here — that marker is produced deliberately by validate.py when the officer
# answers UNKNOWN, and flagging it would fight the checklist design.
FORBIDDEN_PLACEHOLDERS = [
    "[incident number]", "[name]", "[date]", "[time]", "[location]",
    "[NOT IN NOTES]", "[NEEDED:",
]

# Ruling 13: the house style has no closer. Individual officers write these.
CLOSERS = [
    "end of report.", "end of statement.", "end of report",
    "disciplinary action taken.",
]

# Ruling 4: 'ADC# 123456' — one space after the hash.
ADC_NO_SPACE = re.compile(r"ADC#\d")
# Ruling 2: ranks keep the period. A bare 'Sgt' before a capitalized name is
# the abbreviation written without one.
RANK_NO_PERIOD = re.compile(r"\b(Sgt|Cpl|Lt|Cpt)\s+[A-Z]")
# Ruling 11: '9:50 pm' — space, lowercase. Anything 24-hour or military is wrong.
BAD_TIME = re.compile(r"\b\d{1,2}:\d{2}\s?[AP]\.?M\.?|\b\d{3,4}\s?hours\b")
FIRST_PERSON_TYPES = ("first_person", "disciplinary")


@dataclass
class Violation:
    rule_id: str       # e.g. "RW-001"
    severity: str      # BLOCKING | WARN
    message: str
    context: str = ""  # snippet that triggered it


@dataclass
class ValidationResult:
    report_type: str
    violations: list = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0

    @property
    def score(self) -> float:
        total = self.checks_passed + self.checks_failed
        return self.checks_passed / total if total else 1.0

    @property
    def blocking(self) -> list:
        return [v for v in self.violations if v.severity == "BLOCKING"]

    @property
    def has_blocking(self) -> bool:
        return bool(self.blocking)

    def as_dict(self) -> dict:
        """JSON shape for the API response."""
        return {
            "report_type": self.report_type,
            "score": round(self.score, 3),
            "violations": [
                {"rule_id": v.rule_id, "severity": v.severity,
                 "message": v.message, "context": v.context}
                for v in self.violations
            ],
        }


def validate_report(report_type: str, text: str, officer: dict,
                    notes: str = "", auto_content: list | None = None,
                    allow: list | None = None,
                    answers: dict | None = None) -> ValidationResult:
    """Check one generated report against the rulings."""
    r = ValidationResult(report_type=report_type)
    if not text or not text.strip():
        _fail(r, "RW-000", "BLOCKING", "Report is empty")
        return r

    rank = (officer or {}).get("rank", "")
    first = (officer or {}).get("first", "")
    last = (officer or {}).get("last", "")
    lower = text.lower()

    _check_inmate_naming(r, text)
    _check_adc_spacing(r, text)
    _check_rank_periods(r, text)
    _check_self_reference(r, report_type, text, rank, first, last)
    _check_time_format(r, text)
    _check_placeholder_names(r, text)
    _check_opening(r, report_type, text)
    _check_charging_closer(r, report_type, text)
    _check_statement_closer(r, text, lower)
    _check_secondhand(r, text, notes, lower)
    _check_fabrication(r, text, notes, allow, answers)
    _check_medical_detail(r, text, lower)
    _check_required_sentences(r, text, auto_content)
    _check_placeholders(r, text)
    _check_tone(r, text, lower)
    _check_third_person(r, report_type, text)
    return r


# ── Individual rules ────────────────────────────────────────────────────────

def _check_inmate_naming(r, text):
    """RW-001 — first mention carries the full form (rulings 4, 6)."""
    # 'inmate' may be either case: capital at a sentence start, lowercase
    # mid-sentence. ADC# may carry the space or not — RW-002 judges the space.
    full = re.search(r"[Ii]nmate\s+[A-Z][\w'-]+,\s*[A-Z][\w'-]+\s+ADC#\s?\d+", text)
    last_adc = re.search(r"[Ii]nmate\s+[A-Z][\w'-]+\s+ADC#\s?\d+", text)
    bare = re.search(r"[Ii]nmate\s+[A-Z][\w'-]+", text)
    if full or last_adc:
        r.checks_passed += 1
    elif bare:
        _fail(r, "RW-001", "WARN",
              "Inmate referenced by last name only — no ADC# on first mention",
              _snippet(text, bare.start()))
    else:
        # Not every report names an inmate (a staff-only incident, a cover
        # letter). Absence is not a violation.
        r.checks_passed += 1


def _check_adc_spacing(r, text):
    """RW-002 — 'ADC# 123456', one space after the hash (ruling 4)."""
    m = ADC_NO_SPACE.search(text)
    if m:
        _fail(r, "RW-002", "BLOCKING", "ADC# written without a space after the hash",
              _snippet(text, m.start()))
    else:
        r.checks_passed += 1


def _check_rank_periods(r, text):
    """RW-003 — ranks keep their period: Sgt. / Cpl. / Lt. / Cpt. (ruling 2)."""
    m = RANK_NO_PERIOD.search(text)
    if m:
        _fail(r, "RW-003", "BLOCKING",
              f"Rank abbreviation missing its period: {m.group(1)}",
              _snippet(text, m.start()))
    else:
        r.checks_passed += 1


def _check_self_reference(r, report_type, text, rank, first, last):
    """RW-004 — the reporting officer names himself exactly once."""
    if report_type not in FIRST_PERSON_TYPES:
        r.checks_passed += 1
        return
    if not (rank or first or last):
        r.checks_passed += 1  # nothing to match against
        return
    full_ref = f"I, {rank} {first} {last}".strip()
    count = text.count(full_ref)
    if count == 1:
        r.checks_passed += 1
    elif count == 0:
        _fail(r, "RW-004", "BLOCKING", f"Missing self-reference '{full_ref}'")
    else:
        _fail(r, "RW-004", "BLOCKING",
              f"Self-reference '{full_ref}' appears {count} times (must be exactly 1)")

    if count and last and first:
        after = text.split(full_ref, 1)[1]
        for form in (f"{rank} {first} {last}".strip(), f"{rank} {last}".strip()):
            if form and form in after:
                _fail(r, "RW-004", "WARN",
                      "Officer refers to himself by rank/name after the first mention")
                return


def _check_time_format(r, text):
    """RW-005 — narrative times read '9:50 pm' (ruling 11)."""
    bad = BAD_TIME.findall(text)
    if bad:
        _fail(r, "RW-005", "BLOCKING",
              f"Non-standard time format: {sorted(set(bad))[:3]}")
    else:
        r.checks_passed += 1


def _check_placeholder_names(r, text):
    """RW-006 — 'None'/'Unknown' must never stand in for a name."""
    m = re.search(r"(?:[Ii]nmate|Sgt\.?|Cpl\.?|Lt\.?|Cpt\.?)\s+(None|Unknown)\b", text)
    if m:
        _fail(r, "RW-006", "BLOCKING",
              f"Placeholder '{m.group(1)}' used as a name", _snippet(text, m.start()))
    else:
        r.checks_passed += 1


def _check_opening(r, report_type, text):
    """RW-010 — the opening formula each prompt actually specifies."""
    first_sent = _split_sentences(text)
    if not first_sent:
        return
    opening = first_sent[0]
    if report_type in FIRST_PERSON_TYPES:
        # FIRST_PERSON_PROMPT: must begin 'I, {Rank} {First} {Last},'
        ok = re.match(r"^I,\s+\S+", opening)
    elif report_type == "cover_letter":
        # COVER_LETTER_PROMPT: 'On {date} I, {Rank} {First} {Last}, was notified...'
        ok = re.match(r"^On .+\bI,\s", opening)
    elif report_type == "investigation":
        # INVESTIGATION_PROMPT: 'I, ... started an investigation at ...'
        ok = re.match(r"^I,\s+.*started an investigation", opening, re.I)
    else:
        # supervisor_summary: 'On {date} at approximately {time} ...'
        ok = re.match(r"^On .+", opening)
    if ok:
        r.checks_passed += 1
    else:
        _fail(r, "RW-010", "WARN",
              f"Opening may not match the formula: {opening[:90]!r}")


def _check_charging_closer(r, report_type, text):
    """RW-013 — the disciplinary closer, worded per ruling 5."""
    if report_type != "disciplinary":
        return
    if re.search(r"Due to the above stated facts", text, re.I):
        r.checks_passed += 1
    else:
        _fail(r, "RW-013", "BLOCKING",
              "Disciplinary report missing the 'Due to the above stated facts' closer")
    if re.search(r"pending DCR", text, re.I):
        r.checks_passed += 1
    else:
        _fail(r, "RW-013", "BLOCKING", "Disciplinary report missing 'pending DCR'")


def _check_statement_closer(r, text, lower):
    """RW-014 — no statement closer (ruling 13)."""
    hit = next((c for c in CLOSERS if c in lower), None)
    if hit:
        _fail(r, "RW-014", "BLOCKING",
              f"Statement closer {hit!r} — the house style has none")
    else:
        r.checks_passed += 1


def _check_secondhand(r, text, notes, lower):
    """RW-020 — don't claim to have witnessed what was reported to you."""
    if not notes:
        r.checks_passed += 1
        return
    notes_lower = notes.lower()
    told = any(w in notes_lower for w in ("notified", "reported to me", "informed"))
    if told and re.search(r"\bI (observed|witnessed|saw)\b", text):
        _fail(r, "RW-020", "BLOCKING",
              "Claims firsthand observation, but the notes say the officer was notified")
    else:
        r.checks_passed += 1


def _check_fabrication(r, text, notes, allow, answers):
    """RW-030 — every ADC#, date and time in the output came from the officer.

    Uses the same checker the pipeline uses, with the same inputs: the notes,
    the officer's gap answers, and the allow-list of values the pipeline itself
    produced (a normalized 12-hour time, a fallback date, a built incident
    number). Passing anything less makes the system's own correct work read as
    fabrication — an ADC# the officer typed into the gap panel is not invented.
    """
    if not notes:
        return
    flags = invented_facts(text, notes, answers or {}, allow=allow)
    if flags:
        _fail(r, "RW-030", "BLOCKING", f"Facts not present in the source: {flags[:5]}")
    else:
        r.checks_passed += 1


def _check_medical_detail(r, text, lower):
    """RW-031 — clinical detail lives in the infirmary report, not here."""
    hits = [w for w in MEDICAL_WORDS if w in lower]
    if hits:
        _fail(r, "RW-031", "BLOCKING", f"Medical detail in the narrative: {hits}")
    else:
        r.checks_passed += 1


def _check_required_sentences(r, text, auto_content):
    """RW-032 — auto_content sentences appear verbatim."""
    if not auto_content:
        return
    lower = text.lower()
    missing = [s for s in auto_content if isinstance(s, str) and s.lower() not in lower]
    if missing:
        _fail(r, "RW-032", "BLOCKING",
              f"{len(missing)} required sentence(s) missing", missing[0][:120])
    else:
        r.checks_passed += 1


def _check_placeholders(r, text):
    """RW-033 — no bracketed placeholder text reaches the officer."""
    hits = [p for p in FORBIDDEN_PLACEHOLDERS if p in text]
    if hits:
        _fail(r, "RW-033", "BLOCKING", f"Bracketed placeholders: {hits}")
    else:
        r.checks_passed += 1


def _check_tone(r, text, lower):
    """RW-034 — objective language only."""
    hits = [w for w in FORBIDDEN_WORDS if re.search(rf"\b{w}\b", lower)]
    if hits:
        _fail(r, "RW-034", "WARN", f"Subjective language: {hits}")
    else:
        r.checks_passed += 1


def _check_third_person(r, report_type, text):
    """RW-035 — the supervisor summary is third person outside quotes."""
    if report_type != "supervisor_summary":
        return
    stripped = re.sub(r'"[^"]*"', "", text)
    if re.search(r"\b(I|me|my)\b", stripped):
        _fail(r, "RW-035", "BLOCKING",
              "First-person pronoun in the supervisor summary")
    else:
        r.checks_passed += 1


# ── Auto-repair ─────────────────────────────────────────────────────────────
#
# Only mechanical transforms of text that is already present. Nothing here can
# add, remove or change a fact — a "repair" that invents the missing piece is
# the failure mode this whole system exists to prevent.

def repair(text: str) -> tuple[str, list[str]]:
    """Apply the safe deterministic fixes. Returns (text, rules_repaired)."""
    if not text:
        return text, []
    fixed: list[str] = []

    # RW-002: 'ADC#123456' -> 'ADC# 123456' (ruling 4)
    new = ADC_NO_SPACE.sub(lambda m: m.group(0).replace("#", "# "), text)
    if new != text:
        fixed.append("RW-002")
        text = new

    # RW-003: 'Sgt Smith' -> 'Sgt. Smith' (ruling 2)
    new = RANK_NO_PERIOD.sub(lambda m: m.group(0).replace(
        m.group(1), m.group(1) + ".", 1), text)
    if new != text:
        fixed.append("RW-003")
        text = new

    # RW-014: strip a statement closer (ruling 13)
    new = re.sub(r"\s*(?:End of (?:report|statement)\.?|Disciplinary action taken\.)\s*$",
                 "", text, flags=re.I)
    if new != text:
        fixed.append("RW-014")
        text = new.rstrip()

    return text, fixed


def repair_all(reports: dict) -> tuple[dict, dict]:
    """Repair every report. Returns (reports, {report_type: [rule_ids]})."""
    out, repaired = {}, {}
    for rtype, text in reports.items():
        if not isinstance(text, str):
            out[rtype] = text
            continue
        out[rtype], fixed = repair(text)
        if fixed:
            repaired[rtype] = fixed
    return out, repaired


def required_sentences_for(report_type: str, auto_content: list | None) -> list[str]:
    """The auto_content sentences that belong in THIS report.

    Each item names the reports it targets via `insert_into`. Checking every
    report against every sentence flags a cover letter for missing the
    first-person narrative's lines — three false BLOCKING violations on a
    perfectly good set of reports.

    A plain list of strings (no routing information) is taken as applying to
    every report, so callers that already filtered still work.
    """
    out: list[str] = []
    for item in auto_content or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and report_type in item.get("insert_into", []):
            out.append(item.get("text", ""))
    return [s for s in out if s]


def validate_all(reports: dict, officer: dict, notes: str = "",
                 auto_content: list | None = None,
                 allow: list | None = None,
                 answers: dict | None = None) -> dict:
    """Validate every generated report. Keys mirror `reports`."""
    return {
        rtype: validate_report(rtype, text, officer, notes,
                               required_sentences_for(rtype, auto_content),
                               allow, answers)
        for rtype, text in reports.items()
        if isinstance(text, str)
    }


def summarize(results: dict) -> dict:
    """Flatten results into the JSON the UI renders."""
    blocking = [
        {"report_type": rtype, "rule_id": v.rule_id,
         "message": v.message, "context": v.context}
        for rtype, res in results.items() for v in res.blocking
    ]
    return {
        "reports": {rtype: res.as_dict() for rtype, res in results.items()},
        "blocking": blocking,
        "blocking_count": len(blocking),
        "score": (round(sum(r.score for r in results.values()) / len(results), 3)
                  if results else 1.0),
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def _fail(r: ValidationResult, rule_id: str, severity: str,
          message: str, context: str = ""):
    r.violations.append(Violation(rule_id, severity, message, context))
    r.checks_failed += 1


def _snippet(text: str, at: int, width: int = 60) -> str:
    start = max(0, at - width // 3)
    return text[start:start + width].strip()


# Ruling 2 requires the period on ranks, which makes a naive sentence split
# tear 'I, Sgt. Dana Vance, was assigned...' into 'I, Sgt.' — and then every
# opening-formula check fails on correct text. Abbreviations that legitimately
# end in a period never end a sentence here.
# The split point sits AFTER the period, so each lookbehind has to include it.
_ABBREV = (r"(?<!\bSgt\.)(?<!\bCpl\.)(?<!\bLt\.)(?<!\bCpt\.)"
           r"(?<!\bMr\.)(?<!\bMs\.)(?<!\bDr\.)(?<!\bAPX\.)")
_SENTENCE_SPLIT = re.compile(rf"(?<=[.!?]){_ABBREV}\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
