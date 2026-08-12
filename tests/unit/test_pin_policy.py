import pytest

from backend.identity.pins import (
    PinPolicyError,
    generate_temporary_pin,
    hash_pin,
    needs_rehash,
    normalize_pin,
    validate_new_pin,
    verify_pin,
)


@pytest.mark.parametrize("raw,expected", [("001a", "001A"), ("aBcD12", "ABCD12")])
def test_pin_normalization_preserves_leading_zeroes(raw, expected):
    assert normalize_pin(raw) == expected


@pytest.mark.parametrize("pin", ["0000", "1111", "1234", "4321", "ABCD", "DCBA"])
def test_obvious_pins_are_rejected(pin):
    with pytest.raises(PinPolicyError, match="PIN is too easy to guess"):
        validate_new_pin(pin, employee_number="EMP-9001")


def test_pin_equal_to_employee_number_is_rejected_case_insensitively():
    with pytest.raises(PinPolicyError, match="employee number"):
        validate_new_pin("ab12", employee_number=" AB12 ")


@pytest.mark.parametrize("pin", ["abc", "123456789", "12-4", "A B4", "åBCD"])
def test_pin_character_and_length_rules(pin):
    with pytest.raises(PinPolicyError, match="4 through 8 ASCII"):
        normalize_pin(pin)


def test_argon2_hash_uses_required_parameters_and_verifies():
    first = hash_pin("A7b902")
    second = hash_pin("A7b902")
    assert "$argon2id$v=19$m=65536,t=3,p=1$" in first
    assert first != second
    assert verify_pin(first, "a7B902") is True
    assert verify_pin(first, "WRONG1") is False
    assert needs_rehash(first) is False


def test_temporary_pin_is_eight_characters_and_policy_valid():
    pin = generate_temporary_pin("EMP-9001")
    assert len(pin) == 8
    assert validate_new_pin(pin, "EMP-9001") == pin
