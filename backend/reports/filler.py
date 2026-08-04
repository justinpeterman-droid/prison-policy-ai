"""
DOCX template filler — pure ZIP/XML, no python-docx or lxml needed.
Opens a .docx (ZIP of XML), replaces {{placeholders}}, saves filled copy.
"""
import zipfile
import tempfile
import os
from pathlib import Path
from datetime import datetime

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "005_template_v3.docx"

# What marks a ticked box on the 005 header, per the unit supervisor's ruling.
TICK = "X"

# Categories that additionally carry the 409 (Use of Force) designation.
# Kept here rather than in routes so the filler is correct on its own — a
# caller that forgets to pass box_409 still produces a correct form.
FORCE_CATEGORIES = {"use_of_force"}


def designation_boxes(category: str) -> dict:
    """Which form-designation boxes to tick (STYLE_RULINGS.md ruling 9).

    Every incident report is a 005. A use of force is filed as a 005 that ALSO
    carries the 409, so both boxes are ticked — not the 409 alone.
    """
    return {"box_005": TICK,
            "box_409": TICK if category in FORCE_CATEGORIES else ""}


def fill_template(metadata: dict, output_path: Path | None = None) -> dict:
    """
    Fill the 005 incident report template with metadata + report text.
    
    Args:
        metadata: dict with keys matching {{placeholders}} in template:
            unit_division, officer_last, officer_first, employee_number,
            rank, shift_assignment, date, time, location,
            inmates_involved, employees_involved, others_present,
            inmate_injuries, inmate_treatment, officer_injuries,
            officer_treatment, recommendation, narrative,
            officer_signature, date_filed, supervisor_name
    
    Returns:
        {"path": "/path/to/filled.docx"} on success,
        {"text": "fallback text"} if template not found
    """
    if not TEMPLATE_PATH.exists():
        # Fallback: plain text
        return {"text": _build_text(metadata)}
    
    template = _ensure_template()
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".docx", prefix="incident_")
        os.close(fd)  # close fd, we'll write via zipfile
    output_path = Path(output_path)
    
    # Decision §3: the 005 "middle" spot is the employee #, not middle name.
    # Map employee_number → officer_middle so the template placeholder is filled.
    metadata.setdefault("officer_middle", metadata.get("employee_number", ""))

    # Form designation boxes (STYLE_RULINGS.md ruling 9). These are handled
    # ahead of the generic defaults because "" is a MEANINGFUL value here —
    # an unticked box — and the defaults loop below treats empty as "unset"
    # and would silently re-tick it. The download fills from the reviewed
    # on-screen form, so an officer who unticks a box must get it unticked.
    # A caller that omits the keys entirely gets a plain 005.
    metadata.setdefault("box_005", TICK)
    metadata.setdefault("box_409", "")

    # Fill defaults
    defaults = {
        "unit_division": "",
        "officer_last": "",
        "officer_first": "",
        "employee_number": "",
        "rank": "",
        "shift_assignment": "",
        "date": datetime.now().strftime("%B %d, %Y"),
        "time": datetime.now().strftime("%I:%M %p"),
        "location": "",
        "inmates_involved": "",
        "employees_involved": "",
        "inmates_present": "",
        "employees_present": "",
        "others_present": "N/A",
        "inmate_injuries": "N/A",
        "inmate_treatment": "N/A",
        "officer_injuries": "N/A",
        "officer_treatment": "N/A",
        "recommendation": "",
        "narrative": "",
        "reporting_employee_signature": "",
        "supervisor_signature": "",
        "officer_signature": "",
        "date_filed": datetime.now().strftime("%B %d, %Y"),
        "supervisor_name": "",
    }
    
    for k, v in defaults.items():
        if k not in metadata or not metadata[k]:
            metadata[k] = v
    
    # Read template, replace placeholders, write filled copy
    with (zipfile.ZipFile(template, 'r') as zin,
          zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout):
        
        for item in zin.infolist():
            data = zin.read(item.filename)
            
            # Replace placeholders in XML files
            if item.filename.endswith('.xml') or item.filename.endswith('.rels'):
                text = data.decode('utf-8', errors='replace')
                for key, value in metadata.items():
                    placeholder = "{{" + key + "}}"
                    if placeholder in text:
                        text = text.replace(placeholder, _xml_escape(str(value)))
                data = text.encode('utf-8')
            
            zout.writestr(item, data)
    
    return {"path": str(output_path)}


def _ensure_template() -> Path:
    """Return the template path, building it if missing."""
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH
    
    from scripts.build_template import build
    build()
    return TEMPLATE_PATH


def _xml_escape(s: str) -> str:
    """Escape XML special characters."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_text(metadata: dict) -> str:
    """Fallback: build a plain-text representation."""
    lines = [
        "INCIDENT REPORT FORM",
        "=" * 40,
        f"Unit/Division: {metadata.get('unit_division', '')}",
        f"Reporting Officer: {metadata.get('officer_last', '')}, {metadata.get('officer_first', '')} {metadata.get('employee_number', '')}",
        f"Rank: {metadata.get('rank', '')}",
        f"Shift: {metadata.get('shift_assignment', '')}",
        f"Date: {metadata.get('date', '')}",
        f"Time: {metadata.get('time', '')}",
        f"Location: {metadata.get('location', '')}",
        f"Inmates: {metadata.get('inmates_involved', '')}",
        "",
        "STATEMENT OF FACTS",
        "-" * 20,
        metadata.get('narrative', ''),
        "",
        f"Respectfully submitted: {metadata.get('officer_signature', '')}",
        f"Date: {metadata.get('date_filed', '')}",
        f"Reviewed by: {metadata.get('supervisor_name', '')}",
    ]
    return "\n".join(lines)
