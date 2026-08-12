import os
import time

import pytest

from backend.identity.pins import hash_pin, verify_pin


@pytest.mark.skipif(
    os.environ.get("RUN_ARGON2_BENCHMARK") != "1",
    reason="RUN_ARGON2_BENCHMARK is not enabled",
)
def test_argon2_verification_is_below_five_hundred_milliseconds():
    encoded = hash_pin("A7B902")
    started = time.perf_counter()
    assert verify_pin(encoded, "A7B902") is True
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert elapsed_ms < 500
