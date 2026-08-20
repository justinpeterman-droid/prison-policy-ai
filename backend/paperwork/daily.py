"""Strict payload contracts and derived rules for daily operational paperwork."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from copy import deepcopy
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.paperwork.daily_templates import (
    DailyPaperworkKind,
    load_daily_template,
)


ShortText = Annotated[str, Field(max_length=160)]
RequiredShortText = Annotated[str, Field(min_length=1, max_length=160)]
InspectionValue = Literal["S", "N/I", "U", "NONE"]
EquipmentState = Literal["yes", "no", "not_checked"]
AssignmentState = Literal["unassigned", "assigned", "no_officer_available"]
DetectorResult = Literal["P", "F"]
PerimeterResult = Literal["S", "U"]

ROSTER_DEFINITION = load_daily_template(DailyPaperworkKind.ASSIGNMENT_ROSTER).definition
ROSTER_ZONE_POSTS = {
    str(zone["code"]): tuple(str(post["code"]) for post in zone["posts"])
    for zone in ROSTER_DEFINITION["zones"]
}
ROSTER_ZONE_CODES = tuple(ROSTER_ZONE_POSTS)
SECURITY_EQUIPMENT_KEYS = (
    "digital_camera",
    "video_camera_go_pro",
    "metal_detector_wands",
)
DETECTOR_CODES = tuple(str(number) for number in range(1, 12))
DETECTOR_POSITION_CODES = tuple(f"position_{number}" for number in range(1, 8))
PERIMETER_DEFINITION = load_daily_template(DailyPaperworkKind.PERIMETER_CHECK).definition
PERIMETER_CHECK_CODES = tuple(
    str(item["code"])
    for group in PERIMETER_DEFINITION["groups"]
    for item in group["items"]
)
RANDOM_SEARCH_SECTION_CODES = ("north_1", "north_2", "south_1", "south_2")
DETECTOR_SIGN_OUT_CODES = tuple(f"D{number}" for number in range(1, 10))

ROSTER_POST_METADATA = {
    str(post["code"]): {
        "label": str(post["label"]),
        "priority": str(post["priority"]),
    }
    for zone in ROSTER_DEFINITION["zones"]
    for post in zone["posts"]
}


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StaffSelection(ClosedModel):
    staff_id: UUID
    display_name_snapshot: RequiredShortText

    @field_validator("display_name_snapshot")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("display name is required")
        return cleaned


class DailyPayloadBase(ClosedModel):
    schema_version: Literal[1] = 1
    work_date: date
    shift: str = Field(min_length=1, max_length=32)

    @field_validator("shift")
    @classmethod
    def normalize_shift(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("shift is required")
        return cleaned


class PostAssignment(ClosedModel):
    post_code: str = Field(min_length=1, max_length=80)
    initial_staff: StaffSelection | None = None
    rotation_staff: StaffSelection | None = None
    initial_state: AssignmentState = "unassigned"
    rotation_state: AssignmentState = "unassigned"

    @model_validator(mode="before")
    @classmethod
    def infer_legacy_assignment_states(cls, value):
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "initial_state" not in normalized:
            normalized["initial_state"] = (
                "assigned" if normalized.get("initial_staff") is not None else "unassigned"
            )
        if "rotation_state" not in normalized:
            normalized["rotation_state"] = (
                "assigned" if normalized.get("rotation_staff") is not None else "unassigned"
            )
        return normalized

    @model_validator(mode="after")
    def match_assignment_states_to_staff(self):
        for state, staff, label in (
            (self.initial_state, self.initial_staff, "initial"),
            (self.rotation_state, self.rotation_staff, "rotation"),
        ):
            if (state == "assigned") != (staff is not None):
                raise ValueError(f"{label} assignment state does not match selected staff")
        return self


class ZoneAssignment(ClosedModel):
    zone_code: str = Field(min_length=1, max_length=80)
    supervisor: StaffSelection | None = None
    posts: list[PostAssignment] = Field(max_length=40)


class LeaveEntry(ClosedModel):
    staff: StaffSelection
    leave_time: ShortText = ""
    leave_type: ShortText = ""


class ExtraAssignment(ClosedModel):
    label: RequiredShortText
    staff: StaffSelection | None = None


class AssignmentRosterV1(DailyPayloadBase):
    captain: StaffSelection | None = None
    lieutenant: StaffSelection | None = None
    duty_warden: ShortText | None = None
    alternate_shift_supervisor: StaffSelection | None = None
    leave_entries: list[LeaveEntry] = Field(default_factory=list, max_length=40)
    extra_assignments: list[ExtraAssignment] = Field(default_factory=list, max_length=40)
    zones: list[ZoneAssignment]
    briefing_minutes: str = Field(default="", max_length=10_000)
    roll_call_completed: bool = False
    uniform_inspection_completed: bool = False
    equipment: dict[str, EquipmentState]
    briefing_guests: list[RequiredShortText] = Field(default_factory=list, max_length=20)
    assigned_and_dismissed: bool = False
    lieutenant_signature_name: ShortText | None = None

    @model_validator(mode="after")
    def match_approved_roster_structure(self):
        zone_codes = tuple(zone.zone_code for zone in self.zones)
        if zone_codes != ROSTER_ZONE_CODES:
            raise ValueError("roster zones must match the approved template order")
        for zone in self.zones:
            post_codes = tuple(post.post_code for post in zone.posts)
            approved_codes = ROSTER_ZONE_POSTS[zone.zone_code]
            if len(post_codes) != len(approved_codes) or set(post_codes) != set(approved_codes):
                raise ValueError(
                    f"posts for {zone.zone_code} must contain each approved post exactly once"
                )
        if set(self.equipment) != set(SECURITY_EQUIPMENT_KEYS):
            raise ValueError("equipment keys must match the approved template")
        return self


class UniformInspectionRow(ClosedModel):
    staff: StaffSelection
    shirt: InspectionValue | None = None
    pants: InspectionValue | None = None
    shoes: InspectionValue | None = None
    cap: InspectionValue | None = None
    coat: InspectionValue | None = None
    id: InspectionValue | None = None
    hair: InspectionValue | None = None
    nails: InspectionValue | None = None
    comments: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_comment_for_unsatisfactory_result(self):
        values = (
            self.shirt,
            self.pants,
            self.shoes,
            self.cap,
            self.coat,
            self.id,
            self.hair,
            self.nails,
        )
        if "U" in values and not self.comments.strip():
            raise ValueError("an unsatisfactory uniform result requires a comment")
        return self


class UniformInspectionV1(DailyPayloadBase):
    roster_record_id: UUID | None = None
    roster_revision_number: int | None = Field(default=None, ge=1)
    inspector: StaffSelection | None = None
    rows: list[UniformInspectionRow] = Field(default_factory=list, max_length=250)

    @model_validator(mode="after")
    def reject_duplicate_staff(self):
        staff_ids = [row.staff.staff_id for row in self.rows]
        if len(staff_ids) != len(set(staff_ids)):
            raise ValueError("uniform inspection staff must be unique")
        if (self.roster_record_id is None) != (self.roster_revision_number is None):
            raise ValueError("roster provenance must include both record and revision")
        return self


class DetectorPositionTest(ClosedModel):
    position_code: str = Field(min_length=1, max_length=80)
    result: DetectorResult | None = None


class DetectorTestRow(ClosedModel):
    detector_code: str = Field(min_length=1, max_length=16)
    location: ShortText = ""
    equipment_identifier: ShortText = ""
    tests: list[DetectorPositionTest]
    corrective_action: str = Field(default="", max_length=2_000)

    @model_validator(mode="after")
    def validate_positions_and_failures(self):
        if tuple(test.position_code for test in self.tests) != DETECTOR_POSITION_CODES:
            raise ValueError("detector positions must match the approved template order")
        if any(test.result == "F" for test in self.tests) and not self.corrective_action.strip():
            raise ValueError("a failed detector test requires corrective action")
        return self


class MetalDetectorTestV1(DailyPayloadBase):
    detectors: list[DetectorTestRow]
    tested_by: StaffSelection | None = None
    reviewed_by: StaffSelection | None = None
    comments: str = Field(default="", max_length=10_000)

    @model_validator(mode="after")
    def match_approved_detectors(self):
        if tuple(detector.detector_code for detector in self.detectors) != DETECTOR_CODES:
            raise ValueError("detectors must match the approved template order")
        return self


class PerimeterCheckResult(ClosedModel):
    check_code: str = Field(min_length=1, max_length=100)
    result: PerimeterResult | None = None


class PerimeterCheckV1(DailyPayloadBase):
    checks: list[PerimeterCheckResult]
    perimeter_inspector: StaffSelection | None = None
    perimeter_signature_name: ShortText | None = None
    perimeter_inspected_at: datetime | None = None
    senstar_inspector: StaffSelection | None = None
    supervisor_signature_name: ShortText | None = None
    supervisor_signed_at: datetime | None = None

    @model_validator(mode="after")
    def match_approved_checks(self):
        if tuple(check.check_code for check in self.checks) != PERIMETER_CHECK_CODES:
            raise ValueError("perimeter checks must match the approved template order")
        return self


class RandomSearchBlock(ClosedModel):
    officer: StaffSelection | None = None
    search_date: date | None = None
    search_time: time | None = None
    individual_last_name: ShortText = ""
    individual_number: str = Field(default="", max_length=64)
    barracks_rack: ShortText = ""
    contraband_disposition: str = Field(default="", max_length=2_000)


class RandomSearchSection(ClosedModel):
    section_code: str = Field(min_length=1, max_length=32)
    blocks: list[RandomSearchBlock] = Field(min_length=4, max_length=4)


class RandomSearchLogV1(DailyPayloadBase):
    sections: list[RandomSearchSection]

    @model_validator(mode="after")
    def match_approved_sections(self):
        if tuple(section.section_code for section in self.sections) != RANDOM_SEARCH_SECTION_CODES:
            raise ValueError("random-search sections must match the approved template order")
        return self


class DetectorSignOutRow(ClosedModel):
    unit_code: str = Field(min_length=1, max_length=16)
    staff: StaffSelection | None = None
    area_of_assignment: ShortText = ""


class DetectorSignOutV1(DailyPayloadBase):
    units: list[DetectorSignOutRow]
    shift_supervisor: StaffSelection | None = None
    sign_out_date: date | None = None

    @model_validator(mode="after")
    def match_approved_units(self):
        if tuple(unit.unit_code for unit in self.units) != DETECTOR_SIGN_OUT_CODES:
            raise ValueError("detector units must match the approved template order")
        return self


DailyPayload = (
    AssignmentRosterV1
    | UniformInspectionV1
    | MetalDetectorTestV1
    | PerimeterCheckV1
    | RandomSearchLogV1
    | DetectorSignOutV1
)

DAILY_PAYLOAD_MODELS: dict[DailyPaperworkKind, type[DailyPayloadBase]] = {
    DailyPaperworkKind.ASSIGNMENT_ROSTER: AssignmentRosterV1,
    DailyPaperworkKind.UNIFORM_INSPECTION: UniformInspectionV1,
    DailyPaperworkKind.METAL_DETECTOR_TEST: MetalDetectorTestV1,
    DailyPaperworkKind.PERIMETER_CHECK: PerimeterCheckV1,
    DailyPaperworkKind.RANDOM_SEARCH_LOG: RandomSearchLogV1,
    DailyPaperworkKind.DETECTOR_SIGN_OUT: DetectorSignOutV1,
}


def validate_daily_payload(
    kind: DailyPaperworkKind | str,
    payload: dict[str, object],
) -> DailyPayloadBase:
    try:
        selected_kind = kind if isinstance(kind, DailyPaperworkKind) else DailyPaperworkKind(kind)
    except ValueError:
        raise ValueError("daily paperwork kind is invalid") from None
    return DAILY_PAYLOAD_MODELS[selected_kind].model_validate(payload)


@dataclass(frozen=True)
class CoverageWarning:
    code: Literal[
        "p1_unfilled",
        "duplicate_initial_assignment",
        "duplicate_rotation_assignment",
    ]
    message: str
    zone_code: str
    post_code: str | None
    staff_id: UUID | None


def calculate_roster_coverage(
    roster: AssignmentRosterV1 | dict[str, object],
) -> tuple[CoverageWarning, ...]:
    """Return immutable coverage warnings without altering roster assignments."""
    model = (
        roster
        if isinstance(roster, AssignmentRosterV1)
        else AssignmentRosterV1.model_validate(roster)
    )
    warnings: list[CoverageWarning] = []
    for zone in model.zones:
        for post in zone.posts:
            metadata = ROSTER_POST_METADATA[post.post_code]
            if metadata["priority"] == "P1" and post.initial_staff is None:
                warnings.append(CoverageWarning(
                    code="p1_unfilled",
                    message=f'{metadata["label"]} requires an initial assignment.',
                    zone_code=zone.zone_code,
                    post_code=post.post_code,
                    staff_id=None,
                ))

    for attribute, code, label in (
        ("initial_staff", "duplicate_initial_assignment", "initial"),
        ("rotation_staff", "duplicate_rotation_assignment", "rotation"),
    ):
        assignments: dict[UUID, list[tuple[str, str]]] = {}
        for zone in model.zones:
            for post in zone.posts:
                if ROSTER_POST_METADATA[post.post_code]["priority"] != "P1":
                    continue
                staff = getattr(post, attribute)
                if staff is not None:
                    assignments.setdefault(staff.staff_id, []).append(
                        (zone.zone_code, post.post_code)
                    )
        for staff_id, locations in assignments.items():
            if len(locations) < 2:
                continue
            zone_code, _ = locations[0]
            warnings.append(CoverageWarning(
                code=code,
                message=f"One staff member has multiple simultaneous {label} P1 assignments.",
                zone_code=zone_code,
                post_code=None,
                staff_id=staff_id,
            ))
    return tuple(warnings)


def prepare_copied_roster_payload(
    source: AssignmentRosterV1 | dict[str, object],
    *,
    target_work_date: date | str,
    shift: str,
) -> AssignmentRosterV1:
    """Copy stable assignment structure while clearing daily completion data."""
    model = (
        source
        if isinstance(source, AssignmentRosterV1)
        else AssignmentRosterV1.model_validate(source)
    )
    copied = deepcopy(model.model_dump(mode="json"))
    copied.update({
        "work_date": target_work_date,
        "shift": shift,
        "captain": None,
        "lieutenant": None,
        "duty_warden": None,
        "alternate_shift_supervisor": None,
        "leave_entries": [],
        "briefing_minutes": "",
        "roll_call_completed": False,
        "uniform_inspection_completed": False,
        "equipment": {key: "not_checked" for key in SECURITY_EQUIPMENT_KEYS},
        "briefing_guests": [],
        "assigned_and_dismissed": False,
        "lieutenant_signature_name": None,
    })
    copied["extra_assignments"] = [
        {"label": assignment.label, "staff": None}
        for assignment in model.extra_assignments
    ]
    return AssignmentRosterV1.model_validate(copied)


def build_uniform_rows_from_roster(
    roster: AssignmentRosterV1 | dict[str, object],
    *,
    roster_record_id: UUID,
    roster_revision_number: int,
) -> UniformInspectionV1:
    """Derive blank, unique inspection rows from roster print order."""
    model = (
        roster
        if isinstance(roster, AssignmentRosterV1)
        else AssignmentRosterV1.model_validate(roster)
    )
    ordered_staff: list[StaffSelection] = []
    seen: set[UUID] = set()

    def add(staff: StaffSelection | None) -> None:
        if staff is not None and staff.staff_id not in seen:
            seen.add(staff.staff_id)
            ordered_staff.append(staff)

    for zone in model.zones:
        add(zone.supervisor)
        for post in zone.posts:
            add(post.initial_staff)
            add(post.rotation_staff)

    rows = [
        {
            "staff": staff.model_dump(mode="json"),
            "shirt": None,
            "pants": None,
            "shoes": None,
            "cap": None,
            "coat": None,
            "id": None,
            "hair": None,
            "nails": None,
            "comments": "",
        }
        for staff in ordered_staff
    ]
    return UniformInspectionV1.model_validate({
        "schema_version": 1,
        "work_date": model.work_date,
        "shift": model.shift,
        "roster_record_id": roster_record_id,
        "roster_revision_number": roster_revision_number,
        "inspector": None,
        "rows": rows,
    })
