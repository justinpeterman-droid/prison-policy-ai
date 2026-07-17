"""005/409 DOC template filler using python-docx."""
from pathlib import Path
from backend.pipeline.config import TEMPLATES_DIR

TEMPLATE_PATH = TEMPLATES_DIR / "005.doc"


def fill_005_form(fields: dict, output_path: Path = None) -> Path:
    """Fill the 005/409 DOC template with provided fields.

    Args:
        fields: dict with keys matching form fields:
            unit_division, reporting_employee_last,
            reporting_employee_first, reporting_employee_middle,
            rank, shift_assignment, date, time, location,
            inmates_involved, narrative_1st_person, recommendation
        output_path: where to save filled form

    Returns:
        Path to filled document
    """
    if output_path is None:
        output_path = Path("/tmp/005_filled.docx")

    try:
        from docx import Document

        # If template is .doc (old format), attempt conversion
        if TEMPLATE_PATH.suffix == ".doc":
            return _fill_legacy_doc(fields, output_path)

        doc = Document(str(TEMPLATE_PATH))

        # Replace placeholder text in paragraphs
        field_map = {
            "FORMTEXT": fields.get("reporting_employee_last", ""),
            "UNIT/DIVISION": fields.get("unit_division", ""),
            "SHIFT": fields.get("shift_assignment", ""),
            "DATE": fields.get("date", ""),
            "TIME": fields.get("time", ""),
            "LOCATION": fields.get("location", ""),
            "INMATE": fields.get("inmates_involved", ""),
        }

        for para in doc.paragraphs:
            for key, val in field_map.items():
                if key in para.text:
                    para.text = para.text.replace(key, str(val))

        doc.save(str(output_path))
        return output_path

    except ImportError:
        return _generate_text_output(fields, output_path)


def _fill_legacy_doc(fields: dict, output_path: Path) -> Path:
    """Fallback: generate a text-based representation of the filled form."""
    return _generate_text_output(fields, output_path)


def _generate_text_output(fields: dict, output_path: Path) -> Path:
    """Generate a text file with the filled form content."""
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
    output_path = output_path.with_suffix(".txt")
    output_path.write_text(content)
    return output_path
