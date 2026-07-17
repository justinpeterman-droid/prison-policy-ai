"""Text chunking for RAG embedding."""
import json
from pathlib import Path


def chunk_text(text: str, source: str,
               chunk_size: int = 1000,
               overlap: int = 200) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
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
        start += (chunk_size - overlap)

    return chunks


def chunk_all(reviewed_dir: Path, out_dir: Path,
              chunk_size: int = 1000,
              overlap: int = 200) -> Path:
    """Chunk all reviewed files → chunks/all_chunks.jsonl."""
    out_dir.mkdir(parents=True, exist_ok=True)
    reviewed = sorted(reviewed_dir.glob("*.txt"))
    if not reviewed:
        raise FileNotFoundError(f"No reviewed files in {reviewed_dir}")

    all_chunks = []
    for f in reviewed:
        text = f.read_text(encoding="utf-8")
        lines = text.split("\n")
        content_start = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                content_start = i + 1
                break
        body = "\n".join(lines[content_start:])
        if "\n\n# REVIEWED:" in body:
            body = body.split("\n\n# REVIEWED:")[0]

        chunks = chunk_text(body, source=f.stem,
                           chunk_size=chunk_size, overlap=overlap)
        all_chunks.extend(chunks)
        print(f"  {f.name}: {len(chunks)} chunks")

    out_path = out_dir / "all_chunks.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")

    print(f"\nTotal: {len(all_chunks)} chunks → {out_path}")
    return out_path
