from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from backend.reports.admin_incidents import AdminIncidentFilters


def test_admin_incident_filters_accept_structured_search_fields():
    filters = AdminIncidentFilters(
        q="2026-08-029",
        incident_number="2026-08-029",
        reporting_staff_id=UUID("00000000-0000-4000-8000-000000000101"),
        prepared_by_staff_id=UUID("00000000-0000-4000-8000-000000000102"),
        incident_date_from=date(2026, 8, 1),
        incident_date_to=date(2026, 8, 31),
        created_at_from=datetime(2026, 8, 1, tzinfo=UTC),
        created_at_to=datetime(2026, 8, 31, 23, 59, tzinfo=UTC),
        category="fight",
        facility="North Central Unit",
        location="Barracks 4",
        shift="A",
        records_status="in_progress",
        last_editor_staff_id=UUID("00000000-0000-4000-8000-000000000103"),
        updated_at_from=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at_to=datetime(2026, 8, 31, 23, 59, tzinfo=UTC),
    )

    filters.validate()


def test_admin_incident_filters_reject_invalid_ranges_and_records_status():
    with pytest.raises(ValueError, match="records status"):
        AdminIncidentFilters(records_status="ready_to_review").validate()

    with pytest.raises(ValueError, match="date range"):
        AdminIncidentFilters(
            incident_date_from=date(2026, 8, 20),
            incident_date_to=date(2026, 8, 19),
        ).validate()

    with pytest.raises(ValueError, match="updated range"):
        AdminIncidentFilters(
            updated_at_from=datetime(2026, 8, 20, tzinfo=UTC),
            updated_at_to=datetime(2026, 8, 19, tzinfo=UTC),
        ).validate()
