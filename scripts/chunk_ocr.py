#!/usr/bin/env python3
"""Chunk OCR output for RAG — character-based, matching backend/pipeline/chunk.py."""
import json
from pathlib import Path

CHUNK_SIZE = 1000   # characters (matching existing pipeline)
CHUNK_OVERLAP = 200

INPUT_DIR = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_output")
OUTPUT_FILE = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_chunks_v3.jsonl")


def chunk_text(text, source, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    chunk_num = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append({
                "id": f"{source}_chunk_{chunk_num:04d}",
                "source": source,
                "chunk_num": chunk_num,
                "start_char": start,
                "end_char": end,
                "text": chunk_content,
            })
            chunk_num += 1
        start += chunk_size - overlap
    return chunks


def main():
    txt_files = sorted(INPUT_DIR.rglob("*.txt"))
    print(f"Found {len(txt_files)} files")

    all_chunks = []
    for tf in txt_files:
        text = tf.read_text(encoding="utf-8", errors="replace")
        source = tf.relative_to(INPUT_DIR).with_suffix("").as_posix().replace("/", "_")
        chunks = chunk_text(text, source)
        all_chunks.extend(chunks)
        if len(txt_files) <= 10 or txt_files.index(tf) % 20 == 0:
            print(f"  {tf.name}: {len(chunks)} chunks ({len(text):,} chars)")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_chunks)} chunks from {len(txt_files)} files")
    print(f"Output: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
