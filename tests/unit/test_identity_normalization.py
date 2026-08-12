import pytest

from backend.identity.normalization import normalize_device_label, normalize_employee_number


def test_employee_number_is_trimmed_and_uppercase():
    assert normalize_employee_number("  emp-001  ") == "EMP-001"


def test_empty_employee_number_is_rejected():
    with pytest.raises(ValueError, match="employee number is required"):
        normalize_employee_number("   ")


def test_invalid_employee_number_is_rejected():
    with pytest.raises(ValueError, match="employee number is invalid"):
        normalize_employee_number("employee 001")


def test_device_label_is_bounded_and_single_line():
    assert normalize_device_label("  Intake\nDesk  ") == "Intake Desk"
    assert len(normalize_device_label("x" * 300)) == 120
