#!/usr/bin/env python3
"""OCR the ADC Disciplinary Manual using Gemini REST API directly (no SDK)."""
import base64, json, sys, os, requests
from pathlib import Path

API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if not API_KEY:
    print("ERROR: GOOGLE_API_KEY not set")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data"

PROMPT = """Transcribe ALL text verbatim from this scanned policy document page. 
This is the Arkansas Department of Correction Inmate Disciplinary Manual (AD 15-10).
Focus on rule violation numbers, categories (Class I/II), full descriptions, and sanctions.
Do NOT summarize. Transcribe every word exactly."""

def ocr_page(page_num):
    img_path = DATA_DIR / f"discipline_page_{page_num:02d}.png"
    if not img_path.exists():
        return ""
    
    img_b64 = base64.b64encode(img_path.read_bytes()).decode()
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": img_b64}}
            ]
        }]
    }
    
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code != 200:
        return f"ERROR: {r.status_code} {r.text[:200]}"
    
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return f"PARSE ERROR: {json.dumps(data, indent=2)[:300]}"

all_text = []
for page in range(1, 36):
    print(f"Page {page}/35...", end=" ", flush=True)
    text = ocr_page(page)
    all_text.append(f"--- PAGE {page} ---\n{text}")
    print(f"{len(text)} chars")

full_path = DATA_DIR / "discipline_manual_full.txt"
full_path.write_text("\n\n".join(all_text), encoding="utf-8")
print(f"\nDone: {full_path} ({sum(len(t) for t in all_text)} chars)")
