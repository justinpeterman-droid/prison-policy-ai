import re
import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

from backend.identity.errors import PinPolicyError
from backend.identity.normalization import normalize_employee_number


ALPHABET = string.ascii_uppercase + string.digits
SEQUENCES = (string.digits, string.ascii_uppercase)
HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def normalize_pin(value: str) -> str:
    pin = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9]{4,8}", pin):
        raise PinPolicyError("PIN must contain 4 through 8 ASCII letters or digits")
    return pin.upper()


def _is_obvious(pin: str) -> bool:
    if len(set(pin)) == 1:
        return True
    return any(pin in sequence or pin in sequence[::-1] for sequence in SEQUENCES)


def validate_new_pin(pin: str, employee_number: str) -> str:
    normalized = normalize_pin(pin)
    if normalized == normalize_employee_number(employee_number):
        raise PinPolicyError("PIN cannot equal the employee number")
    if _is_obvious(normalized):
        raise PinPolicyError("PIN is too easy to guess")
    return normalized


def hash_pin(pin: str) -> str:
    return HASHER.hash(normalize_pin(pin))


def verify_pin(encoded_hash: str, pin: str) -> bool:
    try:
        return HASHER.verify(encoded_hash, normalize_pin(pin))
    except (InvalidHashError, PinPolicyError, VerifyMismatchError):
        return False


def needs_rehash(encoded_hash: str) -> bool:
    try:
        return HASHER.check_needs_rehash(encoded_hash)
    except InvalidHashError:
        return True


def generate_temporary_pin(employee_number: str) -> str:
    while True:
        candidate = "".join(secrets.choice(ALPHABET) for _ in range(8))
        try:
            return validate_new_pin(candidate, employee_number)
        except PinPolicyError:
            continue
