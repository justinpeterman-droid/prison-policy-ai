#!/usr/bin/env python3
"""
Chunk OCR output text files for RAG indexing.
Mirrors the existing pipeline/chunk.py logic.
"""

import json
import sys
from pathlib import Path

CHUNK_SIZE = 512  # tokens (~words)
CHUNK_OVERLAP = 64

INPUT_DIR = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_output")
OUTPUT_FILE = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_chunks.jsonl")

def chunk_text(text, source, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks. Simple word-based (approximates tokens)."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "id": f"{source}#chunk{len(chunks)}",
            "content": chunk_text,
            "source": source,
            "chunk_index": len(chunks),
        })
        if end >= len(words):
            break
        start += chunk_size - overlap
    return chunks


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    txt_files = sorted(INPUT_DIR.rglob("*.txt"))
    print(f"Found {len(txt_files)} .txt files in {INPUT_DIR}")

    if limit:
        txt_files = txt_files[:limit]

    all_chunks = []
    total_chars = 0

    for tf in txt_files:
        text = tf.read_text(encoding="utf-8", errors="replace")
        total_chars += len(text)
        source = tf.relative_to(INPUT_DIR).with_suffix("").as_posix()
        chunks = chunk_text(text, source)
        all_chunks.extend(chunks)
        if len(txt_files) <= 10 or txt_files.index(tf) % 20 == 0:
            print(f"  {tf.name}: {len(chunks)} chunks ({len(text):,} chars)")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_chunks)} chunks from {len(txt_files)} files ({total_chars:,} chars)")
    print(f"Output: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
