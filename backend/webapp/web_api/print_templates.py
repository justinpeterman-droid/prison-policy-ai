"""Cookie-authenticated, read-only weekly and monthly print template routes."""

from __future__ import annotations

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.audit import AuditEventInput
from backend.paperwork.templates import (
    PrintTemplateDefinition,
    PrintTemplatePeriod,
    list_print_templates,
    load_print_template,
    validate_print_prefill,
)
from backend.persistence.database import DatabaseUnavailable
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.common import json_body, request_metadata
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


print_templates_bp = Blueprint("web_print_templates", __name__)
_PERIODS = frozenset(item.value for item in PrintTemplatePeriod)
_ACTIONS = frozenset({"preview", "print"})


def _template_data(template: PrintTemplateDefinition) -> dict[str, object]:
    return {
        "code": template.code,
        "title": template.title,
        "period": template.period.value,
        "category": template.category,
        "schema_version": template.schema_version,
        "page_size": template.page_size,
        "orientation": template.orientation,
        "definition": template.definition,
    }


def _period(value: object) -> PrintTemplatePeriod:
    try:
        return PrintTemplatePeriod(value)
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "The print template period is invalid.", status=400) from None


def _codes(value: object, *, period: PrintTemplatePeriod) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 20:
        raise ApiError("validation_failed", "The print template selection is invalid.", status=400)
    if any(not isinstance(code, str) for code in value) or len(value) != len(set(value)):
        raise ApiError("validation_failed", "The print template selection is invalid.", status=400)
    try:
        templates = [load_print_template(code) for code in value]
    except KeyError:
        raise ApiError("validation_failed", "The print template selection is invalid.", status=400) from None
    if any(template.period is not period for template in templates):
        raise ApiError("validation_failed", "The print template selection is invalid.", status=400)
    return value


@print_templates_bp.get("/print-templates")
@require_browser_session
def list_print_templates_route():
    if set(request.args) != {"period"}:
        raise ApiError("validation_failed", "The print template request is invalid.", status=400)
    period = _period(request.args.get("period"))
    return success({"items": [_template_data(item) for item in list_print_templates(period)]})


@print_templates_bp.get("/print-templates/<template_code>")
@require_browser_session
def get_print_template_route(template_code: str):
    if request.args:
        raise ApiError("validation_failed", "The print template request is invalid.", status=400)
    try:
        return success(_template_data(load_print_template(template_code)))
    except KeyError:
        raise ApiError("not_found", "Print template not found.", status=404) from None


@print_templates_bp.post("/print-templates/packet")
@require_browser_session
@require_browser_csrf
def print_packet_route():
    payload = json_body(
        exact={"period", "template_codes", "prefill"},
        message="The print packet request is invalid.",
    )
    period = _period(payload["period"])
    codes = _codes(payload["template_codes"], period=period)
    if not isinstance(payload["prefill"], dict):
        raise ApiError("validation_failed", "The print packet request is invalid.", status=400)
    templates = [load_print_template(code) for code in codes]
    try:
        normalized_prefill: dict[str, object] = {}
        for key, value in payload["prefill"].items():
            matching = [
                template for template in templates
                if key in template.definition.get("prefill_fields", [])
            ]
            if not matching:
                raise ValueError("print prefill is not supported by this packet")
            normalized_prefill.update(validate_print_prefill(matching[0], {key: value}))
    except ValueError:
        raise ApiError("validation_failed", "The print packet prefill is invalid.", status=400) from None
    return success({
        "period": period.value,
        "items": [_template_data(template) for template in templates],
        "prefill": normalized_prefill,
    })


@print_templates_bp.post("/print-templates/actions")
@require_browser_session
@require_browser_csrf
def record_print_template_action_route():
    payload = json_body(
        exact={"period", "template_codes", "action"},
        message="The print template action is invalid.",
    )
    period = _period(payload["period"])
    codes = _codes(payload["template_codes"], period=period)
    action = payload["action"]
    if action not in _ACTIONS:
        raise ApiError("validation_failed", "The print template action is invalid.", status=400)
    request_id, client_version = request_metadata()
    actor = current_browser_actor()
    try:
        current_app.config["AUDIT_WRITER"].append(current_browser_session(), AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action="print_template.action_recorded",
            result="success",
            request_id=request_id,
            target_type="print_template_packet",
            target_id=None,
            details={"template_codes": codes, "print_template_action": action},
            client_version=client_version,
        ))
        current_browser_session().flush()
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError, ValueError):
        raise ApiError(
            "dependency_unavailable",
            "Print template action recording is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    return success({"recorded": True, "period": period.value, "template_codes": codes, "action": action})
