import re, json
from pathlib import Path

rtf_path = Path(r"C:\Users\justi\workspace\.hermes\desktop-attachments\Incident-Accident Package Checklist.rtf")
text = rtf_path.read_text(encoding="utf-8", errors="replace")

# Strip RTF markup
text = re.sub(r'\\[a-zA-Z]+\d*\s?', '', text)
text = re.sub(r"\\'[0-9a-fA-F]{2}", ' ', text)
text = re.sub(r'[{}]', '', text)
text = re.sub(r'\\\n', '\n', text)

# Find checklist items — look for lines with form names
lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5 and not l.startswith('\\')]

print("=== RAW LINES ===")
for l in lines[:80]:
    print(l)

# Now look for form names
forms_found = set()
for l in lines:
    lower = l.lower()
    if '005' in l or '409' in l:
        forms_found.add('005/409 Form')
    if 'disciplinary' in lower and 'form' in lower:
        forms_found.add('Major Disciplinary Form')
    if 'chain' in lower and 'custody' in lower:
        forms_found.add('Chain of Custody Form')
    if 'confiscation' in lower:
        forms_found.add('Confiscation Form')
    if 'photo' in lower or 'video' in lower or 'footage' in lower:
        forms_found.add('Photograph/Video Footage')
    if 'cover letter' in lower:
        forms_found.add('Cover Letter')
    if 'prea' in lower:
        forms_found.add('PREA Supplement')
    if 'introduction' in lower and 'contraband' in lower:
        forms_found.add('Introduction of Contraband')

print(f"\n=== FORMS FOUND: {len(forms_found)} ===")
for f in sorted(forms_found):
    print(f"  - {f}")
