# BMU (Benny Magness Unit) Report Writing Style Guide
Extracted from Sgt. Peterman's actual reports (2023–2024). These formulas are injected
into generation prompts and enforced by post-generation checks. All names/ADC numbers
below are placeholders — no real identities in this file.

## Naming conventions (ALWAYS, no exceptions)
- Inmates: `Inmate {Last}, {First} ADC#{number}` — e.g., "Inmate Doe, John ADC#123456"
  - After first full reference, may shorten to `Inmate {Last}`
- Staff: `{Rank abbrev.} {First} {Last}` — Cpl. / Sgt. / Lt. / Cpt.
  - Reporting officer refers to self as `I, {Rank} {First} {Last},` on first reference,
    then "I" afterward
- Times: `approximately {H:MM}{am/pm}` (lowercase am/pm, no space)
- Dates: as written by officer (M/D/YYYY or M-D-YY both appear; do not reformat)

## First-person report structure
1. **Opening sentence** — one of two formulas:
   - Activity: `On {date} at approximately {time} I, {Rank} {First} {Last}, was {assigned post / activity} when {trigger event}.`
   - Notification: `On {date} at approximately {time} I, {Rank} {First} {Last}, was notified by {source} that {event}.`
2. **Body** — chronological, past tense, one action per sentence. Only facts the
   officer personally observed or was told (attribute told facts: "stated", "informed me").
3. **Response actions** — orders given, restraints applied, escorts, notifications
   made (supervisor, medical, control center), in order.
4. **Restraints & escort** (ALWAYS documented on fights/assaults/RH placements) —
   formula: `{Rank} {Name} placed hand restraints onto {Inmate} and {Rank} {Name1}
   and {Rank} {Name2} escorted him to {destination}.` Destination is normally
   "Restrictive Housing" or "the infirmary, then Restrictive Housing".
5. **Medical** — state disposition (`{Inmate} was evaluated by Infirmary staff` /
   `refused medical treatment` / `was sent by ambulance`). Evaluator name and
   outcome are OPTIONAL — include only if the officer provided them; never ask
   for them as required.
6. **Disciplinary closing** (when charging) — EXACT formula:
   `Due to the above stated facts I, {Rank} {First} {Last}, am charging Inmate {Last}, {First} ADC#{number} with rule violation {code}[, and {code}]. Pending DCR.`

## Supervisor summary (3rd person)
Identical structure to first-person but converted: `I, Sgt. {Name},` → `Sgt. {Name}`.
Never introduces facts absent from the first-person report(s).
Opening: `On {date} at approximately {time} {Rank} {Name} {was notified / observed}...`

## Cover letter
Header block:
```
To:   Deputy Warden {Last}
From: {Rank} {First} {Last}, Shift Supervisor
Re:   Incident {YYYY-MM-###}
Date: {M/D/YYYY}
```
Body: single narrative paragraph, written by/for the shift supervisor, opening with the
notification chain (`On {date} I, {Rank} {Name}, was notified by {officer} who was
working as {post} that at approximately {time} {event}...`), then supervisor's own
response actions, authorizations obtained, and current status.

## Enemy alert / cross-reference line
`{Inmate A} and {Inmate B} was involved in a physical altercation at BMU in {location} on {date} (refer to BMU Incident Report {YYYY-MM-###}).`

## Tone rules
- Objective and factual. No opinions, no speculation, no emotional language.
- Profanity or explicit statements by inmates are quoted verbatim in quotation marks —
  never paraphrased or censored (they are evidence).
- Unsubstantiated allegations stated as such: "I was unable to substantiate..."
- Never state a conclusion the evidence doesn't support (e.g., "appeared to have a
  seizure", not "had a seizure" — officers are not medical staff).

## Per-officer perspective reports
Each security staff member named in the notes can have their own first-person report
generated. That report is written AS that officer and may contain ONLY actions and
observations the notes attribute to them — never facts only other officers witnessed.
Anything they only learned secondhand is attributed ("Sgt. {Name} informed me that...").
Each officer reviews and signs their own draft.

## Hard checks (run in code after generation)
- Every inmate mention matches regex `Inmate [A-Z][a-z]+, [A-Z][a-z]+ ADC#\d+` on first reference
- Every name, ADC#, time, and date in the output must appear in the officer's input
  (flag anything novel for review — AI-invented facts are prohibited)
- Disciplinary reports must end with the charging formula + "Pending DCR."
- No first-person pronouns in supervisor summaries except inside quoted statements
