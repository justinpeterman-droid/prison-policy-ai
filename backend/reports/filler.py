"""005/409 DOC template filler — text output for now (.doc needs conversion to .docx)."""
from pathlib import Path
from backend.pipeline.config import TEMPLATES_DIR


def fill_005_form(fields: dict, output_path: Path = None) -> Path:
    """Fill the 005/409 form fields and produce a text representation.

    Note: TEMPLATES_DIR/005.doc is OLE2 binary format (.doc).
    python-docx only handles .docx (Office Open XML).
    For now, output a clean text representation.
    When a .docx version of the template is available, this
    can switch to Document() with field replacement.
    """
    if output_path is None:
        output_path = Path("/tmp/005_filled.txt")

    content = f"""ARKANSAS DEPARTMENT OF CORRECTION
INCIDENT REPORT — FORM 005/409

UNIT/DIVISION: {fields.get('unit_division', '')}
REPORTING EMPLOYEE: {fields.get('reporting_employee_last', '')}, {fields.get('reporting_employee_first', '')} {fields.get('reporting_employee_middle', '')}
RANK: {fields.get('rank', '')}
SHIFT ASSIGNMENT: {fields.get('shift_assignment', '')}
DATE: {fields.get('date', '')}
TIME: {fields.get('time', '')}
LOCATION: {fields.get('location', '')}
INMATE(S) INVOLVED: {fields.get('inmates_involved', '')}

NARRATIVE:
{fields.get('narrative_1st_person', '')}

RECOMMENDATION:
{fields.get('recommendation', '')}

SIGNATURE DATE: {fields.get('date', '')}
"""
    output_path.write_text(content)
    return output_path
