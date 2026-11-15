"""Never re-execute an accepted request ID, including after process failure."""
import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .auth import CurrentUser, DB
from .models import AIRequest, Session as TalkSession

router = APIRouter(prefix="/requests")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def claim(db: Session, user_id: int, request_id: UUID, kind: str, inputs: dict) -> tuple[int, list[dict] | None]:
    """The new claim and session reservation must be committed in one transaction."""
    session_id = inputs.get("session_id")
    if session_id is not None:
        # Lock order matches session deletion and turn commits: session before request.
        owned = db.scalar(select(TalkSession.id).where(
            TalkSession.id == session_id, TalkSession.user_id == user_id,
        ).with_for_update())
        if owned is None:
            db.rollback()
            raise HTTPException(404, "Session not found")
    fingerprint = sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    statement = insert(AIRequest).values(
        user_id=user_id, session_id=session_id, request_id=str(request_id), kind=kind, fingerprint=fingerprint,
        status="running", events_json="[]", created_at=utcnow(), deadline=utcnow() + timedelta(minutes=4),
    ).on_conflict_do_nothing(index_elements=[AIRequest.user_id, AIRequest.request_id]).returning(AIRequest.id)
    record_id = db.execute(statement).scalar_one_or_none()
    if record_id is not None:
        return record_id, None
    existing = db.scalar(select(AIRequest).where(AIRequest.user_id == user_id, AIRequest.request_id == str(request_id)))
    if existing.kind != kind or existing.fingerprint != fingerprint:
        db.rollback()
        raise HTTPException(409, "request_conflict")
    record_id = existing.id
    db.rollback()
    expire(db, record_id)
    existing = db.get(AIRequest, record_id)
    if existing.status == "running":
        db.rollback()
        raise HTTPException(409, "request_processing", headers={"Retry-After": "2"})
    events = json.loads(existing.events_json)
    db.rollback()
    return record_id, events


def record_events(db: Session, record_id: int, events: list[dict], terminal: bool = False) -> list[dict]:
    """Fence late workers and store result events in the same transaction as domain writes."""
    row = db.execute(update(AIRequest).where(
        AIRequest.id == record_id, AIRequest.status == "running", AIRequest.deadline > utcnow(),
    ).values(status="running").returning(AIRequest.request_id, AIRequest.events_json, AIRequest.kind)).one_or_none()
    if row is None:
        db.rollback()
        raise HTTPException(409, "request_expired")
    saved = json.loads(row.events_json)
    additions = [{**event, "request_id": row.request_id} for event in events]
    saved.extend(additions)
    values = {"events_json": json.dumps(saved, ensure_ascii=False)}
    if terminal:
        values["status"] = "failed" if any(event["type"] == "error" for event in saved) else "completed"
    db.execute(update(AIRequest).where(AIRequest.id == record_id).values(**values))
    return additions


def persist_events(db: Session, record_id: int, events: list[dict], terminal: bool = False) -> list[dict]:
    result = record_events(db, record_id, events, terminal)
    db.commit()
    return result


def interrupt(db: Session, record_id: int, code: str = "request_interrupted", expired_only: bool = False) -> None:
    db.rollback()
    conditions = [AIRequest.id == record_id, AIRequest.status == "running"]
    if expired_only:
        conditions.append(AIRequest.deadline <= utcnow())
    row = db.execute(update(AIRequest).where(*conditions).values(status="failed").returning(
        AIRequest.request_id, AIRequest.events_json,
    )).one_or_none()
    if row is not None:
        events = json.loads(row.events_json)
        events.append({"type": "error", "code": code, "request_id": row.request_id})
        db.execute(update(AIRequest).where(AIRequest.id == record_id).values(events_json=json.dumps(events, ensure_ascii=False)))
    db.commit()


def expire(db: Session, record_id: int) -> None:
    interrupt(db, record_id, "request_expired", expired_only=True)


def replay_events(events: list[dict]):
    for event in events:
        if event["type"] == "done":
            yield {"type": "token", "text": event["text"], "request_id": event["request_id"], "replayed": True}
        yield {**event, "replayed": True}


class RequestView(BaseModel):
    request_id: UUID
    kind: Literal["chat", "audio"]
    status: Literal["running", "completed", "failed"]
    created_at: datetime
    deadline: datetime
    events: list[dict]


@router.get("/{request_id}")
def request_status(request_id: UUID, user: CurrentUser, db: DB) -> RequestView:
    record_id = db.scalar(select(AIRequest.id).where(AIRequest.user_id == user.id, AIRequest.request_id == str(request_id)))
    if record_id is None:
        raise HTTPException(404, "Request not found")
    expire(db, record_id)
    row = db.get(AIRequest, record_id)
    return RequestView(
        request_id=row.request_id, kind=row.kind, status=row.status,
        created_at=row.created_at.replace(tzinfo=timezone.utc), deadline=row.deadline.replace(tzinfo=timezone.utc),
        events=json.loads(row.events_json),
    )
