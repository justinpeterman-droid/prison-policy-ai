"""Unit Roster API — read/write staff_roster.json."""
import json
import logging
from pathlib import Path

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

ROSTER_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "staff_roster.json"
VALID_SHIFTS = {"A", "B", "C", "D", "U", "F"}

roster_bp = Blueprint("roster", __name__)


def _load() -> dict:
    if not ROSTER_PATH.exists():
        return {"shifts": {}, "staff": []}
    return json.loads(ROSTER_PATH.read_text())


def _save(data: dict) -> None:
    ROSTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROSTER_PATH.write_text(json.dumps(data, indent=2) + "\n")


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

    data = _load()

    # Check duplicate
    if any(s.get("employee_number", "").strip().lower() == emp.lower() for s in data.get("staff", [])):
        return jsonify({"error": f"Employee number {emp} already exists."}), 409

    entry = {"rank": rank, "first": first, "last": last, "employee_number": emp, "shift": shift}
    data.setdefault("staff", []).append(entry)
    _save(data)
    logger.info("Added staff: %s %s (%s) → shift %s", rank, f"{first} {last}", emp, shift)
    return jsonify({"ok": True})


@roster_bp.route("/api/roster/staff/<emp_id>", methods=["PUT"])
def update_staff(emp_id):
    """Update a staff member's fields (shift reassign, name fix, etc.)."""
    body = request.get_json(silent=True) or {}
    data = _load()

    for person in data.get("staff", []):
        if person.get("employee_number", "").strip() == emp_id.strip():
            if "rank" in body:
                person["rank"] = body["rank"].strip()
            if "first" in body:
                person["first"] = body["first"].strip()
            if "last" in body:
                person["last"] = body["last"].strip()
            if "employee_number" in body:
                person["employee_number"] = body["employee_number"].strip()
            if "shift" in body:
                new_shift = body["shift"].strip().upper()
                if new_shift not in VALID_SHIFTS:
                    return jsonify({"error": f"Invalid shift '{new_shift}'."}), 400
                person["shift"] = new_shift
            _save(data)
            logger.info("Updated staff %s", emp_id)
            return jsonify({"ok": True})

    return jsonify({"error": f"Staff member {emp_id} not found."}), 404


@roster_bp.route("/api/roster/staff/<emp_id>", methods=["DELETE"])
def delete_staff(emp_id):
    """Remove a staff member from the roster."""
    data = _load()
    staff = data.get("staff", [])
    before = len(staff)
    data["staff"] = [s for s in staff if s.get("employee_number", "").strip() != emp_id.strip()]

    if len(data["staff"]) == before:
        return jsonify({"error": f"Staff member {emp_id} not found."}), 404

    _save(data)
    logger.info("Removed staff %s", emp_id)
    return jsonify({"ok": True})
