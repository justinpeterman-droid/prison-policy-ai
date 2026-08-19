"""Pure contracts for checklist-driven incident packet planning."""
import json
from pathlib import Path
from uuid import uuid4

import pytest

from backend.forms.packets import (
    PacketConfigurationError,
    PlannedPacketItem,
    plan_incident_packet,
)


ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "templates" / "incident_checklist_v2.json"
CATALOG_CODES = {
    "form_005_409",
    "cover_letter",
    "chain_of_custody_physical",
    "medical_documentation_checklist",
    "additional_officer_statement",
    "photo_video_attachment",
    "confiscation_f401_physical",
    "field_test_result_attachment",
    "inmate_drug_test_reminder",
    "business_office_receipt_reminder",
    "enemy_alert_form",
    "review_24_hour",
    "review_72_hour",
    "emergency_gate_pass",
    "company_nurse_confirmation",
    "officer_accident_report",
    "forced_cell_movement_fact_sheet",
    "prea_checklist",
    "prea_notification",
}


def _by_key(items: tuple[PlannedPacketItem, ...]):
    return {
        (item.template_code, item.reporting_staff_member_id): item
        for item in items
    }


def test_contraband_plan_is_officer_scoped_and_condition_driven():
    first = uuid4()
    second = uuid4()
    items = plan_incident_packet(
        category="contraband",
        snapshot={
            "extracted_facts": {
                "contraband_is_suspected_drugs": True,
                "contraband_includes_money": False,
            },
            "gap_answers": {
                "photo_video_obtained": "No",
                "medical_disposition": "N/A - no injuries reported",
                "drug_test_disposition": "N/A",
            },
        },
        reporting_staff_ids=(first, second),
        catalog_codes=CATALOG_CODES,
        checklist_path=CHECKLIST,
    )
    by_key = _by_key(items)

    assert ("form_005_409", first) in by_key
    assert ("form_005_409", second) in by_key
    assert ("cover_letter", None) in by_key
    assert ("chain_of_custody_physical", None) in by_key
    assert ("confiscation_f401_physical", None) in by_key
    assert ("field_test_result_attachment", None) in by_key
    assert ("business_office_receipt_reminder", None) not in by_key
    assert ("photo_video_attachment", None) not in by_key
    assert ("medical_documentation_checklist", None) not in by_key
    assert ("inmate_drug_test_reminder", None) not in by_key
    assert all(item.packet_group == "required" for item in items)


def test_unknown_answers_create_removable_recommendations_not_fake_requirements():
    officer = uuid4()
    items = plan_incident_packet(
        category="incident_no_disciplinary",
        snapshot={},
        reporting_staff_ids=(officer,),
        catalog_codes=CATALOG_CODES,
        checklist_path=CHECKLIST,
    )
    by_key = _by_key(items)

    assert by_key[("cover_letter", None)].packet_group == "required"
    assert by_key[("form_005_409", officer)].packet_group == "required"
    assert by_key[("photo_video_attachment", None)].packet_group == "recommended"
    assert by_key[("medical_documentation_checklist", None)].packet_group == "recommended"


def test_external_treatment_and_weapon_facts_activate_required_items():
    officer = uuid4()
    items = plan_incident_packet(
        category="inmate_fight",
        snapshot={
            "extracted_facts": {"weapon_involved": True},
            "gap_answers": {
                "medical_disposition": "Sent by ambulance to outside facility",
                "drug_test_disposition": "Conducted",
                "photo_video_obtained": "Yes",
                "witness_statements_collected": "Yes",
                "enemy_alert_filed": "Yes",
            },
        },
        reporting_staff_ids=(officer,),
        catalog_codes=CATALOG_CODES,
        checklist_path=CHECKLIST,
    )
    by_key = _by_key(items)

    for code in (
        "chain_of_custody_physical",
        "confiscation_f401_physical",
        "medical_documentation_checklist",
        "inmate_drug_test_reminder",
        "photo_video_attachment",
        "additional_officer_statement",
        "enemy_alert_form",
        "review_24_hour",
        "review_72_hour",
        "emergency_gate_pass",
    ):
        assert by_key[(code, None)].packet_group == "required"


def test_report_only_outputs_are_explicitly_excluded_from_form_packet():
    officer = uuid4()
    items = plan_incident_packet(
        category="use_of_force",
        snapshot={
            "gap_answers": {
                "medical_disposition": "N/A - no injuries reported",
                "drug_test_disposition": "N/A",
                "photo_video_obtained": "No",
            }
        },
        reporting_staff_ids=(officer,),
        catalog_codes=CATALOG_CODES,
        checklist_path=CHECKLIST,
    )

    assert all(item.template_code != "major_disciplinary_form" for item in items)
    assert all(item.template_code != "use_of_force_report_409" for item in items)
    assert sum(item.template_code == "form_005_409" for item in items) == 1


def test_unknown_checklist_requirement_fails_closed(tmp_path):
    checklist = {
        "categories": [{
            "name": "fictional_category",
            "label": "Fictional Category",
            "forms_required": ["unknown_official_form"],
        }]
    }
    path = tmp_path / "checklist.json"
    path.write_text(json.dumps(checklist), encoding="utf-8")

    with pytest.raises(PacketConfigurationError, match="unknown checklist requirement"):
        plan_incident_packet(
            category="fictional_category",
            snapshot={},
            reporting_staff_ids=(uuid4(),),
            catalog_codes=CATALOG_CODES,
            checklist_path=path,
        )


def test_missing_catalog_template_fails_before_any_packet_write():
    with pytest.raises(PacketConfigurationError, match="missing active catalog template"):
        plan_incident_packet(
            category="incident_no_disciplinary",
            snapshot={},
            reporting_staff_ids=(uuid4(),),
            catalog_codes={"cover_letter"},
            checklist_path=CHECKLIST,
        )
