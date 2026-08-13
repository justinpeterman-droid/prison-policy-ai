from backend.identity.rate_limits import consume_limit


def test_rate_limit_state_is_shared_and_contains_only_hash(db_session, identity_fixed_now):
    decisions = [
        consume_limit(
            db_session,
            dimension="employee",
            value="TEST-5001",
            now=identity_fixed_now,
            pepper="p" * 32,
        )
        for _ in range(11)
    ]
    assert all(decision.allowed for decision in decisions[:10])
    assert decisions[10].allowed is False
