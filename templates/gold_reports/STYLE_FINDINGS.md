# What the real reports say vs. what the code enforces

Observations from 94 real reports (de-identified). Several conventions the code
currently enforces are contradicted by how reports are actually written. Each
item needs a ruling: **the real reports win, or the guide wins** — but they can't
both be right, and right now the code is picking on its own.

---

## 1. 🔴 `_clean_report()` strips rank periods the real reports use

`backend/reports/generator.py`:

```python
text = re.sub(r'\b(Sgt|Cpl|Lt|Cpt)\.(\s)', r'\1\2', text)   # "Sgt." -> "Sgt"
```

Every real report writes the abbreviation **with** the period:

> "**Sgt.** Whitfield started an investigation…"
> "**Cpl.** Guthrie notified me…"
> "**Cpt.** Alder ordered inmate Brewer to the hallway…"

The code is actively rewriting correct output into something you don't write.
`prompts_v2.py` reinforces it: *"NEVER use a period after a rank."*

**Recommendation:** delete that rule from both. This one looks like a straight bug.

---

## 2. Rank is spelled out on first mention, abbreviated after

The guide says first mention is `{Rank abbrev.} {First} {Last}`. The reports do
something more specific:

> "I, **Sergeant** Daniel Whitfield, escorted inmate Green…"  → later → "**Sgt.** Whitfield was unable to substantiate…"
> "I observed **Corporal** Marcus Alder, **Corporal** Trevor Kemp…"  → later → "**Cpl.** Alder and **Cpl.** Kemp applied hand restraints…"

So: **full rank word + full name on first mention; abbreviated rank + surname after.**
That's a real pattern the generator isn't currently taught.

---

## 3. `ADC#` spacing is genuinely inconsistent

Both appear, often in the same document:

| Form | Example |
|---|---|
| No space | `ADC#208317`, `ADC#144608` |
| Space after `#` | `ADC# 204118`, `ADC# 225414` |
| Bare number | `#220686`, `#181119` |

**Needs a ruling.** The generator should pick one and apply it everywhere —
consistency matters more than which one wins.

---

## 4. Time format is inconsistent

`9:12 pm` (space) and `7:15pm` (no space) both appear, as does `11:45AM` /
`9:15PM` in caps. The code normalizes to lowercase-no-space (`7:15pm`), which
matches the majority — but not all.

**Recommendation:** keep the code's normalization. Just confirming it's what you want.

---

## 5. Closing lines vary by report type — and the generator knows none of them

| Closing | Where it appears |
|---|---|
| `End of report.` / `End of Report.` | individual officer statements |
| `End of Statement.` | Lt. Lindsey's PREA narrative |
| `Disciplinary action taken.` | short summaries |
| `Appropriate action taken by staff. All inmates received disciplinary action.` | use-of-force cover letter |
| `Due to the above stated facts I, {Rank} {First} {Last}, am charging inmate {Last}, {First} ADC#{n} with major rule violation {code} pending DCR.` | charging reports |

The charging formula itself has two variants:

> "**Due to** the above stated facts I, Sergeant Daniel Whitfield, am charging inmate Marcelis, Alder ADC#144608 with **major rule violation 4-8 pending DCR.**"
> "**For** the above stated facts, I, Cpl. Terri Guthrie, am charging inmate Sims, Paul ADC#173338 with **rule violations 10-2 and 11-1, pending DCR.**"

Note singular/plural, `major` present or absent, and the comma before `pending`.
**Needs a ruling on the canonical form.**

---

## 6. `inmate` vs `Inmate` is mixed mid-sentence

> "…**inmate** Marcelis started to go up the stairs and went to **Inmate** Green's rack…"

Both capitalizations appear within a single sentence. **Needs a ruling** — this is
the kind of thing a reviewer notices immediately.

---

## 7. Style varies by officer

These are recognizably different voices:

- **Sgt. Whitfield** — `I, Sergeant Daniel Whitfield,` … `End of report.`
- **Lt. Lindsey** — `I Lt. Owen Lindsey` (no comma) … `End of Statement.`
- **Lt. Marsh** — `On 7-29-23, I, Lt Lonnie Marsh was working as A-shift Supervisor.` (no rank period, comma before `I`)

**Decision needed:** should the generator produce one house style for everyone, or
match the individual officer? A single house style is far easier to make
consistent, and is what the current architecture assumes.

---

## 8. Investigation reports have a structure the generator doesn't model

A distinct and very common shape:

> "I started an investigation at **{time}** and concluded it at **{time}** on **{date}** with the following findings: …"

…then findings in chronological order, then disposition, then the charging line.
This is arguably a **9th report type**, separate from the four currently generated.

---

## 9. Profanity and slurs are preserved verbatim

Real reports quote inmates exactly, including racial slurs and obscenity. This
matches the existing rule that quotes are evidence and must not be censored —
worth confirming it survives review, since it will look jarring in a demo.

---

## Coverage against the 7 configured categories

| Category | Real examples found |
|---|---|
| `inmate_fight` | ✅ 5 incidents |
| `staff_assault` | ✅ 6 incidents |
| `prea` | ✅ 6 incidents |
| `contraband` | ⚠️ 2 incidents |
| `incident_no_disciplinary` | ⚠️ 1 (laundry fire) |
| `forced_cell_movement` | ❌ none clearly labelled |
| `other_rule_violation` | ✅ 27 incidents |

Plus two clusters the config has no category for: **use of force** (3) and
**medical emergency** (6). Use of force in particular is high-stakes and
well-represented in the archive — worth its own category.

---

# Addendum — findings from the scanned incident packets

Read: the full 18-page packet `2022-02-041`, plus the first pages of the
49-page use-of-force packet. Both are complete filings, not loose narratives.

## 10. 🔴 The 005 field values in code don't match the real form

From three real 005s in one packet:

| 005 field | Real value | Code currently writes |
|---|---|---|
| INMATE(S) PRESENT | `Same as above` | `See Above` ❌ |
| EMPLOYEE(S) PRESENT | `Same as above` | `See Above` ❌ |
| OTHERS PRESENT/INVOLVED | `N/A` | `See Above` ❌ |
| EXTENT OF INJURY TO INMATE(S) | `MSF 205` | *(blank)* ❌ |
| TREATMENT AFFORDED INMATE(S) | `MSF 205` | *(blank)* ❌ |
| EXTENT OF INJURY TO OFFICER(S) | `N/A` | `N/A` or blank ✅ |
| TIME | `APX. 9:50 PM` | `9:50pm` ❌ |

`MSF 205` appears to be the medical form reference. The code deliberately leaves
injury lines blank (`SEE_INFIRMARY = ""`), on the stated basis that "medical
detail is not written onto the 005" — but the real forms *do* carry a value
there, just a form pointer rather than a description. **Needs a ruling.**

Time on the form is `APX. 9:50 PM` — the `APX.` prefix, a space before `PM`, and
caps. That is the *form* convention; the *narrative* convention is
`approximately 9:50pm`. They are different and both appear in the same document.

## 11. ✅ One 005 per officer — confirmed

The packet contains three 005s for one incident (Cpl. Burton, Cpl. Pendergrass,
Sgt. Delgado). Each lists itself as REPORTING EMPLOYEE and the others under
EMPLOYEE(S) INVOLVED, and each carries that officer's own first-person
STATEMENT OF FACTS. Times differ per officer (9:50 PM vs 9:56 PM) because the
supervisor arrived later. This validates the existing `bind_reporter()` design.

## 12. There is a 005 continuation form the filler doesn't handle

When a narrative overruns the STATEMENT OF FACTS box, it continues onto
`REPORT OF INCIDENTS- 005 USE OF FORCE –409 (CONTINUED)` — a different layout
(DATE / TIME / LOCATION header, OFFICER(S) INVOLVED, INMATE(S) INVOLVED, then
STATEMENT OF OFFICER). Long narratives currently have nowhere to go.

## 13. Another charging-formula variant

> "**Therefore, due to** the above stated facts I, Cpl. Charene Burton am charging inmate Pierce, Joshua ADC #128870 with **major rule violations** 2-21, 4-4, 5-3, 5-5, 11-1, and 12-3. **Pending DCR.**"

Note `Therefore, due to`, no comma after the officer's name, `ADC #` with a
space, and `Pending DCR.` as its own sentence. That is now a **third** variant.

## 14. Cover letter `RE:` is just the incident number

> `To: Jason Davis CSO` / `From: Sgt. Katie Delgado` / `RE: 2022-02-041` / `Date: February 16, 2022`

Not a description — the bare incident number. The other packet uses
`Re: Use of Force Incident #2023-07-126`. The cover letter body is **third
person** about the reporting officer's actions, and is signed with the author's
name on its own line at the end.

## 15. 📋 The checklist page is the source of truth for `incident_checklist_v2.json`

Page 1 of each packet is the **North Central Unit Incident Checklist** — the
same 7 categories the config uses, each with its authoritative `forms_required`
list, and three signature lines (Shift Lieutenant, Shift Captain, Chief of
Security). This should be diffed against `templates/incident_checklist_v2.json`
to confirm the configured form lists are complete and correctly named.
