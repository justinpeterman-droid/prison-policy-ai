"""
Build a clean incident report DOCX template using raw XML (ZIP of XML files).
No python-docx dependency — just Python stdlib.
"""
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).parent.parent / "templates" / "005_template.docx"


def xml_esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


FIELDS = [
    ("Unit/Division:", "{{unit_division}}"),
    ("Reporting Officer (Last):", "{{officer_last}}"),
    ("Reporting Officer (First):", "{{officer_first}}"),
    ("Reporting Officer (Middle):", "{{officer_middle}}"),
    ("Rank:", "{{rank}}"),
    ("Shift Assignment:", "{{shift_assignment}}"),
    ("Date:", "{{date}}"),
    ("Time:", "{{time}}"),
    ("Location:", "{{location}}"),
    ("Inmate(s) Involved:", "{{inmates_involved}}"),
    ("Employee(s) Involved:", "{{employees_involved}}"),
    ("Others Present:", "{{others_present}}"),
    ("Inmate Injuries:", "{{inmate_injuries}}"),
    ("Inmate Treatment:", "{{inmate_treatment}}"),
    ("Officer Injuries:", "{{officer_injuries}}"),
    ("Officer Treatment:", "{{officer_treatment}}"),
    ("Recommendation:", "{{recommendation}}"),
]


def build_table_rows() -> str:
    rows = []
    for label, placeholder in FIELDS:
        rows.append(
            '<w:tr>'
            f'<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{xml_esc(label)} </w:t></w:r></w:p></w:tc>'
            f'<w:tc><w:p><w:r><w:t xml:space="preserve">{xml_esc(placeholder)}</w:t></w:r></w:p></w:tc>'
            '</w:tr>'
        )
    return "\n".join(rows)


def build_document_xml() -> str:
    table_rows = build_table_rows()
    
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p>
    <w:pPr><w:jc w:val="center"/></w:pPr>
    <w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>INCIDENT REPORT FORM</w:t></w:r>
</w:p>
<w:p>
    <w:pPr><w:jc w:val="center"/></w:pPr>
    <w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>Confidential - For Official Use Only</w:t></w:r>
</w:p>
<w:tbl>
    <w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr>
    <w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="6000"/></w:tblGrid>
    {table_rows}
</w:tbl>
<w:p/>
<w:p>
    <w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>STATEMENT OF FACTS</w:t></w:r>
</w:p>
<w:p>
    <w:r><w:rPr><w:i/></w:rPr><w:t>The reporting officer's first-person account follows:</w:t></w:r>
</w:p>
<w:p>
    <w:r><w:t xml:space="preserve">{{{{narrative}}}}</w:t></w:r>
</w:p>
<w:p/>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Respectfully submitted,</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">{{{{officer_signature}}}}</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Date: {{{{date_filed}}}}</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Reviewed by: {{{{supervisor_name}}}}</w:t></w:r></w:p>
</w:body>
</w:document>'''


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    
    document_xml = build_document_xml()
    
    with zipfile.ZipFile(str(OUTPUT), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
        
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        
        z.writestr('word/_rels/document.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>''')
        
        z.writestr('word/document.xml', document_xml)

    print(f"Template built: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
