"""Vertex AI RAG corpus management."""
import json
from pathlib import Path
from google.cloud import storage
import vertexai
from vertexai.preview import rag
from backend.pipeline.config import (
    PROJECT_ID, LOCATION, BUCKET_NAME, CORPUS_NAME
)

vertexai.init(project=PROJECT_ID, location=LOCATION)


def get_or_create_corpus() -> str:
    """Get existing corpus or create in serverless mode."""
    for c in rag.list_corpora():
        if c.display_name == CORPUS_NAME:
            print(f"Using existing corpus: {c.name}")
            return c.name

    print(f"Creating corpus: {CORPUS_NAME}")
    config_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=config_name,
            rag_managed_db_config=rag.RagManagedDbConfig(
                mode=rag.Serverless()
            )
        )
    )
    corpus = rag.create_corpus(display_name=CORPUS_NAME)
    print(f"Created: {corpus.name}")
    return corpus.name


def upload_chunks_to_gcs(chunks_path: Path) -> str:
    """Upload chunk file to GCS, return gs:// path."""
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    if not bucket.exists():
        bucket = client.create_bucket(BUCKET_NAME, location=LOCATION)

    blob_name = "chunks/all_chunks.jsonl"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(chunks_path))
    gcs_path = f"gs://{BUCKET_NAME}/{blob_name}"
    print(f"Uploaded: {gcs_path}")
    return gcs_path


def import_to_corpus(corpus_name: str, gcs_path: str):
    """Import chunks from GCS into the RAG corpus."""
    print(f"Importing from {gcs_path} ...")
    response = rag.import_files(
        corpus_name=corpus_name,
        paths=[gcs_path],
        max_embedding_requests_per_min=100,
    )
    print(f"Import submitted: {response}")


def embed_all(chunks_dir: Path):
    """Full embed pipeline: upload to GCS, import to corpus."""
    chunks_path = chunks_dir / "all_chunks.jsonl"
    if not chunks_path.exists():
        raise FileNotFoundError(f"{chunks_path} not found. Run chunking first.")

    gcs_path = upload_chunks_to_gcs(chunks_path)
    corpus_name = get_or_create_corpus()
    import_to_corpus(corpus_name, gcs_path)

    print(f"\n✅ Corpus ready: {corpus_name}")


if __name__ == "__main__":
    from pathlib import Path
    chunks_dir = Path(__file__).parent.parent.parent / "chunks"
    embed_all(chunks_dir)
