# Incident Packet Forms

A single-page React app that reproduces five corrections-department documents as
fillable, printable forms. Open `forms/index.html` in any browser — no server or
build step, and it works fully offline (React is vendored under `forms/vendor/`).

## Forms included

| Tab | Source document | Fillable? |
|-----|-----------------|-----------|
| Supervisor Checklist | Shift Supervisor Paperwork Checklist (Incident Packet review) | Checkboxes on every line + the inline "Refused / transported" options |
| PREA Cover | PREA Incident After Action Review cover page | Incident Tracking #, Inmate(s), Staff |
| Hotline Warning | Abuse of the PREA Hotline Warning (Arkansas DOC) | Name, ADC/PID, Facility, Call Date, Issuing Staff, signatures + dates |
| Gate Pass Steps | Emergency Medical Gate Pass Creation Checklist | Reference sheet — only Job Code, Section, and Sequence # blanks are fillable |
| Chain of Custody | Chain of Custody (Arkansas DOC) | Date/Time/DOC Employee, Description, Location, Victim, Suspect + signature table |

## Usage

- Type into the blue underlined blanks and tick the checkboxes.
- **Print / Save this form** prints just the active tab; **Print all** prints all five.
- Use your browser's "Save as PDF" print destination to keep a filled copy.

## Notes

- Department seals/badges are shown as simple placeholder circles (the original
  raster logos aren't reproduced).
- To regenerate `app.js` after editing the JSX source, recompile with Babel; the
  committed `app.js` is the pre-compiled output so no build tooling is needed to run it.
