# Report-Writing Rules & Behavior (living spec)

This is the current, authoritative description of how the report generator
should behave — the accumulated rules Justin has asked for. It complements
`REPORT_ENGINE_SPEC.md` (the original build spec): that one says how the engine
was built; **this one says exactly what the output must do**, so Hermes (with
live GCP) can run reports, compare against these rules, and refine.

Each rule notes **where it lives** in code and whether it's **deterministic**
(guaranteed by Python, verified in-sandbox) or **prompt** (depends on the LLM,
must be validated on a live run).

---

## 1. Pipeline & safety model

```
notes ──▶ /classify ──▶ officer confirms type + AI-suggested charges
      ──▶ /extract  ──▶ Gemini fills a strict slot schema (null = not stated)
                        + deterministic gap questions
      ──▶ officer answers gaps (nothing blocks generation)
      ──▶ /generate ──▶ narrative-only LLM pass over STRUCTURED SLOTS
                        + deterministic auto-content sentences
```

- **Extraction is the ONLY place the raw notes are read.** It is grammar-constrained
  (`backend/reports/schema.py`) and returns `null` for anything the notes don't state.
- **Generation never sees the raw notes** — only structured slots + required
  sentences. Every header field is rendered by code.
- `invented_facts()` hard-checks that every ADC#, time, and date in the output
  traces back to the officer's input. Files: `backend/reports/validate.py`,
  `backend/reports/generator.py`, `backend/reports/prompts_v2.py`.

---

## 2. Missing-Information (gap) behavior

| Rule | Behavior | Where | Type |
|---|---|---|---|
| Nothing blocks generation | Continue is always enabled; blanks become `[TO BE SUPPLEMENTED]` markers on the Review card | `reports.html` `updateProgress()` | deterministic |
| Charges are not asked here | Picked from the handbook, confirmed in the charges panel | `validate.COLLECTED_ELSEWHERE` | deterministic |
| Involved lists not asked | `inmates_involved` / `employees_involved` come from the extracted persons | `routes/reports.py` `/extract` | deterministic |
| Medical disposition default | Pre-selects "Seen by Infirmary staff" for medical-involving incidents (fight, staff assault, forced cell move, PREA), else "N/A - no injuries reported"; changeable | `_apply_gap_defaults` | deterministic |
| Drug test default | Pre-selects "N/A" | `_apply_gap_defaults` | deterministic |
| Escort default (fights) | Pre-selects "Infirmary, then Restrictive Housing" | `_apply_gap_defaults` | deterministic |
| Missing inmate first name | Asks "First name for Inmate <Last>?" per inmate; if left blank, the name renders `[FIRST NAME NEEDED]` and a marker is surfaced | `/extract`, `/generate`, `_inmates_missing_first` | deterministic |
| Shift assignment | Filled from the unit roster; if unresolved, asks a question | `/extract`, roster | deterministic |

---

## 3. Deterministic field & value rules

| Field / rule | Behavior | Where |
|---|---|---|
| **Incident number** | `YYYY-MM-###` — year & month auto-filled; officer types only the last 3 digits | `_build_incident_number` |
| **Date** | If the notes don't state one, default to today | `/extract`, `/generate` |
| **Time** | Always 12-hour (`2200` → `10:00pm`, `0930` → `9:30am`) everywhere | `_to_12h` |
| **Shift** | Roster stores a letter (`A`..`F`); rendered as "`B Shift`". Follows the selected reporting officer | `_format_shift` |
| **Names capitalized** | Hand-typed names are title-cased (`john` → `John`) | `_titlecase` |
| **EXTENT/TREATMENT — INMATE** | Only "See Infirmary Report" (when medical was involved) or "N/A". Never medical detail on the 005 | `/generate` `MEDICAL_INJURY_DISPOSITIONS` |
| **EXTENT/TREATMENT — OFFICER** | "See Medical Report" only when the inmate used force on the officer (staff assault / recorded officer injury), else "N/A" | `/generate` `OFFICER_FORCE_CATEGORIES` |
| **INMATE/EMPLOYEE/OTHERS PRESENT** | "See Above" when the notes didn't name separate people present | `/generate` `SEE_ABOVE` |
| **Fights end in Restrictive Housing** | For fights/assaults the escort destination always ends at Restrictive Housing (after the infirmary if treated first) | `/generate` `FIGHT_RH_CATEGORIES` |
| **Download == preview** | The .docx download sends every field the reviewed on-screen 005 shows; template has 21 placeholders, all filled | `reports.html` `collectMetadata`, `filler.py` |

---

## 4. Auto-content sentences (deterministic, inserted verbatim)

Driven by `templates/incident_checklist_v2.json` and resolved in
`validate._resolve_auto_content`. A line fires only when its condition is met;
N/A / No / a missing slot produce nothing. Inmate references adapt to the count:
one inmate → the name ("Inmate Smith"), two or more → "The inmates" with the
correct verb (see `validate._inmate_phrases`).

**Universal (every category):**

| Trigger | Sentence | Inserted into |
|---|---|---|
| Medical = Seen by Infirmary staff | "Inmate Smith was seen by medical staff (refer to the Infirmary Report)." | first-person, supervisor |
| Medical = Refused | "…refused medical attention and the Refuse box was checked…" | first-person, supervisor |
| Medical = Ambulance | "…was transported by ambulance to an outside facility…" | first-person, supervisor |
| Photo/video = Yes | "Photographs were taken." | first-person, supervisor |
| Drug test = Conducted | "A drug test was conducted on Inmate Smith." | first-person, supervisor |
| Drug test = Refused | "…refused a drug test and the Refuse box was checked." | first-person, supervisor |
| Witness statements = Yes | "Witness statements were collected." | first-person, supervisor |
| **Charges present** | "Disciplinary action was taken against <inmate(s)> (refer to the Disciplinary Report)." | first-person, supervisor, cover letter |

**Fights (inmate_fight, staff_assault):**

| Trigger | Sentence | Inserted into |
|---|---|---|
| always | "Inmate Smith and Inmate Jones were involved in a physical altercation at BMU in <loc> on <date> (refer to BMU Incident Report <#>)." | disciplinary, cover letter |
| always | "The inmates were placed in Restrictive Housing." | first-person |
| always | restraint + escort, combined, ending at Restrictive Housing | supervisor |

> The restraint/escort line lives in the **supervisor summary only** — it is
> third-person, so it must not appear in the first-person report.

---

## 5. Narrative rules (PROMPT — validate on a live run)

In `backend/reports/prompts_v2.py` (`STYLE_RULES` + per-report prompts):

- **First person throughout** for the reporting officer ("I, Sgt. First Last," then "I"); never revert to third person or restate his own rank+name.
- **Notified ≠ observed**: if an event was reported to him, "was notified by X that…", never "observed"/"witnessed".
- **First mention = full name**: staff "Rank First Last" then "Rank Last"; inmate "Inmate Last, First ADC#" then "Inmate Last". Never a bare last name on first mention.
- **Combine repeated actions**: one sentence when the same action applies to several people ("I applied hand restraints to Inmate Smith and Inmate Jones."), never one per person.
- **No self-written medical sentence** — the required sentences already carry the medical reference (combined). No injury/diagnosis/evaluator/outcome in the narrative.
- **Unknown first name** → use "Inmate Last" only; never print "None"/a placeholder.
- **Times are 12-hour** already; never restate in 24-hour form.
- **No bracketed placeholders** in output; omit a missing clause instead.

---

## 6. How to test (recipe)

Paste into the generator, classify → Inmate on Inmate Fight:

```
Smith ADC#123456 & Jones ADC#654321 fighting 8 Barracks ~2200.
Jones cut over left eye. Sgt Peterman applied cuffs.
Cpl Powell & Cpl Sohns escorted to infirmary.
```

On Missing Info: confirm the suggested charges; medical = Seen by Infirmary
staff; photos = Yes; witnesses = Yes; type first names in **lowercase** to test
capitalization; leave incident # blank.

Expect:
- Time "10:00pm"; shift "B Shift"; names capitalized; first mention full form.
- One combined restraint sentence, one combined escort sentence, one medical
  line, no third-person leakage in the first-person report.
- "The inmates were placed in Restrictive Housing." + "Disciplinary action was
  taken against the inmates (refer to the Disciplinary Report)."
- 005 front: PRESENT = "See Above", inmate injury/treatment = "See Infirmary
  Report", officer injury/treatment = "N/A".
- Download .docx matches the on-screen 005.

---

## 7. Refining

- **Deterministic rules** (sections 2–4): change the JSON checklist or the
  helpers in `routes/reports.py` / `validate.py`; they're covered by the
  sandbox tests and need no LLM.
- **Narrative rules** (section 5): tune `prompts_v2.py`; must be checked on a
  live GCP run. If a narrative rule keeps failing, promote it into the
  deterministic auto-content layer (section 4) where it can be guaranteed.
