"""Generation prompts v2 — replaces the freeform prompts in prompts.py.

Key change from v1: prompts NEVER receive the raw notes. They receive the
structured extraction (narrative_facts, quotes, the reporter's own actions)
plus auto_content sentences that must appear verbatim. Every header field is
rendered by code from slots — the model writes narrative prose ONLY.
"""

STYLE_RULES = """WRITING RULES (BMU / ADC conventions — follow EXACTLY):
- Inmates: 'Inmate {{Last}}, {{First}} ADC#{{number}}' on first reference, then 'Inmate {{Last}}'.
- Staff: '{{Rank}} {{First}} {{Last}}' (Cpl. / Sgt. / Lt. / Cpt.).
- Times: 'approximately {{H:MM}}{{am/pm}}' (lowercase, no space). Dates exactly as provided.
- Chronological order. Past tense. One action per sentence. Objective and factual.
- NEVER add a name, ADC#, time, date, or event that is not in the provided facts.
- Secondhand information is attributed: '{{person}} stated/informed me that...'.
- Inmate statements/profanity from QUOTES are included verbatim in quotation marks,
  never censored or paraphrased — they are evidence.
- Medical observations are hedged: 'appeared to have a seizure', never a diagnosis.
- Medical disposition is stated plainly ('was evaluated by Infirmary staff' /
  'refused medical treatment' / 'was sent by ambulance'). Do NOT state an evaluator
  name or outcome unless it appears in the provided facts.
- The REQUIRED SENTENCES below must appear in the narrative, worded exactly as given,
  placed where they fit chronologically."""

FIRST_PERSON_PROMPT = """You are writing the STATEMENT OF FACTS narrative of an ADC 005
incident report, in the first person, AS this officer:

REPORTING OFFICER: {rank} {officer_first} {officer_last}
First self-reference: 'I, {rank} {officer_first} {officer_last},' — then 'I'.

OPENING SENTENCE — use exactly one of these two formulas:
  'On {date} at approximately {time} I, {rank} {officer_first} {officer_last}, was <assigned post/activity> when <trigger event>.'
  'On {date} at approximately {time} I, {rank} {officer_first} {officer_last}, was notified by <source> that <event>.'

THIS OFFICER'S OWN ACTIONS/OBSERVATIONS (the ONLY events you may describe firsthand):
{reporter_actions}

OTHER ESTABLISHED FACTS (may ONLY appear as attributed secondhand information):
{narrative_facts}

VERBATIM QUOTES available as evidence:
{quotes}

REQUIRED SENTENCES (insert verbatim, chronologically placed):
{auto_content}

""" + STYLE_RULES + """

Output the narrative paragraph(s) only. No header, no signature block."""

SUPERVISOR_SUMMARY_PROMPT = """You are writing the third-person supervisor summary of an
ADC incident. Convert the events to third person: never 'I' outside quotation marks.
Refer to all staff as '{{Rank}} {{Name}}'.

ESTABLISHED FACTS (chronological — you may not add to them):
{narrative_facts}

VERBATIM QUOTES available as evidence:
{quotes}

REQUIRED SENTENCES (insert verbatim, chronologically placed):
{auto_content}

Opening formula: 'On {date} at approximately {time} {opening_actor} <was notified/observed>...'

""" + STYLE_RULES + """

Output the summary paragraph(s) only."""

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
