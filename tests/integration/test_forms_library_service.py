from datetime import UTC, datetime

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.library import FormsLibraryFilters, list_forms_library


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

    page = list_forms_library(
        db_session,
        filters=FormsLibraryFilters(),
        limit=50,
    )

    assert page.items
    by_code = {item.code: item for item in page.items}
    digital = by_code["form_005_409"]
    physical = by_code["chain_of_custody_physical"]

    assert digital.output_kind == "digital_document"
    assert digital.actions.preview is True
    assert digital.actions.print is True
    assert digital.actions.physical_guidance is False
    assert "template_path" not in repr(digital)

    assert physical.output_kind == "physical_only"
    assert physical.actions.preview is False
    assert physical.actions.print is False
    assert physical.actions.download_word is False
    assert physical.actions.download_pdf is False
    assert physical.actions.physical_guidance is True
    assert physical.obtain_from


def test_forms_library_search_and_filters_are_case_insensitive(db_session):
    _catalog(db_session)

    searched = list_forms_library(
        db_session,
        filters=FormsLibraryFilters(q="CHAIN OF CUSTODY"),
        limit=20,
    )
    assert [item.code for item in searched.items] == [
        "chain_of_custody_physical"
    ]

    physical = list_forms_library(
        db_session,
        filters=FormsLibraryFilters(output_kind="physical_only"),
        limit=50,
    )
    assert physical.items
    assert all(item.output_kind == "physical_only" for item in physical.items)

    incident_forms = list_forms_library(
        db_session,
        filters=FormsLibraryFilters(category="incident_forms"),
        limit=50,
    )
    assert incident_forms.items
    assert all(item.category == "incident_forms" for item in incident_forms.items)


def test_forms_library_keyset_pagination_is_stable(db_session):
    _catalog(db_session)

    first = list_forms_library(
        db_session,
        filters=FormsLibraryFilters(),
        limit=3,
    )
    assert len(first.items) == 3
    assert first.next_cursor is not None

    second = list_forms_library(
        db_session,
        filters=FormsLibraryFilters(),
        limit=3,
        cursor=first.next_cursor,
    )
    assert {item.code for item in first.items}.isdisjoint(
        item.code for item in second.items
    )
