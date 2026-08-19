"""Server-enforced action policy for incident forms and report presentations."""
from collections.abc import Mapping

from backend.persistence.models.reporting import ReportType


class DocumentActionNotAllowed(ValueError):
    """The requested action is not valid for the output presentation."""


_DOWNLOAD_ACTIONS = {
    "word": "download_word",
    "pdf": "download_pdf",
    "print": "print",
}
_COPY_REPORT_TYPES = frozenset({
    ReportType.SUPERVISOR_SUMMARY,
    ReportType.DISCIPLINARY,
})
_DOCUMENT_REPORT_TYPES = frozenset({
    ReportType.FIRST_PERSON,
    ReportType.COVER_LETTER,
    ReportType.INVESTIGATION,
    ReportType.FORM_005,
})


def allowed_form_actions(
    output_kind: str,
    definition: Mapping[str, object],
) -> frozenset[str]:
    """Return only actions explicitly supported by a catalog form definition."""
    if output_kind == "physical_only":
        return frozenset()
    if output_kind != "digital_document":
        raise DocumentActionNotAllowed(f"Unknown form output kind: {output_kind}")
    if not isinstance(definition, Mapping):
        raise DocumentActionNotAllowed("The form definition is invalid.")
    raw_formats = definition.get("download_formats", [])
    if not isinstance(raw_formats, list) or not all(
        isinstance(value, str) for value in raw_formats
    ):
        raise DocumentActionNotAllowed("The form download formats are invalid.")

    actions = {"preview"}
    for value in raw_formats:
        mapped = _DOWNLOAD_ACTIONS.get(value)
        if mapped is None:
            raise DocumentActionNotAllowed(
                f"Unsupported form download format: {value}"
            )
        actions.add(mapped)
    return frozenset(actions)


def validate_form_action(
    *,
    output_kind: str,
    definition: Mapping[str, object],
    action: str,
) -> None:
    if output_kind == "physical_only":
        raise DocumentActionNotAllowed(
            "Physical-only paperwork has no digital action."
        )
    if action not in allowed_form_actions(output_kind, definition):
        raise DocumentActionNotAllowed(
            f"{action} is not allowed for {output_kind}."
        )


def _report_type(value: str | ReportType) -> ReportType:
    if isinstance(value, ReportType):
        return value
    try:
        return ReportType(value)
    except ValueError as exc:
        raise DocumentActionNotAllowed(f"Unknown report type: {value}") from exc


def allowed_report_actions(report_type: str | ReportType) -> frozenset[str]:
    """Separate copy-to-records reports from printable document reports."""
    resolved = _report_type(report_type)
    if resolved in _COPY_REPORT_TYPES:
        return frozenset({"edit", "copy_text"})
    if resolved in _DOCUMENT_REPORT_TYPES:
        return frozenset({"edit", "preview", "print", "download_word"})
    raise DocumentActionNotAllowed(f"Unknown report type: {resolved.value}")


def validate_report_action(
    report_type: str | ReportType,
    action: str,
) -> None:
    resolved = _report_type(report_type)
    if action not in allowed_report_actions(resolved):
        raise DocumentActionNotAllowed(
            f"{action} is not allowed for {resolved.value}."
        )
