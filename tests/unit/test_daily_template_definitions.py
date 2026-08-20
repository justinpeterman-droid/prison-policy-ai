import json

import pytest

from backend.paperwork.daily_templates import (
    DAILY_TEMPLATE_FILES,
    DAILY_TEMPLATE_DIR,
    DailyPaperworkKind,
    load_all_daily_templates,
    load_daily_template,
)


EXPECTED_KINDS = {
    "assignment_roster",
    "uniform_inspection",
    "metal_detector_test",
    "perimeter_check",
    "random_search_log",
    "detector_sign_out",
}
EXPECTED_ROOT_KEYS = {
    "kind",
    "title",
    "schema_version",
    "print_orientation",
    "definition",
}


def test_daily_template_files_are_complete_and_sanitized():
    assert {kind.value for kind in DailyPaperworkKind} == EXPECTED_KINDS
    assert set(DAILY_TEMPLATE_FILES) == set(DailyPaperworkKind)

    for kind, filename in DAILY_TEMPLATE_FILES.items():
        path = DAILY_TEMPLATE_DIR / filename
        raw = json.loads(path.read_text(encoding="utf-8"))

        assert set(raw) == EXPECTED_ROOT_KEYS
        assert raw["kind"] == kind.value
        assert raw["schema_version"] == 1
        assert raw["print_orientation"] in {"portrait", "landscape"}

        serialized = json.dumps(raw, ensure_ascii=False)
        assert "<script" not in serialized.lower()
        assert "ADC#" not in serialized.upper()

        loaded = load_daily_template(kind)
        assert loaded.kind is kind
        assert loaded.schema_version == 1
        assert loaded.title == raw["title"]


def test_load_all_daily_templates_uses_stable_product_order():
    assert [item.kind for item in load_all_daily_templates()] == list(DailyPaperworkKind)


def test_assignment_roster_preserves_zone_and_post_order():
    definition = load_daily_template("assignment_roster").definition
    zones = definition["zones"]

    assert [zone["code"] for zone in zones] == [
        "zone_1",
        "zone_2",
        "zone_3",
        "zone_4",
        "zone_5",
    ]
    assert [post["code"] for post in zones[0]["posts"]] == [
        "bks_8_control",
        "bks_9_10_control",
        "bks_9_10_desk",
        "bks_11_12_control",
        "bks_13_14_control",
        "south_tower",
        "east_tower",
        "south_hall_rover",
    ]
    assert zones[4]["posts"] == [
        {"code": "boiler_room", "label": "Boiler Room", "priority": "P1"}
    ]

    assert definition["assignment_columns"] == ["Initial Officer", "Rotation Officer"]
    assert definition["notes"] == [
        "NOA = No Officer Available",
        "CGPS = Cross Gender Pat Searches",
    ]
    assert definition["distribution"] == [
        "Assistant Warden",
        "Major",
        "Building Captain",
        "Control Center",
        "Human Resources",
        "Training Officer",
        "Shift Supervisor",
        "File",
    ]


def test_remaining_controlled_values_match_approved_structure():
    uniform = load_daily_template("uniform_inspection").definition
    assert uniform["columns"] == [
        "shirt",
        "pants",
        "shoes",
        "cap",
        "coat",
        "id",
        "hair",
        "nails",
    ]
    assert uniform["values"] == ["S", "N/I", "U", "NONE"]

    metal = load_daily_template("metal_detector_test").definition
    assert metal["detectors"] == [str(value) for value in range(1, 12)]
    assert metal["positions"] == [
        "Inner left leg, pointing down",
        "Centered on front of body, pointing down",
        "Left side of body, pointing down",
        "Center of back, pointing down",
        "Center of back, pointing left",
        "Under left arm, pointing down",
        "Centered on top of head, pointing forward",
    ]
    assert metal["values"] == ["P", "F"]
    assert metal["runtime_detector_fields"] == {
        "location": "",
        "equipment_identifier": "",
    }

    searches = load_daily_template("random_search_log").definition
    assert searches["sections"] == ["North 1", "North 2", "South 1", "South 2"]
    assert searches["blocks_per_section"] == 4
    assert searches["fields"] == [
        "officer_staff_id",
        "date",
        "time",
        "individual_last_name",
        "individual_number",
        "barracks_rack",
        "contraband_disposition",
    ]

    signout = load_daily_template("detector_sign_out").definition
    assert signout["units"] == [f"D{value}" for value in range(1, 10)]
    assert signout["fields"] == [
        "staff_id",
        "area_of_assignment",
        "shift_supervisor_staff_id",
        "date",
    ]


def test_perimeter_template_preserves_full_grouped_location_order():
    perimeter = load_daily_template("perimeter_check").definition
    groups = perimeter["groups"]

    assert [group["code"] for group in groups] == [
        "doors",
        "outside_doors",
        "fence_gates",
    ]
    assert [len(group["items"]) for group in groups] == [25, 19, 21]

    assert [item["label"] for item in groups[0]["items"]][-2:] == [
        "Senstar Test",
        "Pipe Chases",
    ]
    assert [item["label"] for item in groups[1]["items"]][-2:] == [
        "Manholes",
        "Metal Detector",
    ]
    assert [item["label"] for item in groups[2]["items"]][-2:] == [
        "Sally Port Inner Fence Gate",
        "Fence And Alleyways",
    ]
    assert perimeter["sign_off_fields"] == [
        "Perimeter Inspected by",
        "Signature",
        "Date / Time",
        "Senstar Inspected by",
        "Shift Supervisor's Signature",
        "Date / Time",
    ]


@pytest.mark.parametrize("kind", list(DailyPaperworkKind))
def test_template_definitions_have_unique_codes(kind):
    definition = load_daily_template(kind).definition
    codes = []

    def collect(value):
        if isinstance(value, dict):
            if "code" in value:
                codes.append(value["code"])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(definition)
    assert len(codes) == len(set(codes))
