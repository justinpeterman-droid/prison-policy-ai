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
| 8 | Investigation reports | **yes — 5th generated type**, only when an investigation actually happened | 4 types | build |
| 9 | `use_of_force` category | **yes — add it**; ticks **both** 005 and 409 boxes | not a category | build |
| 10 | `medical_emergency` category | **yes — add it**; takes precedence over `incident_no_disciplinary` | not a category | build |

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

### 8. Investigation report — new 5th generated type

Generated **only when the field notes show an investigation actually took place**
(statements collected, camera footage reviewed, findings reached). A simple
incident must not produce an empty investigation report.

Structure observed in the archive:

```
I started an investigation at {start_time} and concluded it at {end_time}
on {date} with the following findings: {findings, chronological}
{disposition — rehousing, separation alert, medical, evidence}
{charging closer, if charges are brought}
```

Needs new slots: `investigation_start_time`, `investigation_end_time`,
`investigation_findings`. Detection should be a deterministic signal from
extraction, not a guess by the generator.

### 9. `use_of_force` — new category, ticks BOTH form boxes

The 005 header carries two checkboxes: **Incident Report** (005) and **Use of
Force** (409). When the category is `use_of_force`, **both are ticked** — the
incident is filed as a 005 that additionally carries the 409 designation.

> Note: on the paper NCU checklist, use of force is a *form designation* rather
> than one of the seven categories. Adding it as a category is a deliberate
> divergence, so the generator can ask force-specific questions (chemical agent
> type, lot/serial numbers, taser deployment, decontamination, authorizing
> officer) that no existing category covers.

### 10. `medical_emergency` — new category, takes precedence

Seizures, injuries and medical events classify as `medical_emergency`.
`incident_no_disciplinary` keeps the remaining non-disciplinary incidents
(fires, accidents, property).

Where both could apply, **medical wins** — it has its own gap questions
(evaluation, observation orders, gurney/escort, ward placement) that the generic
category does not ask.

---

## Implementation checklist — ALL SHIPPED

Rulings 1–7 are formatting and were low risk. Rulings 8–10 are structural:

| Ruling | Touches |
|---|---|
| ✅ 1 `MSF 205` | `SEE_INFIRMARY` / `SEE_MEDICAL` in `routes/reports.py` |
| ✅ 2 `Sgt.` period | `_clean_report()` in `generator.py`; `prompts_v2.py` rule |
| ✅ 3 `Same as above` | `SEE_ABOVE` in `routes/reports.py` |
| ✅ 4 `ADC# 123456` | `name_fixer.py`, `prompts_v2.py`, `report_style_guide.md` |
| ✅ 6 lowercase `inmate` | `name_fixer.py`, `prompts_v2.py` |
| ✅ 8 investigation type | `prompts_v2.py`, `generator.py`, `schema.py`, `validate.py`, reports UI |
| ✅ 9 `use_of_force` | `incident_checklist_v2.json`, `classifier.py` (`VALID_CATEGORIES` + response schema enum), `filler.py` (409 checkbox) |
| ✅ 10 `medical_emergency` | `incident_checklist_v2.json`, `classifier.py`, classifier prompt precedence |

✅ Rulings 9 and 10 took the category count from **7 → 9**, changed atomically
across `VALID_CATEGORIES`, the `CLASSIFIER_RESPONSE_SCHEMA` enum, the classifier
prompt, `incident_checklist_v2.json`, `routes/reports.py`, `reports.html`, and the
parity tests. `tests/unit/test_classifier_schema.py` fails on any partial change.

### How ruling 8 is gated

The investigation report is generated only when `investigation_findings` comes
back non-empty from extraction. That is a **deterministic check**
(`validate.investigation_occurred()`), not a judgement the generator makes — the
same contract as every other slot: the officer's notes decide. An ordinary
incident yields no findings, so no investigation report is written. The
follow-up gap questions (start time, end time, disposition) are gated the same
way, so a routine incident is never interrogated about an investigation it never
had.

### Not yet done

Ruling 9 says the 005 header ticks **both** the 005 and 409 boxes. The category
and its gap questions ship, but `filler.py` does not tick either box — the two
checkbox cells in `005_template_v3.docx` carry no `{{placeholder}}`, so the
template itself needs editing first. Neither box is ticked on any generated 005
today, which predates this work.

---

## Still open — do not implement without a ruling

| Question | Options seen | Status |
|---|---|---|
| Narrative time format | `7:15pm` / `9:12 pm` / `11:45AM` | code does `7:15pm`; unconfirmed |
| 005 form time format | `APX. 9:50 PM` (differs from narrative) | unconfirmed |
| Statement closer | `End of report.` / `End of Statement.` / `Disciplinary action taken.` | unconfirmed |
| 005 continuation page for long narratives | form exists, filler has no support | unconfirmed |
