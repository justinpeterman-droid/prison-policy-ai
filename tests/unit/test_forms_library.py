from types import SimpleNamespace
from uuid import uuid4

from backend.forms.library import (
    filter_form_library,
    form_library_item,
    plan_form_selection,
)


def _template(
    *,
    code="fictional_form",
    name="Fictional Form",
    category="incident",
    output_kind="digital_document",
    active=True,
    render_kind="browser_form",
    download_formats=None,
):
    definition = {
        "description": f"Purpose for {name}.",
        "render_kind": render_kind,
        "download_formats": download_formats or ["print", "pdf"],
        "required_fields": [],
        "review_fields": [],
        "optional_fields": [],
    } if output_kind == "digital_document" else {
        "description": f"Purpose for {name}.",
        "obtain_from": "approved paperwork location",
        "guidance_fields": ["incident_number"],
    }
    return SimpleNamespace(
        id=uuid4(),
        code=code,
        name=name,
        category=category,
        output_kind=output_kind,
        revision_label="fictional-v1",
        active=active,
        definition=definition,
    )


def test_digital_library_item_exposes_only_supported_capabilities():
    item = form_library_item(_template(
        code="medical_documentation_checklist",
        name="Medical Documentation Checklist",
        category="medical",
        download_formats=["print", "pdf"],
    ))

    assert item.purpose == "Purpose for Medical Documentation Checklist."
    assert "medical" in item.when_used.lower()
    assert item.capabilities == frozenset({
        "preview",
        "print",
        "download_pdf",
        "fillable",
        "blank",
        "attach_to_incident",
    })
    assert item.frequent is True
    assert item.revision_label == "fictional-v1"


def test_physical_only_item_has_guidance_and_no_digital_substitute_actions():
    item = form_library_item(_template(
        code="chain_of_custody_physical",
        name="Chain of Custody Form",
        category="evidence",
        output_kind="physical_only",
    ))

    assert item.capabilities == frozenset({
        "physical_guidance",
        "attach_to_incident",
    })
    assert "preview" not in item.capabilities
    assert "print" not in item.capabilities
    assert "download_pdf" not in item.capabilities
    assert "download_word" not in item.capabilities
    assert item.obtain_from == "approved paperwork location"


def test_officer_scoped_005_cannot_be_added_as_one_incident_wide_form():
    item = form_library_item(_template(
        code="form_005_409",
        name="005/409 Incident Report",
        render_kind="docx_template",
        download_formats=["print", "word", "pdf"],
    ))

    assert "attach_to_incident" not in item.capabilities
    assert {"preview", "print", "download_word", "download_pdf"} <= item.capabilities


def test_filtering_is_active_only_case_insensitive_and_frequent_first():
    regular = form_library_item(_template(
        code="regular_form",
        name="Regular Incident Form",
    ))
    frequent = form_library_item(_template(
        code="cover_letter",
        name="Incident Cover Letter",
    ))
    medical = form_library_item(_template(
        code="medical_documentation_checklist",
        name="Medical Documentation Checklist",
        category="medical",
    ))

    page = filter_form_library(
        [regular, medical, frequent],
        q="incident",
        category=None,
        limit=10,
        offset=0,
    )
    assert [item.code for item in page.items] == ["cover_letter", "regular_form"]

    category_page = filter_form_library(
        [regular, medical, frequent],
        q=None,
        category="medical",
        limit=10,
        offset=0,
    )
    assert [item.code for item in category_page.items] == [
        "medical_documentation_checklist"
    ]


def test_selection_preserves_order_and_separates_physical_guidance():
    digital = form_library_item(_template(
        code="cover_letter",
        name="Incident Cover Letter",
    ))
    physical = form_library_item(_template(
        code="chain_of_custody_physical",
        name="Chain of Custody Form",
        output_kind="physical_only",
    ))

    plan = plan_form_selection([physical, digital])

    assert [item.code for item in plan.items] == [
        "chain_of_custody_physical",
        "cover_letter",
    ]
    assert [item.code for item in plan.digital_items] == ["cover_letter"]
    assert [item.code for item in plan.physical_items] == [
        "chain_of_custody_physical"
    ]
