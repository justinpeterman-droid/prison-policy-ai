"""Generation prompts v2 — replaces the freeform prompts in prompts.py.

Key change from v1: prompts NEVER receive the raw notes. They receive the
structured extraction (narrative_facts, quotes, the reporter's own actions)
plus auto_content sentences that must appear verbatim. Every header field is
rendered by code from slots — the model writes narrative prose ONLY.
"""

STYLE_RULES = """WRITING RULES (BMU / ADC conventions — follow EXACTLY):
- ADC numbers are written with a space after the hash: 'ADC# 123456'
  (never 'ADC#123456').
- The word 'inmate' is LOWERCASE mid-sentence ('...escorted inmate Smith
  to the infirmary.'), and capitalized only when it starts a sentence.
- EVERY first mention of ANY person in the narrative MUST use the full introduction form.
  There are NO exceptions — never start with a bare last name on first mention.
  * INMATE first mention:  'Inmate {{Last}}, {{First}} ADC# {{number}}'  (Last, First + ADC#)
    - If first name is unknown: 'Inmate {{Last}} ADC# {{number}}'
    - If ADC# is unknown: 'Inmate {{Last}}, {{First}}'
    - If both unknown: 'Inmate {{Last}}'  (only when both first and ADC# truly unavailable)
  * STAFF first mention:   '{{Rank}} {{First}} {{Last}}'  (Cpl. / Sgt. / Lt. / Cpt.)
    - Example: 'Sgt. Justin Peterman', 'Cpl. Austin Powell'
  * ALL later references to the same person use SHORT FORM:
    - Inmate: 'Inmate {{Last}}'
    - Staff: '{{Rank}} {{Last}}'
- NEVER write a bare last name for the first mention of any person. If the first name
  is available in the facts, you MUST use it. Only omit the first name when the facts
  genuinely contain only a last name with nothing else to identify the person.
- Staff: '{{Rank}} {{First}} {{Last}}' on FIRST reference (Cpl. / Sgt. / Lt. / Cpt.),
  then '{{Rank}} {{Last}}' on all later references. NEVER a bare last name for staff
  on first mention — always include the rank and first name.
- The FIRST time any person is named, ALWAYS give the full form: {{Last}}, {{First}} ADC# {{number}}
  for inmates; {{Rank}} {{First}} {{Last}} for staff. Never use a bare last name on first
  mention. Every later mention uses the short form ({{Last}} only for inmates; {{Rank}} {{Last}} for staff).
- Times: 'approximately {{H:MM}} {{am/pm}}' (lowercase, WITH a space before am/pm). Use the exact time
  from the facts — if the notes say '~10pm', write 'approximately 10:00 pm'.
- Dates: write the date EXACTLY as provided in the header (do NOT reformat it).
  If the header date is 'July 21, 2026', use 'July 21, 2026'. Follow the format
  the officer provided.
- Chronological order. Past tense. One action per sentence. Objective and factual.
- Rank abbreviations ALWAYS keep the period: Sgt. / Cpl. / Lt. / Cpt.
- Spell the rank out in full on a person's FIRST mention ('Sergeant John Smith'), then abbreviate on every later mention ('Sgt. Smith').
- NEVER use ampersands (&) in formal reports — always write \"and\" between names.
- \"applied hand restraints to\" (not \"placed hand restraints onto\").
- The reporting officer identifies himself ONCE ('I, {{Rank}} {{First}} {{Last}},')
  and is 'I' / 'me' / 'my' everywhere after — NEVER his own rank+name again, and NEVER
  written in the third person. His own actions are 'I applied...', never
  '{{Rank}} {{Last}} applied...'. Every OTHER staff member is named '{{Rank}} {{Last}}'.
- NEVER add a name, ADC#, time, date, or event that is not in the provided facts.
- Claim the officer personally saw/observed something ONLY if the facts say he witnessed
  it. If he was told or notified, write 'was notified by {{person}} that...' — never
  'observed' or 'witnessed' for events reported to him.
- Secondhand information is attributed: '{{person}} stated/informed me that...'.
- Inmate statements/profanity from QUOTES are included verbatim in quotation marks,
  never censored or paraphrased — they are evidence.
- When the SAME action applies to more than one inmate or staff member, write ONE
  combined sentence ('I applied hand restraints to Inmate Smith and Inmate Jones.';
  'Cpl. Powell and Cpl. Sohns escorted Inmate Smith and Inmate Jones to the
  infirmary.') — NEVER a separate, near-identical sentence per person.
- Do NOT describe injuries, wounds, or medical findings, and do NOT write your own
  'seen by medical' sentence — the REQUIRED SENTENCES below already state the medical
  reference correctly and combined across inmates. Never add a diagnosis, an injury
  detail, an evaluator's name, or a treatment outcome — those live in the infirmary
  report.
- If an inmate's first name is unknown, refer to him as 'Inmate {{Last}}' only. NEVER
  write 'None', 'Unknown', or a placeholder in place of a name.
- Times are already provided in 12-hour form (e.g. '10:00 pm') — use them exactly as
  given; never restate a time in 24-hour form.
- Never output a bracketed placeholder such as [incident number] or [name]. If a value
  is genuinely missing, omit that clause entirely rather than inventing a placeholder.
- NEVER add a closing line such as 'End of report.', 'End of Statement.' or
  'Disciplinary action taken.' The narrative ends on its last factual sentence.
  Individual officers write different closers; the house style has none.
- The REQUIRED SENTENCES below must appear in the narrative, worded exactly as given,
  placed where they fit chronologically."""

# The shared writing rules are sent ONCE as the model's system instruction (not
# duplicated into every user prompt). Braces are single here because this text is
# never run through str.format — the per-report templates below still are.
REPORT_STYLE_SYSTEM = (
    STYLE_RULES.replace("{{", "{").replace("}}", "}")
    .replace("REQUIRED SENTENCES below", "REQUIRED SENTENCES provided")
)

FIRST_PERSON_PROMPT = """You are writing the STATEMENT OF FACTS narrative of an ADC 005
incident report, in the first person, AS this officer:

REPORTING OFFICER: {rank} {officer_first} {officer_last}
First self-reference: 'I, {rank} {officer_first} {officer_last},' — then 'I'.

REQUIRED OPENING FORMULA — the first sentence MUST start EXACTLY with \"I, {rank} {officer_first} {officer_last},\":
Choose one:
  WITNESSED:  'I, {rank} {officer_first} {officer_last}, was <assigned post/activity> in <location> when at approximately {time} <trigger event occurred — Inmate X and Inmate Y began fighting>.'
  NOTIFIED:   'I, {rank} {officer_first} {officer_last}, was notified by <source> that at approximately {time} <event — Inmate X and Inmate Y were fighting in 8 Barracks>.'
The opening MUST begin with 'I, {rank} {officer_first} {officer_last},' — this is not optional.

THIS OFFICER'S OWN ACTIONS/OBSERVATIONS (the ONLY events you may describe firsthand):
{reporter_actions}

OTHER ESTABLISHED FACTS (may ONLY appear as attributed secondhand information):
{narrative_facts}

VERBATIM QUOTES available as evidence:
{quotes}

REQUIRED SENTENCES (insert verbatim, chronologically placed):
{auto_content}

PER-INMATE DISPOSITION — after the narrative, add one line per inmate:
'Inmate {{Last}}, {{First}} ADC# {{number}} was [placed in restrictive housing / released to barracks / transferred to medical / etc.].'
Different inmates may have different outcomes — state each individually. ALWAYS use the full
Last, First ADC# form in the disposition line since it is the final reference for the record.

""" + """

Output the narrative paragraph(s) only. No header, no signature block.
Include the per-inmate disposition lines at the end."""

SUPERVISOR_SUMMARY_PROMPT = """You are writing the third-person supervisor summary of an
ADC incident. Convert the events to third person: never 'I' outside quotation marks.
Refer to all staff as '{{Rank}} {{Name}}'.

ESTABLISHED FACTS (chronological — you may not add to them):
{narrative_facts}

VERBATIM QUOTES available as evidence:
{quotes}

REQUIRED SENTENCES (insert verbatim, chronologically placed):
{auto_content}

Opening formula: 'On {date} at approximately {time} {opening_actor} <was notified by
{{officer}} that / observed>...'. Use 'was notified by {{officer}} that' unless the facts
state {opening_actor} personally witnessed the event — never write 'observed' for an
event that was reported to him.

""" + """

Output the summary paragraph(s) only.
Include per-inmate disposition at the end."""

DISCIPLINARY_PROMPT = """You are writing the disciplinary report narrative for an ADC
incident, first person as {rank} {officer_first} {officer_last}. Same events as the
first-person report, focused on the rule-violating conduct.

FIRST-PERSON REPORT (your factual source — do not add to it):
{first_person_report}

CHARGES to bring: {charges}

CLOSING — the report MUST end with this exact formula, one sentence per charged inmate
(EVERY inmate MUST be named Last, First ADC# in full since this is their final reference):
'Due to the above stated facts I, {rank} {officer_first} {officer_last}, am charging inmate {{Last}}, {{First}} ADC# {{number}} with major rule violation {{code}} pending DCR.'
When an inmate is charged with more than one code, make it plural and list them:
'...with major rule violations {{a}}, {{b}}, and {{c}} pending DCR.'
Note 'inmate' is lowercase here (it is mid-sentence) and 'pending DCR' is part of
the same sentence — not a separate 'Pending DCR.' line.

""" + """

Output the narrative only."""

INVESTIGATION_PROMPT = """You are writing the investigation report for an ADC incident,
first person as {rank} {officer_first} {officer_last}.

This report exists ONLY because the officer conducted an investigation. Write what
the investigation found — do NOT re-tell the incident narrative.

REQUIRED OPENING FORMULA — the first sentence MUST be exactly:
'I, {rank} {officer_first} {officer_last}, started an investigation at {start_time} and
concluded it at {end_time} on {date} with the following findings:'

FINDINGS (chronological — these are the ONLY findings you may state):
{findings}

DISPOSITION — what the investigation resulted in:
{disposition}

VERBATIM QUOTES available as evidence:
{quotes}

STRUCTURE:
1. The opening formula above, exactly as written.
2. The findings in the order given, one plain factual sentence each.
3. The disposition (rehousing, separation alert, medical referral, evidence secured).
   If the disposition is '(none stated)', omit this entirely — never invent an outcome.

Do NOT add a charging sentence — the disciplinary report carries the charges.

""" + """

Output the investigation narrative only. No header, no signature block."""

COVER_LETTER_PROMPT = """You are writing the body paragraph of a shift supervisor's
incident cover letter. The To/From/Re/Date header is added by code — do NOT write it.

SUPERVISOR (letter author): {rank} {officer_first} {officer_last}
Opening formula: 'On {date} I, {rank} {officer_first} {officer_last}, was notified by
<officer> who was working as <post> that at approximately {time} <event>...'
Then: the supervisor's own response actions, authorizations obtained, current status.

ESTABLISHED FACTS:
{narrative_facts}

REQUIRED SENTENCES (insert verbatim where they fit):
{auto_content}

""" + """

Output one narrative paragraph only."""
