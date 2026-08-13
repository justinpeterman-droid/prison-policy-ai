from datetime import UTC, datetime

from backend.identity.rate_limits import consume_limit, subject_hash


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


class Row:
    def __init__(self, count, window):
        self.hit_count = count
        self.window_started_at = window


class Result:
    def __init__(self, row):
        self.row = row

    def one(self):
        return self.row


class Session:
    def __init__(self, row):
        self.row = row
        self.parameters = None

    def execute(self, _statement, parameters):
        self.parameters = parameters
        return Result(self.row)


def test_subject_hash_is_dimension_and_value_specific():
    pepper = "p" * 32
    assert subject_hash("employee", "EMP-1001", pepper) != subject_hash(
        "employee", "EMP-1002", pepper
    )
    assert subject_hash("employee", "EMP-1001", pepper) != subject_hash(
        "device", "EMP-1001", pepper
    )


def test_limit_decision_uses_persisted_count_without_raw_subject():
    session = Session(Row(11, NOW))
    decision = consume_limit(
        session, dimension="employee", value="EMP-1001", now=NOW, pepper="p" * 32
    )
    assert decision.allowed is False
    assert decision.retry_after_seconds == 900
    assert session.parameters["subject_hash"] != b"EMP-1001"
    assert "EMP-1001" not in repr(session.parameters)
