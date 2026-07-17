"""PDF text extraction using pymupdf."""
import pymupdf
from pathlib import Path

def extract_pdf(pdf_path: Path) -> str:
    """Extract all text from a single PDF, preserving page breaks."""
    doc = pymupdf.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"[PAGE {i+1}]\n{text.strip()}")
    doc.close()
    return "\n\n".join(pages)


def extract_all(pdf_dir: Path, out_dir: Path) -> list[Path]:
    """Extract all PDFs in pdf_dir → out_dir. Returns list of output paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found.")
        return []

    results = []
    for pdf in pdfs:
        out_path = out_dir / f"{pdf.stem}.txt"
        print(f"Extracting: {pdf.name} → {out_path.name}")
        text = extract_pdf(pdf)

        issues = []
        if len(text) < 100:
            issues.append("VERY_SHORT")
        if "\ufffd" in text:
            issues.append("UNICODE_ERRORS")

        header = (
            f"# SOURCE: {pdf.name}\n"
            f"# PAGES: {len(text.split('[PAGE ')) - 1}\n"
            f"# ISSUES: {', '.join(issues) if issues else 'NONE'}\n"
            f"---\n\n"
        )
        out_path.write_text(header + text, encoding="utf-8")
        results.append(out_path)

    print(f"\nDone. {len(pdfs)} files in {out_dir}/")
    return results
