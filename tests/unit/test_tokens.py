import pytest

from backend.identity.tokens import hash_device_id, hash_token, issue_credential


def test_opaque_credential_has_256_bits_and_only_hash_is_persistable():
    credential = issue_credential()
    assert len(credential.raw) >= 43
    assert len(credential.digest) == 32
    assert credential.digest == hash_token(credential.raw)
    assert credential.raw.encode("utf-8") != credential.digest


def test_credentials_are_random_and_device_hash_is_peppered():
    first, second = issue_credential(), issue_credential()
    assert first.raw != second.raw
    assert first.digest != second.digest
    assert hash_device_id("device-fictional-0001", "p" * 32) != hash_device_id("device-fictional-0001", "q" * 32)


@pytest.mark.parametrize("device_id", ["short", "x" * 257, " leading-device-0001", "device-0001\nmarker"])
def test_device_id_validation_is_exact_and_bounded(device_id):
    with pytest.raises(ValueError, match="device id is invalid"):
        hash_device_id(device_id, "p" * 32)
