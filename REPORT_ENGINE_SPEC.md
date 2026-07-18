# Report Engine v2 — Implementation Spec (Handoff to Claude Code)

This document is the single source of truth for rebuilding the report engine.
It replaces guesswork: every decision below was made by Justin. Do not
reinterpret them. Read this whole file before writing code.

## What we're building
Officers paste rough field notes → the incident is classified (officer confirms)
→ Gemini extracts facts into a strict slot schema (nulls for anything unstated)
→ deterministic Python validation finds gaps → officer answers pre-written gap
questions (dropdowns/yes-no/text) → reports render from templates + a
narrative-only generation pass. Structure and wording are guaranteed because
the model never controls them.

## Decision log (authoritative)
1. **Categories** are the 7 from the BMU checklist (matches Grimes Unit
   requirements): contraband, inmate_fight, staff_assault, forced_cell_movement,
   prea, incident_no_disciplinary, other_rule_violation. The old invented
   categories are deleted.
2. **Unit is BMU (Benny Magness Unit)** — all generated text says BMU, not NCU/Grimes.
3. **005 header "middle" spot = officer's EMPLOYEE #**, not middle name.
   Rename docx placeholder {{officer_middle}} → {{employee_number}} in
   templates/005_template.docx and map it in filler.py.
4. **Input flow is hybrid**: narrative first, then gap questions.
5. **Classifier proposes, officer confirms** with one tap; dropdown to override.
6. **Gap questions are pre-written data** (incident_checklist_v2.json) — the AI
   never invents question wording.
7. **Answer types**: choice = dropdown of the normal options + final
   "Other (type your own)" (swaps to text input); yes_no = buttons; text = input.
   Free text only for names/ADC#s/numbers. Every field also has an "Unknown"
   button → value "UNKNOWN".
8. **Yes/No never blocks.** "No" just leaves the checklist box unchecked.
9. **Fights always document**: who applied hand restraints, who escorted
   (usually two officers), destination (normally Restrictive Housing or
   "Infirmary, then Restrictive Housing"). Medical evaluator/outcome are
   OPTIONAL — include only if provided, never asked as required.
10. **auto_content**: category-driven sentences inserted by CODE (enemy alert
    cross-reference line, footage-attached line, restraint/escort line, etc.).
    A fight gets them automatically; a broken sink gets none. Missing values
    render as visible [NEEDED: ...] — never silently dropped.
11. **Per-officer reports**: every security staff member named in the notes
    gets a button — "Generate {Rank} {Name}'s report". Tapping re-binds the
    reporter block, SO THE 005 HEADER (name / employee # / rank / shift)
    CHANGES TO THAT OFFICER, and the narrative may contain ONLY actions the
    notes attribute to them (secondhand info is attributed). Each officer
    reviews and signs their own draft.
12. **No witness-statement generation** (witnesses hand-write; it stays a
    checklist form only).
13. **UNKNOWN renders as ⚠ [TO BE SUPPLEMENTED: ...]** bold in the output doc.
14. **Invented-fact scan**: any ADC#, time, or date in generated text that
    doesn't appear in the notes/answers is highlighted yellow for review.
15. **Quotes verbatim, uncensored** (evidence). Medical events hedged
    ("appeared to have a seizure").

## Files provided (place at these paths, replacing old versions)
- templates/incident_checklist_v2.json   ← categories, slots, rules, questions,
  option sets, auto_content, per_officer_reports spec. Delete incident_checklist.json.
- backend/reports/schema.py              ← slot schema + Gemini response_schema
  builder + bind_reporter() + security_staff()
- backend/reports/extraction.py          ← the only Gemini call that sees raw
  notes; temperature 0, response_schema-constrained, extraction only
- backend/reports/validate.py            ← deterministic rule loop: gaps,
  checklist box state, auto_content resolution, invented_facts() scan
- backend/reports/prompts_v2.py          ← generation prompts (narrative only;
  they receive structured facts, NEVER raw notes). Replaces the report prompts
  in prompts.py (keep the classifier prompt + charge catalog loader).
- REPORT_ENGINE_SPEC.md (this file)      ← repo root
- report_style_guide.md                  ← templates/ (reference for humans + prompts)

## API (backend/webapp/routes/reports.py)
Replace single POST /api/reports with:

1. **POST /api/reports/classify** {notes} → {incident_type, label}
   Existing classify_incident(), constrained to the 7 category names.
2. **POST /api/reports/extract** {notes, category} →
   {slots, gaps, blocking_remaining, checklist, auto_content, officers}
   = extraction.extract_slots() then validate.find_gaps();
   officers = schema.security_staff(slots).
3. **POST /api/reports/generate** {notes, category, slots, reporter_index} →
   {reports, form005, flags}
   - merge gap answers into slots client-side before sending
   - schema.bind_reporter(slots, officers[reporter_index]) → 005 header fields
   - build prompts from prompts_v2 with: narrative_facts, quotes,
     persons[reporter].actions (as reporter_actions), resolved auto_content
   - after generation run validate.invented_facts() → flags for yellow highlight
   - UNKNOWN slots → "⚠ [TO BE SUPPLEMENTED: {slot}]" in rendered fields

## UI (backend/webapp/templates/reports.html — extend existing page)
Existing textarea/preview/download stay. Add, in order:
1. Category chip after classify: "Inmate on Inmate Fight/Assault ✓ | change ▾"
2. **Missing Information panel** (between #badges and #reports):
   blocking questions first, then a visually separate "Checklist items"
   group for the non-blocking yes/no toggles. Each field: its widget +
   "Unknown" button. Progress: "3 of 6 required items remaining".
   Continue button enables at blocking_remaining == 0.
3. **Officer buttons row**: one button per security staff
   ("Generate Cpl. Powell's report"); tap → /generate with reporter_index →
   re-render preview with that officer's header + perspective narrative.
   If an officer is named but has no actions, ask (text):
   "What did {Rank} {Name} do or observe?"
4. Yellow highlight on flagged tokens in the preview; the existing
   click-to-edit fields remain the correction mechanism.
5. Checklist sidebar/section rendering each forms_required item with its
   checked/unchecked box from validate output.

## Task list (implement in order; commit per task)
1. Drop in the 6 provided files; delete stale incident_checklist.json;
   update imports; rename {{officer_middle}} → {{employee_number}} in
   005_template.docx + filler.py mapping.
2. Constrain classifier output to the 7 category names; add confirm/override.
3. Wire /classify, /extract, /generate routes per above.
4. Build the Missing Information panel + widgets (choice→dropdown+Other,
   yes_no→buttons, text→input, Unknown everywhere).
5. Officer buttons + reporter re-binding (verify the 005 header swaps).
6. Rewrite generator.py to use prompts_v2 with structured facts only;
   delete raw-notes prose generation.
7. Markers + invented-fact highlighting in preview and docx.
8. Checklist box rendering.

## Acceptance test (must pass end-to-end)
Notes: "inmates smith and jones fighting in 8 barracks around 10pm, broke it
up, jones has a cut over his eye, sgt peterman cuffed jones, powell and sohns
took him to RH"
Expected: classified inmate_fight → blocking gaps exactly {date, charges,
incident_number, medical_disposition (dropdown), drug_test_disposition
(dropdown)} + ADC#s for Smith/Jones → non-blocking toggles {witness
statements, enemy alert, footage} → after answers, disciplinary + cover letter
contain the enemy-alert line with real values; first-person contains
"Sgt. Justin Peterman placed hand restraints onto Inmate Jones... and
Cpl. Austin Powell and Cpl. Jack Sohns escorted him to Restrictive Housing.";
tapping "Generate Cpl. Powell's report" produces a 005 whose header is
Powell's name/employee #/rank and whose narrative contains only Powell's
attributed actions; any planted fake ADC# gets flagged yellow.
