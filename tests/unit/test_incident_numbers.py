import pytest

from backend.reports.incident_numbers import (
    normalize_incident_number,
    suggest_incident_name,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-08-029", "2026-08-029"),
        ("202608029", "2026-08-029"),
        (" 2026-08-029 ", "2026-08-029"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_incident_number(raw, expected):
    assert normalize_incident_number(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "2026-13-001",
        "2026-00-001",
        "26-08-001",
        "2026-8-001",
        "2026-08-01",
        "2026-08-1000",
        "2026/08/001",
        "abcdefghi",
    ],
)
def test_rejects_invalid_incident_number(raw):
    with pytest.raises(ValueError, match="YYYY-MM-NNN"):
        normalize_incident_number(raw)


def test_suggest_incident_name_combines_clean_location_and_category():
    assert suggest_incident_name(
        location="  Barracks 4 ",
        category_label=" Fight/Assault ",
    ) == "Barracks 4 Fight/Assault"


def test_suggest_incident_name_uses_whichever_label_is_known():
    assert suggest_incident_name(location="East Hall", category_label=None) == "East Hall"
    assert suggest_incident_name(location=None, category_label="Contraband") == "Contraband"
    assert suggest_incident_name(location="  ", category_label=" ") is None


def test_suggest_incident_name_never_exceeds_storage_limit():
    value = suggest_incident_name(location="L" * 120, category_label="C" * 120)
    assert value is not None
    assert len(value) == 160
