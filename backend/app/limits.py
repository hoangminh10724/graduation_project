"""Database-backed limits shared by all API workers."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .models import RateLimit


def enforce_limit(db: Session, scope: str, identity: str, maximum: int) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window = now.replace(second=0, microsecond=0)
    key = f"{scope}:{sha256(identity.encode()).hexdigest()}:{window:%Y%m%d%H%M}"
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    statement = insert(RateLimit).values(key=key, window_start=window, hits=1)
    statement = statement.on_conflict_do_update(
        index_elements=[RateLimit.key], set_={"hits": RateLimit.hits + 1},
        where=RateLimit.hits < maximum,
    ).returning(RateLimit.hits)
    try:
        accepted = db.execute(statement).scalar_one_or_none()
        db.execute(delete(RateLimit).where(RateLimit.window_start < window - timedelta(minutes=2)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if accepted is None:
        retry_after = 60 - now.second
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(retry_after)})


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
