# Style rulings — AUTHORITATIVE

Decisions made by the unit supervisor against the evidence in `STYLE_FINDINGS.md`.
**This file wins over `report_style_guide.md`, `REPORT_WRITING_RULES.md`, and the
prompts.** Where the code currently disagrees, the code is wrong and must change.

No style change ships without a ruling recorded here first.

| # | Question | **RULING** | Code today | Action |
|---|---|---|---|---|
| 1 | Injury / treatment lines on the 005 | **`MSF 205`** | *(blank)* | change |
| 2 | Rank abbreviation | **`Sgt.` — keep the period** (it is an abbreviation) | strips it | change |
| 3 | PRESENT lines on the 005 | **`Same as above`** | `See Above` | change |
| 4 | ADC number format | **`ADC# 123456`** (space after `#`) | `ADC#123456` | change |
| 5 | Charging closer | **`Due to the above stated facts...`** | matches | keep |
| 6 | `inmate` before a name | **lowercase mid-sentence** (`inmate Smith`) | capitalizes | change |
| 7 | Voice | **one house style for all officers** | matches | keep |

## Detail

### 1. `MSF 205` on injury and treatment lines
`EXTENT OF INJURY TO INMATE(S)` and `TREATMENT AFFORDED INMATE(S)` carry
**`MSF 205`** — the medical form reference. Not blank, and **not**
"See Medical Report" / "See Infirmary Report".

Affects `SEE_INFIRMARY` / `SEE_MEDICAL` in `backend/webapp/routes/reports.py`,
currently `""`.

Officer lines stay `N/A` when no officer was injured.

### 2. Rank keeps its period
`Sgt.` `Cpl.` `Lt.` `Cpt.` — it is an abbreviation, so it takes a period.

Two places currently fight this and both must change:
- `_clean_report()` in `generator.py` strips it via regex.
- `prompts_v2.py` instructs *"NEVER use a period after a rank."*

### 3. `Same as above`
`INMATE(S) PRESENT` and `EMPLOYEE(S) PRESENT` → **`Same as above`** (not
`See Above`). `OTHERS PRESENT/INVOLVED` → `N/A` when nobody else was involved.

### 4. `ADC# 123456`
One space after the `#`, everywhere — narrative and form alike.

### 5. Charging closer
> `Due to the above stated facts I, {Rank} {First} {Last}, am charging inmate {Last}, {First} ADC# {number} with major rule violation {code} pending DCR.`

Plural to `major rule violations {a}, {b}, and {c}` when charging more than one.

### 6. `inmate` is lowercase mid-sentence
`...escorted inmate Smith to the infirmary.` Capitalized only at the start of a
sentence. Applies to the narrative; the 005 form's printed field labels are
unaffected.

### 7. One house style
Every officer's report is generated in the same format. Personal quirks
(`End of Statement.` vs `End of report.`) are **not** reproduced per-officer.
Officers can still edit before filing.

---

## Still open — do not implement without a ruling

| Question | Options seen | Status |
|---|---|---|
| Narrative time format | `7:15pm` / `9:12 pm` / `11:45AM` | code does `7:15pm`; unconfirmed |
| 005 form time format | `APX. 9:50 PM` (differs from narrative) | unconfirmed |
| Statement closer | `End of report.` / `End of Statement.` / `Disciplinary action taken.` | unconfirmed |
| Investigation reports as a 5th generated type | `I started an investigation at X and concluded it at Y with the following findings:` | unconfirmed |
| 005 continuation page for long narratives | form exists, filler has no support | unconfirmed |
| New categories: use of force, medical emergency | both common; checklist has neither | unconfirmed |
