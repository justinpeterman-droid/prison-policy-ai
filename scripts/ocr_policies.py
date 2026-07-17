"""OCR all scanned policy PDFs using Vertex AI Gemini Vision."""
import os, json, pymupdf, sys
from pathlib import Path
import vertexai
from vertexai.generative_models import GenerativeModel, Part

vertexai.init(project="gen-lang-client-0968389176", location="us-central1")

PDF_DIR = Path(__file__).parent.parent / "pdfs"
OUT_DIR = Path(__file__).parent.parent / "data" / "extracted"

def is_scanned(pdf_path: Path) -> bool:
    doc = pymupdf.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()
    return len(text.strip()) < 200

def ocr_pdf(pdf_path: Path) -> str:
    doc = pymupdf.open(str(pdf_path))
    model = GenerativeModel("gemini-2.5-flash")
    pages_text = []
    
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        
        response = model.generate_content([
            "Transcribe ALL text from this document page verbatim. "
            "Include headers, section numbers, body text. "
            "Do not summarize. Output raw text.",
            Part.from_data(data=img_bytes, mime_type="image/png"),
        ])
        pages_text.append(f"[PAGE {i+1}]\n{response.text.strip()}")
        print(f"  Page {i+1}/{len(doc)}")
    
    doc.close()
    return "\n\n".join(pages_text)

# Find scanned PDFs
pdfs = sorted(PDF_DIR.glob("*.pdf"))
scanned = [p for p in pdfs if p.stat().st_size > 0 and is_scanned(p)]
print(f"Found {len(scanned)} scanned PDFs to OCR")

# Also check for already-OCRed (extracted files)
already_done = set()
out_dir = Path(r"C:\Users\justi\workspace\prison-policy-ai\extracted")
if out_dir.exists():
    for f in out_dir.glob("*.txt"):
        content = f.read_text(encoding="utf-8", errors="replace")
        # Skip placeholders (very short files)
        if len(content) > 300:
            already_done.add(f.stem)

remaining = [p for p in scanned if p.stem not in already_done]
print(f"Already have text for: {len(already_done)}")
print(f"Remaining to OCR: {len(remaining)}")

if not remaining:
    print("Nothing to OCR!")
    sys.exit(0)

OUT_DIR.mkdir(parents=True, exist_ok=True)
for pdf in remaining:
    print(f"\nOCR: {pdf.name}")
    try:
        text = ocr_pdf(pdf)
        out_path = out_dir / f"{pdf.stem}.txt"
        header = f"# SOURCE: {pdf.name}\n# OCR: Gemini Vision\n# PAGES: {text.count('[PAGE ')}\n---\n\n"
        out_path.write_text(header + text, encoding="utf-8")
        print(f"  Saved: {out_path.name} ({len(text)} chars)")
    except Exception as e:
        print(f"  ERROR: {e}")
