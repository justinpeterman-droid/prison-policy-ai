# REPORT_WRITING_RULES.md — Single Source of Truth

Every rule BMU/ADC reports must follow. Sourced from Sgt. Peterman's actual
reports (2023–2024) and codified into deterministic checks.

## Rule Index

Each rule has an ID (`RW-###`) and a severity: `BLOCKING` (must fix before use),
`ERROR` (should fix), `WARN` (review).

---

## NAMING CONVENTIONS

### RW-001 — Inmate First Reference [BLOCKING]
`Inmate {Last}, {First} ADC#{number}`
- Example: "Inmate Smith, John ADC#123456"
- After first reference: "Inmate {Last}" is acceptable
- Regex: `Inmate [A-Z][a-z]+, [A-Z][a-z]+ ADC#\d+`

### RW-002 — Staff Naming [BLOCKING]
`{Rank} {First} {Last}` — Cpl. / Sgt. / Lt. / Cpt.
- Example: "Sgt. Justin Peterman"
- Never: "Officer Joe" or bare last name alone

### RW-003 — Reporting Officer Self-Reference [BLOCKING]
- FIRST reference: `I, {Rank} {First} {Last},`
- EVERY reference after: `I` / `me` / `my` — NEVER own rank+name again
- NEVER written in third person for self
- Check: count of `I, {own_rank} {own_first} {own_last}` must be exactly 1
- Check: own name must NOT appear again outside first reference

### RW-004 — Time Format [BLOCKING]
`approximately {H:MM}{am/pm}` — lowercase, no space
- Example: "approximately 10:00pm"
- Never: "10:00 PM", "2200 hours", "22:00"
- Check: all times match `approximately \d{1,2}:\d{2}[ap]m`

### RW-005 — Dates [WARN]
As provided by officer — do not reformat
- Both `7/21/2026` and `7-21-26` are valid
- Check: date in output matches date in input

### RW-006 — Unknown Names [BLOCKING]
If first name unknown: "Inmate {Last}" only
- NEVER: "None", "Unknown", placeholder text
- Check: no "None" or "Unknown" as a name

---

## STRUCTURE RULES

### RW-010 — Opening Sentence [BLOCKING]
Exactly one of two formulas:
1. Activity: `On {date} at approximately {time} I, {Rank} {First} {Last}, was {assigned post/activity} when {trigger event}.`
2. Notification: `On {date} at approximately {time} I, {Rank} {First} {Last}, was notified by {source} that {event}.`

Pick NOTIFIED unless officer personally witnessed the trigger.
Check: first sentence must match one of these patterns.

### RW-011 — Chronological Order [WARN]
Past tense. One action per sentence. Events in order they occurred.

### RW-012 — Single Combined Sentences [ERROR]
When same action applies to multiple people, write ONE combined sentence:
- ✓ "I applied hand restraints to Inmate Smith and Inmate Jones."
- ✗ "I applied hand restraints to Inmate Smith. I applied hand restraints to Inmate Jones."
- Check: no consecutive sentences with identical structure differing only by name

### RW-013 — Disciplinary Closing [BLOCKING]
Disciplinary reports MUST end with:
`Due to the above stated facts I, {Rank} {First} {Last}, am charging Inmate {Last}, {First} ADC#{number} with rule violation {codes}. Pending DCR.`
- One sentence per charged inmate
- Check: report ends with "Pending DCR."

---

## ATTRIBUTION RULES

### RW-020 — Personal Observation Only [BLOCKING]
Only claim officer saw/observed what facts state he witnessed.
- If told/notified: `was notified by {person} that...`
- Never: `observed` or `witnessed` for reported events
- Check: if notes say "notified" or "reported," output must NOT say "observed"

### RW-021 — Secondhand Attribution [ERROR]
Attributed with: `{person} stated/informed me that...`
- No unattributed secondhand facts

### RW-022 — Verbatim Quotes [BLOCKING]
Inmate statements/profanity in QUOTES are verbatim — never censored or paraphrased.
- They are evidence

### RW-023 — Unsubstantiated Allegations [WARN]
Stated as: `I was unable to substantiate...`

---

## CONTENT RULES

### RW-030 — No Fabrication [BLOCKING]
Every name, ADC#, time, and date in output MUST appear in officer's input.
- invented_facts() scan runs automatically
- Flagged tokens get yellow highlight in UI

### RW-031 — No Medical Detail [BLOCKING]
Do NOT describe injuries, wounds, diagnoses, evaluator names, or treatment outcomes.
- Medical reference is provided by auto_content sentences — use those verbatim
- Never add: diagnosis, injury detail, evaluator's name, treatment outcome
- Check: no words like "laceration," "fracture," "diagnosed," "treated by"

### RW-032 — Required Sentences [BLOCKING]
auto_content sentences from checklist MUST appear verbatim in narrative.
- Check: every auto_content text string is a substring of the output (case-insensitive)

### RW-033 — No Bracketed Placeholders [BLOCKING]
Never: `[incident number]`, `[name]`, `[NEEDED: ...]`
- If value missing, omit the clause — don't invent a placeholder
- (Exception: TO BE SUPPLEMENTED markers only in draft, stripped before final)

### RW-034 — Objective Tone [ERROR]
No opinions, speculation, or emotional language.
- No: "clearly," "obviously," "unfortunately," "thankfully"
- "Appeared to have a seizure" — not "had a seizure" (officers aren't medical staff)
- Check: prohibited words list

### RW-035 — No First-Person in Supervisor Summary [BLOCKING]
Supervisor summary must be third person throughout.
- Never: "I" outside quotation marks
- Check: count of " I " and " me " and " my " equals 0 (except in quotes)

---

## SIGNATURE / FORM RULES

### RW-040 — Per-Officer Reports [WARN]
Each staff member named in notes can have own report.
- Contains ONLY their actions/observations
- Secondhand for that officer: "{Other Officer} informed me that..."

---

## HARD CHECKS (deterministic, run in code)

| Check | Severity | Implementation |
|-------|----------|---------------|
| Inmate first-ref matches regex | BLOCKING | validate.py |
| Every ADC#/time/date in output appears in input | BLOCKING | invented_facts() |
| Disciplinary ends with "Pending DCR." | BLOCKING | regex |
| No first-person in supervisor summary | BLOCKING | regex |
| No medical detail words | BLOCKING | keyword blocklist |
| Required sentences present verbatim | BLOCKING | substring check |
| Officer self-reference count = 1 | ERROR | regex |
| No bracketed placeholders | BLOCKING | regex |
| No consecutive duplicate sentences | ERROR | levenshtein |
| Names match roster when available | WARN | roster lookup |

---

## TEST NOTES (canonical test cases)

### Test 1: Standard Fight
```
Smith ADC#123456 and Jones ADC#654321 fighting 8 Barracks ~10pm.
Jones cut over eye. Sgt Peterman cuffed both.
Cpl Powell and Sohns escorted Jones to Infirmary.
```
Expected: enemy_alert, restraint_line, escort_line, medical note, charges

### Test 2: Notification (not witnessed)
```
Inmate Williams ADC#111111 reported to me that Inmate Davis ADC#222222
stole his commissary from 4 House ~2pm. I reviewed camera footage which
confirmed the theft. Confiscated items returned to Williams.
```
Expected: NOTIFIED opening, attributed facts, no "observed"
