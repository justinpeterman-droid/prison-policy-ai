"""Audited, deterministic Word exports of immutable report revisions (RP-09).

An export is metadata plus bytes that are *reproducible*: the same immutable
revision, exported again under the same idempotency key, must produce the same
document and the same SHA-256. That is what makes an exported 005 evidentiary
rather than merely printed.

Three rules hold this together:

1. **The revision is the only input.** The filler is fed a deep copy of the
   saved snapshot -- `fill_template()` mutates the metadata dict it is given,
   and it fills date/time defaults from `datetime.now()`, so every volatile
   field is supplied explicitly from the revision's own timestamp instead.
2. **Bytes are normalized** by `deterministic_docx.normalize_docx_bytes()`.
3. **Only metadata is persisted.** The `exports` row stores identifiers, a
   digest, a size, a MIME type, a template version and a download name. The
   document itself lives in a per-request temporary directory that is removed
   when the response closes; nothing is retained centrally.

Export row identifiers are derived (`uuid5`) from the idempotency record and
the revision, so a replay re-derives the identifiers it already wrote instead
of inserting a second row or handing back a different manifest.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from uuid import NAMESPACE_URL, UUID, uuid5
import zipfile

from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput
from backend.identity.idempotency import (
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.models.jobs import Export
from backend.persistence.models.reporting import Report, ReportRevision
from backend.reports.deterministic_docx import ZIP_ENTRY_TIMESTAMP, normalize_docx_bytes
from backend.reports.filler import TEMPLATE_PATH, fill_template


EXPORT_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
BULK_EXPORT_MIME_TYPE = "application/zip"
#: Release-1 ceiling on one bulk operation (Admin client design).
BULK_EXPORT_MAX_DOCUMENTS = 100
#: The sole release-1 bulk revision policy.
BULK_REVISION_SELECTION = "current_at_request"
MANIFEST_NAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = 1
#: Every per-request temporary directory this module owns carries this prefix.
EXPORT_TEMP_PREFIX = "prison-policy-export-"
BULK_ARCHIVE_NAME = "report-export.zip"

_EXPORT_NAMESPACE = uuid5(NAMESPACE_URL, "https://prison-policy.invalid/exports/document")
_BULK_NAMESPACE = uuid5(NAMESPACE_URL, "https://prison-policy.invalid/exports/bulk")

#: Placeholder names the 005 template understands. Anything else a client put
#: in `editable_fields` is ignored rather than smuggled into the document.
FILLER_FIELDS = frozenset(
    {
        "unit_division",
        "officer_last",
        "officer_first",
        "employee_number",
        "rank",
        "shift_assignment",
        "date",
        "time",
        "location",
        "inmates_involved",
        "employees_involved",
        "inmates_present",
        "employees_present",
        "others_present",
        "inmate_injuries",
        "inmate_treatment",
        "officer_injuries",
        "officer_treatment",
        "recommendation",
        "officer_signature",
        "date_filed",
        "supervisor_name",
        "reporting_employee_signature",
        "supervisor_signature",
        "box_005",
        "box_409",
    }
)

#: Compact failure codes for the bounded idempotency response reference.
_FAILURE_CODES = {"n": "not_found", "g": "generation_failed"}
_FAILURE_LETTERS = {value: key for key, value in _FAILURE_CODES.items()}

_template_version: str | None = None


class ExportGenerationFailed(RuntimeError):
    """One document could not be produced; the bulk manifest records it."""


@dataclass(frozen=True)
class ExportedDocument:
    report_id: UUID
    revision_id: UUID
    revision_number: int
    export_id: UUID
    data: bytes
    sha256: bytes
    download_name: str
    template_version: str

    @property
    def byte_length(self) -> int:
        return len(self.data)

    def reference(self) -> dict[str, object]:
        """Safe scalars only -- identifiers, digest, size, name."""
        return {
            "export_id": str(self.export_id),
            "report_id": str(self.report_id),
            "revision_number": self.revision_number,
            "sha256": self.sha256.hex(),
            "byte_length": self.byte_length,
            "download_name": self.download_name,
            "template_version": self.template_version,
        }


@dataclass(frozen=True)
class ExportFailure:
    report_id: UUID
    revision_number: int | None
    reason_code: str


@dataclass(frozen=True)
class BulkExportResult:
    export_id: UUID
    data: bytes
    sha256: bytes
    download_name: str
    template_version: str
    documents: list[ExportedDocument] = field(default_factory=list)
    failures: list[ExportFailure] = field(default_factory=list)

    @property
    def byte_length(self) -> int:
        return len(self.data)


# --- Template identity ------------------------------------------------------


def template_version() -> str:
    """A stable, short identity for the 005 template that produced a document."""
    global _template_version
    if _template_version is None:
        try:
            digest = hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest()[:16]
        except OSError:
            digest = "unavailable"
        _template_version = f"{TEMPLATE_PATH.stem}:{digest}"
    return _template_version


# --- Deterministic document generation --------------------------------------


def _revision_time(revision: ReportRevision) -> datetime:
    created = revision.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created.astimezone(UTC)


def revision_metadata(report: Report, revision: ReportRevision) -> dict[str, str]:
    """Build filler metadata from a deep copy of the saved snapshot.

    `fill_template()` mutates the dict it is handed and fills `date`, `time`
    and `date_filed` from the wall clock when they are absent -- which would
    make two exports of one immutable revision differ. Every volatile value is
    therefore derived here from the revision's own timestamp.
    """
    snapshot = deepcopy(revision.snapshot) if isinstance(revision.snapshot, dict) else {}
    editable = snapshot.get("editable_fields")
    metadata: dict[str, str] = {}
    if isinstance(editable, dict):
        for name, value in editable.items():
            if name in FILLER_FIELDS and isinstance(value, (str, int, float)):
                metadata[name] = str(value)
    narrative = snapshot.get("narrative")
    metadata["narrative"] = narrative if isinstance(narrative, str) else ""
    moment = _revision_time(revision)
    metadata.setdefault("date", moment.strftime("%B %d, %Y"))
    metadata.setdefault("time", moment.strftime("%I:%M %p"))
    metadata.setdefault("date_filed", moment.strftime("%B %d, %Y"))
    return metadata


def build_revision_docx(report: Report, revision: ReportRevision) -> bytes:
    """Fill and normalize one immutable revision into deterministic bytes."""
    workspace = tempfile.mkdtemp(prefix=EXPORT_TEMP_PREFIX)
    try:
        target = Path(workspace) / "document.docx"
        result = fill_template(revision_metadata(report, revision), output_path=target)
        path = result.get("path")
        if not path:
            raise ExportGenerationFailed("the 005 template is unavailable")
        raw = Path(path).read_bytes()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    return normalize_docx_bytes(raw, document_time=_revision_time(revision))


def download_name(report_id: UUID, revision_number: int) -> str:
    """A name built from identifiers only -- never a staff or inmate name."""
    return f"report-{report_id}-revision-{revision_number}.docx"


def _document_export_id(idempotency_record_id: UUID, revision_id: UUID) -> UUID:
    return uuid5(_EXPORT_NAMESPACE, f"{idempotency_record_id}:{revision_id}")


def bulk_export_id(idempotency_record_id: UUID) -> UUID:
    return uuid5(_BULK_NAMESPACE, str(idempotency_record_id))


def export_report_docx(
    session: Session,
    *,
    actor,
    report: Report,
    revision: ReportRevision,
    request_id: str,
    idempotency_record_id: UUID,
    persist: bool = True,
) -> ExportedDocument:
    """Generate one deterministic DOCX and record its metadata exactly once."""
    data = build_revision_docx(report, revision)
    digest = hashlib.sha256(data).digest()
    export_id = _document_export_id(idempotency_record_id, revision.id)
    name = download_name(report.id, revision.revision_number)
    version = template_version()
    if persist:
        session.add(
            Export(
                id=export_id,
                report_id=report.id,
                report_revision_id=revision.id,
                exported_by_account_id=actor.account_id,
                template_version=version,
                output_sha256=digest,
                size_bytes=len(data),
                mime_type=EXPORT_MIME_TYPE,
                download_name=name,
                request_id=request_id,
            )
        )
        session.flush()
    return ExportedDocument(
        report_id=report.id,
        revision_id=revision.id,
        revision_number=revision.revision_number,
        export_id=export_id,
        data=data,
        sha256=digest,
        download_name=name,
        template_version=version,
    )


def perform_single_export(
    session: Session,
    *,
    actor,
    report: Report,
    revision: ReportRevision,
    request_id: str,
    idempotency_key: str,
    idempotency_action: str,
    audit_action: str,
    audit_writer,
    client_version: str,
    now: datetime,
) -> ExportedDocument:
    """Claim ID-06, generate, record metadata, and audit in one transaction.

    A replay of the same key regenerates the same bytes from the same
    immutable revision without inserting a second `exports` row or writing a
    second audit event.
    """
    claim = claim_idempotency(
        session,
        actor,
        key=idempotency_key,
        action=idempotency_action,
        request_sha256=request_digest(
            {
                "action": idempotency_action,
                "report_id": str(report.id),
                "revision_number": revision.revision_number,
            }
        ),
        now=now,
    )
    document = export_report_docx(
        session,
        actor=actor,
        report=report,
        revision=revision,
        request_id=request_id,
        idempotency_record_id=claim.record_id,
        persist=not claim.replayed,
    )
    if not claim.replayed:
        audit_writer.append(
            session,
            AuditEventInput(
                actor_account_id=actor.account_id,
                actor_staff_member_id=actor.staff_member_id,
                action=audit_action,
                result="success",
                request_id=request_id,
                target_type="report",
                target_id=report.id,
                details={
                    "report_id": str(report.id),
                    "export_id": str(document.export_id),
                    "export_format": "docx",
                },
                client_version=client_version,
            ),
        )
        complete_idempotency(
            session,
            claim,
            response_status=200,
            response_reference=document.reference(),
            now=now,
        )
    return document


# --- Bulk archive -----------------------------------------------------------


def _manifest_document(
    documents: list[ExportedDocument],
    failures: list[ExportFailure],
    *,
    actor_account_id: UUID,
    reason: str,
    filter_names: list[str],
    selection_mode: str,
    recorded_at: datetime,
) -> dict[str, object]:
    return {
        "actor_account_id": str(actor_account_id),
        "failures": [
            {
                "report_id": str(item.report_id),
                "reason_code": item.reason_code,
                "revision_number": item.revision_number,
            }
            for item in failures
        ],
        "filter_names": filter_names,
        "idempotency_recorded_at": recorded_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "reason": reason,
        "reports": [
            {
                "byte_length": document.byte_length,
                "document_name": document.download_name,
                "export_id": str(document.export_id),
                "report_id": str(document.report_id),
                "revision_id": str(document.revision_id),
                "revision_number": document.revision_number,
                "sha256": document.sha256.hex(),
            }
            for document in documents
        ],
        "revision_selection": BULK_REVISION_SELECTION,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "selection_mode": selection_mode,
        "template_version": template_version(),
    }


def _zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, ZIP_ENTRY_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload)
    return output.getvalue()


def export_reports_zip(
    session: Session,
    *,
    actor,
    selections: list[tuple[Report, ReportRevision]],
    known_failures: tuple[ExportFailure, ...] = (),
    request_id: str,
    idempotency_record_id: UUID,
    reason: str,
    filter_names: list[str],
    selection_mode: str,
    recorded_at: datetime,
    persist: bool = True,
) -> BulkExportResult:
    """Generate the bounded archive for an already-resolved selection.

    `selections` is resolved and ordered by the caller *before* this runs, so
    no document is generated for an unbounded or floating selection. A failure
    here is explicit in the manifest and never produces an `exports` row.
    """
    documents: list[ExportedDocument] = []
    failures = list(known_failures)
    for report, revision in selections:
        try:
            documents.append(
                export_report_docx(
                    session,
                    actor=actor,
                    report=report,
                    revision=revision,
                    request_id=request_id,
                    idempotency_record_id=idempotency_record_id,
                    persist=persist,
                )
            )
        except Exception:  # noqa: BLE001 - one document must not fail the archive
            failures.append(
                ExportFailure(
                    report_id=report.id,
                    revision_number=revision.revision_number,
                    reason_code="generation_failed",
                )
            )
    failures.sort(key=lambda item: str(item.report_id))
    manifest = _manifest_document(
        documents,
        failures,
        actor_account_id=actor.account_id,
        reason=reason,
        filter_names=filter_names,
        selection_mode=selection_mode,
        recorded_at=recorded_at,
    )
    entries = [(document.download_name, document.data) for document in documents]
    entries.append(
        (
            MANIFEST_NAME,
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
        )
    )
    data = _zip_bytes(sorted(entries, key=lambda item: item[0]))
    return BulkExportResult(
        export_id=bulk_export_id(idempotency_record_id),
        data=data,
        sha256=hashlib.sha256(data).digest(),
        download_name=BULK_ARCHIVE_NAME,
        template_version=template_version(),
        documents=documents,
        failures=failures,
    )


# --- Bounded idempotency reference ------------------------------------------


def bulk_reference(result: BulkExportResult) -> dict[str, object]:
    """Encode the resolved selection compactly enough for ID-06 storage.

    Revision identifiers are enough to regenerate byte-identical documents;
    export identifiers are re-derived from the idempotency record, so they do
    not need storing. No name, note, filter value, or byte ever appears here.
    """
    return {
        "format": "docx_zip",
        "ok": ",".join(document.revision_id.hex for document in result.documents),
        "failed": ",".join(
            f"{item.report_id.hex}{_FAILURE_LETTERS[item.reason_code]}{item.revision_number or 0}"
            for item in result.failures
        ),
        "report_count": len(result.documents),
    }


def stream_export(
    *,
    data: bytes,
    mime_type: str,
    name: str,
    sha256: bytes,
    export_id: UUID,
    template_version_value: str,
    revision_number: int | None = None,
):
    """Write the document to an owned temporary directory and stream it back.

    The bytes leave through the response and the directory is removed when the
    response closes, so nothing is retained centrally after delivery.
    """
    from flask import current_app, request
    from werkzeug.wsgi import wrap_file

    workspace = tempfile.mkdtemp(prefix=EXPORT_TEMP_PREFIX)
    path = Path(workspace) / name
    path.write_bytes(data)
    handle = path.open("rb")

    def _cleanup() -> None:
        try:
            handle.close()
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    try:
        # Deliberately not `direct_passthrough`: Werkzeug returns a
        # passthrough iterable unwrapped, so the response's close callbacks --
        # the ones that delete this workspace -- would never run.
        response = current_app.response_class(
            wrap_file(request.environ, handle),
            mimetype=mime_type,
        )
    except BaseException:
        _cleanup()
        raise
    response.call_on_close(_cleanup)
    response.headers["Content-Length"] = str(len(data))
    response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    response.headers["Digest"] = "sha-256=" + _b64(sha256)
    response.headers["X-Export-ID"] = str(export_id)
    response.headers["X-Template-Version"] = template_version_value
    if revision_number is not None:
        response.headers["X-Report-Revision"] = str(revision_number)
    response.headers["Cache-Control"] = "no-store"
    return response


def _b64(digest: bytes) -> str:
    import base64

    return base64.b64encode(digest).decode("ascii")


def decode_bulk_reference(
    reference: dict[str, object],
) -> tuple[tuple[UUID, ...], tuple[tuple[UUID, int | None, str], ...]]:
    """Decode a stored selection back into revision ids and explicit failures."""
    raw_ok = str(reference.get("ok") or "")
    revision_ids = tuple(UUID(hex=item) for item in raw_ok.split(",") if item)
    failures: list[tuple[UUID, int | None, str]] = []
    for item in str(reference.get("failed") or "").split(","):
        if not item:
            continue
        report_id, letter, number = UUID(hex=item[:32]), item[32], item[33:]
        failures.append(
            (
                report_id,
                int(number) or None,
                _FAILURE_CODES[letter],
            )
        )
    return revision_ids, tuple(failures)
