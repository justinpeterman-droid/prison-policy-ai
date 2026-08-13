"""Vertex AI RAG corpus management."""

from functools import lru_cache
from importlib import import_module
from pathlib import Path
from collections.abc import Callable, Iterable
from typing import Protocol, runtime_checkable

from backend.pipeline.config import PROJECT_ID, LOCATION, BUCKET_NAME, CORPUS_NAME


class _Corpus(Protocol):
    display_name: str
    name: str


@runtime_checkable
class _VertexAiModule(Protocol):
    def init(self, *, project: str, location: str) -> object: ...


@runtime_checkable
class _RagModule(Protocol):
    RagEngineConfig: Callable[..., object]
    RagManagedDbConfig: Callable[..., object]
    Serverless: Callable[[], object]

    def list_corpora(self) -> Iterable[_Corpus]: ...

    def update_rag_engine_config(self, *, rag_engine_config: object) -> object: ...

    def create_corpus(self, *, display_name: str) -> _Corpus: ...

    def import_files(
        self,
        *,
        corpus_name: str,
        paths: list[str],
        max_embedding_requests_per_min: int,
    ) -> object: ...


class _Blob(Protocol):
    def upload_from_filename(self, filename: str) -> object: ...


class _Bucket(Protocol):
    def exists(self) -> bool: ...

    def blob(self, name: str) -> _Blob: ...


class _StorageClient(Protocol):
    def bucket(self, name: str) -> _Bucket: ...

    def create_bucket(self, name: str, *, location: str) -> _Bucket: ...


@runtime_checkable
class _StorageModule(Protocol):
    Client: Callable[..., _StorageClient]


@lru_cache(maxsize=1)
def _legacy_rag_module() -> _RagModule:
    """Load deployment-only legacy corpus dependencies when this CLI is invoked."""
    vertexai = import_module("vertexai")
    rag = import_module("vertexai.preview.rag")
    if not isinstance(vertexai, _VertexAiModule) or not isinstance(rag, _RagModule):
        raise RuntimeError("legacy Vertex AI RAG modules do not match the expected API")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    return rag


def get_or_create_corpus() -> str:
    """Get existing corpus or create in serverless mode."""
    rag = _legacy_rag_module()
    for c in rag.list_corpora():
        if c.display_name == CORPUS_NAME:
            print(f"Using existing corpus: {c.name}")
            return c.name

    print(f"Creating corpus: {CORPUS_NAME}")
    config_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=config_name,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rag.Serverless()),
        )
    )
    corpus = rag.create_corpus(display_name=CORPUS_NAME)
    print(f"Created: {corpus.name}")
    return corpus.name


def upload_chunks_to_gcs(chunks_path: Path) -> str:
    """Upload chunk file to GCS, return gs:// path."""
    storage = import_module("google.cloud.storage")
    if not isinstance(storage, _StorageModule):
        raise RuntimeError(
            "Google Cloud Storage module does not match the expected API"
        )
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
    rag = _legacy_rag_module()
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
