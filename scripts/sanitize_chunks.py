#!/usr/bin/env python3
"""Sanitize chunk IDs and re-export for RAG import."""
import json
from pathlib import Path

INPUT = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_chunks.jsonl")
OUTPUT = Path(r"C:\Users\justi\workspace\prison-policy-ai\data\ocr_chunks_sanitized.jsonl")

with open(INPUT, encoding="utf-8") as fin, open(OUTPUT, "w", encoding="utf-8") as fout:
    for line in fin:
        chunk = json.loads(line)
        # Sanitize ID: replace / and # with _
        chunk["id"] = chunk["id"].replace("/", "_").replace("#", "_")
        fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")

print(f"Sanitized: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
