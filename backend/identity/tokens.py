from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets


DEVICE_ID_PATTERN = re.compile(r"^[\x21-\x7E]{16,256}$")


@dataclass(frozen=True)
class OpaqueCredential:
    raw: str
    digest: bytes


def hash_token(raw: str) -> bytes:
    if not isinstance(raw, str) or not raw:
        raise ValueError("token is invalid")
    return hashlib.sha256(raw.encode("utf-8")).digest()


def issue_credential() -> OpaqueCredential:
    raw = secrets.token_urlsafe(32)
    return OpaqueCredential(raw=raw, digest=hash_token(raw))


def hash_device_id(device_id: str, pepper: str) -> bytes:
    if not isinstance(device_id, str) or not DEVICE_ID_PATTERN.fullmatch(device_id):
        raise ValueError("device id is invalid")
    if not isinstance(pepper, str) or not pepper:
        raise ValueError("device hash pepper is unavailable")
    return hmac.new(pepper.encode("utf-8"), device_id.encode("utf-8"), hashlib.sha256).digest()
