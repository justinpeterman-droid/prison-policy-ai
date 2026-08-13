"""Deterministic DOCX normalization (RP-09).

Every fixture here is a synthetic, in-memory ZIP built by the test itself --
never a real report, a real officer, or a real ADC document.
"""

from datetime import UTC, datetime
import hashlib
import io
import zipfile

import pytest

from backend.reports.deterministic_docx import (
    CORE_PROPERTIES_NAME,
    ZIP_ENTRY_TIMESTAMP,
    normalize_docx_bytes,
)


FICTIONAL_CORE_XML = (
    "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n"
    "<cp:coreProperties"
    ' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
    ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
    ' xmlns:dcterms="http://purl.org/dc/terms/"'
    ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:title>Fictional Example Form</dc:title>"
    '<dcterms:created xsi:type="dcterms:W3CDTF">2001-02-03T04:05:06Z</dcterms:created>'
    '<dcterms:modified xsi:type="dcterms:W3CDTF">2009-08-07T06:05:04Z</dcterms:modified>'
    "</cp:coreProperties>"
).encode("utf-8")

FICTIONAL_MEMBERS = (
    (
        "word/document.xml",
        b"<w:document>Fictional example narrative.</w:document>",
        zipfile.ZIP_DEFLATED,
    ),
    (CORE_PROPERTIES_NAME, FICTIONAL_CORE_XML, zipfile.ZIP_DEFLATED),
    ("[Content_Types].xml", b"<Types>fictional</Types>", zipfile.ZIP_DEFLATED),
    ("word/media/image1.bin", b"\x00\x01fictional-bytes\x02", zipfile.ZIP_STORED),
)


def _fictional_docx(*, date_time=(2026, 8, 4, 14, 52, 12)) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload, compress_type in FICTIONAL_MEMBERS:
            info = zipfile.ZipInfo(name, date_time)
            info.compress_type = compress_type
            info.external_attr = 0o600 << 16
            info.comment = b"fictional-entry-comment"
            archive.writestr(info, payload)
    return buffer.getvalue()


@pytest.fixture
def fictional_docx_bytes() -> bytes:
    return _fictional_docx()


@pytest.fixture
def fictional_revision_time() -> datetime:
    return datetime(2026, 8, 12, 15, 4, 5, tzinfo=UTC)


def test_docx_normalization_is_byte_stable(fictional_docx_bytes, fictional_revision_time):
    first = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)
    second = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)

    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_normalization_survives_a_differently_stamped_source(fictional_revision_time):
    early = _fictional_docx(date_time=(1999, 1, 2, 3, 4, 5))
    late = _fictional_docx(date_time=(2031, 12, 30, 23, 58, 58))

    assert normalize_docx_bytes(early, document_time=fictional_revision_time) == (
        normalize_docx_bytes(late, document_time=fictional_revision_time)
    )


def test_members_are_emitted_sorted_by_name(fictional_docx_bytes, fictional_revision_time):
    normalized = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)

    with zipfile.ZipFile(io.BytesIO(normalized)) as archive:
        names = archive.namelist()

    assert names == sorted(name for name, _payload, _compress in FICTIONAL_MEMBERS)


def test_every_entry_timestamp_is_rewritten_to_the_fixed_epoch(
    fictional_docx_bytes,
    fictional_revision_time,
):
    normalized = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)

    with zipfile.ZipFile(io.BytesIO(normalized)) as archive:
        stamps = {item.date_time for item in archive.infolist()}

    assert ZIP_ENTRY_TIMESTAMP == (1980, 1, 1, 0, 0, 0)
    assert stamps == {ZIP_ENTRY_TIMESTAMP}


def test_content_compression_permissions_and_comments_are_preserved(
    fictional_docx_bytes,
    fictional_revision_time,
):
    normalized = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)

    with zipfile.ZipFile(io.BytesIO(normalized)) as archive:
        items = {item.filename: item for item in archive.infolist()}
        for name, payload, compress_type in FICTIONAL_MEMBERS:
            if name == CORE_PROPERTIES_NAME:
                continue
            assert archive.read(name) == payload
            assert items[name].compress_type == compress_type
            assert items[name].external_attr == 0o600 << 16
            assert items[name].comment == b"fictional-entry-comment"


def test_core_properties_times_are_normalized_to_the_revision_time(
    fictional_docx_bytes,
    fictional_revision_time,
):
    normalized = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)

    with zipfile.ZipFile(io.BytesIO(normalized)) as archive:
        core = archive.read(CORE_PROPERTIES_NAME).decode("utf-8")

    assert "2026-08-12T15:04:05Z" in core
    assert core.count("2026-08-12T15:04:05Z") == 2
    assert "2001-02-03T04:05:06Z" not in core
    assert "2009-08-07T06:05:04Z" not in core
    assert "Fictional Example Form" in core


def test_a_non_utc_revision_time_is_normalized_to_utc(fictional_docx_bytes):
    from datetime import timedelta, timezone

    utc_bytes = normalize_docx_bytes(
        fictional_docx_bytes,
        document_time=datetime(2026, 8, 12, 15, 4, 5, tzinfo=UTC),
    )
    offset_bytes = normalize_docx_bytes(
        fictional_docx_bytes,
        document_time=datetime(
            2026,
            8,
            12,
            10,
            4,
            5,
            tzinfo=timezone(timedelta(hours=-5)),
        ),
    )

    assert utc_bytes == offset_bytes


def test_normalizing_an_already_normalized_document_is_a_fixed_point(
    fictional_docx_bytes,
    fictional_revision_time,
):
    once = normalize_docx_bytes(fictional_docx_bytes, document_time=fictional_revision_time)
    twice = normalize_docx_bytes(once, document_time=fictional_revision_time)

    assert once == twice


def test_a_document_without_core_properties_still_normalizes(fictional_revision_time):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", b"<w:document>Fictional.</w:document>")

    normalized = normalize_docx_bytes(buffer.getvalue(), document_time=fictional_revision_time)

    with zipfile.ZipFile(io.BytesIO(normalized)) as archive:
        assert archive.namelist() == ["word/document.xml"]


def test_a_document_that_is_not_a_zip_is_rejected(fictional_revision_time):
    with pytest.raises(ValueError):
        normalize_docx_bytes(b"not a fictional zip archive", document_time=fictional_revision_time)
