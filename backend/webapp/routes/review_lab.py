"""Admin-only Demo Review Lab page and persistence APIs."""

from flask import Blueprint, Response, jsonify, render_template, request

from backend.pipeline.config import (
    REVIEW_BUCKET,
    REVIEW_LAB_ENABLED,
    REVIEW_OBJECT_PREFIX,
)
from backend.reports.demo_scenarios import load_demo_scenarios
from backend.reports.review_schema import (
    ReviewValidationError,
    build_review_submission,
    review_summary,
)
from backend.reports.review_store import (
    ReviewConflictError,
    ReviewStore,
    ReviewStoreUnavailable,
)
from backend.identity.browser_handoffs import require_review_lab_access

review_lab_bp = Blueprint("review_lab", __name__)
_store = None


def _get_store():
    global _store
    if _store is None:
        _store = ReviewStore(REVIEW_BUCKET, REVIEW_OBJECT_PREFIX)
    return _store


def _not_found():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found."}), 404
    return render_template("404.html"), 404


def _limit(default: int, maximum: int) -> int:
    raw = request.args.get("limit", str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ReviewValidationError("limit must be an integer") from exc
    if not 1 <= value <= maximum:
        raise ReviewValidationError(f"limit must be from 1 to {maximum}")
    return value


@review_lab_bp.route("/review-lab")
@require_review_lab_access
def review_lab_page():
    if not REVIEW_LAB_ENABLED:
        return _not_found()
    return render_template(
        "reports.html",
        demo_scenarios=load_demo_scenarios(),
        review_mode=True,
    )


@review_lab_bp.route("/api/review-lab/submissions", methods=["POST"])
@require_review_lab_access
def review_lab_submit():
    if not REVIEW_LAB_ENABLED:
        return _not_found()
    payload = request.get_json(silent=True) or {}
    try:
        record = build_review_submission(payload)
        try:
            object_name = _get_store().save(record)
        except ReviewConflictError:
            record = build_review_submission(payload)
            object_name = _get_store().save(record)
    except ReviewValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except (ReviewStoreUnavailable, ReviewConflictError):
        return jsonify({"error": "Review could not be saved. Your edits are still on this page."}), 503
    return jsonify(
        {
            "submission_id": record["submission_id"],
            "object_name": object_name,
        }
    ), 201


@review_lab_bp.route("/api/review-lab/submissions", methods=["GET"])
@require_review_lab_access
def review_lab_list():
    if not REVIEW_LAB_ENABLED:
        return _not_found()
    try:
        records, skipped = _get_store().list_records(limit=_limit(50, 200))
    except ReviewValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ReviewStoreUnavailable:
        return jsonify({"error": "Saved reviews are temporarily unavailable."}), 503
    return jsonify(
        {
            "submissions": [review_summary(item) for item in records],
            "skipped": skipped,
        }
    )


@review_lab_bp.route("/api/review-lab/submissions/<submission_id>")
@require_review_lab_access
def review_lab_get(submission_id):
    if not REVIEW_LAB_ENABLED:
        return _not_found()
    try:
        record = _get_store().get(submission_id)
    except ValueError:
        return _not_found()
    except ReviewStoreUnavailable:
        return jsonify({"error": "Saved review is temporarily unavailable."}), 503
    if record is None:
        return _not_found()
    response = jsonify(record)
    response.headers["Content-Disposition"] = f'attachment; filename="{submission_id}.json"'
    return response


@review_lab_bp.route("/api/review-lab/export")
@require_review_lab_access
def review_lab_export():
    if not REVIEW_LAB_ENABLED:
        return _not_found()
    try:
        payload, skipped = _get_store().export_jsonl(limit=_limit(1000, 1000))
    except ReviewValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ReviewStoreUnavailable:
        return jsonify({"error": "Saved reviews are temporarily unavailable."}), 503
    return Response(
        payload,
        mimetype="application/x-ndjson",
        headers={
            "Content-Disposition": ('attachment; filename="review-lab-submissions.jsonl"'),
            "X-Review-Records-Skipped": str(skipped),
        },
    )
