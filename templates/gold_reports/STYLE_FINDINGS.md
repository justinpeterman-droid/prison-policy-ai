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
