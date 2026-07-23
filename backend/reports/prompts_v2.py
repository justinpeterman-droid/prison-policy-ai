"""Generation prompts v2 — replaces the freeform prompts in prompts.py.

Key change from v1: prompts NEVER receive the raw notes. They receive the
structured extraction (narrative_facts, quotes, the reporter's own actions)
plus auto_content sentences that must appear verbatim. Every header field is
rendered by code from slots — the model writes narrative prose ONLY.
"""

STYLE_RULES = """WRITING RULES (BMU / ADC conventions — follow EXACTLY):
- Inmate naming on FIRST reference (pick the most complete form you have):
  * EVERY time an ADC# appears in the facts, it MUST be included in the inmate's
    first reference: 'Inmate {{Last}} ADC#{{number}}' at minimum, 'Inmate {{Last}},
    {{First}} ADC#{{number}}' when the first name is also available.
  * If you have BOTH first and last name AND ADC#: 'Inmate {{Last}}, {{First}} ADC#{{number}}'
  * If you have last name and ADC# but no first name: 'Inmate {{Last}} ADC#{{number}}'
  * If you have only a last name (no ADC#): 'Inmate {{Last}}'
  * On EVERY later reference: 'Inmate {{Last}}' (short form).
- NEVER write 'Inmate Smith ADC#123456' on first reference without the first name
  when the first name IS available in the facts — include it in 'Last, First' order.
- Staff: '{{Rank}} {{First}} {{Last}}' on first reference (Cpl. / Sgt. / Lt. / Cpt.),
  then '{{Rank}} {{Last}}'.
- The FIRST time any person is named, give the full form above (never a bare last
  name on first mention); every later mention uses the short form.
- Times: 'approximately {{H:MM}}{{am/pm}}' (lowercase, no space). Use the exact time
  from the facts — if the notes say '~10pm', write 'approximately 10:00pm'.
- Dates: write the date EXACTLY as provided in the header (do NOT reformat it).
  If the header date is 'July 21, 2026', use 'July 21, 2026'. Follow the format
  the officer provided.
- Chronological order. Past tense. One action per sentence. Objective and factual.
- Rank abbreviations: Sgt, Cpl, Lt, Cpt. NEVER use a period after a rank (not \"Sgt.\", \"Cpl.\", etc.).
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
- Times are already provided in 12-hour form (e.g. '10:00pm') — use them exactly as
  given; never restate a time in 24-hour form.
- Never output a bracketed placeholder such as [incident number] or [name]. If a value
  is genuinely missing, omit that clause entirely rather than inventing a placeholder.
- The REQUIRED SENTENCES below must appear in the narrative, worded exactly as given,
  placed where they fit chronologically."""

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
'Inmate {{Last}}, {{First}} ADC#{{number}} was [placed in restrictive housing / released to barracks / transferred to medical / etc.].'
Different inmates may have different outcomes — state each individually.

""" + STYLE_RULES + """

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

""" + STYLE_RULES + """

Output the summary paragraph(s) only.
Include per-inmate disposition at the end."""

DISCIPLINARY_PROMPT = """You are writing the disciplinary report narrative for an ADC
incident, first person as {rank} {officer_first} {officer_last}. Same events as the
first-person report, focused on the rule-violating conduct.

FIRST-PERSON REPORT (your factual source — do not add to it):
{first_person_report}

CHARGES to bring: {charges}

CLOSING — the report MUST end with this exact formula, one sentence per charged inmate:
'Due to the above stated facts I, {rank} {officer_first} {officer_last}, am charging Inmate {{Last}}, {{First}} ADC#{{number}} with rule violation {{codes}}. Pending DCR.'

""" + STYLE_RULES + """

Output the narrative only."""

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

""" + STYLE_RULES + """

Output one narrative paragraph only."""
