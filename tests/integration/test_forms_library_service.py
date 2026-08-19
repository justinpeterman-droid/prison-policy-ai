from datetime import UTC, datetime

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.library import search_form_library


def _catalog(db_session):
    definitions = load_form_catalog("templates/paperwork/catalog.json")
    sync_form_catalog(
        db_session,
        definitions,
        now=datetime(2026, 8, 19, 13, tzinfo=UTC),
    )
    db_session.flush()


def test_forms_library_returns_sanitized_active_catalog_entries(db_session):
    _catalog(db_session)

    page = search_form_library(db_session, limit=50)

    assert page.items
    by_code = {item.code: item for item in page.items}
    digital = by_code["form_005_409"]
    physical = by_code["chain_of_custody_physical"]

    assert digital.output_kind == "digital_document"
    assert "preview" in digital.capabilities
    assert "print" in digital.capabilities
    assert "physical_guidance" not in digital.capabilities
    assert "template_path" not in repr({
        "template_id": digital.template_id,
        "code": digital.code,
        "name": digital.name,
        "category": digital.category,
        "purpose": digital.purpose,
        "when_used": digital.when_used,
        "output_kind": digital.output_kind,
        "revision_label": digital.revision_label,
        "capabilities": digital.capabilities,
        "frequent": digital.frequent,
        "obtain_from": digital.obtain_from,
    })

    assert physical.output_kind == "physical_only"
    assert "preview" not in physical.capabilities
    assert "print" not in physical.capabilities
    assert "download_word" not in physical.capabilities
    assert "download_pdf" not in physical.capabilities
    assert "physical_guidance" in physical.capabilities
    assert physical.obtain_from


def test_forms_library_search_and_category_filter_are_case_insensitive(db_session):
    _catalog(db_session)

    searched = search_form_library(
        db_session,
        q="CHAIN OF CUSTODY",
        limit=20,
    )
    assert [item.code for item in searched.items] == [
        "chain_of_custody_physical"
    ]

    incident_forms = search_form_library(
        db_session,
        category="INCIDENT",
        limit=50,
    )
    assert incident_forms.items
    assert all(item.category == "incident" for item in incident_forms.items)


def test_forms_library_offset_pagination_is_stable(db_session):
    _catalog(db_session)

    first = search_form_library(db_session, limit=3, offset=0)
    assert len(first.items) == 3
    assert first.next_offset == 3

    second = search_form_library(
        db_session,
        limit=3,
        offset=first.next_offset,
    )
    assert {item.code for item in first.items}.isdisjoint(
        item.code for item in second.items
    )
