"""Unit Roster API — read/write the unit roster.

Storage lives in backend/reports/roster_store.py: GCS when ROSTER_BUCKET is
set, the packaged JSON file otherwise. Every mutation goes through
`roster_store.update()` so concurrent edits can't silently drop each other.
"""

import logging

from flask import Blueprint, request, jsonify

from backend.reports import roster_store

logger = logging.getLogger(__name__)

VALID_SHIFTS = {"A", "B", "C", "D", "U", "F"}

roster_bp = Blueprint("roster", __name__)


def _load() -> dict:
    return roster_store.read()


@roster_bp.route("/api/roster", methods=["GET"])
def get_roster():
    """Return the full roster: shifts + staff."""
    data = _load()
    return jsonify({"shifts": data.get("shifts", {}), "staff": data.get("staff", [])})


@roster_bp.route("/api/roster/lookup", methods=["GET"])
def lookup_staff():
    """Search staff by name or employee number (partial match)."""
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"matches": []})

    data = _load()
    matches = []
    for person in data.get("staff", []):
        last = (person.get("last") or "").lower()
        first = (person.get("first") or "").lower()
        emp = (person.get("employee_number") or "").lower()
        full = f"{first} {last}"

        if q in last or q in first or q in full or q in emp or emp.endswith(q):
            matches.append(dict(person))

    return jsonify({"matches": matches})


@roster_bp.route("/api/roster/staff", methods=["POST"])
def add_staff():
    """Add a staff member to the roster."""
    body = request.get_json(silent=True) or {}
    rank = (body.get("rank") or "").strip()
    first = (body.get("first") or "").strip()
    last = (body.get("last") or "").strip()
    emp = (body.get("employee_number") or "").strip()
    shift = (body.get("shift") or "").strip().upper()

    if not last or not emp:
        return jsonify({"error": "Last name and employee number are required."}), 400
    if shift not in VALID_SHIFTS:
        return jsonify({"error": f"Invalid shift '{shift}'. Must be one of: {', '.join(sorted(VALID_SHIFTS))}"}), 400

    def mutate(data: dict):
        # Duplicate check runs inside the mutation so it is re-evaluated after a
        # write conflict — otherwise two simultaneous adds of the same employee
        # number would both pass a check made before either wrote.
        if any(s.get("employee_number", "").strip().lower() == emp.lower() for s in data.get("staff", [])):
            return "duplicate"
        data.setdefault("staff", []).append(
            {
                "rank": rank,
                "first": first,
                "last": last,
                "employee_number": emp,
                "shift": shift,
            }
        )
        return "added"

    if roster_store.update(mutate) == "duplicate":
        return jsonify({"error": f"Employee number {emp} already exists."}), 409

    # Do not log names/employee numbers (PII / CodeQL clear-text-logging).
    logger.info("Added a staff member to the roster (shift %s)", shift)
    return jsonify({"ok": True})


@roster_bp.route("/api/roster/staff/<emp_id>", methods=["PUT"])
def update_staff(emp_id):
    """Update a staff member's fields (shift reassign, name fix, etc.)."""
    body = request.get_json(silent=True) or {}
    new_employee_number = body["employee_number"].strip() if "employee_number" in body else None

    # Validate before mutating so a bad shift is rejected without a round-trip.
    new_shift = body["shift"].strip().upper() if "shift" in body else None
    if new_shift is not None and new_shift not in VALID_SHIFTS:
        return jsonify({"error": f"Invalid shift '{new_shift}'."}), 400

    def mutate(data: dict):
        for person in data.get("staff", []):
            if (person.get("employee_number") or "").strip().casefold() == (emp_id or "").strip().casefold():
                if new_employee_number is not None:
                    candidate = new_employee_number.casefold()
                    if any(
                        other is not person and (other.get("employee_number") or "").strip().casefold() == candidate
                        for other in data.get("staff", [])
                    ):
                        return "duplicate"
                for field in ("rank", "first", "last"):
                    if field in body:
                        person[field] = body[field].strip()
                if new_employee_number is not None:
                    person["employee_number"] = new_employee_number
                if new_shift is not None:
                    person["shift"] = new_shift
                return "updated"
        return "missing"

    result = roster_store.update(mutate)
    if result == "duplicate":
        return jsonify(
            {
                "error": f"Employee number {new_employee_number} already exists.",
            }
        ), 409
    if result == "missing":
        return jsonify({"error": f"Staff member {emp_id} not found."}), 404

    logger.info("Updated a staff member")
    return jsonify({"ok": True})


@roster_bp.route("/api/roster/staff/<emp_id>", methods=["DELETE"])
def delete_staff(emp_id):
    """Remove a staff member from the roster."""

    def mutate(data: dict):
        staff = data.get("staff", [])
        kept = [s for s in staff if s.get("employee_number", "").strip() != emp_id.strip()]
        if len(kept) == len(staff):
            return None  # not found — nothing to write
        data["staff"] = kept
        return "removed"

    if roster_store.update(mutate) is None:
        return jsonify({"error": f"Staff member {emp_id} not found."}), 404

    logger.info("Removed a staff member")
    return jsonify({"ok": True})
