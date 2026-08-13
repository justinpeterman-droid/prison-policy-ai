"""Byte-deterministic DOCX normalization for audited exports (RP-09).

A DOCX is a ZIP, and a ZIP carries volatile metadata: per-entry modification
timestamps, member order, and -- inside `docProps/core.xml` -- created/modified
document properties. None of that is report content, but all of it changes the
SHA-256 of an otherwise identical document. An export's promise is that the
*same immutable revision* always produces the *same bytes*, so this module
strips exactly the volatility and preserves everything else.

What is preserved, deliberately: each member's content, compression type,
permissions/external attributes, per-entry comment, and extra fields. What is
rewritten: member order (sorted by name), every entry timestamp (the fixed
1980-01-01 ZIP epoch), and the core-properties created/modified values (the
saved revision's timestamp, in UTC). Nothing in this module reads or logs
document text.
"""
from datetime import UTC, datetime
import io
import re
import zipfile


#: The DOCX part holding volatile created/modified document properties.
CORE_PROPERTIES_NAME = "docProps/core.xml"
#: Every normalized entry carries the earliest timestamp the ZIP format allows.
ZIP_ENTRY_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
#: Used when a caller has no revision timestamp to bind the document to.
DEFAULT_DOCUMENT_TIME = datetime(1980, 1, 1, tzinfo=UTC)

_CREATED_PATTERN = re.compile(
    r"(<dcterms:created\b[^>]*>)(.*?)(</dcterms:created>)", re.DOTALL,
)
_MODIFIED_PATTERN = re.compile(
    r"(<dcterms:modified\b[^>]*>)(.*?)(</dcterms:modified>)", re.DOTALL,
)


def core_timestamp(value: datetime | None) -> str:
    """Render one W3CDTF UTC timestamp for the core-properties part."""
    moment = (value or DEFAULT_DOCUMENT_TIME)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_core_properties(raw: bytes, stamp: str) -> bytes:
    text = raw.decode("utf-8", errors="strict")
    text = _CREATED_PATTERN.sub(lambda m: f"{m.group(1)}{stamp}{m.group(3)}", text)
    text = _MODIFIED_PATTERN.sub(lambda m: f"{m.group(1)}{stamp}{m.group(3)}", text)
    return text.encode("utf-8")


def normalize_docx_bytes(raw: bytes, *, document_time: datetime | None = None) -> bytes:
    """Return `raw` re-emitted with every volatile ZIP/DOCX field pinned.

    `document_time` is the saved report revision's timestamp; the same source
    value must be supplied on every regeneration so the bytes -- and therefore
    the recorded SHA-256 -- stay stable.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("document bytes are invalid")
    stamp = core_timestamp(document_time)
    output = io.BytesIO()
    try:
        with zipfile.ZipFile(io.BytesIO(bytes(raw))) as source:
            members = sorted(source.infolist(), key=lambda item: item.filename)
            with zipfile.ZipFile(output, "w") as target:
                target.comment = source.comment
                for item in members:
                    data = source.read(item.filename)
                    if item.filename == CORE_PROPERTIES_NAME:
                        data = _normalize_core_properties(data, stamp)
                    entry = zipfile.ZipInfo(item.filename, ZIP_ENTRY_TIMESTAMP)
                    entry.compress_type = item.compress_type
                    entry.create_system = item.create_system
                    entry.external_attr = item.external_attr
                    entry.internal_attr = item.internal_attr
                    entry.comment = item.comment
                    entry.extra = item.extra
                    target.writestr(entry, data)
    except zipfile.BadZipFile:
        raise ValueError("document is not a valid DOCX archive") from None
    return output.getvalue()
