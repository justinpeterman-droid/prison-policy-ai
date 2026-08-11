"""Immutable GCS storage for versioned demo review submissions."""
import json
import logging
import re


logger = logging.getLogger(__name__)
SUBMISSION_ID_RE = re.compile(
    r"^review_(?P<year>[0-9]{4})(?P<month>[0-9]{2})[0-9]{2}T"
    r"[0-9]{6}Z_[a-zA-Z0-9_-]{6,64}$"
)


class ReviewStoreUnavailable(RuntimeError):
    """The review bucket is not configured or cannot be reached."""


class ReviewConflictError(RuntimeError):
    """A create-only review object already exists."""


class ReviewStore:
    def __init__(self, bucket_name: str, prefix: str, client_factory=None):
        self.bucket_name = (bucket_name or "").strip()
        self.prefix = (prefix or "review-lab/submissions").strip("/")
        if not self.prefix or ".." in self.prefix.split("/"):
            raise ValueError("review object prefix is invalid")
        self._client_factory = client_factory or self._default_client

    @staticmethod
    def _default_client():
        from google.cloud import storage
        return storage.Client()

    def _client(self):
        if not self.bucket_name:
            raise ReviewStoreUnavailable("review bucket is not configured")
        return self._client_factory()

    def _name_for_id(self, submission_id: str) -> str:
        match = SUBMISSION_ID_RE.fullmatch(submission_id or "")
        if not match:
            raise ValueError("invalid review submission id")
        return (f"{self.prefix}/{match.group('year')}/{match.group('month')}/"
                f"{submission_id}.json")

    @staticmethod
    def _is_conflict(exc: Exception) -> bool:
        try:
            from google.api_core.exceptions import PreconditionFailed
        except ImportError:  # pragma: no cover - dependency is deployed
            PreconditionFailed = ()
        return (isinstance(exc, PreconditionFailed)
                or "precondition" in str(exc).lower())

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        if isinstance(exc, FileNotFoundError):
            return True
        try:
            from google.api_core.exceptions import NotFound
        except ImportError:  # pragma: no cover - dependency is deployed
            return False
        return isinstance(exc, NotFound)

    def save(self, record: dict) -> str:
        submission_id = record.get("submission_id", "")
        object_name = self._name_for_id(submission_id)
        payload = json.dumps(
            record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        blob = self._client().bucket(self.bucket_name).blob(object_name)
        try:
            blob.upload_from_string(
                payload,
                content_type="application/json",
                if_generation_match=0,
            )
        except Exception as exc:
            if self._is_conflict(exc):
                raise ReviewConflictError(
                    f"review {submission_id} already exists") from exc
            raise ReviewStoreUnavailable("review could not be saved") from exc
        return object_name

    def get(self, submission_id: str) -> dict | None:
        object_name = self._name_for_id(submission_id)
        blob = self._client().bucket(self.bucket_name).blob(object_name)
        try:
            return json.loads(blob.download_as_text())
        except Exception as exc:
            if self._is_not_found(exc):
                return None
            if isinstance(exc, json.JSONDecodeError):
                logger.warning("Malformed review object at %s", object_name)
                return None
            raise ReviewStoreUnavailable("review could not be read") from exc

    def list_records(self, limit: int = 50) -> tuple[list[dict], int]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("review list limit must be from 1 to 1000")
        client = self._client()
        records = []
        skipped = 0
        try:
            blobs = client.list_blobs(
                self.bucket_name, prefix=f"{self.prefix}/")
            for blob in blobs:
                try:
                    item = json.loads(blob.download_as_text())
                    if not isinstance(item, dict) or not item.get("submission_id"):
                        raise ValueError("missing submission id")
                    records.append(item)
                except (json.JSONDecodeError, ValueError, TypeError):
                    skipped += 1
                    logger.warning("Skipping malformed review object at %s", blob.name)
        except ReviewStoreUnavailable:
            raise
        except Exception as exc:
            raise ReviewStoreUnavailable("reviews could not be listed") from exc
        records.sort(key=lambda item: item.get("submitted_at", ""), reverse=True)
        return records[:limit], skipped

    def export_jsonl(self, limit: int = 1000) -> tuple[bytes, int]:
        records, skipped = self.list_records(limit=limit)
        text = "".join(
            json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n"
            for item in records
        )
        return text.encode("utf-8"), skipped
