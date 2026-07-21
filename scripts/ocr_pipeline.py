#!/usr/bin/env python3
"""
Local batch OCR pipeline for prison-policy-ai scanned PDFs.
Reads from OneDrive, saves OCR output locally.
"""

import json
import sys
import time
import traceback
from pathlib import Path

import fitz  # pymupdf
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# ── Config ──────────────────────────────────────────────────────
PROJECT = "gen-lang-client-0968389176"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

PDF_DIR = Path(r"C:\Users\justi\OneDrive\Desktop\ADC Policies")
OUTPUT_DIR = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_output")
PROGRESS_FILE = Path(r"C:\Users\justi\workspace\prison-policy-ai\scripts\ocr_progress.json")

MIN_TEXT_CHARS = 50
DELAY_SECONDS = 2

# Only process these subdirectories (skip BMU Forms = OneDrive stubs)
INCLUDE_DIRS = {"BMU Policies", "BMU Post Orders", "SD"}


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed": [], "failed": [], "total_pages_ocrd": 0}


def save_progress(data):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2))


def ocr_page_with_gemini(model, page):
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    image_part = Part.from_data(img_bytes, "image/png")
    prompt = (
        "Extract ALL text from this document image exactly as it appears. "
        "Preserve the original formatting, line breaks, and structure. "
        "Do not summarize, paraphrase, or add any commentary. "
        "Output ONLY the extracted text."
    )
    response = model.generate_content([prompt, image_part])
    return response.text.strip()


def process_pdf(pdf_path, model, progress):
    pdf_name = pdf_path.name
    parent_dir = pdf_path.parent.name

    if pdf_name in progress["completed"]:
        return None

    print(f"  [{pdf_name}] ({pdf_path.stat().st_size:,} bytes)")

    try:
        doc = fitz.open(str(pdf_path))
        num_pages = len(doc)
        all_text = []
        pages_ocrd = 0
        pages_text = 0

        for i in range(num_pages):
            page = doc[i]
            txt = page.get_text().strip()
            if len(txt) >= MIN_TEXT_CHARS:
                all_text.append(f"--- Page {i+1} (extracted) ---\n{txt}")
                pages_text += 1
            else:
                print(f"    Page {i+1}/{num_pages}: OCR via Gemini...")
                try:
                    text = ocr_page_with_gemini(model, page)
                    all_text.append(f"--- Page {i+1} (OCR) ---\n{text}")
                    pages_ocrd += 1
                    time.sleep(DELAY_SECONDS)
                except Exception as e:
                    err = str(e)[:200]
                    print(f"    Page {i+1} OCR FAILED: {err}")
                    all_text.append(f"--- Page {i+1} (OCR FAILED: {err}) ---")
                    progress.setdefault("failed", []).append(
                        {"pdf": pdf_name, "page": i + 1, "error": err}
                    )

        doc.close()

        out_dir = OUTPUT_DIR / parent_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / pdf_path.with_suffix(".txt").name
        full_text = "\n\n".join(all_text)
        out_path.write_text(full_text, encoding="utf-8")

        progress["completed"].append(pdf_name)
        progress["total_pages_ocrd"] += pages_ocrd
        save_progress(progress)

        print(f"    → {out_path} ({len(full_text):,} chars) [{pages_text} text, {pages_ocrd} OCR]")
        return {"pdf": pdf_name, "pages": num_pages, "pages_text": pages_text, "pages_ocrd": pages_ocrd, "chars": len(full_text)}

    except Exception as e:
        print(f"    [ERROR] {pdf_name}: {e}")
        traceback.print_exc()
        progress.setdefault("failed", []).append({"pdf": pdf_name, "error": str(e)})
        save_progress(progress)
        return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    limit = int(args[0]) if args else None
    scanned_only = "--scanned-only" in flags

    print("Initializing Vertex AI...")
    vertexai.init(project=PROJECT, location=LOCATION)
    model = GenerativeModel(MODEL_NAME)

    # Collect valid PDFs from allowed dirs
    pdfs = []
    for d in sorted(PDF_DIR.iterdir()):
        if d.is_dir() and d.name in INCLUDE_DIRS:
            for p in sorted(d.rglob("*.pdf")):
                # Filter out known bad OneDrive stubs
                try:
                    doc = fitz.open(str(p))
                    num_pages = len(doc)
                    doc.close()
                    pdfs.append((p, num_pages))
                except Exception:
                    pass  # skip unreadable files

    print(f"Found {len(pdfs)} readable PDFs in {INCLUDE_DIRS}")

    if scanned_only:
        scanned = []
        for pdf_path, num_pages in pdfs:
            doc = fitz.open(str(pdf_path))
            has_text = any(len(doc[i].get_text().strip()) >= MIN_TEXT_CHARS for i in range(num_pages))
            doc.close()
            if not has_text:
                scanned.append(pdf_path)
                print(f"  SCANNED: {pdf_path.name} ({num_pages} pp)")
            else:
                print(f"  TEXT:   {pdf_path.name} ({num_pages} pp)")
        pdfs = [(p, 0) for p in scanned]
        print(f"\nScanned PDFs to process: {len(pdfs)}")

    if limit:
        pdfs = pdfs[:limit]

    progress = load_progress()
    print(f"Progress: {len(progress['completed'])} done, {len(progress.get('failed', []))} failed, {progress['total_pages_ocrd']} pages OCR'd\n")

    results = []
    for i, (pdf_path, _) in enumerate(pdfs):
        print(f"[{i+1}/{len(pdfs)}]", end=" ")
        result = process_pdf(pdf_path, model, progress)
        if result:
            results.append(result)

    print("\n" + "=" * 60)
    print(f"DONE. {len(results)} processed this run.")
    print(f"Total completed: {len(progress['completed'])}")
    print(f"Total pages OCR'd: {progress['total_pages_ocrd']}")
    if progress.get("failed"):
        print(f"Failures: {len(progress['failed'])}")

    return results


if __name__ == "__main__":
    main()
