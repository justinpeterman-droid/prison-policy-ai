"""OCR the ADC Inmate Disciplinary Manual using Vertex AI Gemini Vision."""
import os, json, pymupdf, base64, sys
from pathlib import Path
import vertexai
from vertexai.generative_models import GenerativeModel, Part

vertexai.init(
    project="gen-lang-client-0968389176",
    location="us-central1",
)

doc_path = str(Path(__file__).parent.parent / "pdfs" / "ADC_Inmate_Disciplinary_Manual.pdf")
doc = pymupdf.open(doc_path)
total = len(doc)
print(f"Processing {total} pages...")

model = GenerativeModel("gemini-2.5-flash")
charges = {}

for i in range(total):
    page = doc[i]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")

    response = model.generate_content(
        [
            "Extract all rule violation numbers and descriptions from this page. "
            "Format each as: RULE_NUMBER | DESCRIPTION | CATEGORY. "
            "If you see violations like '10-1 Failure to obey...' extract them. "
            "If this page has no violations, reply NO_VIOLATIONS. "
            "Only output violations, no other text.",
            Part.from_data(data=img_bytes, mime_type="image/png"),
        ]
    )
    text = response.text.strip()
    if "NO_VIOLATIONS" not in text and text:
        print(f"\n--- Page {i+1} ---")
        print(text[:400])

    for line in text.split("\n"):
        line = line.strip()
        if line and "NO_VIOLATIONS" not in line and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                code = parts[0]
                desc = parts[1]
                cat = parts[2]
                if code not in charges and len(code) > 1:
                    charges[code] = {
                        "category": cat,
                        "description": desc,
                        "sanction": "",
                    }

doc.close()

if charges:
    out_path = Path(__file__).parent.parent / "templates" / "disciplinary_charges.json"
    out = {"_source": "ADC_Inmate_Disciplinary_Manual.pdf", "charges": charges}
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"\nSaved {len(charges)} charges to {out_path}")
else:
    print("\nNo charges found in any pages")
