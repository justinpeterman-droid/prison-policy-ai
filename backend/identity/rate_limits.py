from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import math

from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.persistence.models.security import AuthRateLimit


LIMITS = {"employee": 10, "device": 30, "network": 200}
WINDOW_SECONDS = 15 * 60


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


def subject_hash(dimension: str, value: str, pepper: str) -> bytes:
    if dimension not in LIMITS or not isinstance(value, str) or not value or not pepper:
        raise ValueError("rate limit subject is invalid")
    message = f"{dimension}:{value}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), message, hashlib.sha256).digest()


def consume_limit(
    session: Session,
    *,
    dimension: str,
    value: str,
    now: datetime,
    pepper: str,
    limit: int | None = None,
) -> RateLimitDecision:
    maximum = LIMITS[dimension] if limit is None else limit
    digest = subject_hash(dimension, value, pepper)
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)
    insert_statement = insert(AuthRateLimit).values(
        dimension=dimension,
        subject_hash=digest,
        window_started_at=now,
        hit_count=1,
        updated_at=now,
    )
    statement = insert_statement.on_conflict_do_update(
        constraint="uq_auth_rate_limit_dimension_subject",
        set_={
            "window_started_at": case(
                (AuthRateLimit.window_started_at <= cutoff, now),
                else_=AuthRateLimit.window_started_at,
            ),
            "hit_count": case(
                (AuthRateLimit.window_started_at <= cutoff, 1),
                else_=AuthRateLimit.hit_count + 1,
            ),
            "updated_at": now,
        },
    ).returning(AuthRateLimit.hit_count, AuthRateLimit.window_started_at)
    row = session.execute(
        statement,
        {
            "dimension": dimension,
            "subject_hash": digest,
        },
    ).one()
    allowed = row.hit_count <= maximum
    retry = (
        0
        if allowed
        else max(
            1,
            math.ceil(
                (
                    row.window_started_at + timedelta(seconds=WINDOW_SECONDS) - now
                ).total_seconds()
            ),
        )
    )
    return RateLimitDecision(allowed, retry)
